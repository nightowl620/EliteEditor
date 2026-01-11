"""
Timeline - Multi-track timeline with clips, markers, and playhead management
"""

import json
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import uuid

from timeline.clip import Clip, Marker, ClipType


@dataclass
class Track:
    """Audio/video track in timeline."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ''
    track_type: str = 'video'  # video, audio, adjustment
    index: int = 0
    visible: bool = True
    locked: bool = False
    muted: bool = False
    solo: bool = False
    height: int = 80
    clips: List[Clip] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            'id': self.id,
            'name': self.name,
            'track_type': self.track_type,
            'index': self.index,
            'visible': self.visible,
            'locked': self.locked,
            'muted': self.muted,
            'solo': self.solo,
            'height': self.height,
            'clips': [c.to_dict() for c in self.clips]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Track':
        """Deserialize from dict."""
        track = cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            track_type=data.get('track_type', 'video'),
            index=data.get('index', 0),
            visible=data.get('visible', True),
            locked=data.get('locked', False),
            muted=data.get('muted', False),
            solo=data.get('solo', False),
            height=data.get('height', 80)
        )
        for clip_data in data.get('clips', []):
            track.clips.append(Clip.from_dict(clip_data))
        return track


class Timeline:
    """
    Multi-track timeline with frame-accurate playback.
    
    Features:
    - Unlimited video/audio tracks
    - Clips with effects and keyframes
    - Frame-accurate playhead
    - Markers and nested sequences
    - Undo/redo integration
    """
    
    def __init__(self, name: str, fps: int = 30, width: int = 1920, height: int = 1080):
        """
        Initialize timeline.
        
        Args:
            name: Timeline name
            fps: Frame rate (default 30)
            width: Video width (default 1920)
            height: Video height (default 1080)
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.fps = fps
        self.width = width
        self.height = height
        
        # Playback state
        self.playhead_frame = 0
        self.duration_frames = 0
        self.is_playing = False
        self.loop_enabled = False
        self.loop_start = 0
        self.loop_end = 0
        
        # Tracks
        self.tracks: Dict[str, Track] = {}
        self.track_order: List[str] = []
        
        # Markers
        self.markers: List[Marker] = []
        
        # Selection and editing state
        self.selected_clips: List[str] = []
        self.selected_track_id: Optional[str] = None
    
    # ===== TRACK MANAGEMENT =====
    
    def add_track(self, track_type: str = 'video', index: Optional[int] = None) -> Track:
        """Add new track."""
        track = Track(
            name=f'{track_type.capitalize()} {len(self.tracks) + 1}',
            track_type=track_type,
            index=len(self.tracks)
        )
        self.tracks[track.id] = track
        if index is not None:
            self.track_order.insert(index, track.id)
        else:
            self.track_order.append(track.id)
        return track
    
    def remove_track(self, track_id: str) -> bool:
        """Remove track by ID."""
        if track_id in self.tracks:
            del self.tracks[track_id]
            if track_id in self.track_order:
                self.track_order.remove(track_id)
            return True
        return False
    
    def get_track(self, track_id: str) -> Optional[Track]:
        """Get track by ID."""
        return self.tracks.get(track_id)
    
    def reorder_track(self, track_id: str, new_index: int) -> None:
        """Reorder track."""
        if track_id in self.track_order:
            self.track_order.remove(track_id)
            self.track_order.insert(new_index, track_id)
    
    # ===== CLIP MANAGEMENT =====
    
    def add_clip_to_track(self, track_id: str, clip: Clip, start_time: float = 0.0) -> bool:
        """Add clip to track at time."""
        track = self.get_track(track_id)
        if not track:
            return False
        
        clip.start_time = start_time
        clip.track_index = self.track_order.index(track_id) if track_id in self.track_order else 0
        track.clips.append(clip)
        track.clips.sort(key=lambda c: c.start_time)
        
        # Update timeline duration
        end_time = clip.end_time
        if end_time > (self.duration_frames / self.fps):
            self.duration_frames = int(end_time * self.fps)
        
        return True
    
    def remove_clip(self, track_id: str, clip_id: str) -> bool:
        """Remove clip from track."""
        track = self.get_track(track_id)
        if not track:
            return False
        
        for i, clip in enumerate(track.clips):
            if clip.id == clip_id:
                track.clips.pop(i)
                return True
        return False
    
    def get_clip(self, clip_id: str) -> Optional[Clip]:
        """Get clip by ID across all tracks."""
        for track in self.tracks.values():
            for clip in track.clips:
                if clip.id == clip_id:
                    return clip
        return None
    
    def get_clips_at_frame(self, frame: int) -> List[Clip]:
        """Get all clips at given frame."""
        clips = []
        for track in self.tracks.values():
            for clip in track.clips:
                start_frame = int(clip.start_time * self.fps)
                end_frame = int(clip.end_time * self.fps)
                if start_frame <= frame < end_frame:
                    clips.append(clip)
        return clips
    
    def move_clip(self, clip_id: str, new_track_id: str, new_start_time: float) -> bool:
        """Move clip to new track and time."""
        clip = self.get_clip(clip_id)
        if not clip:
            return False
        
        # Find and remove from old track
        for track in self.tracks.values():
            for i, c in enumerate(track.clips):
                if c.id == clip_id:
                    track.clips.pop(i)
                    break
        
        # Add to new track
        return self.add_clip_to_track(new_track_id, clip, new_start_time)
    
    # ===== MARKER MANAGEMENT =====
    
    def add_marker(self, marker: Marker) -> None:
        """Add timeline marker."""
        self.markers.append(marker)
        self.markers.sort(key=lambda m: m.frame)
    
    def remove_marker(self, marker_id: str) -> bool:
        """Remove marker."""
        for i, m in enumerate(self.markers):
            if m.id == marker_id:
                self.markers.pop(i)
                return True
        return False
    
    # ===== PLAYBACK CONTROL =====
    
    def set_playhead(self, frame: int) -> None:
        """Set playhead position."""
        frame = max(0, min(frame, self.duration_frames))
        self.playhead_frame = frame
    
    def set_playhead_seconds(self, seconds: float) -> None:
        """Set playhead in seconds."""
        self.set_playhead(int(seconds * self.fps))
    
    def get_playhead_seconds(self) -> float:
        """Get playhead in seconds."""
        return self.playhead_frame / self.fps
    
    def frame_to_seconds(self, frame: int) -> float:
        """Convert frame to seconds."""
        return frame / self.fps
    
    def seconds_to_frame(self, seconds: float) -> int:
        """Convert seconds to frame."""
        return int(seconds * self.fps)
    
    # ===== SELECTION =====
    
    def select_clip(self, clip_id: str, multi_select: bool = False) -> None:
        """Select clip."""
        if not multi_select:
            self.selected_clips.clear()
        if clip_id not in self.selected_clips:
            self.selected_clips.append(clip_id)
    
    def deselect_clip(self, clip_id: str) -> None:
        """Deselect clip."""
        if clip_id in self.selected_clips:
            self.selected_clips.remove(clip_id)
    
    def deselect_all(self) -> None:
        """Deselect all clips."""
        self.selected_clips.clear()
    
    # ===== TIMELINE EDITS =====
    
    def ripple_delete(self, track_id: str, clip_id: str) -> bool:
        """Delete clip and close gap."""
        clip = self.get_clip(clip_id)
        if not clip:
            return False
        
        if not self.remove_clip(track_id, clip_id):
            return False
        
        # Move following clips backward
        track = self.get_track(track_id)
        if not track:
            return False
        
        gap = clip.current_duration
        for c in track.clips:
            if c.start_time >= clip.start_time:
                c.start_time -= gap
        
        return True
    
    def split_clip(self, clip_id: str, split_time: float) -> Optional[Clip]:
        """Split clip at time and return the second part."""
        clip = self.get_clip(clip_id)
        if not clip:
            return None
        
        if split_time <= clip.start_time or split_time >= clip.end_time:
            return None
        
        # Calculate new in/out points
        offset = split_time - clip.start_time
        offset_frames = int(offset * self.fps)
        
        # Create second clip
        second_clip = Clip(
            name=f'{clip.name} (2)',
            clip_type=clip.clip_type,
            media_path=clip.media_path,
            duration=clip.duration,
            fps=clip.fps
        )
        second_clip.start_time = split_time
        second_clip.in_point = clip.in_point + offset_frames
        second_clip.out_point = clip.out_point
        second_clip.track_index = clip.track_index
        
        # Update first clip
        clip.out_point = clip.in_point + offset_frames
        
        # Add to appropriate track
        for track_id, track in self.tracks.items():
            for c in track.clips:
                if c.id == clip_id:
                    self.add_clip_to_track(track_id, second_clip, split_time)
                    return second_clip
        
        return None
    
    def update_duration(self) -> None:
        """Update total timeline duration based on clips."""
        max_end = 0.0
        for track in self.tracks.values():
            for clip in track.clips:
                if clip.end_time > max_end:
                    max_end = clip.end_time
        self.duration_frames = int(max_end * self.fps)
    
    # ===== SERIALIZATION =====
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            'id': self.id,
            'name': self.name,
            'fps': self.fps,
            'width': self.width,
            'height': self.height,
            'playhead_frame': self.playhead_frame,
            'duration_frames': self.duration_frames,
            'loop_enabled': self.loop_enabled,
            'loop_start': self.loop_start,
            'loop_end': self.loop_end,
            'tracks': {tid: track.to_dict() for tid, track in self.tracks.items()},
            'track_order': self.track_order,
            'markers': [m.to_dict() for m in self.markers]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Timeline':
        """Deserialize from dict."""
        timeline = cls(
            name=data.get('name', 'Timeline'),
            fps=data.get('fps', 30),
            width=data.get('width', 1920),
            height=data.get('height', 1080)
        )
        timeline.id = data.get('id', str(uuid.uuid4()))
        timeline.playhead_frame = data.get('playhead_frame', 0)
        timeline.duration_frames = data.get('duration_frames', 0)
        timeline.loop_enabled = data.get('loop_enabled', False)
        timeline.loop_start = data.get('loop_start', 0)
        timeline.loop_end = data.get('loop_end', 0)
        
        # Load tracks
        track_order = data.get('track_order', [])
        for track_id in track_order:
            if track_id in data.get('tracks', {}):
                timeline.tracks[track_id] = Track.from_dict(data['tracks'][track_id])
        timeline.track_order = track_order
        
        # Load markers
        for marker_data in data.get('markers', []):
            timeline.markers.append(Marker.from_dict(marker_data))
        
        return timeline
    
    def __repr__(self) -> str:
        return f"<Timeline '{self.name}' {self.fps}fps {len(self.tracks)} tracks>"
