"""
Real Theming System

Dark/Light mode that:
- Switches instantly
- Affects ALL widgets
- Uses .qss stylesheets
- Persists across restarts
"""

import logging
from pathlib import Path
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class Theme(Enum):
    """Available themes."""
    DARK = 'dark'
    LIGHT = 'light'


DARK_STYLESHEET = """
/* Dark Theme for ELITE EDITOR */

* {
    background-color: #1e1e1e;
    color: #e0e0e0;
}

QMainWindow {
    background-color: #1e1e1e;
}

QDockWidget {
    background-color: #252525;
    color: #e0e0e0;
}

QDockWidget::title {
    background-color: #2d2d2d;
    color: #e0e0e0;
    padding: 5px;
}

QMenuBar {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border-bottom: 1px solid #3d3d3d;
}

QMenuBar::item:selected {
    background-color: #404040;
}

QMenu {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #3d3d3d;
}

QMenu::item:selected {
    background-color: #404040;
}

QToolBar {
    background-color: #252525;
    border: none;
}

QPushButton {
    background-color: #404040;
    color: #e0e0e0;
    border: 1px solid #505050;
    border-radius: 3px;
    padding: 5px 10px;
}

QPushButton:hover {
    background-color: #505050;
    border: 1px solid #606060;
}

QPushButton:pressed {
    background-color: #303030;
}

QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #404040;
    border-radius: 3px;
    padding: 5px;
}

QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #506080;
}

QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #404040;
    border-radius: 3px;
    padding: 5px;
}

QCheckBox, QRadioButton {
    color: #e0e0e0;
}

QSlider::groove:horizontal {
    background-color: #3d3d3d;
    height: 8px;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background-color: #505080;
    width: 18px;
    margin: -5px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background-color: #6070a0;
}

QTableWidget, QTableView {
    background-color: #2d2d2d;
    color: #e0e0e0;
    gridline-color: #3d3d3d;
}

QTableWidget::item:selected {
    background-color: #404060;
}

QListWidget, QListView {
    background-color: #2d2d2d;
    color: #e0e0e0;
}

QListWidget::item:selected {
    background-color: #404060;
}

QTabBar::tab {
    background-color: #2d2d2d;
    color: #e0e0e0;
    padding: 5px 15px;
    border: 1px solid #3d3d3d;
}

QTabBar::tab:selected {
    background-color: #404040;
    border-bottom: 2px solid #506080;
}

QScrollBar:vertical {
    background-color: #2d2d2d;
    width: 12px;
}

QScrollBar::handle:vertical {
    background-color: #505050;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #606060;
}

QScrollBar:horizontal {
    background-color: #2d2d2d;
    height: 12px;
}

QScrollBar::handle:horizontal {
    background-color: #505050;
    border-radius: 6px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #606060;
}
"""

