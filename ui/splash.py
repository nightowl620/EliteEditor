"""
Splash Screen - Startup screen with branding and loading status
"""

from PySide6.QtWidgets import QSplashScreen, QApplication
from PySide6.QtGui import QPixmap, QColor, QFont
from PySide6.QtCore import Qt, QTimer
from pathlib import Path
import os


class SplashScreen(QSplashScreen):
    """Professional splash screen with loading animation."""
    
    def __init__(self, parent=None, auto_close_time: float = 2.0):
        """
        Initialize splash screen.
        
        Args:
            parent: Parent widget
            auto_close_time: Auto close after this many seconds (0 = manual)
        """
        # Create pixmap
        pixmap = QPixmap(400, 300)
        pixmap.fill(QColor(20, 20, 20))
        
        super().__init__(pixmap, parent)
        
        # Messages
        self.show_message(
            "Initializing Elite Editor...",
            alignment=Qt.AlignBottom | Qt.AlignCenter,
            color=QColor(200, 200, 200)
        )
        
        # Auto-close timer
        if auto_close_time > 0:
            self.timer = QTimer()
            self.timer.timeout.connect(self.close)
            self.timer.start(int(auto_close_time * 1000))
        
        self.move(
            (QApplication.primaryScreen().geometry().width() - 400) // 2,
            (QApplication.primaryScreen().geometry().height() - 300) // 2
        )
    
    def show_message(self, message: str, msecs: int = 0, color: QColor = None) -> None:
        """Show message on splash screen."""
        if color is None:
            color = QColor(200, 200, 200)
        super().showMessage(message, alignment=Qt.AlignBottom | Qt.AlignCenter, color=color)


logger = Logger.setup(__name__, "SPLASH")


class SplashScreen(QMainWindow):
    """
    Full-screen splash screen with video playback.
    
    Displays startup animation and optional status messages.
    Closes automatically when done or on key/mouse press.
    """
    
    def __init__(self, auto_close_time: float = 3.0):
        """
        Initialize splash screen.
        
        Args:
            auto_close_time: Seconds to display before auto-closing. 0 to disable.
        """
        super().__init__()
        self.auto_close_time = auto_close_time
        self.startup_start_time = time.time()
        
        # Window setup
        self.setWindowTitle("Elite Editor - Starting")
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.SplashScreen
        )
        
        # Fullscreen
        screen = self.screen()
        self.setGeometry(screen.availableGeometry())
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Video widget
        self.video_widget = QVideoWidget()
        layout.addWidget(self.video_widget)
        
        # Media player
        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        # Rely on application stylesheet (style.qss) for styling
        self.setObjectName("splashScreen")
        
        # Load video
        self._load_startup_video()
        
        # Auto-close timer
        if auto_close_time > 0:
            self.auto_close_timer = QTimer()
            self.auto_close_timer.setSingleShot(True)
            self.auto_close_timer.timeout.connect(self.close)
            self.auto_close_timer.start(int(auto_close_time * 1000))
        
        logger.info("Splash screen initialized")
    

    
    def _load_startup_video(self):
        """Load and play startup video."""
        paths = PathManager.instance()
        video_path = paths.startup_dir / "load.mp4"
        
        if video_path.exists():
            try:
                self.media_player.setSource(video_path.as_uri())
                self.media_player.play()
                logger.info(f"Playing startup video: {video_path}")
            except Exception as e:
                logger.error(f"Failed to load video: {e}")
                self._fallback_to_static_splash()
        else:
            logger.warning(f"Startup video not found: {video_path}")
            self._fallback_to_static_splash()
    
    def _fallback_to_static_splash(self):
        """Fallback to static splash if video fails."""
        logger.info("Using static splash fallback")
        # Styling handled by application stylesheet (style.qss); object name 'splashScreen' is set.
    
    def keyPressEvent(self, event):
        """Close on any key press."""
        if not event.isAutoRepeat():
            self.close()
    
    def mousePressEvent(self, event):
        """Close on any mouse click."""
        self.close()
    
    def closeEvent(self, event):
        """Stop playback on close."""
        self.media_player.stop()
        super().closeEvent(event)


class QuickSplash:
    """
    Quick fallback splash using QPixmap if video playback unavailable.
    
    Creates a simple splash screen with logo and status text.
    """
    
    @staticmethod
    def show_for(seconds: float = 2.0):
        """
        Show simple splash screen briefly.
        
        Args:
            seconds: Duration to display splash.
        """
        try:
            from PySide6.QtWidgets import QApplication, QSplashScreen
            from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
            
            app = QApplication.instance()
            if not app:
                return
            
            # Create pixmap
            pixmap = QPixmap(1920, 1080)
            pixmap.fill(QColor("#000000"))
            
            # Draw text
            painter = QPainter(pixmap)
            painter.setFont(QFont("Segoe UI", 32, QFont.Bold))
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(pixmap.rect(), 0x0084, "Elite Editor")
            painter.drawText(pixmap.rect(), 0x0084, "\nInitializing...")
            painter.end()
            
            # Show splash
            splash = QSplashScreen(pixmap)
            splash.show()
            app.processEvents()
            
            # Wait
            import time
            time.sleep(seconds)
            
            splash.finish(None)
            
            logger.info(f"Quick splash shown for {seconds}s")
        
        except Exception as e:
            logger.error(f"Quick splash failed: {e}")
