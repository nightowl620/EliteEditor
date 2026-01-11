"""
HomePage - Project browser and launcher

Shows recent projects, allows create/open/delete projects.
This is the startup page for Elite Editor.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QDialog, QLineEdit, QSpinBox, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap, QColor

from core.config import ConfigManager
from core.project import ProjectManager, ProjectMetadata

logger = logging.getLogger(__name__)


class ProjectItem(QListWidgetItem):
    """Custom item for recent project."""
    
    def __init__(self, project_path: Path, metadata: ProjectMetadata):
        super().__init__()
        
        self.project_path = project_path
        self.metadata = metadata
        
        # Display text
        display = f"{metadata.name}\n{metadata.modified_at}"
        self.setText(display)
        
        # Store path for retrieval
        self.setData(Qt.UserRole, str(project_path))


class NewProjectDialog(QDialog):
    """Dialog to create new project."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Project name
        layout.addWidget(QLabel("Project Name:"))
        self.name_input = QLineEdit()
        self.name_input.setText("Untitled Project")
        layout.addWidget(self.name_input)
        
        # Resolution
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("Resolution:"))
        
        self.width_input = QSpinBox()
        self.width_input.setValue(1920)
        self.width_input.setSuffix(" px")
        res_layout.addWidget(self.width_input)
        
        res_layout.addWidget(QLabel("×"))
        
        self.height_input = QSpinBox()
        self.height_input.setValue(1080)
        self.height_input.setSuffix(" px")
        res_layout.addWidget(self.height_input)
        
        layout.addLayout(res_layout)
        
        # FPS
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("Frame Rate:"))
        
        self.fps_input = QSpinBox()
        self.fps_input.setValue(30)
        self.fps_input.setSuffix(" fps")
        fps_layout.addWidget(self.fps_input)
        
        layout.addLayout(fps_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        create_btn = QPushButton("Create")
        create_btn.clicked.connect(self.accept)
        btn_layout.addWidget(create_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def get_project_params(self) -> Dict[str, Any]:
        """Get entered project parameters."""
        return {
            'name': self.name_input.text(),
            'width': self.width_input.value(),
            'height': self.height_input.value(),
            'fps': self.fps_input.value(),
        }


class HomePage(QWidget):
    """
    Home page / project browser.
    
    Shown on startup. Allows create/open/delete projects.
    """
    
    # Signals
    project_selected = Signal(Path)  # Path to .eep file
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.config_manager = ConfigManager.instance()
        self.project_manager = ProjectManager.instance()
        
        self._setup_ui()
        self._refresh_recent_projects()
    
    def _setup_ui(self) -> None:
        """Setup UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Elite Editor")
        title.setObjectName("homeTitle")
        layout.addWidget(title)
        
        subtitle = QLabel("Professional Desktop Video Editor")
        subtitle.setObjectName("homeSubtitle")
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # Recent projects section
        recent_label = QLabel("Recent Projects")
        recent_label.setObjectName("recentLabel")
        layout.addWidget(recent_label)
        
        # Recent projects list
        self.projects_list = QListWidget()
        self.projects_list.itemDoubleClicked.connect(self._on_project_selected)
        layout.addWidget(self.projects_list)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        new_btn = QPushButton("New Project")
        new_btn.clicked.connect(self._on_new_project)
        btn_layout.addWidget(new_btn)
        
        open_btn = QPushButton("Open Project")
        open_btn.clicked.connect(self._on_open_project)
        btn_layout.addWidget(open_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._on_delete_project)
        btn_layout.addWidget(delete_btn)
        
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        
        self.setLayout(layout)
    
    def _refresh_recent_projects(self) -> None:
        """Refresh recent projects list."""
        self.projects_list.clear()
        
        recent = self.project_manager.get_recent_projects()
        if not recent:
            empty_item = QListWidgetItem("No recent projects")
            empty_item.setFlags(empty_item.flags() & ~Qt.ItemIsSelectable)
            empty_item.setForeground(QColor(150, 150, 150))
            self.projects_list.addItem(empty_item)
            return
        
        for project_info in recent[:10]:  # Show last 10
            try:
                project_path = Path(project_info['path'])
                if project_path.exists():
                    # Load metadata to display
                    metadata = ProjectMetadata.from_dict(project_info.get('metadata', {}))
                    item = ProjectItem(project_path, metadata)
                    self.projects_list.addItem(item)
            except Exception as e:
                logger.warning(f"Failed to load recent project: {e}")
    
    def _on_project_selected(self, item: QListWidgetItem) -> None:
        """Handle project selection."""
        if isinstance(item, ProjectItem):
            logger.info(f"Opening project: {item.project_path}")
            self.project_selected.emit(item.project_path)
    
    def _on_new_project(self) -> None:
        """Handle new project button."""
        dialog = NewProjectDialog(self)
        if dialog.exec() == QDialog.Accepted:
            params = dialog.get_project_params()
            
            # Create project
            project = self.project_manager.create_project(
                name=params['name'],
                fps=params['fps'],
                width=params['width'],
                height=params['height']
            )
            
            # Save project
            if self.project_manager.save_project(project):
                logger.info(f"Created project: {params['name']}")
                self._refresh_recent_projects()
                
                # Open it
                self.project_selected.emit(project.file_path)
            else:
                QMessageBox.critical(self, "Error", "Failed to create project")
    
    def _on_open_project(self) -> None:
        """Handle open project button."""
        projects_dir = ConfigManager.instance().paths.projects_dir
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            str(projects_dir),
            "Elite Editor Projects (*.eep);;All Files (*)"
        )
        
        if file_path:
            project_path = Path(file_path)
            logger.info(f"Opening project: {project_path}")
            self.project_selected.emit(project_path)
    
    def _on_delete_project(self) -> None:
        """Handle delete project button."""
        item = self.projects_list.currentItem()
        if not isinstance(item, ProjectItem):
            return
        
        reply = QMessageBox.question(
            self,
            "Delete Project",
            f"Delete project '{item.metadata.name}'?\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                item.project_path.unlink()
                logger.info(f"Deleted project: {item.project_path}")
                self._refresh_recent_projects()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete project: {e}")
