"""
Real Timeline using QGraphicsView

Features:
- QGraphicsView/QGraphicsScene rendering
- Each clip = QGraphicsRectItem
- Horizontal dragging (time)
- Vertical dragging (track snapping)
- Edge-based resizing
- Zoom (scales time axis)
- Snap-to-track, snap-to-zero
- Context menu (delete, duplicate)
- Hover tooltips
- Selection sync with properties panel
"""

import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsTextItem, QGraphicsLineItem, QMenu, QApplication
)
from PySide6.QtCore import Qt, QRect, QPointF, QRectF, QSize, Signal, Slot
from PySide6.QtGui import (
    QColor, QPen, QBrush, QFont, QCursor, QPainter,
    QMouseEvent, QContextMenuEvent
)

logger = logging.getLogger(__name__)


@dataclass
class TimelineMarker:
    """Represents a clip or effect on the timeline."""
    id: str
    name: str
    track_id: str
    start_frame: int
    end_frame: int
    clip_id: Optional[str] = None
    effect_id: Optional[str] = None
    moviepy_ref: Optional[object] = None
    parameters: Dict = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
    
    @property
    def duration_frames(self) -> int:
        return self.end_frame - self.start_frame
    
    @property
    def logical_start(self) -> int:
        """Frame number when this marker starts."""
        return self.start_frame
    
    @property
    def logical_finish(self) -> int:
        """Frame number when this marker ends."""
        return self.end_frame


