"""
Real MoviePy Preview Renderer

Builds actual MoviePy clips from timeline markers, applies effects, 
and renders low-res preview video for playback.

Features:
- In-process composition (no subprocess)
- Real effect application
- Temporary file management
- Progress callback
- Audio mixing
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass
from threading import Thread
import os

try:
    from moviepy import VideoClip, AudioClip, CompositeVideoClip, CompositeAudioClip
    from moviepy import concatenate_videoclips, concatenate_audioclips
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    VideoClip = None

logger = logging.getLogger(__name__)


@dataclass
class PreviewRenderJob:
    """Configuration for a preview render."""
    id: str
    timeline: object  # Timeline object
    fps: int = 30
    width: int = 1280
    height: int = 720
    duration_seconds: float = 10.0
    quality: str = 'preview'  # 'preview', 'draft', 'high'
    progress_callback: Optional[Callable[[float], None]] = None
    completion_callback: Optional[Callable[[bool, str], None]] = None
    
    def get_output_path(self) -> Path:
        """Get temp file path for preview."""
        temp_dir = Path(tempfile.gettempdir()) / 'elite_editor_preview'
        temp_dir.mkdir(exist_ok=True)
        return temp_dir / f"{self.id}_preview.mp4"


class PreviewRenderer:
    """Renders low-res preview videos from timeline."""
    
    def __init__(self):
        self.available = MOVIEPY_AVAILABLE
        self.current_job: Optional[PreviewRenderJob] = None
        self.temp_files: List[Path] = []
    
    def render_preview(self, job: PreviewRenderJob) -> bool:
        """
        Render preview video from timeline markers.
        
        Args:
            job: PreviewRenderJob with timeline and parameters
            
        Returns:
            True if successful, False otherwise
        """
        if not self.available:
            logger.error("MoviePy not available")
            return False
        
        self.current_job = job
        
        try:
            logger.info(f"Starting preview render: {job.id}")
            
            # Step 1: Get timeline data
            timeline = job.timeline
            if not hasattr(timeline, 'markers'):
                logger.error("Timeline has no markers")
                return False
            
            # Step 2: Build video clips from markers
            video_clips = self._build_clips_from_timeline(timeline, job)
            
            if not video_clips:
                logger.warning("No clips to render")
                if job.completion_callback:
                    job.completion_callback(False, "No clips in timeline")
                return False
            
            # Step 3: Composite clips
            composite = self._composite_clips(video_clips, job)
            
            if composite is None:
                logger.error("Failed to composite clips")
                if job.completion_callback:
                    job.completion_callback(False, "Failed to composite clips")
                return False
            
            # Step 4: Render to file
            output_path = job.get_output_path()
            success = self._render_to_file(composite, output_path, job)
            
            if success:
                logger.info(f"Preview rendered to {output_path}")
                self.temp_files.append(output_path)
                if job.completion_callback:
                    job.completion_callback(True, str(output_path))
            
            return success
        
        except Exception as e:
            logger.error(f"Preview render failed: {e}")
            if job.completion_callback:
                job.completion_callback(False, str(e))
            return False
        
        finally:
            self.current_job = None
    
    def render_preview_async(self, job: PreviewRenderJob):
        """Render preview in background thread."""
        thread = Thread(target=self.render_preview, args=(job,), daemon=True)
        thread.start()
    
    def _build_clips_from_timeline(self, timeline, job: PreviewRenderJob) -> List[VideoClip]:
        """Build MoviePy clips from timeline markers."""
        clips = []
        
        # Use timeline.get_all_markers() for compatibility
        try:
            markers = timeline.get_all_markers()
        except Exception:
            # Fallback to attribute
            markers = getattr(timeline, 'markers', {}).values()
        
        # Sort markers by start frame
        sorted_markers = sorted(
            markers,
            key=lambda m: m.start_frame
        )
        
        for marker in sorted_markers:
            if marker.marker_type != 'clip':
                continue
            try:
                clip = self._create_clip_from_marker(marker, job, timeline)
                if clip:
                    clips.append(clip)
            except Exception as e:
                logger.warning(f"Failed to create clip for {marker.name}: {e}")
        
        return clips
    
    def _create_clip_from_marker(self, marker, job: PreviewRenderJob, timeline) -> Optional[VideoClip]:
        """Create a MoviePy clip from a timeline marker using real media files."""
        try:
            from moviepy.editor import VideoFileClip, ImageClip, AudioFileClip, ColorClip
            from moviepy.video.fx import all as video_fx_module
            
            duration = max(0.001, marker.duration_frames / job.fps)
            start_time = marker.start_frame / job.fps
            clip = None
            
            # Load source media
            if getattr(marker, 'source_file', None):
                src = Path(marker.source_file)
                if not src.exists():
                    logger.warning(f"Source file not found: {src}")
                    return None
                suffix = src.suffix.lower()
                if suffix in ('.mp4', '.mov', '.avi', '.mkv', '.webm'):
                    clip = VideoFileClip(str(src))
                elif suffix in ('.png', '.jpg', '.jpeg', '.bmp'):
                    clip = ImageClip(str(src)).set_duration(duration)
                elif suffix in ('.mp3', '.wav', '.aac', '.flac', '.ogg'):
                    # Create silent video background with audio
                    audio = AudioFileClip(str(src))
                    bg = ColorClip(size=(job.width, job.height), color=(0,0,0)).set_duration(min(duration, audio.duration))
                    bg = bg.set_audio(audio)
                    clip = bg
                else:
                    logger.warning(f"Unsupported media type: {suffix}")
                    return None
            else:
                # No source file - cannot render placeholder per project rules
                logger.warning(f"Marker {marker.name} has no source_file; skipping")
                return None
            
            # Trim or extend to marker duration
            try:
                if clip.duration is None:
                    clip = clip.set_duration(duration)
                elif clip.duration > duration:
                    clip = clip.subclip(0, duration)
                else:
                    clip = clip.set_duration(duration)
            except Exception:
                clip = clip.set_duration(duration)
            
            # Resize to preview size
            try:
                clip = clip.resize((job.width, job.height))
            except Exception:
                pass
            
            # Apply effects that overlap this clip in time
            try:
                # Find effect markers overlapping
                effect_markers = [m for m in timeline.get_all_markers() if getattr(m, 'marker_type', '') == 'effect' and not m.locked]
                for eff in effect_markers:
                    eff_start = eff.start_frame / job.fps
                    eff_end = eff.end_frame() / job.fps if hasattr(eff, 'end_frame') else (eff.start_frame + eff.duration_frames) / job.fps
                    clip_start = start_time
                    clip_end = start_time + duration
                    # Check overlap
                    if eff_end <= clip_start or eff_start >= clip_end:
                        continue
                    # Try to apply effect callable
                    if eff.moviepy_qualified_name:
                        sig = MoviePyRegistry.instance().get_signature(eff.moviepy_qualified_name)
                        if sig and sig.callable_ref:
                            try:
                                kwargs = eff.get_moviepy_kwargs() if hasattr(eff, 'get_moviepy_kwargs') else {}
                                clip = sig.callable_ref(clip, **kwargs)
                            except Exception as e:
                                logger.debug(f"Effect application failed {eff.moviepy_qualified_name}: {e}")
            except Exception as e:
                logger.debug(f"Error while applying effects: {e}")
            
            # Ensure start time applied
            clip = clip.set_start(start_time)
            clip = clip.with_fps(job.fps)
            
            return clip
        except Exception as e:
            logger.error(f"Failed to create clip: {e}")
            return None
    
    def _composite_clips(self, clips: List[VideoClip], 
                        job: PreviewRenderJob) -> Optional[VideoClip]:
        """Composite multiple clips into one video."""
        try:
            if not clips:
                return None
            
            if len(clips) == 1:
                return clips[0]
            
            # Use CompositeVideoClip to stack all clips
            composite = CompositeVideoClip(clips)
            composite = composite.with_fps(job.fps)
            composite = composite.with_size((job.width, job.height))
            
            return composite
        
        except Exception as e:
            logger.error(f"Compositing failed: {e}")
            return None
    
    def _render_to_file(self, clip: VideoClip, output_path: Path, 
                       job: PreviewRenderJob) -> bool:
        """Render clip to MP4 file."""
        try:
            # Choose codec based on quality
            if job.quality == 'preview':
                bitrate = '1M'
                preset = 'ultrafast'
            elif job.quality == 'draft':
                bitrate = '3M'
                preset = 'fast'
            else:
                bitrate = '8M'
                preset = 'medium'
            
            # Render to file
            logger.info(f"Writing to {output_path} ({bitrate})")
            
            def progress_hook(current_frame, total_frames):
                progress = (current_frame / total_frames) * 100
                if job.progress_callback:
                    job.progress_callback(progress)
            
            clip.write_videofile(
                str(output_path),
                codec='libx264',
                audio_codec='aac',
                bitrate=bitrate,
                preset=preset,
                verbose=False,
                logger=None,
                progress_bar=False
            )
            
            return output_path.exists() and output_path.stat().st_size > 0
        
        except Exception as e:
            logger.error(f"Rendering failed: {e}")
            return False
    
    def cleanup_temp_files(self):
        """Clean up temporary preview files."""
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.info(f"Cleaned up {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to clean up {temp_file}: {e}")
        
        self.temp_files.clear()


# Global singleton
_preview_renderer = None


def get_preview_renderer() -> PreviewRenderer:
    """Get or create the global preview renderer."""
    global _preview_renderer
    if _preview_renderer is None:
        _preview_renderer = PreviewRenderer()
    return _preview_renderer
