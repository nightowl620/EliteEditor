"""
QGraphicsTimeline - Professional timeline UI using QGraphicsView

Features:
- Track rows with grid
- Draggable/resizable clip items
- Snap to grid and tracks
- Visual feedback
- Updates underlying data model
- DnD support
"""

from typing import Optional, Dict, List, Tuple
import logging

from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem,
    QAbstractItemView, QApplication
)
from PySide6.QtCore import Qt, QRect, QSize, QPoint, QTimer, Signal, Slot
from PySide6.QtGui import (
    QColor, QPen, QBrush, QFont, QDrag, QCursor, QPainter
)
from PySide6.QtCore import QMimeData

from core.timeline_markers import Timeline, TimelineMarker, TimelineTrack
from core.dnd_payload import DnDPayload

logger = logging.getLogger(__name__)


class TimelineMarkerItem(QGraphicsRectItem):
    """
    Single clip/effect item on timeline.
    
    - Draggable horizontally and vertically (between tracks)
    - Resizable from edges
    - Updates model on move/resize
    - Shows parameter info
    """
    
    # Resize edge width (pixels)
    EDGE_WIDTH = 8
    
    def __init__(self, marker: TimelineMarker, timeline: Timeline,
                 pixels_per_frame: float, track_height: int):
        super().__init__()
        
        self.marker = marker
        self.timeline = timeline
        self.pixels_per_frame = pixels_per_frame
        self.track_height = track_height
        
        # Visual state
        self.is_selected = False
        self.is_resizing_left = False
        self.is_resizing_right = False
        self.drag_start_pos = None
        
        # Setup graphics item
        self._update_geometry()
        self._setup_appearance()
        
        # Make interactive
        self.setAcceptHoverEvents(True)
        self.setFlag(self.ItemIsSelectable, True)
        self.setFlag(self.ItemIsMovable, True)
        self.setCursor(QCursor(Qt.ArrowCursor))
        
        # Text label
        self.text_item = QGraphicsTextItem(self)
        self.text_item.setPlainText(marker.name or marker.marker_type)
        font = QFont("Segoe UI", 9)
        self.text_item.setFont(font)
        self.text_item.setPos(4, 4)
    
    def _update_geometry(self) -> None:
        """Update item position/size from marker data."""
        x = self.marker.start_frame * self.pixels_per_frame
        y = self.marker.track_index * self.track_height + 2
        width = max(10, self.marker.duration_frames * self.pixels_per_frame)
        height = self.track_height - 4
        
        self.setRect(QRect(0, 0, int(width), int(height)))
        self.setPos(int(x), int(y))
    
    def _setup_appearance(self) -> None:
        """Setup colors and styling."""
        if self.marker.marker_type == 'clip':
            color = QColor(50, 150, 200)  # Blue
        elif self.marker.marker_type == 'effect':
            color = QColor(150, 100, 50)  # Brown
        else:
            color = QColor(100, 100, 100)  # Gray
        
        self.setBrush(QBrush(color))
        
        border = QColor(255, 255, 255) if self.is_selected else QColor(150, 150, 150)
        pen = QPen(border, 2 if self.is_selected else 1)
        self.setPen(pen)
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse press (drag start)."""
        if event.button() == Qt.LeftButton:
            # Check if clicking edge for resize
            rect = self.rect()
            pos = event.pos()
            
            if pos.x() < self.EDGE_WIDTH:
                self.is_resizing_left = True
            elif pos.x() > rect.width() - self.EDGE_WIDTH:
                self.is_resizing_right = True
            else:
                self.drag_start_pos = self.pos()
            
            self.is_selected = True
            self._setup_appearance()
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move (dragging/resizing)."""
        if self.is_resizing_left:
            # Resize from left
            delta = event.scenePos().x() - self.scenePos().x()
            frames = int(delta / self.pixels_per_frame)
            new_start = max(0, self.marker.start_frame + frames)
            duration_delta = self.marker.start_frame - new_start
            new_duration = self.marker.duration_frames + duration_delta
            
            if new_duration > 1:
                self.marker.start_frame = new_start
                self.marker.duration_frames = new_duration
                self._update_geometry()
        
        elif self.is_resizing_right:
            # Resize from right
            delta = event.scenePos().x() - (self.scenePos().x() + self.rect().width())
            frames = int(delta / self.pixels_per_frame)
            new_duration = max(1, self.marker.duration_frames + frames)
            self.marker.duration_frames = new_duration
            self._update_geometry()
        
        else:
            # Regular drag
            super().mouseMoveEvent(event)
        
        self.scene().update()
    
    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release (drop/end resize)."""
        if event.button() == Qt.LeftButton:
            if self.is_resizing_left or self.is_resizing_right:
                # Resize done
                self.is_resizing_left = False
                self.is_resizing_right = False
            
            elif self.drag_start_pos is not None:
                # Drag done - update model
                new_pos = self.pos()
                new_frame = int(new_pos.x() / self.pixels_per_frame)
                new_track = int((new_pos.y() - 2) / self.track_height)
                
                # Snap to grid
                snap_frames = 5
                new_frame = (new_frame // snap_frames) * snap_frames
                
                # Constrain
                new_frame = max(0, new_frame)
                new_track = max(0, min(new_track, len(self.timeline.tracks) - 1))
                
                # Update marker
                self.marker.start_frame = new_frame
                self.marker.track_index = new_track
                self.drag_start_pos = None
                
                self._update_geometry()
        
        super().mouseReleaseEvent(event)
    
    def mouseDoubleClickEvent(self, event) -> None:
        """Handle double-click (select and emit)."""
        self.is_selected = True
        self._setup_appearance()
        # Will emit selection signal to properties panel
        super().mouseDoubleClickEvent(event)
    
    def hoverEnterEvent(self, event) -> None:
        """Handle hover enter."""
        self.setCursor(QCursor(Qt.PointingHandCursor))
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event) -> None:
        """Handle hover leave."""
        self.setCursor(QCursor(Qt.ArrowCursor))
        super().hoverLeaveEvent(event)
    
    def hoverMoveEvent(self, event) -> None:
        """Handle hover move (show resize cursor at edges)."""
        rect = self.rect()
        pos = event.pos()
        
        if pos.x() < self.EDGE_WIDTH or pos.x() > rect.width() - self.EDGE_WIDTH:
            self.setCursor(QCursor(Qt.SizeHorCursor))
        else:
            self.setCursor(QCursor(Qt.PointingHandCursor))
        
        super().hoverMoveEvent(event)


class TimelineGraphicsView(QGraphicsView):
    """
    Professional timeline view.
    
    Shows tracks, clips, effects with full interactivity.
    Handles DnD, zooming, scrolling, playhead.
    """
    
    # Signals
    marker_selected = Signal(str)  # marker_id
    marker_double_clicked = Signal(str)  # marker_id
    marker_moved = Signal(str)  # marker_id
    
    # Default parameters
    DEFAULT_PIXELS_PER_FRAME = 2.0
    TRACK_HEIGHT = 100
    GRID_SPACING = 5  # frames
    
    def __init__(self, timeline: Timeline, parent=None):
        super().__init__(parent)
        
        self.timeline = timeline
        self.pixels_per_frame = self.DEFAULT_PIXELS_PER_FRAME
        self.playhead_x = 0
        
        # Graphics scene
        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)
        
        # Timeline items cache
        self.marker_items: Dict[str, TimelineMarkerItem] = {}
        
        # Setup
        self._setup_view()
        self._create_tracks()
        self._add_markers()
    
    def _setup_view(self) -> None:
        """Setup view properties."""
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setAcceptDrops(True)
        
        # Scene background
        self.scene_obj.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
    
    def _create_tracks(self) -> None:
        """Create track background items."""
        num_tracks = len(self.timeline.tracks)
        
        for i in range(num_tracks):
            # Track background
            track_rect = self.scene_obj.addRect(
                0, i * self.TRACK_HEIGHT, 10000, self.TRACK_HEIGHT
            )
            
            if i % 2 == 0:
                track_rect.setBrush(QBrush(QColor(40, 40, 40)))
            else:
                track_rect.setBrush(QBrush(QColor(50, 50, 50)))
            
            track_rect.setPen(QPen(QColor(70, 70, 70), 1))
            track_rect.setZValue(-100)
            
            # Track label
            track = self.timeline.get_track_by_index(i)
            if track:
                label = self.scene_obj.addText(track.name)
                label.setPos(-100, i * self.TRACK_HEIGHT + 5)
                label.setDefaultTextColor(QColor(200, 200, 200))
                label.setZValue(-50)
    
    def _add_markers(self) -> None:
        """Add all markers as graphics items."""
        for marker in self.timeline.get_all_markers():
            self._create_marker_item(marker)
    
    def _create_marker_item(self, marker: TimelineMarker) -> TimelineMarkerItem:
        """Create and add graphics item for marker."""
        item = TimelineMarkerItem(
            marker, self.timeline, self.pixels_per_frame, self.TRACK_HEIGHT
        )
        self.scene_obj.addItem(item)
        self.marker_items[marker.id] = item
        return item
    
    def add_marker_from_payload(self, payload: DnDPayload, frame: int,
                               track_index: int) -> Optional[TimelineMarker]:
        """
        Create and add marker from DnD payload.
        
        This is called on drop.
        """
        marker = TimelineMarker(
            name=payload.display_name,
            marker_type=payload.payload_type,
            start_frame=frame,
            duration_frames=60,  # Default 2 seconds at 30fps
            track_index=track_index,
            moviepy_qualified_name=payload.moviepy_qualified_name,
            source_file=payload.source_file,
        )
        
        # Add parameters
        for param_name, param_value in payload.initial_parameters.items():
            marker.add_parameter(param_name, param_value, 'float', param_name)
        
        # Add to timeline
        if self.timeline.add_marker(marker):
            self._create_marker_item(marker)
            return marker
        
        return None
    
    def dragEnterEvent(self, event) -> None:
        """Handle drag enter."""
        mime_data = event.mimeData()
        if mime_data.hasFormat('application/x-eliteeditor-dnd'):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event) -> None:
        """Handle drag move."""
        event.acceptProposedAction()
    
    def dropEvent(self, event) -> None:
        """Handle drop."""
        mime_data = event.mimeData()
        if mime_data.hasFormat('application/x-eliteeditor-dnd'):
            payload_json = mime_data.data('application/x-eliteeditor-dnd').data().decode()
            payload = DnDPayload.from_json(payload_json)
            
            if payload:
                # Get drop position
                scene_pos = self.mapToScene(event.pos())
                frame = int(scene_pos.x() / self.pixels_per_frame)
                track_index = int(scene_pos.y() / self.TRACK_HEIGHT)
                
                # Add marker
                marker = self.add_marker_from_payload(payload, frame, track_index)
                if marker:
                    logger.info(f"Added marker: {marker.name} at frame {frame}")
                    event.acceptProposedAction()
        
        event.ignore()
    
    def wheelEvent(self, event) -> None:
        """Handle zoom via mouse wheel."""
        if event.modifiers() & Qt.ControlModifier:
            # Zoom
            zoom_factor = 1.2 if event.angleDelta().y() > 0 else 0.8
            self.pixels_per_frame *= zoom_factor
            
            # Update all items
            for item in self.marker_items.values():
                item.pixels_per_frame = self.pixels_per_frame
                item._update_geometry()
            
            self.scene_obj.update()
            event.accept()
        else:
            super().wheelEvent(event)
    
    def set_playhead(self, frame: int) -> None:
        """Update playhead position."""
        self.playhead_x = int(frame * self.pixels_per_frame)
        self.scene_obj.update()
    
    def paintEvent(self, event) -> None:
        """Paint playhead line."""
        super().paintEvent(event)
        
        # Draw playhead (vertical red line)
        if self.playhead_x > 0:
            painter = QPainter(self.viewport())
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            x = self.mapFromScene(self.playhead_x, 0).x()
            painter.drawLine(x, 0, x, self.height())
