"""UI Module - Professional PySide6-based user interface"""

from typing import Optional
import logging

from ui.properties_panel import PropertiesPanel

logger = logging.getLogger(__name__)

__all__ = [
    'PropertiesPanel',
    'UIManager'
]


class UIManager:
    """Centralized UI manager."""
    
    def __init__(self):
        self._main_window: Optional['EliteEditorMainWindow'] = None
        self._app = None
    
    def initialize(self, app) -> None:
        """Initialize UI system."""
        self._app = app
        logger.info("UI Manager initialized")
    
    def create_main_window(self) -> 'EliteEditorMainWindow':
        """Create main application window."""
        if self._main_window is None:
            from ui.main_window import EliteEditorMainWindow
            self._main_window = EliteEditorMainWindow()
        return self._main_window
    
    @property
    def main_window(self) -> Optional['EliteEditorMainWindow']:
        """Get main window instance."""
        return self._main_window


# Placeholder imports - these will be implemented next
__all__ = [
    'UIManager',
]
