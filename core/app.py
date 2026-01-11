"""
Elite Editor Application - Main bootstrap and window management

This is the main application controller that:
- Manages the application lifecycle
- Shows Home Page on startup
- Loads projects when selected
- Manages the main editor window layout
"""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QDockWidget, QMenu, QToolBar, QStatusBar, QMessageBox,
    QProgressDialog, QApplication, QSplitter
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, Slot
from PySide6.QtGui import QIcon, QAction, QKeySequence, QFontDatabase, QFont

from core.config import ConfigManager
from core.project import ProjectManager
from core.timeline_markers import Timeline
from core.moviepy_registry import MoviePyRegistry

from ui.home_page import HomePage
from ui.graphics_timeline import TimelineGraphicsView
from ui.effects_panel import EffectsPanel, AssetsPanel
from ui.properties_panel import PropertiesPanel
from ui.main_window import PreviewWidget

from rendering.preview_renderer import get_preview_renderer, PreviewRenderJob
import uuid
from PySide6.QtCore import QUrl, QTimer

logger = logging.getLogger(__name__)


class EditorView(QWidget):
    """
    Main editor view when project is loaded.
    
    Contains:
    - Timeline graphics view (center)
    - Effects panel (left)
    - Properties panel (right)
    - Assets panel (bottom)
    """
    
    def __init__(self, timeline: Timeline, parent=None):
        super().__init__(parent)
        
        self.timeline = timeline
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup main editor layout."""
        main_layout = QHBoxLayout(self)
        
        # Left: Effects panel
        self.effects_panel = EffectsPanel()
        
        # Center: Timeline and preview
        center_layout = QVBoxLayout()
        
        # Timeline graphics view
        self.timeline_view = TimelineGraphicsView(self.timeline)
        center_layout.addWidget(self.timeline_view, 2)
        
        # Assets panel at bottom
        self.assets_panel = AssetsPanel()
        center_layout.addWidget(self.assets_panel, 1)
        
        center_widget = QWidget()
        center_widget.setLayout(center_layout)
        
        # Right: Properties panel
        self.properties_panel = PropertiesPanel()
        
        # Create splitters for flexible layout
        center_splitter = QSplitter(Qt.Horizontal)
        center_splitter.addWidget(self.effects_panel)
        center_splitter.addWidget(center_widget)
        center_splitter.addWidget(self.properties_panel)
        center_splitter.setSizes([300, 1000, 300])
        
        main_layout.addWidget(center_splitter)
        self.setLayout(main_layout)


class EliteEditorApp(QMainWindow):
    """
    Main application window for Elite Editor.
    
    Manages:
    - Startup with Home Page
    - Project loading/unloading
    - Main editor layout
    - File I/O
    - Rendering
    """
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Elite Editor - Professional Video Editor")
        self.setGeometry(100, 100, 1920, 1200)
        
        # Managers
        self.config_manager = ConfigManager.instance()
        self.project_manager = ProjectManager.instance()
        self.registry = MoviePyRegistry.instance()
        
        # Load stylesheet
        self._load_stylesheet()
        
        # State
        self.current_project = None
        self.current_timeline: Optional[Timeline] = None
        self.editor_view: Optional[EditorView] = None
        
        # Setup window
        self._setup_ui()
        self._load_app_state()
        
        # Start with Home Page
        self._show_home_page()
    
    def _load_stylesheet(self) -> None:
        """Load application stylesheet."""
        from pathlib import Path
        style_path = Path(__file__).parent.parent / 'ui' / 'style.qss'

        # Load bundled application font before applying stylesheet so QSS can reference it
        font_path = Path(__file__).parent.parent / 'font' / 'font.ttf'
        try:
            if font_path.exists():
                fid = QFontDatabase.addApplicationFont(str(font_path))
                if fid != -1:
                    families = QFontDatabase.applicationFontFamilies(fid)
                    if families:
                        app = QApplication.instance()
                        if app:
                            app.setFont(QFont(families[0]))
                        logger.info(f"Loaded application font: {families[0]}")
                    else:
                        logger.warning(f"Loaded font id {fid} but no families returned")
                else:
                    logger.warning(f"Failed to load font from {font_path}")
        except Exception:
            logger.exception("Unexpected error loading custom font")

        if style_path.exists():
            try:
                with open(style_path, 'r', encoding='utf-8') as f:
                    stylesheet = f.read()
                QApplication.instance().setStyleSheet(stylesheet)
                logger.info(f"Loaded stylesheet: {style_path}")
            except Exception as e:
                logger.warning(f"Failed to load stylesheet: {e}")
        
        # Try to load icon
        from core.paths import PathManager
        paths = PathManager.instance()
        if paths.app_icon_file.exists():
            try:
                icon = QIcon(str(paths.app_icon_file))
                self.setWindowIcon(icon)
                QApplication.instance().setWindowIcon(icon)
                logger.info(f"Loaded icon: {paths.app_icon_file}")
            except Exception as e:
                logger.warning(f"Failed to load icon: {e}")
    
    def _setup_ui(self) -> None:
        """Setup main UI."""
        # Central stacked widget to switch between Home and Editor
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        # Setup menus
        self._setup_menu_bar()
        
        # Setup toolbar
        self._setup_toolbar()
        
        # Status bar
        self.statusBar().showMessage("Ready")

    def _setup_menu_bar(self) -> None:
        """Setup application menus."""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        
        new_action = QAction("New Project", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self._on_new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction("Open Project", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self._on_open_project)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._on_save_project)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menu_bar.addMenu("Edit")
        
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.Undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence.Redo)
        edit_menu.addAction(redo_action)
        
        # View menu
        view_menu = menu_bar.addMenu("View")
        
        # Help menu
        help_menu = menu_bar.addMenu("Help")
        
        about_action = QAction("About Elite Editor", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
    
    def _setup_toolbar(self) -> None:
        """Setup toolbar."""
        toolbar = self.addToolBar("Main Toolbar")
        
        # Will add toolbar buttons as needed
    
    def _load_app_state(self) -> None:
        """Load application state from config."""
        window_width = self.config_manager.get('ui', 'window.width', 1920)
        window_height = self.config_manager.get('ui', 'window.height', 1080)
        maximized = self.config_manager.get('ui', 'window.maximized', True)
        
        self.resize(window_width, window_height)
        if maximized:
            self.showMaximized()
    
    def _save_app_state(self) -> None:
        """Save application state to config."""
        self.config_manager.set('ui', 'window.width', self.width())
        self.config_manager.set('ui', 'window.height', self.height())
        self.config_manager.set('ui', 'window.maximized', self.isMaximized())
    
    def _show_home_page(self) -> None:
        """Show home page."""
        home_page = HomePage()
        home_page.project_selected.connect(self._on_project_selected)
        
        # Clear stack and add home page
        while self.stack.count():
            self.stack.removeWidget(self.stack.widget(0))
        
        self.stack.addWidget(home_page)
        self.current_project = None
        self.current_timeline = None
        self.editor_view = None
        
        self.statusBar().showMessage("Ready")
    
    @Slot(Path)
    def _on_project_selected(self, project_path: Path) -> None:
        """Handle project selection from Home Page."""
        logger.info(f"Loading project: {project_path}")
        
        # Load project
        project = self.project_manager.load_project(project_path)
        if not project:
            QMessageBox.critical(self, "Error", "Failed to load project")
            return
        
        self.current_project = project
        
        # Load timeline (for now, create new empty one)
        # TODO: Load from project file
        self.current_timeline = Timeline(
            project.metadata.name,
            project.metadata.fps,
            project.metadata.width,
            project.metadata.height
        )
        
        # Create editor view
        self.editor_view = EditorView(self.current_timeline)
        
        # Integrate preview widget into editor
        self.preview_widget = PreviewWidget()
        self.editor_view.layout().addWidget(self.preview_widget)
        
        # Hook properties preview
        self.editor_view.properties_panel.parameter_changed.connect(self._on_preview_parameters_changed)
        
        # Switch to editor
        while self.stack.count():
            self.stack.removeWidget(self.stack.widget(0))
        self.stack.addWidget(self.editor_view)
        
        self.setWindowTitle(f"Elite Editor - {project.metadata.name}")
        self.statusBar().showMessage(f"Project: {project.metadata.name}")
    
    def _on_new_project(self) -> None:
        """Handle New Project from menu."""
        self._show_home_page()
    
    def _on_open_project(self) -> None:
        """Handle Open Project from menu."""
        self._show_home_page()

    def _on_preview_parameters_changed(self) -> None:
        """Trigger preview render when properties change."""
        if not self.current_timeline:
            return
        
        # Start async preview render for the first 10 seconds
        job = PreviewRenderJob(
            id=str(uuid.uuid4()),
            timeline=self.current_timeline,
            fps=self.current_timeline.fps,
            width=self.current_timeline.width // 2,
            height=self.current_timeline.height // 2,
            duration_seconds=10.0,
            quality='preview',
            completion_callback=self._on_preview_completed
        )
        
        renderer = get_preview_renderer()
        renderer.render_preview_async(job)

    def _on_preview_completed(self, success: bool, output: str) -> None:
        """Handle preview completion and play result."""
        if success:
            logger.info(f"Preview ready: {output}")
            url = QUrl.fromLocalFile(str(output))
            self.preview_widget.media_player.setSource(url)
            self.preview_widget.play()
        else:
            logger.error(f"Preview failed: {output}")
    
    def _on_save_project(self) -> None:
        """Handle Save Project."""
        if self.current_project:
            if self.project_manager.save_project(self.current_project):
                self.statusBar().showMessage("Project saved")
            else:
                QMessageBox.critical(self, "Error", "Failed to save project")
    
    def _on_about(self) -> None:
        """Handle About dialog."""
        QMessageBox.about(
            self,
            "About Elite Editor",
            "Elite Editor v1.0\n\n"
            "Professional Desktop Video Editor\n"
            "Built with PySide6 and MoviePy"
        )
    
    def closeEvent(self, event) -> None:
        """Handle window close."""
        # Save state and project
        self._save_app_state()
        if self.current_project:
            self.project_manager.save_project(self.current_project)
        
        event.accept()
        event.accept()