LIGHT_STYLESHEET = """
/* Light Theme for ELITE EDITOR */

* {
    background-color: #ffffff;
    color: #2d2d2d;
}

QMainWindow {
    background-color: #f5f5f5;
}

QDockWidget {
    background-color: #fafafa;
    color: #2d2d2d;
}

QDockWidget::title {
    background-color: #e8e8e8;
    color: #2d2d2d;
    padding: 5px;
}

QMenuBar {
    background-color: #f0f0f0;
    color: #2d2d2d;
    border-bottom: 1px solid #d0d0d0;
}

QMenuBar::item:selected {
    background-color: #e0e0e0;
}

QMenu {
    background-color: #f0f0f0;
    color: #2d2d2d;
    border: 1px solid #d0d0d0;
}

QMenu::item:selected {
    background-color: #e0e0e0;
}

QToolBar {
    background-color: #f5f5f5;
    border: none;
}

QPushButton {
    background-color: #e8e8e8;
    color: #2d2d2d;
    border: 1px solid #d0d0d0;
    border-radius: 3px;
    padding: 5px 10px;
}

QPushButton:hover {
    background-color: #d8d8d8;
    border: 1px solid #c0c0c0;
}

QPushButton:pressed {
    background-color: #c8c8c8;
}

QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    color: #2d2d2d;
    border: 1px solid #d0d0d0;
    border-radius: 3px;
    padding: 5px;
}

QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #4080c0;
}

QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #ffffff;
    color: #2d2d2d;
    border: 1px solid #d0d0d0;
    border-radius: 3px;
    padding: 5px;
}

QCheckBox, QRadioButton {
    color: #2d2d2d;
}

QSlider::groove:horizontal {
    background-color: #d0d0d0;
    height: 8px;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background-color: #4080c0;
    width: 18px;
    margin: -5px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background-color: #3070b0;
}

QTableWidget, QTableView {
    background-color: #ffffff;
    color: #2d2d2d;
    gridline-color: #e0e0e0;
}

QTableWidget::item:selected {
    background-color: #b0c8e8;
}

QListWidget, QListView {
    background-color: #ffffff;
    color: #2d2d2d;
}

QListWidget::item:selected {
    background-color: #b0c8e8;
}

QTabBar::tab {
    background-color: #f0f0f0;
    color: #2d2d2d;
    padding: 5px 15px;
    border: 1px solid #d0d0d0;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    border-bottom: 2px solid #4080c0;
}

QScrollBar:vertical {
    background-color: #f5f5f5;
    width: 12px;
}

QScrollBar::handle:vertical {
    background-color: #c0c0c0;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #b0b0b0;
}

QScrollBar:horizontal {
    background-color: #f5f5f5;
    height: 12px;
}

QScrollBar::handle:horizontal {
    background-color: #c0c0c0;
    border-radius: 6px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #b0b0b0;
}
"""


class ThemeManager:
    """Manages application themes."""
    
    def __init__(self):
        self.current_theme = Theme.DARK
        self.app = None
        self._load_theme_preference()
    
    def set_app(self, app):
        """Set QApplication instance."""
        self.app = app
        self.apply_theme(self.current_theme)
    
    def apply_theme(self, theme: Theme):
        """
        Apply theme to entire application.
        
        Args:
            theme: Theme to apply
        """
        if not self.app:
            logger.warning("App not set for theme manager")
            return
        
        style_dir = Path(__file__).parent
        style_file = style_dir / "style.qss"
        if style_file.exists():
            try:
                with open(style_file, 'r', encoding='utf-8') as f:
                    self.app.setStyleSheet(f.read())
            except Exception as e:
                logger.warning(f"Failed to load theme stylesheet: {e}")
        else:
            logger.warning(f"Theme file not found: {style_file}; falling back to embedded theme strings")
            self.app.setStyleSheet(DARK_STYLESHEET if theme == Theme.DARK else LIGHT_STYLESHEET)

        self.current_theme = theme
        self._save_theme_preference()
        logger.info(f"Applied theme: {theme.value}")
    
    def toggle_theme(self):
        """Toggle between dark and light theme."""
        new_theme = Theme.LIGHT if self.current_theme == Theme.DARK else Theme.DARK
        self.apply_theme(new_theme)
    
    def get_current_theme(self) -> Theme:
        """Get current theme."""
        return self.current_theme
    
    def _load_theme_preference(self):
        """Load theme preference from config."""
        try:
            from core.project_system import get_config_manager
            config = get_config_manager()
            theme_name = config.get('ui', 'theme', 'dark')
            self.current_theme = Theme(theme_name)
        except Exception as e:
            logger.debug(f"Could not load theme preference: {e}")
            self.current_theme = Theme.DARK
    
    def _save_theme_preference(self):
        """Save theme preference to config."""
        try:
            from core.project_system import get_config_manager
            config = get_config_manager()
            config.set('ui', 'theme', self.current_theme.value)
        except Exception as e:
            logger.debug(f"Could not save theme preference: {e}")


# Global instance
_theme_manager = None


def get_theme_manager() -> ThemeManager:
    """Get or create theme manager."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager
