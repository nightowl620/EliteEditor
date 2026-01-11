"""
TimelineMarker - Represents clips/effects on the timeline with real MoviePy bindings

A marker is:
- A clip or effect instance
- Positioned in time (start_frame, duration)
- On a track index
- Bound to a MoviePy callable or clip object
- With live parameters
"""

import json
import uuid
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class TimelineMarkerParameter:
    """Single parameter binding for a TimelineMarker."""
    name: str
    value: Any
    parameter_type: str  # float, int, str, bool, selection
    moviepy_param_name: str  # Name in MoviePy function
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize."""
        return {
            'name': self.name,
            'value': self.value,
            'parameter_type': self.parameter_type,
            'moviepy_param_name': self.moviepy_param_name,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimelineMarkerParameter':
        """Deserialize."""
        return cls(**data)


@dataclass
class TimelineMarker:
    """
    Single element on timeline (clip or effect).
    
    Represents a real MoviePy object positioned in time.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Identity
    name: str = ''
    marker_type: str = 'clip'  # clip, effect, adjustment
    
    # Timing
    start_frame: int = 0
    duration_frames: int = 0
    
    # Track
    track_index: int = 0
    
    # MoviePy binding
    moviepy_qualified_name: Optional[str] = None  # e.g., "moviepy.video.fx.blur"
    moviepy_object_reference: Optional[Any] = None  # Actual MoviePy object
    source_file: Optional[str] = None  # For clips: path to media
    
    # Parameters
    parameters: List[TimelineMarkerParameter] = field(default_factory=list)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    enabled: bool = True
    locked: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            'id': self.id,
            'name': self.name,
            'marker_type': self.marker_type,
            'start_frame': self.start_frame,
            'duration_frames': self.duration_frames,
            'track_index': self.track_index,
            'moviepy_qualified_name': self.moviepy_qualified_name,
            'source_file': self.source_file,
            'parameters': [p.to_dict() for p in self.parameters],
            'created_at': self.created_at,
            'modified_at': self.modified_at,
            'enabled': self.enabled,
            'locked': self.locked,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimelineMarker':
        """Deserialize from dict."""
        marker = cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            marker_type=data.get('marker_type', 'clip'),
            start_frame=data.get('start_frame', 0),
            duration_frames=data.get('duration_frames', 0),
            track_index=data.get('track_index', 0),
            moviepy_qualified_name=data.get('moviepy_qualified_name'),
            source_file=data.get('source_file'),
            created_at=data.get('created_at', datetime.now().isoformat()),
            modified_at=data.get('modified_at', datetime.now().isoformat()),
            enabled=data.get('enabled', True),
            locked=data.get('locked', False),
        )
        
        # Restore parameters
        for param_data in data.get('parameters', []):
            marker.parameters.append(TimelineMarkerParameter.from_dict(param_data))
        
        return marker
    
    def add_parameter(self, name: str, value: Any, param_type: str,
                     moviepy_param_name: str) -> TimelineMarkerParameter:
        """Add or update a parameter."""
        # Check if exists
        for param in self.parameters:
            if param.name == name:
                param.value = value
                return param
        
        # Create new
        param = TimelineMarkerParameter(name, value, param_type, moviepy_param_name)
        self.parameters.append(param)
        self.modified_at = datetime.now().isoformat()
        return param
    
    def get_parameter(self, name: str) -> Optional[TimelineMarkerParameter]:
        """Get parameter by name."""
        for p in self.parameters:
            if p.name == name:
                return p
        return None
    
    def get_moviepy_kwargs(self) -> Dict[str, Any]:
        """Get parameters formatted for MoviePy function call."""
        kwargs = {}
        for param in self.parameters:
            kwargs[param.moviepy_param_name] = param.value
        return kwargs
    
    def end_frame(self) -> int:
        """Get end frame (exclusive)."""
        return self.start_frame + self.duration_frames
    
    def contains_frame(self, frame: int) -> bool:
        """Check if marker contains frame."""
        return self.start_frame <= frame < self.end_frame()
    
    def move(self, new_start_frame: int, new_track_index: int) -> None:
        """Move marker to new position."""
        self.start_frame = max(0, new_start_frame)
        self.track_index = max(0, new_track_index)
        self.modified_at = datetime.now().isoformat()
    
    def resize(self, new_duration_frames: int) -> None:
        """Resize marker duration."""
        self.duration_frames = max(1, new_duration_frames)
        self.modified_at = datetime.now().isoformat()


