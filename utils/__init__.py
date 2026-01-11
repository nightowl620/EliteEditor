"""Utility modules and helpers"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging
import json
from pathlib import Path


logger = logging.getLogger(__name__)


class Logger:
    """Configure application logging."""
    
    @staticmethod
    def setup(log_dir: Path, level: int = logging.DEBUG) -> None:
        """Setup logging system."""
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / 'app.log'
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '[%(levelname)s] %(name)s: %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        logger.info(f"Logging initialized: {log_file}")


class JSONHelper:
    """JSON serialization utilities."""
    
    @staticmethod
    def save_json(data: Any, path: Path, indent: int = 2) -> None:
        """Save data to JSON file."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent)
        except Exception as e:
            logger.error(f"Failed to save JSON to {path}: {e}")
    
    @staticmethod
    def load_json(path: Path) -> Optional[Dict[str, Any]]:
        """Load JSON from file."""
        try:
            if not path.exists():
                return None
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load JSON from {path}: {e}")
            return None


class GeometryHelper:
    """Geometry and calculation utilities."""
    
    @staticmethod
    def clamp(value: float, min_val: float, max_val: float) -> float:
        """Clamp value between min and max."""
        return max(min_val, min(value, max_val))
    
    @staticmethod
    def linear_interpolate(a: float, b: float, t: float) -> float:
        """Linear interpolation between a and b, t in [0, 1]."""
        return a + (b - a) * t
    
    @staticmethod
    def ease_in_out(t: float) -> float:
        """Ease in-out cubic function."""
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - pow(-2 * t + 2, 3) / 2
    
    @staticmethod
    def ease_in(t: float) -> float:
        """Ease in cubic function."""
        return t * t * t
    
    @staticmethod
    def ease_out(t: float) -> float:
        """Ease out cubic function."""
        return 1 - pow(1 - t, 3)


class TimeHelper:
    """Time calculation utilities."""
    
    @staticmethod
    def frames_to_timecode(frames: int, fps: int = 30) -> str:
        """Convert frames to HH:MM:SS:FF timecode."""
        total_seconds = frames // fps
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        frame_part = frames % fps
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frame_part:02d}"
    
    @staticmethod
    def seconds_to_frames(seconds: float, fps: int = 30) -> int:
        """Convert seconds to frames."""
        return int(seconds * fps)
    
    @staticmethod
    def frames_to_seconds(frames: int, fps: int = 30) -> float:
        """Convert frames to seconds."""
        return frames / fps
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class ColorHelper:
    """Color utilities."""
    
    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def rgb_to_hex(r: int, g: int, b: int) -> str:
        """Convert RGB to hex color."""
        return f"#{r:02x}{g:02x}{b:02x}"
    
    @staticmethod
    def rgb_to_normalized(r: int, g: int, b: int) -> Tuple[float, float, float]:
        """Convert RGB (0-255) to normalized (0-1)."""
        return (r / 255.0, g / 255.0, b / 255.0)
    
    @staticmethod
    def normalized_to_rgb(r: float, g: float, b: float) -> Tuple[int, int, int]:
        """Convert normalized (0-1) to RGB (0-255)."""
        return (int(r * 255), int(g * 255), int(b * 255))


class UnitConversion:
    """Unit conversion utilities."""
    
    @staticmethod
    def pixels_to_dip(pixels: int, dpi: int = 96) -> float:
        """Convert pixels to device-independent pixels."""
        return pixels * 96 / dpi
    
    @staticmethod
    def dip_to_pixels(dip: float, dpi: int = 96) -> int:
        """Convert DIP to pixels."""
        return int(dip * dpi / 96)


class FileHelper:
    """File system utilities."""
    
    @staticmethod
    def get_file_size_mb(path: Path) -> float:
        """Get file size in MB."""
        if not path.exists():
            return 0.0
        return path.stat().st_size / (1024 * 1024)
    
    @staticmethod
    def get_directory_size_mb(path: Path) -> float:
        """Get directory size in MB."""
        total = 0
        for item in path.rglob('*'):
            if item.is_file():
                total += item.stat().st_size
        return total / (1024 * 1024)
    
    @staticmethod
    def safe_filename(filename: str) -> str:
        """Make filename safe for filesystem."""
        import re
        # Remove invalid characters
        filename = re.sub(r'[<>:"|?*\\/]', '_', filename)
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        return filename if filename else 'unnamed'
