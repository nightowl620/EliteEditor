"""Rendering System - MoviePy-based video rendering with presets and queue management"""

from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
import logging
import json
from datetime import datetime

from rendering.moviepy_registry import get_registry, list_all_effects
logger = logging.getLogger(__name__)


class VideoCodec(Enum):
    """Video codecs."""
    H264 = 'h264'
    H265 = 'h265'
    PRORES = 'prores'
    DNxHD = 'dnxhd'


class AudioCodec(Enum):
    """Audio codecs."""
    AAC = 'aac'
    MP3 = 'mp3'
    PCM = 'pcm'
    OPUS = 'opus'


@dataclass
class RenderPreset:
    """Pre-configured render settings."""
    name: str
    width: int
    height: int
    fps: int
    video_codec: VideoCodec
    video_bitrate: str  # e.g., '8000k'
    audio_codec: AudioCodec
    audio_bitrate: str  # e.g., '192k'
    audio_sample_rate: int = 48000
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            'name': self.name,
            'width': self.width,
            'height': self.height,
            'fps': self.fps,
            'video_codec': self.video_codec.value,
            'video_bitrate': self.video_bitrate,
            'audio_codec': self.audio_codec.value,
            'audio_bitrate': self.audio_bitrate,
            'audio_sample_rate': self.audio_sample_rate,
        }


# Built-in presets
PRESET_720P = RenderPreset(
    name='720p (HD)',
    width=1280,
    height=720,
    fps=30,
    video_codec=VideoCodec.H264,
    video_bitrate='2500k',
    audio_codec=AudioCodec.AAC,
    audio_bitrate='128k',
)

PRESET_1080P = RenderPreset(
    name='1080p (FHD)',
    width=1920,
    height=1080,
    fps=30,
    video_codec=VideoCodec.H264,
    video_bitrate='8000k',
    audio_codec=AudioCodec.AAC,
    audio_bitrate='192k',
)

PRESET_4K = RenderPreset(
    name='4K (UHD)',
    width=3840,
    height=2160,
    fps=30,
    video_codec=VideoCodec.H264,
    video_bitrate='25000k',
    audio_codec=AudioCodec.AAC,
    audio_bitrate='256k',
)

PRESET_PRORES = RenderPreset(
    name='ProRes 422 (Master)',
    width=1920,
    height=1080,
    fps=30,
    video_codec=VideoCodec.PRORES,
    video_bitrate='500000k',  # Very high for master
    audio_codec=AudioCodec.PCM,
    audio_bitrate='1536k',
)


class RenderJob:
    """
    Single render job.
    
    Tracks state, progress, and settings.
    """
    
    def __init__(self, job_id: str, project_name: str, output_path: Path,
                 preset: RenderPreset):
        self.id = job_id
        self.project_name = project_name
        self.output_path = output_path
        self.preset = preset
        
        # State
        self.state = 'queued'  # queued | rendering | completed | failed | cancelled
        self.progress = 0.0  # 0-100
        self.current_frame = 0
        self.total_frames = 0
        
        # Timing
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        
        # Error info
        self.error_message = ""
        
        # Callbacks
        self._progress_callbacks: List[Callable] = []
        self._state_callbacks: List[Callable] = []
    
    def set_state(self, state: str) -> None:
        """Update state."""
        self.state = state
        if state == 'rendering' and not self.started_at:
            self.started_at = datetime.now()
        elif state == 'completed' or state == 'failed':
            self.completed_at = datetime.now()
        
        self._notify_state_callbacks()
    
    def set_progress(self, current_frame: int, total_frames: int) -> None:
        """Update render progress."""
        self.current_frame = current_frame
        self.total_frames = total_frames
        if total_frames > 0:
            self.progress = (current_frame / total_frames) * 100.0
        
        self._notify_progress_callbacks()
    
    @property
    def elapsed_time(self) -> Optional[float]:
        """Elapsed time in seconds."""
        start = self.started_at or self.created_at
        end = self.completed_at or datetime.now()
        return (end - start).total_seconds()
    
    @property
    def estimated_total_time(self) -> Optional[float]:
        """Estimated total render time in seconds."""
        if not self.started_at or self.progress == 0:
            return None
        elapsed = (datetime.now() - self.started_at).total_seconds()
        return elapsed / (self.progress / 100.0)
    
    @property
    def estimated_remaining_time(self) -> Optional[float]:
        """Estimated remaining time in seconds."""
        total = self.estimated_total_time
        if not total:
            return None
        elapsed = (datetime.now() - self.started_at).total_seconds()
        return max(0, total - elapsed)
    
    def register_progress_callback(self, callback: Callable) -> None:
        """Register progress callback."""
        if callback not in self._progress_callbacks:
            self._progress_callbacks.append(callback)
    
    def register_state_callback(self, callback: Callable) -> None:
        """Register state callback."""
        if callback not in self._state_callbacks:
            self._state_callbacks.append(callback)
    
    def _notify_progress_callbacks(self) -> None:
        """Notify progress callbacks."""
        for callback in self._progress_callbacks:
            try:
                callback(self.progress, self.current_frame, self.total_frames)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")
    
    def _notify_state_callbacks(self) -> None:
        """Notify state callbacks."""
        for callback in self._state_callbacks:
            try:
                callback(self.state)
            except Exception as e:
                logger.error(f"State callback error: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            'id': self.id,
            'project_name': self.project_name,
            'output_path': str(self.output_path),
            'preset': self.preset.to_dict(),
            'state': self.state,
            'progress': self.progress,
            'current_frame': self.current_frame,
            'total_frames': self.total_frames,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
        }


