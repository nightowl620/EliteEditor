"""
Elite Editor - Timeline module
Provides Timeline, Track, Clip, and Marker classes
Real QGraphicsView-based timeline
Drag & drop payload system
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from timeline.clip import Clip, ClipType, Effect, Keyframes, Marker, KeyframeValue
from timeline.timeline import Timeline, Track
from timeline.graphics_timeline import RealTimelineWidget, TimelineMarker, ClipRectItem
from timeline.dnd_payload import DragPayload, create_marker_from_payload, EffectDragSource, AssetDragSource

__all__ = [
    'Clip',
    'ClipType',
    'Effect',
    'Keyframes',
    'KeyframeValue',
    'Marker',
    'Timeline',
    'Track',
    'RealTimelineWidget',
    'TimelineMarker',
    'ClipRectItem',
    'DragPayload',
    'create_marker_from_payload',
    'EffectDragSource',
    'AssetDragSource',
]
import logging


logger = logging.getLogger(__name__)


class TrackType(Enum):
    """Track types."""
    VIDEO = 'video'
    AUDIO = 'audio'
    ADJUSTMENT = 'adjustment'


class ClipType(Enum):
    """Clip types."""
    MEDIA = 'media'
    COLOR = 'color'
    TITLE = 'title'
    SHAPE = 'shape'
    NESTED = 'nested'


@dataclass
class Timecode:
    """Frame-accurate timecode representation."""
    frame: int = 0
    fps: int = 30
    
    @property
    def seconds(self) -> float:
        """Convert to seconds."""
        return self.frame / self.fps
    
    @property
    def milliseconds(self) -> int:
        """Convert to milliseconds."""
        return int(self.frame / self.fps * 1000)
    
    @property
    def timecode_str(self) -> str:
        """SMPTE timecode string HH:MM:SS:FF."""
        total_secs = self.frame // self.fps
        hours = total_secs // 3600
        mins = (total_secs % 3600) // 60
        secs = total_secs % 60
        frames = self.frame % self.fps
        return f"{hours:02d}:{mins:02d}:{secs:02d}:{frames:02d}"
    
    @classmethod
    def from_seconds(cls, seconds: float, fps: int = 30) -> 'Timecode':
        """Create from seconds."""
        frame = int(seconds * fps)
        return cls(frame, fps)
    
    def __add__(self, other: 'Timecode') -> 'Timecode':
        return Timecode(self.frame + other.frame, self.fps)
    
    def __sub__(self, other: 'Timecode') -> 'Timecode':
        return Timecode(max(0, self.frame - other.frame), self.fps)
    
    def __lt__(self, other: 'Timecode') -> bool:
        return self.frame < other.frame
    
    def __le__(self, other: 'Timecode') -> bool:
        return self.frame <= other.frame
    
    def __eq__(self, other: 'Timecode') -> bool:
        return self.frame == other.frame
    
    def __repr__(self) -> str:
        return f"<Timecode {self.timecode_str} ({self.frame}f)>"


@dataclass
class ClipRange:
    """Source in/out point range."""
    in_point: Timecode = field(default_factory=Timecode)
    out_point: Timecode = field(default_factory=lambda: Timecode(900))  # 30 frames default
    
    @property
    def duration(self) -> Timecode:
        """Duration in frames."""
        return self.out_point - self.in_point
    
    def is_valid(self) -> bool:
        """Check if range is valid."""
        return self.in_point < self.out_point


class Clip:
    """
    Represents a single clip on the timeline.
    
    Supports:
    - Trimming (in/out points)
    - Speed ramping
    - Reverse playback
    - Freeze frames
    - Audio detach/relink
    - Transitions
    """
    
    def __init__(self, clip_id: str, name: str, clip_type: ClipType):
        self.id = clip_id
        self.name = name
        self.type = clip_type
        
        # Timeline position
        self.timeline_in = Timecode()
        self.timeline_out = Timecode()
        
        # Source range
        self.source_range = ClipRange()
        
        # Properties
        self.enabled = True
        self.locked = False
        self.selected = False
        
        # Effects and animation
        self.effects: List[str] = []
        self.keyframes: Dict[str, List[Any]] = {}
        
        # Speed and direction
        self.speed = 1.0
        self.reverse = False
        self.freeze_frame = False
        
        # Audio (for video clips)
        self.audio_linked = True
        self.audio_clip_id: Optional[str] = None
        
        # Metadata
        self.color_label = '#FF6B6B'
        self.notes = ''
        
        # Observers
        self._changed_callbacks: List[Callable] = []
    
    @property
    def timeline_duration(self) -> Timecode:
        """Duration on timeline."""
        return self.timeline_out - self.timeline_in
    
    @property
    def source_duration(self) -> Timecode:
        """Duration in source."""
        return self.source_range.duration
    
    def set_timeline_position(self, in_frame: int, fps: int = 30) -> None:
        """Set timeline in point."""
        self.timeline_in = Timecode(in_frame, fps)
        # out point is determined by source duration and speed
        duration_frames = int(self.source_duration.frame / self.speed)
        self.timeline_out = Timecode(self.timeline_in.frame + duration_frames, fps)
        self._notify_changed()
    
    def trim_in(self, offset: Timecode) -> None:
        """Trim in point."""
        self.source_range.in_point = self.source_range.in_point + offset
        if self.source_range.in_point > self.source_range.out_point:
            self.source_range.in_point = self.source_range.out_point - Timecode(1)
        self._notify_changed()
    
    def trim_out(self, offset: Timecode) -> None:
        """Trim out point."""
        self.source_range.out_point = self.source_range.out_point + offset
        if self.source_range.out_point < self.source_range.in_point:
            self.source_range.out_point = self.source_range.in_point + Timecode(1)
        self._notify_changed()
    
    def set_speed(self, speed: float) -> None:
        """Set playback speed."""
        if speed <= 0:
            logger.warning("Speed must be positive")
            return
        self.speed = speed
        # Recalculate timeline out
        duration_frames = int(self.source_duration.frame / speed)
        self.timeline_out = Timecode(self.timeline_in.frame + duration_frames, self.timeline_in.fps)
        self._notify_changed()
    
    def add_effect(self, effect_id: str) -> None:
        """Add effect to clip."""
        if effect_id not in self.effects:
            self.effects.append(effect_id)
            self._notify_changed()
    
    def remove_effect(self, effect_id: str) -> None:
        """Remove effect from clip."""
        if effect_id in self.effects:
            self.effects.remove(effect_id)
            self._notify_changed()
    
    def register_changed_callback(self, callback: Callable) -> None:
        """Register callback for changes."""
        if callback not in self._changed_callbacks:
            self._changed_callbacks.append(callback)
    
    def _notify_changed(self) -> None:
        """Notify observers of change."""
        for callback in self._changed_callbacks:
            try:
                callback(self)
            except Exception as e:
                logger.error(f"Clip callback error: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type.value,
            'timeline_in': self.timeline_in.frame,
            'timeline_out': self.timeline_out.frame,
            'source_in': self.source_range.in_point.frame,
            'source_out': self.source_range.out_point.frame,
            'speed': self.speed,
            'reverse': self.reverse,
            'freeze_frame': self.freeze_frame,
            'enabled': self.enabled,
            'locked': self.locked,
            'effects': self.effects,
            'color_label': self.color_label,
            'notes': self.notes,
        }


class Track:
    """
    Represents a single track in the timeline.
    
    Supports:
    - Multiple clips
    - Mute / Solo / Lock
    - Height customization
    - Color
    """
    
    def __init__(self, track_id: str, name: str, track_type: TrackType):
        self.id = track_id
        self.name = name
        self.type = track_type
        
        # Track state
        self.enabled = True
        self.muted = False
        self.solo = False
        self.locked = False
        self.height = 100  # pixels
        
        # Clips on track
        self.clips: List[Clip] = []
        
        # Properties
        self.color = '#1e293b'
        
        # Observers
        self._changed_callbacks: List[Callable] = []
    
    def add_clip(self, clip: Clip, position: int = -1) -> None:
        """Add clip to track."""
        if position < 0:
            self.clips.append(clip)
        else:
            self.clips.insert(position, clip)
        self._notify_changed()
    
    def remove_clip(self, clip: Clip) -> bool:
        """Remove clip from track."""
        if clip in self.clips:
            self.clips.remove(clip)
            self._notify_changed()
            return True
        return False
    
    def get_clip_at_time(self, timecode: Timecode) -> Optional[Clip]:
        """Get clip at specific timeline time."""
        for clip in self.clips:
            if clip.timeline_in <= timecode < clip.timeline_out:
                return clip
        return None
    
    def get_clips_in_range(self, in_time: Timecode, out_time: Timecode) -> List[Clip]:
        """Get all clips that overlap time range."""
        result = []
        for clip in self.clips:
            # Check if clip overlaps range
            if clip.timeline_in < out_time and clip.timeline_out > in_time:
                result.append(clip)
        return result
    
    def register_changed_callback(self, callback: Callable) -> None:
        """Register change callback."""
        if callback not in self._changed_callbacks:
            self._changed_callbacks.append(callback)
    
    def _notify_changed(self) -> None:
        """Notify observers."""
        for callback in self._changed_callbacks:
            try:
                callback(self)
            except Exception as e:
                logger.error(f"Track callback error: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type.value,
            'enabled': self.enabled,
            'muted': self.muted,
            'solo': self.solo,
            'locked': self.locked,
            'height': self.height,
            'color': self.color,
            'clips': [clip.to_dict() for clip in self.clips],
        }


class Timeline:
    """
    Professional multi-track timeline.
    
    Features:
    - Infinite duration
    - Multi-track video/audio
    - Zoom and scroll
    - Snapping
    - Ripple/roll/slip/slide edits
    - Markers
    - Nesting
    """
    
    def __init__(self, fps: int = 30, width: int = 1920, height: int = 1080):
        self.fps = fps
        self.width = width
        self.height = height
        
        # Tracks
        self.tracks: List[Track] = []
        self.next_track_id = 0
        
        # Playhead
        self.playhead = Timecode(0, fps)
        self.duration = Timecode(0, fps)
        
        # Selection
        self.selected_clips: Set[Clip] = set()
        self.selected_tracks: Set[Track] = set()
        
        # Markers
        self.markers: Dict[int, str] = {}  # frame -> name
        
        # View settings
        self.zoom_level = 1.0  # pixels per frame
        self.scroll_x = 0  # horizontal scroll
        self.snap_enabled = True
        self.snap_threshold = 10  # pixels
        
        # Observers
        self._changed_callbacks: List[Callable] = []
    
    # ===== TRACK MANAGEMENT =====
    
    def add_video_track(self, name: str = 'Video') -> Track:
        """Add video track."""
        track = Track(f'v{self.next_track_id}', name, TrackType.VIDEO)
        self.next_track_id += 1
        self.tracks.append(track)
        track.register_changed_callback(self._on_track_changed)
        self._notify_changed()
        return track
    
    def add_audio_track(self, name: str = 'Audio') -> Track:
        """Add audio track."""
        track = Track(f'a{self.next_track_id}', name, TrackType.AUDIO)
        self.next_track_id += 1
        self.tracks.append(track)
        track.register_changed_callback(self._on_track_changed)
        self._notify_changed()
        return track
    
    def add_adjustment_track(self, name: str = 'Adjustment') -> Track:
        """Add adjustment layer."""
        track = Track(f'adj{self.next_track_id}', name, TrackType.ADJUSTMENT)
        self.next_track_id += 1
        self.tracks.append(track)
        track.register_changed_callback(self._on_track_changed)
        self._notify_changed()
        return track
    
    def remove_track(self, track: Track) -> bool:
        """Remove track."""
        if track in self.tracks:
            self.tracks.remove(track)
            self._notify_changed()
            return True
        return False
    
    def move_track(self, track: Track, position: int) -> None:
        """Move track to new position."""
        if track in self.tracks:
            self.tracks.remove(track)
            self.tracks.insert(position, track)
            self._notify_changed()
    
    # ===== CLIP OPERATIONS =====
    
    def get_clip_by_id(self, clip_id: str) -> Optional[Clip]:
        """Find clip by ID."""
        for track in self.tracks:
            for clip in track.clips:
                if clip.id == clip_id:
                    return clip
        return None
    
    def get_clips_at_time(self, timecode: Timecode) -> List[Clip]:
        """Get all clips at specific time across all tracks."""
        result = []
        for track in self.tracks:
            clip = track.get_clip_at_time(timecode)
            if clip:
                result.append(clip)
        return result
    
    # ===== PLAYHEAD =====
    
    def set_playhead(self, frame: int) -> None:
        """Set playhead position."""
        self.playhead = Timecode(frame, self.fps)
        self._notify_changed()
    
    def move_playhead(self, offset: int) -> None:
        """Move playhead by offset."""
        new_frame = max(0, self.playhead.frame + offset)
        self.set_playhead(new_frame)
    
    # ===== MARKERS =====
    
    def add_marker(self, frame: int, name: str) -> None:
        """Add timeline marker."""
        self.markers[frame] = name
        self._notify_changed()
    
    def remove_marker(self, frame: int) -> None:
        """Remove marker."""
        if frame in self.markers:
            del self.markers[frame]
            self._notify_changed()
    
    # ===== ZOOM & VIEW =====
    
    def set_zoom(self, level: float) -> None:
        """Set zoom level (pixels per frame)."""
        self.zoom_level = max(0.1, min(level, 10.0))
        self._notify_changed()
    
    def zoom_in(self) -> None:
        """Zoom in."""
        self.set_zoom(self.zoom_level * 1.2)
    
    def zoom_out(self) -> None:
        """Zoom out."""
        self.set_zoom(self.zoom_level / 1.2)
    
    # ===== SNAPPING =====
    
    def get_snap_point(self, position: int) -> Optional[int]:
        """Get snap-to position if enabled and close."""
        if not self.snap_enabled:
            return None
        
        # Check against playhead
        if abs(position - self.playhead.frame * self.zoom_level) < self.snap_threshold:
            return self.playhead.frame
        
        # Check against clip boundaries
        for track in self.tracks:
            for clip in track.clips:
                for snap_pos in [clip.timeline_in.frame, clip.timeline_out.frame]:
                    if abs(position - snap_pos * self.zoom_level) < self.snap_threshold:
                        return snap_pos
        
        # Check against markers
        for frame in self.markers.keys():
            if abs(position - frame * self.zoom_level) < self.snap_threshold:
                return frame
        
        return None
    
    # ===== OBSERVERS =====
    
    def register_changed_callback(self, callback: Callable) -> None:
        """Register change callback."""
        if callback not in self._changed_callbacks:
            self._changed_callbacks.append(callback)
    
    def _on_track_changed(self, track: Track) -> None:
        """Handle track change."""
        self._notify_changed()
    
    def _notify_changed(self) -> None:
        """Notify observers."""
        for callback in self._changed_callbacks:
            try:
                callback(self)
            except Exception as e:
                logger.error(f"Timeline callback error: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            'fps': self.fps,
            'width': self.width,
            'height': self.height,
            'duration': self.duration.frame,
            'playhead': self.playhead.frame,
            'tracks': [track.to_dict() for track in self.tracks],
            'markers': {str(k): v for k, v in self.markers.items()},
        }
    
    def __repr__(self) -> str:
        return f"<Timeline {self.fps}fps {len(self.tracks)} tracks>"
