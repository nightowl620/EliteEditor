"""
EffectsPanel - Real effects browser with DnD to timeline

Dynamically populated from MoviePyRegistry.
Drag effects onto timeline to add them.
"""

import logging
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLineEdit, QPushButton, QAbstractItemView, QLabel
)
from PySide6.QtCore import Qt, QMimeData, QPoint, Signal
from PySide6.QtGui import QDrag, QIcon, QColor
from PySide6.QtCore import Qt

from core.moviepy_registry import MoviePyRegistry, EffectCategory
from core.dnd_payload import DnDPayload

logger = logging.getLogger(__name__)


class EffectsPanel(QWidget):
    """
    Effects browser with DnD support.
    
    Shows all MoviePy effects organized by category.
    Drag to timeline to apply.
    """
    
    effect_selected = Signal(str)  # qualified_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.registry = MoviePyRegistry.instance()
        self.current_filter = ""
        
        self._setup_ui()
        self._populate_effects()
    
    def _setup_ui(self) -> None:
        """Setup UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Effects")
        title.setObjectName("effectsTitle")
        layout.addWidget(title)
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search effects...")
        self.search_box.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.search_box)
        
        # Effects list
        self.effects_list = QListWidget()
        self.effects_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.effects_list.itemDoubleClicked.connect(self._on_effect_double_clicked)
        self.effects_list.setDragDropMode(QAbstractItemView.DragOnly)
        layout.addWidget(self.effects_list)
        
        self.setLayout(layout)
    
    def _populate_effects(self) -> None:
        """Populate effects list from registry."""
        categories = self.registry.get_all_categories()
        
        for category in [EffectCategory.VIDEO_FX, EffectCategory.AUDIO_FX,
                        EffectCategory.COMPOSITING]:
            if category not in categories:
                continue
            
            # Category header
            header_item = QListWidgetItem(f"--- {category.value} ---")
            header_item.setFlags(header_item.flags() & ~Qt.ItemIsSelectable)
            header_item.setForeground(QColor(150, 150, 150))
            self.effects_list.addItem(header_item)
            
            # Effects in category
            sigs = self.registry.get_category_info(category)
            for qualified_name in sorted(sigs.keys()):
                sig = self.registry.get_signature(qualified_name)
                if sig:
                    item = QListWidgetItem(sig.name)
                    item.setData(Qt.UserRole, qualified_name)
                    self.effects_list.addItem(item)
    
    def _on_search_changed(self, text: str) -> None:
        """Filter effects by search."""
        self.current_filter = text.lower()
        self._populate_effects()
        
        if text:
            # Show only matching items
            for i in range(self.effects_list.count()):
                item = self.effects_list.item(i)
                if item:
                    should_show = text.lower() in item.text().lower()
                    self.effects_list.setRowHidden(i, not should_show)
    
    def _on_effect_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle double-click on effect."""
        qualified_name = item.data(Qt.UserRole)
        if qualified_name:
            self.effect_selected.emit(qualified_name)
    
    def startDrag(self, supportedActions) -> None:
        """Start drag operation."""
        item = self.effects_list.currentItem()
        if not item:
            return
        
        qualified_name = item.data(Qt.UserRole)
        if not qualified_name:
            return
        
        # Get effect signature
        sig = self.registry.get_signature(qualified_name)
        if not sig:
            return
        
        # Create payload
        initial_params = {}
        for param in sig.parameters:
            if param.is_optional and param.default != None:
                initial_params[param.name] = param.default
        
        payload = DnDPayload.create_effect(
            moviepy_qualified_name=qualified_name,
            display_name=sig.name,
            initial_parameters=initial_params,
        )
        
        # Create drag
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData('application/x-eliteeditor-dnd', payload.to_json().encode())
        drag.setMimeData(mime_data)
        
        logger.debug(f"Started drag: {qualified_name}")
        drag.exec(Qt.CopyAction)


class AssetsPanel(QWidget):
    """
    Asset browser with DnD support.
    
    Shows media files in project.
    Drag to timeline to add clips.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = None
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Assets")
        title.setObjectName("assetsTitle")
        layout.addWidget(title)
        
        # Assets list
        self.assets_list = QListWidget()
        self.assets_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.assets_list.setDragDropMode(QAbstractItemView.DragOnly)
        layout.addWidget(self.assets_list)
        
        # Action buttons
        actions_layout = QHBoxLayout()
        
        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self._on_import_clicked)
        actions_layout.addWidget(import_btn)
        
        layout.addLayout(actions_layout)
        self.setLayout(layout)
    
    def set_project(self, project) -> None:
        """Set current project."""
        self.project = project
        self._refresh_assets()
    
    def _refresh_assets(self) -> None:
        """Refresh asset list from project."""
        self.assets_list.clear()
        
        if not self.project:
            return
        
        # TODO: Load from project assets
        # For now, show placeholder
        item = QListWidgetItem("(No assets yet)")
        item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
        self.assets_list.addItem(item)
    
    def _on_import_clicked(self) -> None:
        """Handle import button."""
        from PySide6.QtWidgets import QFileDialog
        
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Media",
            "",
            "Media Files (*.mp4 *.mov *.avi *.mp3 *.wav *.png *.jpg);;All Files (*)"
        )
        
        if files:
            # TODO: Add to project
            logger.info(f"Imported {len(files)} files")
    
    def startDrag(self, supportedActions) -> None:
        """Start drag for asset."""
        item = self.assets_list.currentItem()
        if not item or not self.project:
            return
        
        file_path = item.data(Qt.UserRole)
        if not file_path:
            return
        
        # Create payload
        payload = DnDPayload.create_clip(file_path, item.text())
        
        # Create drag
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData('application/x-eliteeditor-dnd', payload.to_json().encode())
        drag.setMimeData(mime_data)
        
        drag.exec(Qt.CopyAction)