class RenderQueue:
    """
    Manages render jobs.
    
    Features:
    - Queue management
    - Concurrent rendering
    - Pause/resume
    - Job persistence
    """
    
    def __init__(self, max_concurrent: int = 1):
        self.jobs: Dict[str, RenderJob] = {}
        self.queue_order: List[str] = []
        self.max_concurrent = max_concurrent
        self.paused = False
        
        # Observers
        self._queue_callbacks: List[Callable] = []
    
    def add_job(self, job: RenderJob) -> None:
        """Add job to queue."""
        self.jobs[job.id] = job
        self.queue_order.append(job.id)
        self._notify_queue_change()
        logger.info(f"Added render job: {job.id}")
    
    def remove_job(self, job_id: str) -> bool:
        """Remove job from queue."""
        if job_id in self.jobs:
            del self.jobs[job_id]
            self.queue_order.remove(job_id)
            self._notify_queue_change()
            return True
        return False
    
    def get_next_job(self) -> Optional[RenderJob]:
        """Get next job to render."""
        for job_id in self.queue_order:
            job = self.jobs[job_id]
            if job.state == 'queued':
                return job
        return None
    
    def get_active_jobs(self) -> List[RenderJob]:
        """Get currently rendering jobs."""
        return [j for j in self.jobs.values() if j.state == 'rendering']
    
    def pause_queue(self) -> None:
        """Pause queue processing."""
        self.paused = True
    
    def resume_queue(self) -> None:
        """Resume queue processing."""
        self.paused = False
    
    def register_queue_callback(self, callback: Callable) -> None:
        """Register callback for queue changes."""
        if callback not in self._queue_callbacks:
            self._queue_callbacks.append(callback)
    
    def _notify_queue_change(self) -> None:
        """Notify observers of queue change."""
        for callback in self._queue_callbacks:
            try:
                callback(self)
            except Exception as e:
                logger.error(f"Queue callback error: {e}")
    
    def __repr__(self) -> str:
        return f"<RenderQueue {len(self.jobs)} jobs>"


class MoviePyRenderer:
    """
    MoviePy-based video renderer.
    
    Handles actual rendering with progress tracking.
    """
    
    def __init__(self):
        self.job_queue = RenderQueue()
        self._moviepy_available = self._check_moviepy()
    
    def _check_moviepy(self) -> bool:
        """Check if MoviePy is installed."""
        try:
            import moviepy
            return True
        except ImportError:
            logger.warning("MoviePy not installed")
            return False
    
    def create_render_job(self, project_name: str, output_path: Path,
                         preset: RenderPreset) -> RenderJob:
        """Create new render job."""
        job_id = f"{project_name}_{int(datetime.now().timestamp())}"
        job = RenderJob(job_id, project_name, output_path, preset)
        return job
    
    def queue_render(self, job: RenderJob) -> None:
        """Queue render job."""
        self.job_queue.add_job(job)
    
    def render_job(self, job: RenderJob) -> bool:
        """
        Render job.
        
        Returns:
            True if successful
        """
        if not self._moviepy_available:
            logger.error("MoviePy not available")
            return False
        
        try:
            from moviepy import VideoFileClip, concatenate_videoclips
            
            job.set_state('rendering')
            
            # Use real subprocess renderer for production export
            from rendering.subprocess_renderer import get_subprocess_renderer, SubprocessRenderJob
            renderer = get_subprocess_renderer()
            render_job = SubprocessRenderJob(
                id=f'job_{job.id}',
                timeline=job.timeline,
                output_path=job.output_path,
                fps=job.fps,
                width=job.width,
                height=job.height,
                bitrate='8M',
                codec='libx264',
                preset='medium'
            )
            renderer.render(render_job)
            
            logger.info(f"Rendering: {job.id}")
            
            job.set_state('completed')
            return True
        
        except Exception as e:
            logger.error(f"Render error: {e}")
            job.set_state('failed')
            job.error_message = str(e)
            return False
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel render job."""
        if job_id in self.job_queue.jobs:
            self.job_queue.jobs[job_id].set_state('cancelled')
            return True
        return False