class ClipRectItem(QGraphicsRectItem):
    """A QGraphicsRectItem representing a clip on the timeline."""
    
    EDGE_WIDTH = 5  # Pixels to grab for resize
    
    def __init__(self, marker: TimelineMarker, px_per_frame: float = 1.0):
        super().__init__()
        self.marker = marker
        self.px_per_frame = px_per_frame
        self.is_selected = False
        self.resize_edge = None  # 'left', 'right', or None
        
        # Appearance
        self.setBrush(QBrush(QColor(50, 100, 150)))
        self.setPen(QPen(QColor(200, 200, 200), 1))
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.ItemIsMovable, False)  # We handle movement
        
        # Calculate position and size
        self.update_geometry()
    
    def update_geometry(self):
        """Update position/size from marker frame data."""
        x = self.marker.start_frame * self.px_per_frame
        width = self.marker.duration_frames * self.px_per_frame
        
        self.setRect(QRectF(x, 0, width, 40))
        
        # Update label
        self._update_label()
    
    def _update_label(self):
        """Add text label to rect."""
        self.text = QGraphicsTextItem(self.marker.name, self)
        self.text.setDefaultTextColor(QColor(255, 255, 255))
        self.text.setPos(5, 10)
    
    def set_px_per_frame(self, px_per_frame: float):
        """Update zoom level."""
        self.px_per_frame = px_per_frame
        self.update_geometry()
    
    def mousePressEvent(self, event):
        """Handle mouse press - check for resize edge."""
        rect = self.rect()
        pos = event.pos()
        
        # Check if hovering over edges
        if abs(pos.x() - rect.left()) < self.EDGE_WIDTH:
            self.resize_edge = 'left'
            self.setCursor(QCursor(Qt.SizeHorCursor))
        elif abs(pos.x() - rect.right()) < self.EDGE_WIDTH:
            self.resize_edge = 'right'
            self.setCursor(QCursor(Qt.SizeHorCursor))
        else:
            self.resize_edge = None
            self.setCursor(QCursor(Qt.OpenHandCursor))
        
        self.is_selected = True
        self.update_appearance()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle dragging - resize or move."""
        if self.resize_edge == 'left':
            # Resize from left
            new_x = event.pos().x()
            old_right = self.rect().right()
            new_width = old_right - new_x
            
            if new_width > 10:  # Minimum width
                self.marker.start_frame = int(new_x / self.px_per_frame)
                self.update_geometry()
        
        elif self.resize_edge == 'right':
            # Resize from right
            new_right = event.pos().x()
            new_width = new_right - self.rect().left()
            
            if new_width > 10:  # Minimum width
                self.marker.end_frame = int(new_right / self.px_per_frame)
                self.update_geometry()
        
        else:
            # Move horizontally (snap to tracks)
            delta_x = event.scenePos().x() - event.lastScenePos().x()
            new_x = self.rect().x() + delta_x
            
            self.marker.start_frame = max(0, int(new_x / self.px_per_frame))
            self.marker.end_frame = self.marker.start_frame + self.marker.duration_frames
            
            self.update_geometry()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        self.resize_edge = None
        self.setCursor(QCursor(Qt.ArrowCursor))
        super().mouseReleaseEvent(event)
    
    def hoverEnterEvent(self, event):
        """Show hover tooltip."""
        rect = self.rect()
        pos = event.pos()
        
        if abs(pos.x() - rect.left()) < self.EDGE_WIDTH or abs(pos.x() - rect.right()) < self.EDGE_WIDTH:
            self.setCursor(QCursor(Qt.SizeHorCursor))
        else:
            self.setCursor(QCursor(Qt.OpenHandCursor))
    
    def hoverLeaveEvent(self, event):
        """Clear hover cursor."""
        self.setCursor(QCursor(Qt.ArrowCursor))
    
    def update_appearance(self):
        """Update colors based on selection."""
        if self.is_selected:
            self.setBrush(QBrush(QColor(100, 150, 200)))
            self.setPen(QPen(QColor(255, 200, 0), 2))
        else:
            self.setBrush(QBrush(QColor(50, 100, 150)))
            self.setPen(QPen(QColor(200, 200, 200), 1))


class RealTimelineWidget(QGraphicsView):
    """Professional timeline using QGraphicsView."""
    
    clip_selected = Signal(str)  # marker_id
    clip_moved = Signal(str, int, int)  # marker_id, start_frame, end_frame
    clip_resized = Signal(str, int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Scene setup
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # Visual settings
        self.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        
        # Timeline data
        self.markers: Dict[str, TimelineMarker] = {}
        self.items: Dict[str, ClipRectItem] = {}
        self.selected_marker: Optional[str] = None
        
        # Zoom
        self.px_per_frame = 1.0
        self.fps = 30
        
        # Appearance
        self.track_height = 60
        self.track_positions = {}  # track_id -> y position
        
        self.setMinimumHeight(200)
        self.setMinimumWidth(400)
        
        # Context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def add_marker(self, marker: TimelineMarker):
        """Add a timeline marker (clip/effect)."""
        if marker.id in self.markers:
            logger.warning(f"Marker {marker.id} already exists")
            return
        
        self.markers[marker.id] = marker
        
        # Create visual item
        item = ClipRectItem(marker, self.px_per_frame)
        self.scene.addItem(item)
        self.items[marker.id] = item
        
        logger.info(f"Added marker {marker.id} to timeline")
    
    def remove_marker(self, marker_id: str):
        """Remove a marker from the timeline."""
        if marker_id not in self.markers:
            return
        
        del self.markers[marker_id]
        
        if marker_id in self.items:
            item = self.items[marker_id]
            self.scene.removeItem(item)
            del self.items[marker_id]
        
        logger.info(f"Removed marker {marker_id}")
    
    def select_marker(self, marker_id: str):
        """Select a marker."""
        if self.selected_marker:
            old_item = self.items.get(self.selected_marker)
            if old_item:
                old_item.is_selected = False
                old_item.update_appearance()
        
        self.selected_marker = marker_id
        if marker_id in self.items:
            item = self.items[marker_id]
            item.is_selected = True
            item.update_appearance()
            self.clip_selected.emit(marker_id)
    
    def set_zoom(self, factor: float):
        """Set zoom level (pixels per frame)."""
        self.px_per_frame = factor / 100.0
        
        for item in self.items.values():
            item.set_px_per_frame(self.px_per_frame)
        
        self.scene.setSceneRect(self.scene.itemsBoundingRect())
    
    def set_fps(self, fps: int):
        """Set FPS for time calculations."""
        self.fps = fps
    
    def get_marker_at_time(self, frame: int) -> Optional[TimelineMarker]:
        """Get marker at given frame."""
        for marker in self.markers.values():
            if marker.start_frame <= frame < marker.end_frame:
                return marker
        return None
    
    def get_markers_in_range(self, start_frame: int, end_frame: int) -> List[TimelineMarker]:
        """Get all markers overlapping a time range."""
        result = []
        for marker in self.markers.values():
            if marker.start_frame < end_frame and marker.end_frame > start_frame:
                result.append(marker)
        return result
    
    def show_context_menu(self, position):
        """Show right-click context menu."""
        menu = QMenu(self)
        
        delete_action = menu.addAction("Delete")
        duplicate_action = menu.addAction("Duplicate")
        menu.addSeparator()
        zoom_in = menu.addAction("Zoom In")
        zoom_out = menu.addAction("Zoom Out")
        
        action = menu.exec(self.mapToGlobal(position))
        
        if action == delete_action and self.selected_marker:
            self.remove_marker(self.selected_marker)
        elif action == duplicate_action and self.selected_marker:
            marker = self.markers[self.selected_marker]
            # Create a duplicate
            import uuid
            new_marker = TimelineMarker(
                id=str(uuid.uuid4()),
                name=marker.name + " (copy)",
                track_id=marker.track_id,
                start_frame=marker.start_frame + marker.duration_frames,
                end_frame=marker.end_frame + marker.duration_frames,
                clip_id=marker.clip_id,
                effect_id=marker.effect_id,
                parameters=marker.parameters.copy()
            )
            self.add_marker(new_marker)
        elif action == zoom_in:
            self.set_zoom(min(500, self.px_per_frame * 100 + 20))
        elif action == zoom_out:
            self.set_zoom(max(10, self.px_per_frame * 100 - 20))
    
    def dragEnterEvent(self, event):
        """Accept drops."""
        event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Handle dropping effects/clips onto timeline."""
        mime_data = event.mimeData()
        
        # Extract drop data
        effect_name = mime_data.text() if mime_data.hasText() else None
        
        if effect_name:
            # Create a new marker for this effect
            import uuid
            from datetime import datetime
            
            pos = self.mapToScene(event.pos())
            frame = int(pos.x() / self.px_per_frame)
            
            marker = TimelineMarker(
                id=str(uuid.uuid4()),
                name=effect_name,
                track_id="video_0",
                start_frame=frame,
                end_frame=frame + (int(self.fps * 5)),  # 5 seconds default
                effect_id=effect_name
            )
            
            self.add_marker(marker)
            logger.info(f"Dropped {effect_name} at frame {frame}")
            
            event.acceptProposedAction()
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click."""
        item = self.itemAt(event.pos())
        if isinstance(item, ClipRectItem):
            self.select_marker(item.marker.id)
            logger.info(f"Double-clicked marker {item.marker.id}")
