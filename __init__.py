"""
Elite Editor - Professional Python-based NLE with AI Integration
Version: 1.0.0
Author: Elite Development Team
License: Proprietary
"""

__version__ = "1.0.0"
__app_name__ = "Elite Editor"
__app_id__ = "com.eliteeditor.app"

from core.config import ConfigManager
from core.paths import PathManager

__all__ = [
    'ConfigManager',
    'PathManager',
    '__version__',
    '__app_name__',
    '__app_id__',
]
