"""
Clip - Core clip object for timeline
Represents a single media item with effects, keyframes, markers
"""

import json
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import uuid


class ClipType(Enum):
    """Clip type enum."""
    VIDEO = 'video'
    AUDIO = 'audio'
    IMAGE = 'image'
    TEXT = 'text'
    SOLID = 'solid'
    ADJUSTMENT = 'adjustment'
    NESTED = 'nested'


@dataclass
class KeyframeValue:
    """Single keyframe value with interpolation."""
    frame: int
    value: float
    interpolation: str = 'linear'  # linear, bezier, hold
    ease_in: float = 0.0  # 0.0 to 1.0 for bezier
    ease_out: float = 0.0


@dataclass
class Keyframes:
    """Keyframe track for a property."""
    property_name: str
    keyframes: List[KeyframeValue] = field(default_factory=list)
    
    def add_keyframe(self, frame: int, value: float, interpolation: str = 'linear') -> KeyframeValue:
        """Add keyframe, maintaining sorted order."""
        kf = KeyframeValue(frame=frame, value=value, interpolation=interpolation)
        self.keyframes.append(kf)
        self.keyframes.sort(key=lambda k: k.frame)
        return kf
    
    def get_value_at_frame(self, frame: int) -> float:
        """Get interpolated value at frame."""
        if not self.keyframes:
            return 0.0
        
        # Find surrounding keyframes
        before = None
        after = None
        for kf in self.keyframes:
            if kf.frame <= frame:
                before = kf
            if kf.frame >= frame and after is None:
                after = kf
        
        if before is None:
            return self.keyframes[0].value
        if after is None or before.frame == after.frame:
            return before.value
        
        # Interpolate
        t = (frame - before.frame) / (after.frame - before.frame)
        if before.interpolation == 'hold':
            return before.value
        elif before.interpolation == 'bezier':
            # Simple cubic bezier approximation
            t_squared = t * t
            t_cubed = t_squared * t
            return (1 - t) ** 3 * before.value + \
                   3 * (1 - t) ** 2 * t * (before.value + before.ease_out) + \
                   3 * (1 - t) * t ** 2 * (after.value - after.ease_in) + \
                   t_cubed * after.value
        else:  # linear
            return before.value + (after.value - before.value) * t
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            'property_name': self.property_name,
            'keyframes': [
                {
                    'frame': kf.frame,
                    'value': kf.value,
                    'interpolation': kf.interpolation,
                    'ease_in': kf.ease_in,
                    'ease_out': kf.ease_out,
                }
                for kf in self.keyframes
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Keyframes':
        """Deserialize from dict."""
        kf = cls(property_name=data['property_name'])
        for kf_data in data.get('keyframes', []):
            kf.keyframes.append(KeyframeValue(
                frame=kf_data['frame'],
                value=kf_data['value'],
                interpolation=kf_data.get('interpolation', 'linear'),
                ease_in=kf_data.get('ease_in', 0.0),
                ease_out=kf_data.get('ease_out', 0.0),
            ))
        return kf


@dataclass
class Effect:
    """Single effect in clip stack."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ''
    effect_type: str = ''  # fade, blur, color, etc.
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    keyframes: Dict[str, Keyframes] = field(default_factory=dict)
    
    def get_keyframe_track(self, property_name: str) -> Keyframes:
        """Get or create keyframe track for property."""
        if property_name not in self.keyframes:
            self.keyframes[property_name] = Keyframes(property_name=property_name)
        return self.keyframes[property_name]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            'id': self.id,
            'name': self.name,
            'effect_type': self.effect_type,
            'enabled': self.enabled,
            'parameters': self.parameters,
            'keyframes': {k: v.to_dict() for k, v in self.keyframes.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Effect':
        """Deserialize from dict."""
        eff = cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            effect_type=data.get('effect_type', ''),
            enabled=data.get('enabled', True),
            parameters=data.get('parameters', {})
        )
        for kf_name, kf_data in data.get('keyframes', {}).items():
            eff.keyframes[kf_name] = Keyframes.from_dict(kf_data)
        return eff


@dataclass
class Marker:
    """Timeline marker."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ''
    frame: int = 0
    color: str = '#FF0000'
    duration: int = 0
    notes: str = ''
    type: str = 'standard'  # standard, chapter, ai_script
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            'id': self.id,
            'name': self.name,
            'frame': self.frame,
            'color': self.color,
            'duration': self.duration,
            'notes': self.notes,
            'type': self.type,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Marker':
        """Deserialize from dict."""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            frame=data.get('frame', 0),
            color=data.get('color', '#FF0000'),
            duration=data.get('duration', 0),
            notes=data.get('notes', ''),
            type=data.get('type', 'standard'),
            metadata=data.get('metadata', {})
        )


