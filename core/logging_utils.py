"""
Logging utilities for Elite Editor.

Provides consistent logging setup across all modules.
"""

import logging
from pathlib import Path
from typing import Optional


class Logger:
    """Logging configuration and setup."""
    
    _logger_cache = {}
    _log_dir: Optional[Path] = None
    
    @classmethod
    def setup(cls, name: str, prefix: str = "") -> logging.Logger:
        """
        Get or create a logger for a module.
        
        Args:
            name: Module name (__name__)
            prefix: Optional prefix for log messages
        
        Returns:
            Configured logger instance
        """
        cache_key = f"{name}:{prefix}"
        
        if cache_key in cls._logger_cache:
            return cls._logger_cache[cache_key]
        
        logger = logging.getLogger(name)
        
        # Only configure if not already configured
        if not logger.handlers:
            logger.setLevel(logging.DEBUG)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # Formatter with prefix
            if prefix:
                fmt = f"[{prefix}] %(levelname)s: %(message)s"
            else:
                fmt = "%(levelname)s: %(message)s"
            
            formatter = logging.Formatter(fmt)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
            # File handler if log dir set
            if cls._log_dir:
                try:
                    cls._log_dir.mkdir(parents=True, exist_ok=True)
                    file_handler = logging.FileHandler(cls._log_dir / "log")
                    file_handler.setLevel(logging.DEBUG)
                    
                    file_fmt = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
                    file_formatter = logging.Formatter(file_fmt)
                    file_handler.setFormatter(file_formatter)
                    logger.addHandler(file_handler)
                except Exception as e:
                    logger.warning(f"Could not setup file logging: {e}")
        
        cls._logger_cache[cache_key] = logger
        return logger
    
    @classmethod
    def set_log_dir(cls, log_dir: Path):
        """Set the directory for log files."""
        cls._log_dir = Path(log_dir)
