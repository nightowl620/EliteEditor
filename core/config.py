"""
ConfigManager - Unified configuration system for Elite Editor
Handles app, UI, AI, and performance settings with type safety
"""

import json
import logging
from typing import Any, Dict, Optional, Union
from pathlib import Path
from core.paths import PathManager


logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Centralized configuration manager.
    
    Automatically loads/saves from ~/.eliteeditor/config/
    Maintains in-memory cache with file sync.
    Supports app.json, ui.json, ai.json, keybinds.json, settings.json
    """
    
    _instance: Optional['ConfigManager'] = None
    
    def __init__(self):
        """Initialize config manager."""
        self.paths = PathManager.instance()
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._defaults = self._get_defaults()
        self._load_all()
    
    # ===== CORE API =====
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            section: Config file base name (app, ui, ai, keybinds, settings)
            key: Dot-notation key (e.g., 'window.width', 'ai.api_key')
            default: Fallback value
        
        Returns:
            Configuration value or default
        """
        if section not in self._cache:
            self._load_config(section)
        
        config = self._cache.get(section, {})
        
        # Support dot notation
        if '.' in key:
            keys = key.split('.')
            val = config
            for k in keys:
                if isinstance(val, dict):
                    val = val.get(k)
                else:
                    return default
            return val if val is not None else default
        
        return config.get(key, default)
    
    def set(self, section: str, key: str, value: Any, persist: bool = True) -> None:
        """
        Set configuration value.
        
        Args:
            section: Config file base name
            key: Dot-notation key
            value: New value
            persist: Save to disk immediately
        """
        if section not in self._cache:
            self._load_config(section)
        
        config = self._cache[section]
        
        # Support dot notation
        if '.' in key:
            keys = key.split('.')
            current = config
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            current[keys[-1]] = value
        else:
            config[key] = value
        
        if persist:
            self._save_config(section)
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire config section."""
        if section not in self._cache:
            self._load_config(section)
        return self._cache.get(section, {}).copy()
    
    def set_section(self, section: str, data: Dict[str, Any], persist: bool = True) -> None:
        """Replace entire config section."""
        self._cache[section] = data
        if persist:
            self._save_config(section)
    
    def reset_to_defaults(self, section: str) -> None:
        """Reset section to defaults."""
        if section in self._defaults:
            self._cache[section] = self._defaults[section].copy()
            self._save_config(section)
    
    # ===== PRIVATE =====
    
    def _get_defaults(self) -> Dict[str, Dict[str, Any]]:
        """Default configuration templates."""
        return {
            'app': {
                'version': '1.0.0',
                'app_name': 'Elite Editor',
                'show_splash': True,
                'splash_duration': 3.0,
                'startup_animation_enabled': True,
                'window_state': 'normal',
                'recent_projects_limit': 10,
                'autosave_enabled': True,
                'autosave_interval': 30,  # seconds
                'crash_recovery_enabled': True,
            },
            'ui': {
                'theme': 'dark',  # dark | light
                'accent_color': '#0d9488',  # teal
                'ui_scale': 1.0,
                'font_family': 'Segoe UI',
                'font_size': 10,
                'window': {
                    'width': 1920,
                    'height': 1080,
                    'maximized': True,
                },
                'timeline': {
                    'zoom_level': 1.0,
                    'show_grid': True,
                    'snap_enabled': True,
                    'snap_threshold': 10,  # pixels
                },
                'panels': {
                    'left_visible': True,
                    'right_visible': True,
                    'bottom_visible': True,
                    'left_width': 300,
                    'right_width': 350,
                    'bottom_height': 250,
                },
            },
            'ai': {
                'api_key': '',  # User must set
                'model_text': 'gemini-3-flash-preview',
                'model_tts': 'gemini-2.5-flash-preview-tts',
                'model_image': 'gemini-2.5-flash-image',
                'thinking_level': 'HIGH',  # HIGH | MEDIUM | OFF
                'max_tokens': 4096,
                'temperature': 0.7,
                'enabled': False,  # Until API key is set
            },
            'settings': {
                'performance': {
                    'frame_cache_limit': 500,  # frames
                    'proxy_quality': 'half',  # quarter | half | full
                    'max_workers': 4,
                    'debounce_delay': 100,  # ms
                },
                'playback': {
                    'default_fps': 30,
                    'default_width': 1920,
                    'default_height': 1080,
                    'preview_scale': 0.5,
                },
                'render': {
                    'default_preset': '1080p',
                    'codec': 'h264',
                    'bitrate': '8000k',
                    'audio_bitrate': '192k',
                    'threads': 4,
                },
                'audio': {
                    'default_sample_rate': 48000,
                    'default_channels': 2,
                    'normalize_loudness': -23.0,  # LUFS
                },
            },
            'keybinds': self._get_default_keybinds(),
        }
    
    def _get_default_keybinds(self) -> Dict[str, str]:
        """Default keybinds."""
        return {
            # File
            'file.new': 'Ctrl+N',
            'file.open': 'Ctrl+O',
            'file.save': 'Ctrl+S',
            'file.export': 'Ctrl+Shift+E',
            'file.exit': 'Ctrl+Q',
            # Edit
            'edit.undo': 'Ctrl+Z',
            'edit.redo': 'Ctrl+Y',
            'edit.cut': 'Ctrl+X',
            'edit.copy': 'Ctrl+C',
            'edit.paste': 'Ctrl+V',
            'edit.delete': 'Delete',
            'edit.select_all': 'Ctrl+A',
            # Timeline
            'timeline.play_pause': 'Space',
            'timeline.mark_in': 'I',
            'timeline.mark_out': 'O',
            'timeline.goto_start': 'Home',
            'timeline.goto_end': 'End',
            # View
            'view.fullscreen': 'F5',
            'view.fit_to_window': 'Shift+Z',
            'view.zoom_in': 'Ctrl+Plus',
            'view.zoom_out': 'Ctrl+Minus',
        }
    
    def _load_all(self) -> None:
        """Load all config files."""
        for section in self._defaults.keys():
            self._load_config(section)
    
    def _load_config(self, section: str) -> None:
        """Load single config file."""
        config_file = self._get_config_file(section)
        
        # Try to load existing config
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._cache[section] = data
                    logger.debug(f"Loaded config: {config_file}")
                    return
            except Exception as e:
                logger.error(f"Failed to load {config_file}: {e}")
        
        # Use defaults and create file
        if section in self._defaults:
            self._cache[section] = self._defaults[section].copy()
            self._save_config(section)
    
    def _save_config(self, section: str) -> None:
        """Save config section to disk."""
        config_file = self._get_config_file(section)
        
        try:
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache.get(section, {}), f, indent=2)
                logger.debug(f"Saved config: {config_file}")
        except Exception as e:
            logger.error(f"Failed to save {config_file}: {e}")
    
    def _get_config_file(self, section: str) -> Path:
        """Get config file path for section."""
        section_map = {
            'app': self.paths.app_config_file,
            'ui': self.paths.ui_config_file,
            'ai': self.paths.ai_config_file,
            'keybinds': self.paths.keybinds_file,
            'settings': self.paths.settings_file,
        }
        return section_map.get(section, self.paths.config_dir / f'{section}.json')
    
    @classmethod
    def instance(cls) -> 'ConfigManager':
        """Singleton access."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __repr__(self) -> str:
        return f"<ConfigManager sections={list(self._cache.keys())}>"
