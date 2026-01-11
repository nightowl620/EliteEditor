"""
Elite Editor - Main Application Window

Professional desktop video editing interface with timeline,
preview, effects, and AI integration.
"""

import logging
from typing import Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QDockWidget, QMessageBox, QFileDialog, QProgressDialog, QInputDialog,
    QListWidget, QListWidgetItem, QTabWidget, QTextEdit, QTableWidget, QSlider
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QCoreApplication
from PySide6.QtGui import QIcon, QAction, QKeySequence, QFont, QFontDatabase
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from core.paths import PathManager
from core.config import ConfigManager
from core.state import StateManager
from core.project import ProjectManager, ProjectMetadata
from timeline.timeline import Timeline
from timeline.clip import Clip, ClipType
from ai.gemini import get_ai

logger = logging.getLogger(__name__)


class PreviewWidget(QVideoWidget):
    """Video preview with playback controls."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self)
        self.playback_position = 0
        self.setMinimumHeight(300)
    
    def play(self) -> None:
        """Start playback."""
        self.media_player.play()
    
    def pause(self) -> None:
        """Pause playback."""
        self.media_player.pause()
    
    def stop(self) -> None:
        """Stop playback."""
        self.media_player.stop()
    
    def set_position(self, ms: int) -> None:
        """Set playhead position."""
        self.media_player.setPosition(ms)
    
    def get_position(self) -> int:
        """Get current position."""
        return self.media_player.position()


class TimelineWidget(QWidget):
    """Timeline display with clips, tracks, and drag-and-drop."""
    
    clip_selected = Signal(str)
    clip_moved = Signal(str, str, float)
    
    def __init__(self, timeline: Optional[Timeline] = None, parent=None):
        super().__init__(parent)
        self.timeline = timeline
        self.setup_ui()
        self.setAcceptDrops(True)
        self.setMinimumHeight(200)
    
    def setup_ui(self) -> None:
        """Setup UI."""
        layout = QVBoxLayout()
        
        # Timeline display area
        self.canvas = QWidget()
        self.canvas.setObjectName("timelineCanvas")
        self.canvas.setMinimumHeight(150)
        layout.addWidget(self.canvas)
        
        # Zoom and scroll controls
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 500)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setMaximumWidth(200)
        control_layout.addWidget(self.zoom_slider)
        layout.addLayout(control_layout)
        
        self.setLayout(layout)
    
    def dragEnterEvent(self, event):
        """Accept drag events."""
        event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Handle drops."""
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            for url in mime_data.urls():
                path = url.toLocalFile()
                logger.info(f"Dropped file: {path}")
    
    def paintEvent(self, event):
        """Draw timeline."""
        if not self.timeline:
            return
        super().paintEvent(event)


class EffectsPanel(QWidget):
    """Effects and properties inspector."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self) -> None:
        """Setup UI."""
        layout = QVBoxLayout()
        
        # Tabs for different panels
        self.tabs = QTabWidget()
        
        # Effects tab
        effects_widget = QWidget()
        effects_layout = QVBoxLayout()
        self.effects_list = QListWidget()
        effects_layout.addWidget(QLabel("Effects Stack:"))
        effects_layout.addWidget(self.effects_list)
        effects_widget.setLayout(effects_layout)
        self.tabs.addTab(effects_widget, "Effects")
        
        # Properties tab
        props_widget = QWidget()
        props_layout = QVBoxLayout()
        props_layout.addWidget(QLabel("Clip Properties"))
        
        # Opacity
        props_layout.addWidget(QLabel("Opacity:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        props_layout.addWidget(self.opacity_slider)
        
        # Volume
        props_layout.addWidget(QLabel("Volume:"))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        props_layout.addWidget(self.volume_slider)
        
        props_layout.addStretch()
        props_widget.setLayout(props_layout)
        self.tabs.addTab(props_widget, "Properties")
        
        # Keyframes tab
        keyframes_widget = QWidget()
        keyframes_layout = QVBoxLayout()
        keyframes_layout.addWidget(QLabel("Keyframes"))
        self.keyframe_table = QTableWidget()
        self.keyframe_table.setColumnCount(4)
        self.keyframe_table.setHorizontalHeaderLabels(["Frame", "Property", "Value", "Interpolation"])
        keyframes_layout.addWidget(self.keyframe_table)
        keyframes_widget.setLayout(keyframes_layout)
        self.tabs.addTab(keyframes_widget, "Keyframes")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)


class MediaLibrary(QWidget):
    """Media library and asset browser."""
    
    file_selected = Signal(Path)
    file_dropped = Signal(Path)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setAcceptDrops(True)
    
    def setup_ui(self) -> None:
        """Setup UI."""
        layout = QVBoxLayout()
        
        # Tabs for local vs AI assets
        self.tabs = QTabWidget()
        
        # Local media tab
        local_widget = QWidget()
        local_layout = QVBoxLayout()
        local_layout.addWidget(QLabel("Local Media"))
        self.local_list = QListWidget()
        local_layout.addWidget(self.local_list)
        local_widget.setLayout(local_layout)
        self.tabs.addTab(local_widget, "Local")
        
        # AI generated assets tab
        ai_widget = QWidget()
        ai_layout = QVBoxLayout()
        ai_layout.addWidget(QLabel("AI Generated Assets"))
        self.ai_list = QListWidget()
        ai_layout.addWidget(self.ai_list)
        ai_widget.setLayout(ai_layout)
        self.tabs.addTab(ai_widget, "AI Assets")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)
    
    def dragEnterEvent(self, event):
        """Accept drag events."""
        event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Handle drops."""
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            for url in mime_data.urls():
                path = Path(url.toLocalFile())
                self.file_dropped.emit(path)


