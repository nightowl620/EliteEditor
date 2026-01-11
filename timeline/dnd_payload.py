"""
Real Drag & Drop Payload System

DnD payloads carry:
- Effect name
- Asset path  
- Element type (effect, clip, asset)
- Initial parameters
- MoviePy reference

Dropping creates a real TimelineMarker bound to MoviePy object.
"""

import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from PySide6.QtCore import Qt, QMimeData, QUrl
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


@dataclass
class DragPayload:
    """Complete drag payload with all necessary data."""
    type: str  # 'effect', 'clip', 'asset'
    name: str
    asset_path: Optional[str] = None
    moviepy_callable: Optional[str] = None  # Function name in registry
    effect_category: Optional[str] = None  # 'video', 'audio', 'compositing'
    initial_parameters: Dict[str, Any] = None
    duration_seconds: float = 5.0
    
    def __post_init__(self):
        if self.initial_parameters is None:
            self.initial_parameters = {}
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        data = asdict(self)
        return json.dumps(data)
    
    @staticmethod
    def from_json(json_str: str) -> 'DragPayload':
        """Deserialize from JSON."""
        data = json.loads(json_str)
        return DragPayload(**data)
    
    def to_mime(self) -> QMimeData:
        """Create QMimeData for dragging."""
        mime = QMimeData()
        
        # Store as JSON
        mime.setText(self.to_json())
        
        # Also set custom MIME type
        mime.setData("elite/drag-payload", self.to_json().encode('utf-8'))
        
        # If it's an asset, add file URL
        if self.asset_path:
            path = Path(self.asset_path)
            if path.exists():
                mime.setUrls([QUrl.fromLocalFile(str(path))])
        
        return mime
    
    @staticmethod
    def from_mime(mime_data: QMimeData) -> Optional['DragPayload']:
        """Extract payload from QMimeData."""
        # Try custom MIME type first
        if mime_data.hasFormat("elite/drag-payload"):
            try:
                data = mime_data.data("elite/drag-payload").decode('utf-8')
                return DragPayload.from_json(data)
            except Exception as e:
                logger.debug(f"Failed to extract elite payload: {e}")
        
        # Try from text
        if mime_data.hasText():
            try:
                text = mime_data.text()
                if text.startswith('{'):
                    return DragPayload.from_json(text)
            except Exception:
                pass
        
        # Try from URLs (asset files)
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if urls:
                path = urls[0].toLocalFile()
                if path:
                    return DragPayload(
                        type='asset',
                        name=Path(path).stem,
                        asset_path=path
                    )
        
        return None


class EffectDragSource(QWidget):
    """Wrapper for draggable effects."""
    
    def __init__(self, effect_name: str, category: str, parent=None):
        super().__init__(parent)
        self.effect_name = effect_name
        self.category = category
    
    def create_drag_payload(self) -> DragPayload:
        """Create drag payload for this effect."""
        return DragPayload(
            type='effect',
            name=self.effect_name,
            moviepy_callable=self.effect_name,
            effect_category=self.category,
            duration_seconds=5.0
        )
    
    def start_drag(self):
        """Initiate drag operation."""
        payload = self.create_drag_payload()
        drag = QDrag(self)
        drag.setMimeData(payload.to_mime())
        drag.exec(Qt.CopyAction)


class AssetDragSource(QWidget):
    """Wrapper for draggable assets."""
    
    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
    
    def create_drag_payload(self) -> DragPayload:
        """Create drag payload for this asset."""
        path = Path(self.file_path)
        return DragPayload(
            type='asset',
            name=path.stem,
            asset_path=self.file_path
        )
    
    def start_drag(self):
        """Initiate drag operation."""
        payload = self.create_drag_payload()
        drag = QDrag(self)
        drag.setMimeData(payload.to_mime())
        drag.exec(Qt.CopyAction)


def create_marker_from_payload(payload: DragPayload, timeline, track_id: str, 
                              start_frame: int) -> Optional[object]:
    """
    Create a real TimelineMarker from a drag payload.
    Binds to actual MoviePy callable if available.
    """
    if payload is None:
        return None
    
    from timeline.graphics_timeline import TimelineMarker
    from rendering.moviepy_registry import get_registry
    import uuid
    
    try:
        # Get MoviePy reference if available
        moviepy_ref = None
        if payload.moviepy_callable:
            registry = get_registry()
            effect = registry.get_effect(payload.moviepy_callable)
            if effect:
                moviepy_ref = effect.callable
        
        # Determine duration in frames
        fps = getattr(timeline, 'fps', 30)
        duration_frames = int(payload.duration_seconds * fps)
        
        # Create marker
        marker = TimelineMarker(
            id=str(uuid.uuid4()),
            name=payload.name,
            track_id=track_id,
            start_frame=start_frame,
            end_frame=start_frame + duration_frames,
            moviepy_ref=moviepy_ref,
            parameters=payload.initial_parameters.copy()
        )
        
        logger.info(f"Created marker from payload: {marker.name}")
        return marker
    
    except Exception as e:
        logger.error(f"Failed to create marker from payload: {e}")
        return None


# Global drag payload manager
_current_payload = None


def set_current_payload(payload: DragPayload):
    """Store current drag payload."""
    global _current_payload
    _current_payload = payload


def get_current_payload() -> Optional[DragPayload]:
    """Get current drag payload."""
    global _current_payload
    return _current_payload


def clear_current_payload():
    """Clear current drag payload."""
    global _current_payload
    _current_payload = None
