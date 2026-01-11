"""
PathManager - Cross-platform path management for Elite Editor
Ensures all user data lives in ~/.eliteeditor/
"""

import os
import sys
import platform
from pathlib import Path
from typing import Optional


class PathManager:
    """
    Centralized path management for Elite Editor.
    
    All user data must reside in ~/.eliteeditor/ to ensure:
    - Portability
    - Multi-user safety
    - Clean uninstall
    - Settings persistence
    """
    
    _instance: Optional['PathManager'] = None
    
    def __init__(self):
        """Initialize path manager and create directory structure if missing."""
        self._base_dir = self._get_base_dir()
        self._ensure_structure()
    
    @staticmethod
    def _get_base_dir() -> Path:
        """
        Get platform-appropriate base directory.
        Always ~/.eliteeditor/
        """
        home = Path.home()
        base = home / '.eliteeditor'
        return base
    
    def _ensure_structure(self) -> None:
        """Create directory structure if missing."""
        dirs = [
            self.config_dir,
            self.cache_dir,
            self.logs_dir,
            self.projects_dir,
            self.assets_dir,
            self.temp_dir,
            self.backups_dir,
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    # ===== MAIN DIRECTORIES =====
    
    @property
    def base_dir(self) -> Path:
        """~/.eliteeditor/"""
        return self._base_dir
    
    @property
    def config_dir(self) -> Path:
        """~/.eliteeditor/config/"""
        return self._base_dir / 'config'
    
    @property
    def cache_dir(self) -> Path:
        """~/.eliteeditor/cache/"""
        return self._base_dir / 'cache'
    
    @property
    def logs_dir(self) -> Path:
        """~/.eliteeditor/logs/"""
        return self._base_dir / 'logs'
    
    @property
    def projects_dir(self) -> Path:
        """~/.eliteeditor/projects/"""
        return self._base_dir / 'projects'
    
    @property
    def assets_dir(self) -> Path:
        """~/.eliteeditor/assets/"""
        return self._base_dir / 'assets'
    
    @property
    def temp_dir(self) -> Path:
        """~/.eliteeditor/temp/"""
        return self._base_dir / 'temp'
    
    @property
    def backups_dir(self) -> Path:
        """~/.eliteeditor/backups/"""
        return self._base_dir / 'backups'
    
    # ===== CONFIG FILES =====
    
    @property
    def app_config_file(self) -> Path:
        """~/.eliteeditor/config/app.json"""
        return self.config_dir / 'app.json'
    
    @property
    def ui_config_file(self) -> Path:
        """~/.eliteeditor/config/ui.json"""
        return self.config_dir / 'ui.json'
    
    @property
    def ai_config_file(self) -> Path:
        """~/.eliteeditor/config/ai.json"""
        return self.config_dir / 'ai.json'
    
    @property
    def keybinds_file(self) -> Path:
        """~/.eliteeditor/config/keybinds.json"""
        return self.config_dir / 'keybinds.json'
    
    @property
    def settings_file(self) -> Path:
        """~/.eliteeditor/config/settings.json"""
        return self.config_dir / 'settings.json'
    
    @property
    def recent_projects_file(self) -> Path:
        """~/.eliteeditor/config/recent.json"""
        return self.config_dir / 'recent.json'
    
    # ===== INSTALL DIRECTORIES (from workspace root) =====
    
    @property
    def app_root(self) -> Path:
        """Application installation root (where __main__.py lives)"""
        return Path(__file__).parent.parent.parent
    
    @property
    def startup_dir(self) -> Path:
        """startup/ folder (contains load.mp4, etc.)"""
        return self.app_root / 'startup'
    
    @property
    def icon_dir(self) -> Path:
        """icon/ folder (contains icon.ico, etc.)"""
        return self.app_root / 'icon'
    
    @property
    def startup_animation_file(self) -> Path:
        """startup/load.mp4"""
        return self.startup_dir / 'load.mp4'
    
    @property
    def app_icon_file(self) -> Path:
        """icon/icon.ico"""
        return self.icon_dir / 'icon.ico'
    
    # ===== UTILITY METHODS =====
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Remove invalid path characters."""
        invalid_chars = r'<>:"|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename
    
    @staticmethod
    def get_platform() -> str:
        """Return platform identifier."""
        return platform.system().lower()
    
    @classmethod
    def instance(cls) -> 'PathManager':
        """Singleton access."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __repr__(self) -> str:
        return f"<PathManager base={self.base_dir}>"