class Clip:
    """
    Core Clip object representing a timeline item.
    """
    
    def __init__(self, 
                 name: str,
                 clip_type: ClipType = ClipType.VIDEO,
                 media_path: Optional[Path] = None,
                 duration: float = 0.0,
                 fps: int = 30):
        """
        Initialize clip.
        
        Args:
            name: Clip name
            clip_type: Type of clip
            media_path: Path to media file (if applicable)
            duration: Duration in seconds
            fps: Frame rate
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.clip_type = clip_type
        self.media_path = media_path
        self.duration = duration
        self.fps = fps
        self.start_time = 0.0
        self.in_point = 0.0
        self.out_point = duration
        self.track_index = 0
        
        # Visual properties
        self.opacity = 1.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.rotation = 0.0
        self.position_x = 0.0
        self.position_y = 0.0
        
        # Audio properties
        self.volume = 1.0
        self.pan = 0.0
        self.muted = False
        
        # Effects and animations
        self.effects: List[Effect] = []
        self.keyframes: Dict[str, Keyframes] = {}
        self.markers: List[Marker] = []
        
        # Metadata
        self.speed = 1.0
        self.reverse = False
        self.freeze_frame = False
        self.audio_attached = True
        self.linked_clip_id: Optional[str] = None
        self.tags: List[str] = []
        self.metadata: Dict[str, Any] = {}
    
    @property
    def end_time(self) -> float:
        """Get end time in seconds."""
        return self.start_time + ((self.out_point - self.in_point) / self.fps)
    
    @property
    def current_duration(self) -> float:
        """Get current duration (adjusted for in/out points)."""
        return (self.out_point - self.in_point) / self.fps
    
    @property
    def is_nested(self) -> bool:
        """Check if this is a nested timeline."""
        return self.clip_type == ClipType.NESTED
    
    def add_effect(self, effect: Effect) -> None:
        """Add effect to clip."""
        self.effects.append(effect)
    
    def remove_effect(self, effect_id: str) -> bool:
        """Remove effect by ID."""
        for i, eff in enumerate(self.effects):
            if eff.id == effect_id:
                self.effects.pop(i)
                return True
        return False
    
    def get_effect(self, effect_id: str) -> Optional[Effect]:
        """Get effect by ID."""
        for eff in self.effects:
            if eff.id == effect_id:
                return eff
        return None
    
    def reorder_effect(self, effect_id: str, new_index: int) -> None:
        """Reorder effect in stack."""
        effect = self.get_effect(effect_id)
        if effect:
            self.effects.remove(effect)
            self.effects.insert(new_index, effect)
    
    def get_keyframe_track(self, property_name: str) -> Keyframes:
        """Get or create keyframe track."""
        if property_name not in self.keyframes:
            self.keyframes[property_name] = Keyframes(property_name=property_name)
        return self.keyframes[property_name]
    
    def add_marker(self, marker: Marker) -> None:
        """Add marker."""
        self.markers.append(marker)
        self.markers.sort(key=lambda m: m.frame)
    
    def remove_marker(self, marker_id: str) -> bool:
        """Remove marker by ID."""
        for i, m in enumerate(self.markers):
            if m.id == marker_id:
                self.markers.pop(i)
                return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            'id': self.id,
            'name': self.name,
            'clip_type': self.clip_type.value,
            'media_path': str(self.media_path) if self.media_path else None,
            'duration': self.duration,
            'fps': self.fps,
            'start_time': self.start_time,
            'in_point': self.in_point,
            'out_point': self.out_point,
            'track_index': self.track_index,
            'opacity': self.opacity,
            'scale_x': self.scale_x,
            'scale_y': self.scale_y,
            'rotation': self.rotation,
            'position_x': self.position_x,
            'position_y': self.position_y,
            'volume': self.volume,
            'pan': self.pan,
            'muted': self.muted,
            'effects': [eff.to_dict() for eff in self.effects],
            'keyframes': {k: v.to_dict() for k, v in self.keyframes.items()},
            'markers': [m.to_dict() for m in self.markers],
            'speed': self.speed,
            'reverse': self.reverse,
            'freeze_frame': self.freeze_frame,
            'audio_attached': self.audio_attached,
            'linked_clip_id': self.linked_clip_id,
            'tags': self.tags,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Clip':
        """Deserialize from dict."""
        clip = cls(
            name=data.get('name', 'Clip'),
            clip_type=ClipType(data.get('clip_type', 'video')),
            media_path=Path(data['media_path']) if data.get('media_path') else None,
            duration=data.get('duration', 0.0),
            fps=data.get('fps', 30)
        )
        clip.id = data.get('id', str(uuid.uuid4()))
        clip.start_time = data.get('start_time', 0.0)
        clip.in_point = data.get('in_point', 0.0)
        clip.out_point = data.get('out_point', clip.duration)
        clip.track_index = data.get('track_index', 0)
        clip.opacity = data.get('opacity', 1.0)
        clip.scale_x = data.get('scale_x', 1.0)
        clip.scale_y = data.get('scale_y', 1.0)
        clip.rotation = data.get('rotation', 0.0)
        clip.position_x = data.get('position_x', 0.0)
        clip.position_y = data.get('position_y', 0.0)
        clip.volume = data.get('volume', 1.0)
        clip.pan = data.get('pan', 0.0)
        clip.muted = data.get('muted', False)
        clip.speed = data.get('speed', 1.0)
        clip.reverse = data.get('reverse', False)
        clip.freeze_frame = data.get('freeze_frame', False)
        clip.audio_attached = data.get('audio_attached', True)
        clip.linked_clip_id = data.get('linked_clip_id')
        clip.tags = data.get('tags', [])
        clip.metadata = data.get('metadata', {})
        
        for eff_data in data.get('effects', []):
            clip.add_effect(Effect.from_dict(eff_data))
        
        for kf_name, kf_data in data.get('keyframes', {}).items():
            clip.keyframes[kf_name] = Keyframes.from_dict(kf_data)
        
        for m_data in data.get('markers', []):
            clip.add_marker(Marker.from_dict(m_data))
        
        return clip
    
    def __repr__(self) -> str:
        return f"<Clip '{self.name}' {self.clip_type.value} {self.start_time:.2f}s+{self.current_duration:.2f}s>"