class AITab(QWidget):
    """AI conversational interface."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ai = get_ai()
        self.setup_ui()
    
    def setup_ui(self) -> None:
        """Setup UI."""
        layout = QVBoxLayout()
        
        # Tabs
        self.tabs = QTabWidget()
        
        # Chat tab
        chat_widget = QWidget()
        chat_layout = QVBoxLayout()
        chat_layout.addWidget(QLabel("AI Chat"))
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        chat_layout.addWidget(self.chat_display)
        
        # Input area
        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask AI to edit, generate, or modify...")
        self.chat_submit = QPushButton("Send")
        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(self.chat_submit)
        chat_layout.addLayout(input_layout)
        chat_widget.setLayout(chat_layout)
        self.tabs.addTab(chat_widget, "Chat")
        
        # TTS tab
        tts_widget = QWidget()
        tts_layout = QVBoxLayout()
        tts_layout.addWidget(QLabel("Text-to-Speech"))
        tts_layout.addWidget(QLabel("Text:"))
        self.tts_input = QTextEdit()
        tts_layout.addWidget(self.tts_input)
        
        tts_controls = QHBoxLayout()
        tts_layout.addWidget(QLabel("Voice:"))
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(["Zephyr", "Sage", "Puck", "Charon", "Kore", "Orion"])
        tts_controls.addWidget(self.voice_combo)
        self.generate_tts_btn = QPushButton("Generate Audio")
        tts_controls.addWidget(self.generate_tts_btn)
        tts_layout.addLayout(tts_controls)
        tts_layout.addStretch()
        tts_widget.setLayout(tts_layout)
        self.tabs.addTab(tts_widget, "TTS")
        
        # Image generation tab
        image_widget = QWidget()
        image_layout = QVBoxLayout()
        image_layout.addWidget(QLabel("Image Generation"))
        image_layout.addWidget(QLabel("Prompt:"))
        self.image_prompt = QTextEdit()
        image_layout.addWidget(self.image_prompt)
        self.generate_image_btn = QPushButton("Generate Image")
        image_layout.addWidget(self.generate_image_btn)
        image_layout.addStretch()
        image_widget.setLayout(image_layout)
        self.tabs.addTab(image_widget, "Image Gen")
        
        # Captions tab
        captions_widget = QWidget()
        captions_layout = QVBoxLayout()
        captions_layout.addWidget(QLabel("Auto-Captions"))
        self.captions_display = QTextEdit()
        captions_layout.addWidget(self.captions_display)
        self.generate_captions_btn = QPushButton("Generate Captions from Timeline Audio")
        captions_layout.addWidget(self.generate_captions_btn)
        captions_widget.setLayout(captions_layout)
        self.tabs.addTab(captions_widget, "Captions")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)


class SettingsPanel(QWidget):
    """Settings and configuration."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager.instance()
        self.setup_ui()
    
    def setup_ui(self) -> None:
        """Setup UI."""
        layout = QVBoxLayout()
        
        # Tabs
        self.tabs = QTabWidget()
        
        # Project settings
        project_widget = QWidget()
        project_layout = QVBoxLayout()
        project_layout.addWidget(QLabel("Project Settings"))
        
        project_layout.addWidget(QLabel("FPS:"))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 120)
        self.fps_spin.setValue(30)
        project_layout.addWidget(self.fps_spin)
        
        project_layout.addWidget(QLabel("Resolution:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["1920x1080", "1280x720", "3840x2160", "Custom"])
        project_layout.addWidget(self.resolution_combo)
        
        project_layout.addStretch()
        project_widget.setLayout(project_layout)
        self.tabs.addTab(project_widget, "Project")
        
        # UI settings
        ui_widget = QWidget()
        ui_layout = QVBoxLayout()
        ui_layout.addWidget(QLabel("UI Settings"))
        
        ui_layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        ui_layout.addWidget(self.theme_combo)
        
        ui_layout.addWidget(QLabel("UI Scale:"))
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.8, 2.0)
        self.scale_spin.setValue(1.0)
        self.scale_spin.setSingleStep(0.1)
        ui_layout.addWidget(self.scale_spin)
        
        ui_layout.addStretch()
        ui_widget.setLayout(ui_layout)
        self.tabs.addTab(ui_widget, "UI")
        
        # AI settings
        ai_widget = QWidget()
        ai_layout = QVBoxLayout()
        ai_layout.addWidget(QLabel("AI Settings"))
        
        ai_layout.addWidget(QLabel("API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        ai_layout.addWidget(self.api_key_input)
        
        ai_layout.addWidget(QLabel("AI Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["gemini-3-flash-preview", "gemini-2.5-flash-preview"])
        ai_layout.addWidget(self.model_combo)
        
        ai_layout.addStretch()
        ai_widget.setLayout(ai_layout)
        self.tabs.addTab(ai_widget, "AI")
        
        # Performance settings
        perf_widget = QWidget()
        perf_layout = QVBoxLayout()
        perf_layout.addWidget(QLabel("Performance"))
        
        perf_layout.addWidget(QLabel("Cache Size (MB):"))
        self.cache_spin = QSpinBox()
        self.cache_spin.setRange(100, 4000)
        self.cache_spin.setValue(1000)
        perf_layout.addWidget(self.cache_spin)
        
        self.proxy_checkbox = QCheckBox("Enable Proxy Playback")
        self.proxy_checkbox.setChecked(True)
        perf_layout.addWidget(self.proxy_checkbox)
        
        perf_layout.addStretch()
        perf_widget.setLayout(perf_layout)
        self.tabs.addTab(perf_widget, "Performance")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)


class MainWindow(QMainWindow):
    """
    Elite Editor main application window.
    
    Features:
    - Multi-track timeline
    - Clip manipulation (drag, resize, effects)
    - Real-time preview
    - AI integration
    - Full drag-and-drop support
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ELITE EDITOR - Professional Video Editing with AI")
        self.setWindowIcon(self._load_icon())
        self.resize(1600, 900)
        
        # Initialize managers
        self.paths = PathManager.instance()
        self.config = ConfigManager.instance()
        self.state = StateManager.instance()
        self.project_manager = ProjectManager()
        
        # Current project and timeline
        self.current_project = None
        self.timeline = Timeline(name="Main Timeline")
        self.undo_stack = []
        self.redo_stack = []
        
        # Setup UI
        self.setup_ui()
        self.setup_menu_bar()
        self.setup_connections()
        self.show_recent_projects()
        
        logger.info("Elite Editor initialized")
        # Ensure a state_manager attribute for older code paths
        self.state_manager = self.state

        # Robust font loading: check file exists and verify font id/families before applying
        ROOT_DIR = Path(__file__).resolve().parent.parent
        font_path = ROOT_DIR / "font" / "font.ttf"
        try:
            if font_path.exists():
                font_id = QFontDatabase.addApplicationFont(str(font_path))
                if font_id != -1:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        app_font = QFont(families[0])
                        self.setFont(app_font)
                        logger.info(f"Loaded custom font: {families[0]}")
                    else:
                        logger.warning(f"Loaded font id {font_id} but no families returned")
                else:
                    logger.warning(f"Failed to load font from {font_path}")
            else:
                logger.debug(f"Font file not found at {font_path}; using default font")
        except Exception:
            logger.exception("Unexpected error loading custom font; falling back to default")
    
    def _load_icon(self) -> QIcon:
        """Load app icon."""
        icon_path = PathManager.instance().app_icon_file
        if icon_path.exists():
            return QIcon(str(icon_path))
        return QIcon()
    
    def setup_ui(self) -> None:
        """Setup main UI layout."""
        # Central widget
        central = QWidget()
        main_layout = QHBoxLayout(central)
        
        # Left panel: Media Library
        left_dock = QDockWidget("Media Library", self)
        self.media_library = MediaLibrary()
        left_dock.setWidget(self.media_library)
        self.addDockWidget(Qt.LeftDockWidgetArea, left_dock)
        
        # Center: Preview + Timeline
        center_layout = QVBoxLayout()
        
        # Preview widget
        self.preview = PreviewWidget()
        center_layout.addWidget(self.preview)
        
        # Playback controls
        controls_layout = QHBoxLayout()
        self.play_btn = QPushButton("Play")
        self.pause_btn = QPushButton("Pause")
        self.stop_btn = QPushButton("Stop")
        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.pause_btn)
        controls_layout.addWidget(self.stop_btn)
        center_layout.addLayout(controls_layout)
        
        # Timeline
        self.timeline_widget = TimelineWidget(self.timeline)
        center_layout.addWidget(self.timeline_widget)
        
        center_widget = QWidget()
        center_widget.setLayout(center_layout)
        main_layout.addWidget(center_widget, stretch=3)
        
        # Right panel: Inspector + AI
        right_layout = QVBoxLayout()
        
        self.tabs = QTabWidget()
        
        # Effects/Properties tab
        self.effects_panel = EffectsPanel()
        self.tabs.addTab(self.effects_panel, "Inspector")
        
        # AI tab
        self.ai_tab = AITab()
        self.tabs.addTab(self.ai_tab, "AI")
        
        # Settings tab
        self.settings_panel = SettingsPanel()
        self.tabs.addTab(self.settings_panel, "Settings")
        
        right_layout.addWidget(self.tabs)
        
        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        main_layout.addWidget(right_widget, stretch=1)
        
        self.setCentralWidget(central)
        
        # Status bar
        self.statusbar = self.statusBar()
        self.statusbar.showMessage("Ready")
    
    def setup_menu_bar(self) -> None:
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New Project", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction("Open Project", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)
        
        save_action = QAction("Save Project", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)
        
        export_action = QAction("Export Video", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self.export_video)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        delete_action = QAction("Delete", self)
        delete_action.setShortcut(QKeySequence.Delete)
        delete_action.triggered.connect(self.delete_selected)
        edit_menu.addAction(delete_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut(QKeySequence.ZoomIn)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        view_menu.addAction(zoom_out_action)
        
        # Settings menu
        settings_menu = menubar.addMenu("Settings")
        
        prefs_action = QAction("Preferences", self)
        prefs_action.triggered.connect(self.show_settings)
        settings_menu.addAction(prefs_action)
        
        keybinds_action = QAction("Keybinds", self)
        keybinds_action.triggered.connect(self.show_keybinds)
        settings_menu.addAction(keybinds_action)
    
    def setup_connections(self) -> None:
        """Setup signal connections."""
        self.play_btn.clicked.connect(self.preview.play)
        self.pause_btn.clicked.connect(self.preview.pause)
        self.stop_btn.clicked.connect(self.preview.stop)
        self.media_library.file_dropped.connect(self.on_file_dropped)
    
    # ===== FILE OPERATIONS =====
    
    @Slot()
    def new_project(self) -> None:
        """Create new project."""
        self.timeline = Timeline(name="New Project")
        # Add default tracks
        self.timeline.add_track(track_type='video')
        self.timeline.add_track(track_type='audio')
        self.statusbar.showMessage("New project created")
    
    @Slot()
    def open_project(self) -> None:
        """Open project file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "Elite Editor Projects (*.eep)"
        )
        if file_path:
            try:
                self.current_project = self.project_manager.load_project(Path(file_path))
                self.statusbar.showMessage(f"Loaded: {self.current_project.metadata.name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load project: {e}")
    
    @Slot()
    def save_project(self) -> None:
        """Save current project."""
        if not self.current_project:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Project", "", "Elite Editor Projects (*.eep)"
            )
            if not file_path:
                return
            self.current_project = self.project_manager.create_project(
                name="Untitled Project",
                fps=int(self.settings_panel.fps_spin.value())
            )
        
        try:
            # Use ProjectManager API to save current project (it manages file paths)
            self.project_manager.save_project(self.current_project)
            self.statusbar.showMessage("Project saved")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save project: {e}")
    
    @Slot()
    def export_video(self) -> None:
        """Export timeline to video file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Video", "", "Video Files (*.mp4)"
        )
        if not file_path:
            return
        out_path = Path(file_path)

        progress = QProgressDialog("Rendering...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)

        try:
            # Use real subprocess renderer
            from rendering.subprocess_renderer import get_subprocess_renderer, SubprocessRenderJob

            renderer = get_subprocess_renderer()
            job = SubprocessRenderJob(
                id=f'export_{id(self)}',
                timeline=self.timeline,
                output_path=out_path,
                fps=30,
                width=1280,
                height=720,
                bitrate='8M',
                codec='libx264',
                preset='medium'
            )

            def update_progress(pct, status):
                progress.setValue(int(pct))
                self.statusbar.showMessage(status)

            job.progress_callback = update_progress

            def on_complete(success, msg):
                progress.close()
                if success:
                    self.statusbar.showMessage(f"Export complete: {out_path}")
                    QMessageBox.information(self, "Success", f"Video exported successfully!")
                else:
                    QMessageBox.critical(self, "Export Failed", msg)

            job.completion_callback = on_complete
            renderer.render(job)

        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Error", f"Export failed: {e}")
    
    # ===== EDITING OPERATIONS =====
    
    @Slot()
    def undo(self) -> None:
        """Undo last action."""
        if self.undo_stack:
            self.undo_stack.pop()
            self.statusbar.showMessage("Undo")
    
    @Slot()
    def redo(self) -> None:
        """Redo last action."""
        if self.redo_stack:
            self.redo_stack.pop()
            self.statusbar.showMessage("Redo")
    
    @Slot()
    def delete_selected(self) -> None:
        """Delete selected clips."""
        for clip_id in self.timeline.selected_clips:
            # Find and remove clip
            for track_id, track in self.timeline.tracks.items():
                for clip in track.clips:
                    if clip.id == clip_id:
                        self.timeline.remove_clip(track_id, clip_id)
                        break
        self.timeline.deselect_all()
        self.statusbar.showMessage("Deleted")
    
    @Slot()
    def show_settings(self) -> None:
        """Show settings panel."""
        self.tabs.setCurrentWidget(self.settings_panel)
        self.statusbar.showMessage("Settings")
    
    @Slot()
    def show_keybinds(self) -> None:
        """Show keybinds editor."""
        self.statusbar.showMessage("Keybinds editor")
    
    @Slot()
    def show_recent_projects(self) -> None:
        """Show recent projects on startup."""
        try:
            from core.project_system import get_project_manager
            pm = get_project_manager()
            recent = pm.get_recent_projects()
            if recent:
                last_project = recent[0]
                self.load_project(last_project)
        except Exception as e:
            logger.debug(f"Could not load recent project: {e}")
    
    @Slot(Path)
    def on_file_dropped(self, file_path: Path) -> None:
        """Handle dropped files."""
        logger.info(f"File dropped: {file_path}")
        
        # Create clip
        clip = Clip(
            name=file_path.stem,
            clip_type=ClipType.VIDEO if file_path.suffix.lower() in ['.mp4', '.mov', '.avi'] else ClipType.AUDIO,
            media_path=file_path
        )
        
        # Add to first track
        if self.timeline.track_order:
            track_id = self.timeline.track_order[0]
            self.timeline.add_clip_to_track(track_id, clip, start_time=0.0)
            self.statusbar.showMessage(f"Added: {file_path.name}")
    

    
    def _setup_menu_bar(self) -> None:
        """Create menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New Project", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._on_new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction("Open Project", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_project)
        file_menu.addAction(open_action)
        
        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._on_save_project)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("Export...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._on_export)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        undo_action = QAction("Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self._on_undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("Redo", self)
        redo_action.setShortcut("Ctrl+Shift+Z")
        redo_action.triggered.connect(self._on_redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        settings_action = QAction("Preferences...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._on_settings)
        edit_menu.addAction(settings_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        fullscreen_action = QAction("Full Screen", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.triggered.connect(self._on_fullscreen)
        view_menu.addAction(fullscreen_action)
    
    def _setup_ui(self) -> None:
        """Setup main UI layout."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create splitter for resizable panels
        self.splitter = QSplitter(Qt.Horizontal)
        
        # Left panel (Media Library)
        self.media_panel = QWidget()
        self.media_layout = QVBoxLayout(self.media_panel)
        self.media_layout.setContentsMargins(8, 8, 8, 8)
        
        media_title = QLabel("Media Library")
        media_title.setObjectName("mediaTitle")
        self.media_layout.addWidget(media_title)
        
        # Media list
        self.media_list = QListWidget()
        self.media_layout.addWidget(self.media_list)
        
        import_btn = QPushButton("Import Media")
        import_btn.clicked.connect(self._on_import_media)
        self.media_layout.addWidget(import_btn)
        
        self.splitter.addWidget(self.media_panel)
        
        # Center panel (Preview + Timeline)
        self.center_panel = QWidget()
        self.center_layout = QVBoxLayout(self.center_panel)
        self.center_layout.setContentsMargins(0, 0, 0, 0)
        self.center_layout.setSpacing(0)
        
        # Preview area
        preview_title = QLabel("Preview")
        preview_title.setObjectName("previewTitle")
        self.center_layout.addWidget(preview_title)
        
        self.preview_widget = QWidget()
        self.preview_widget.setObjectName("previewWidget")
        self.preview_widget.setMinimumHeight(200)
        self.center_layout.addWidget(self.preview_widget)
        
        # Timeline area
        timeline_title = QLabel("Timeline")
        timeline_title.setObjectName("timelineTitle")
        self.center_layout.addWidget(timeline_title)
        
        self.timeline_widget = QWidget()
        self.timeline_widget.setObjectName("timelineWidget")
        self.timeline_widget.setMinimumHeight(150)
        self.center_layout.addWidget(self.timeline_widget)
        
        self.splitter.addWidget(self.center_panel)
        
        # Right panel (Inspector/Properties)
        self.inspector_panel = QWidget()
        self.inspector_layout = QVBoxLayout(self.inspector_panel)
        self.inspector_layout.setContentsMargins(8, 8, 8, 8)
        
        inspector_title = QLabel("Inspector")
        inspector_title.setObjectName("inspectorTitle")
        self.inspector_layout.addWidget(inspector_title)
        
        # Tabs for different inspector modes
        self.inspector_tabs = QTabWidget()
        self.inspector_tabs.addTab(QWidget(), "Properties")
        self.inspector_tabs.addTab(QWidget(), "Effects")
        self.inspector_tabs.addTab(QWidget(), "Audio")
        self.inspector_layout.addWidget(self.inspector_tabs)
        
        self.splitter.addWidget(self.inspector_panel)
        
        # Set initial sizes
        self.splitter.setSizes([250, 1200, 280])
        self.splitter.setCollapsible(0, True)
        self.splitter.setCollapsible(1, False)
        self.splitter.setCollapsible(2, True)
        
        main_layout.addWidget(self.splitter)
    
    def _setup_status_bar(self) -> None:
        """Setup status bar."""
        self.status_label = QLabel("Ready")
        self.statusBar().addWidget(self.status_label)
    
    def _show_home_page(self) -> None:
        """Show home page with recent projects."""
        logger.info("Showing home page")
        
        # Create layout for timeline widget if it doesn't exist
        if self.timeline_widget.layout() is None:
            layout = QVBoxLayout(self.timeline_widget)
            layout.setContentsMargins(0, 0, 0, 0)
        
        # Clear any existing widgets
        layout = self.timeline_widget.layout()
        while layout.count():
            layout.takeAt(0).widget().deleteLater()
        
        # Add centered message
        timeline_label = QLabel("No project loaded\nCreate a new project or open recent")
        timeline_label.setAlignment(Qt.AlignCenter)
        timeline_label.setObjectName("timelineLabel")
        layout.addWidget(timeline_label)
    
    def _load_last_project(self) -> None:
        """Load the last opened project."""
        if self.recent_projects:
            logger.info(f"Loading recent project: {self.recent_projects[0]}")
            self._load_project(self.recent_projects[0])
    
    def _on_new_project(self) -> None:
        """Handle new project."""
        logger.info("New project requested")

        project_name, ok = QInputDialog.getText(
            self,
            "New Project",
            "Project name:",
            text="Untitled Project"
        )

        if ok and project_name:
            try:
                # Use ProjectManager to create and manage the project
                project = self.project_manager.create_project(
                    name=project_name,
                    fps=30,
                    width=1920,
                    height=1080
                )

                self.current_project = project
                self.status_label.setText(f"Project: {project_name}")

                logger.info(f"New project created: {project_name}")

            except Exception as e:
                logger.error(f"Failed to create project: {e}")
                QMessageBox.critical(self, "Error", f"Failed to create project: {e}")
    
    def _on_open_project(self) -> None:
        """Handle open project."""
        logger.info("Open project requested")
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            str(self.paths.projects_dir),
            "Elite Editor Projects (*.eep);;All Files (*)"
        )
        
        if file_path:
            self._load_project(file_path)
    
    def _load_project(self, file_path: str) -> None:
        """Load a project from file."""
        try:
            logger.info(f"Loading project: {file_path}")
            project = self.project_manager.load_project(Path(file_path))
            if not project:
                raise RuntimeError("Project load failed")
            self.current_project = project

            # Update recent projects (store string paths)
            if isinstance(self.recent_projects, list):
                if file_path not in self.recent_projects:
                    self.recent_projects.insert(0, file_path)
                    if len(self.recent_projects) > 10:
                        self.recent_projects = self.recent_projects[:10]
                    self.config.set('app', 'recent_projects', self.recent_projects, persist=True)

            self.status_label.setText(f"Project: {project.metadata.name}")
            logger.info(f"Project loaded: {project.metadata.name}")

        except Exception as e:
            logger.error(f"Failed to load project: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load project: {e}")
    
    def _on_save_project(self) -> None:
        """Handle save project."""
        if not self.current_project:
            QMessageBox.warning(self, "No Project", "No project is currently open")
            return
        
        logger.info(f"Saving project: {self.current_project.metadata.name}")
        
        try:
            self.project_manager.save_project(self.current_project)
            self.status_label.setText("Project saved")
            logger.info("Project saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save project: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save project: {e}")
    
    def _on_export(self) -> None:
        """Handle export."""
        if not self.current_project:
            QMessageBox.warning(self, "No Project", "No project is currently open")
            return
        
        logger.info("Export requested")
        self.status_label.setText("Exporting project...")
    
    def _on_import_media(self) -> None:
        """Handle media import."""
        logger.info("Import media requested")
        
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Media",
            "",
            "Media Files (*.mp4 *.mov *.avi *.mkv *.wav *.mp3);;All Files (*)"
        )
        
        if file_paths:
            for file_path in file_paths:
                logger.info(f"Importing: {file_path}")
                item = QListWidgetItem(Path(file_path).name)
                item.setData(Qt.UserRole, file_path)
                self.media_list.addItem(item)
    
    def _on_undo(self) -> None:
        """Handle undo."""
        logger.info("Undo")
        self.state_manager.undo()
        self.status_label.setText("Undo")
    
    def _on_redo(self) -> None:
        """Handle redo."""
        logger.info("Redo")
        self.state_manager.redo()
        self.status_label.setText("Redo")
    
    def _on_settings(self) -> None:
        """Handle settings."""
        logger.info("Settings requested")
        self.status_label.setText("Opening settings...")
    
    def _on_fullscreen(self) -> None:
        """Handle fullscreen toggle."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def closeEvent(self, event) -> None:
        """Save state before closing."""
        # Save window state
        self.config.set('ui', 'window_width', self.width(), persist=True)
        self.config.set('ui', 'window_height', self.height(), persist=True)
        self.config.set('ui', 'window_maximized', self.isMaximized(), persist=True)
        
        # Save current project
        if self.current_project:
            try:
                self._on_save_project()
            except Exception as e:
                logger.error(f"Failed to save project on close: {e}")
        
        logger.info("Main window closed")
        event.accept()
