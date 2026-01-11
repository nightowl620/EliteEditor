"""
DnD Payload - Serializable drag-and-drop data

Carries MoviePy callables, effects, clips, and parameters
across UI elements.
"""

import json
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class DnDPayload:
    """
    Drag-and-drop payload.
    
    Carries information needed to create a TimelineMarker
    when dropped on timeline.
    """
    payload_type: str  # 'effect', 'clip', 'asset', 'adjustment'
    source_widget: str  # 'effects_panel', 'assets_panel', 'timeline'
    
    # For effects: MoviePy qualified name
    moviepy_qualified_name: Optional[str] = None
    
    # For clips/assets: file path
    source_file: Optional[str] = None
    
    # Display name
    display_name: str = ''
    
    # Initial parameters
    initial_parameters: Dict[str, Any] = None
    
    # Metadata
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize defaults."""
        if self.initial_parameters is None:
            self.initial_parameters = {}
        if self.metadata is None:
            self.metadata = {}
    
    def to_json(self) -> str:
        """Serialize to JSON string for MIME data."""
        return json.dumps(self.to_dict())
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            'payload_type': self.payload_type,
            'source_widget': self.source_widget,
            'moviepy_qualified_name': self.moviepy_qualified_name,
            'source_file': self.source_file,
            'display_name': self.display_name,
            'initial_parameters': self.initial_parameters,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DnDPayload':
        """Deserialize from JSON string."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except Exception:
            return None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DnDPayload':
        """Deserialize from dict."""
        return cls(
            payload_type=data.get('payload_type', 'effect'),
            source_widget=data.get('source_widget', ''),
            moviepy_qualified_name=data.get('moviepy_qualified_name'),
            source_file=data.get('source_file'),
            display_name=data.get('display_name', ''),
            initial_parameters=data.get('initial_parameters', {}),
            metadata=data.get('metadata', {}),
        )
    
    @classmethod
    def create_effect(cls, moviepy_qualified_name: str, display_name: str,
                     initial_parameters: Dict[str, Any] = None,
                     metadata: Dict[str, Any] = None) -> 'DnDPayload':
        """Create effect payload."""
        return cls(
            payload_type='effect',
            source_widget='effects_panel',
            moviepy_qualified_name=moviepy_qualified_name,
            display_name=display_name or moviepy_qualified_name.split('.')[-1],
            initial_parameters=initial_parameters or {},
            metadata=metadata or {},
        )
    
    @classmethod
    def create_clip(cls, source_file: str, display_name: str = None,
                   metadata: Dict[str, Any] = None) -> 'DnDPayload':
        """Create clip/asset payload."""
        return cls(
            payload_type='clip',
            source_widget='assets_panel',
            source_file=source_file,
            display_name=display_name or source_file.split('\\')[-1],
            metadata=metadata or {},
        )
    
    @classmethod
    def create_from_timeline(cls, marker_id: str, marker_type: str) -> 'DnDPayload':
        """Create payload for drag from timeline (reordering)."""
        return cls(
            payload_type=marker_type,
            source_widget='timeline',
            display_name=f'Timeline {marker_type}',
            metadata={'marker_id': marker_id},
        )