class TimelineTrack:
    """
    Single track (video, audio, adjustment).
    
    Contains markers and track-level properties.
    """
    
    def __init__(self, index: int, track_type: str = 'video', name: str = ''):
        self.id = str(uuid.uuid4())
        self.index = index
        self.track_type = track_type  # video, audio, adjustment
        self.name = name or f"{track_type.capitalize()} {index + 1}"
        
        # State
        self.visible = True
        self.locked = False
        self.muted = False
        self.solo = False
        self.height = 100  # pixels in UI
        self.opacity = 1.0
        
        # Markers (clips/effects)
        self.markers: Dict[str, TimelineMarker] = {}
        self.marker_order: List[str] = []  # Sorted by start_frame
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize."""
        return {
            'id': self.id,
            'index': self.index,
            'track_type': self.track_type,
            'name': self.name,
            'visible': self.visible,
            'locked': self.locked,
            'muted': self.muted,
            'solo': self.solo,
            'height': self.height,
            'opacity': self.opacity,
            'markers': {mid: m.to_dict() for mid, m in self.markers.items()},
            'marker_order': self.marker_order,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimelineTrack':
        """Deserialize."""
        track = cls(
            index=data.get('index', 0),
            track_type=data.get('track_type', 'video'),
            name=data.get('name', ''),
        )
        track.id = data.get('id', track.id)
        track.visible = data.get('visible', True)
        track.locked = data.get('locked', False)
        track.muted = data.get('muted', False)
        track.solo = data.get('solo', False)
        track.height = data.get('height', 100)
        track.opacity = data.get('opacity', 1.0)
        
        # Restore markers
        for mid, marker_data in data.get('markers', {}).items():
            track.markers[mid] = TimelineMarker.from_dict(marker_data)
        track.marker_order = data.get('marker_order', list(track.markers.keys()))
        
        return track
    
    def add_marker(self, marker: TimelineMarker) -> None:
        """Add marker to track."""
        self.markers[marker.id] = marker
        self.marker_order.append(marker.id)
        self._sort_markers()
    
    def remove_marker(self, marker_id: str) -> bool:
        """Remove marker from track."""
        if marker_id in self.markers:
            del self.markers[marker_id]
            self.marker_order.remove(marker_id)
            return True
        return False
    
    def get_marker(self, marker_id: str) -> Optional[TimelineMarker]:
        """Get marker by ID."""
        return self.markers.get(marker_id)
    
    def get_markers_at_frame(self, frame: int) -> List[TimelineMarker]:
        """Get all markers at frame."""
        return [m for m in self.markers.values() if m.contains_frame(frame)]
    
    def _sort_markers(self) -> None:
        """Sort marker order by start_frame."""
        self.marker_order.sort(key=lambda mid: self.markers[mid].start_frame)


class Timeline:
    """
    Multi-track timeline.
    
    Contains tracks, playhead, markers, and composition.
    """
    
    def __init__(self, name: str, fps: int = 30, width: int = 1920, height: int = 1080):
        self.id = str(uuid.uuid4())
        self.name = name
        self.fps = fps
        self.width = width
        self.height = height
        
        # Playback state
        self.playhead_frame = 0
        self.is_playing = False
        self.duration_frames = 0
        
        # Tracks (dict by ID, order tracked separately)
        self.tracks: Dict[str, TimelineTrack] = {}
        self.track_order: List[str] = []
        
        # Add default video and audio tracks
        self._create_default_tracks()
    
    def _create_default_tracks(self) -> None:
        """Create initial video and audio tracks."""
        video_track = TimelineTrack(0, 'video', 'Video 1')
        audio_track = TimelineTrack(1, 'audio', 'Audio 1')
        
        self.add_track(video_track)
        self.add_track(audio_track)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize."""
        return {
            'id': self.id,
            'name': self.name,
            'fps': self.fps,
            'width': self.width,
            'height': self.height,
            'playhead_frame': self.playhead_frame,
            'is_playing': self.is_playing,
            'duration_frames': self.duration_frames,
            'tracks': {tid: t.to_dict() for tid, t in self.tracks.items()},
            'track_order': self.track_order,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Timeline':
        """Deserialize."""
        timeline = cls(
            name=data.get('name', 'Untitled'),
            fps=data.get('fps', 30),
            width=data.get('width', 1920),
            height=data.get('height', 1080),
        )
        timeline.id = data.get('id', timeline.id)
        timeline.playhead_frame = data.get('playhead_frame', 0)
        timeline.is_playing = data.get('is_playing', False)
        timeline.duration_frames = data.get('duration_frames', 0)
        
        # Clear default tracks
        timeline.tracks.clear()
        timeline.track_order.clear()
        
        # Restore tracks
        for tid, track_data in data.get('tracks', {}).items():
            timeline.tracks[tid] = TimelineTrack.from_dict(track_data)
        timeline.track_order = data.get('track_order', list(timeline.tracks.keys()))
        
        return timeline
    
    def add_track(self, track: TimelineTrack) -> None:
        """Add track."""
        self.tracks[track.id] = track
        self.track_order.append(track.id)
    
    def remove_track(self, track_id: str) -> bool:
        """Remove track."""
        if track_id in self.tracks:
            del self.tracks[track_id]
            self.track_order.remove(track_id)
            return True
        return False
    
    def get_track(self, track_id: str) -> Optional[TimelineTrack]:
        """Get track by ID."""
        return self.tracks.get(track_id)
    
    def get_track_by_index(self, index: int) -> Optional[TimelineTrack]:
        """Get track by index."""
        for track in self.tracks.values():
            if track.index == index:
                return track
        return None
    
    def add_marker(self, marker: TimelineMarker) -> bool:
        """Add marker to its assigned track."""
        track = self.get_track_by_index(marker.track_index)
        if track:
            track.add_marker(marker)
            # Update duration
            self.duration_frames = max(
                self.duration_frames,
                marker.end_frame()
            )
            return True
        return False
    
    def get_marker(self, marker_id: str) -> Optional[TimelineMarker]:
        """Get marker by ID from any track."""
        for track in self.tracks.values():
            marker = track.get_marker(marker_id)
            if marker:
                return marker
        return None
    
    def get_all_markers(self) -> List[TimelineMarker]:
        """Get all markers from all tracks."""
        markers = []
        for track in self.tracks.values():
            markers.extend(track.markers.values())
        return markers
    
    def get_markers_at_frame(self, frame: int) -> List[TimelineMarker]:
        """Get all markers at frame from all tracks."""
        markers = []
        for track in self.tracks.values():
            markers.extend(track.get_markers_at_frame(frame))
        return markers
