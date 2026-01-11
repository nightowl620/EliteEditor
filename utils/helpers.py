"""
Elite Editor Utilities - Common functions and helpers
"""

import os
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
import mimetypes


def generate_id() -> str:
    """Generate unique ID."""
    return str(uuid.uuid4())


def is_video_file(path: Path) -> bool:
    """Check if file is video."""
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}
    return path.suffix.lower() in video_extensions


def is_audio_file(path: Path) -> bool:
    """Check if file is audio."""
    audio_extensions = {'.mp3', '.wav', '.aac', '.m4a', '.flac', '.ogg', '.wma'}
    return path.suffix.lower() in audio_extensions


def is_image_file(path: Path) -> bool:
    """Check if file is image."""
    image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp'}
    return path.suffix.lower() in image_extensions


def get_media_type(path: Path) -> Optional[str]:
    """Get media type from file."""
    if is_video_file(path):
        return 'video'
    elif is_audio_file(path):
        return 'audio'
    elif is_image_file(path):
        return 'image'
    return None


def frame_to_timecode(frame: int, fps: float) -> str:
    """Convert frame number to timecode HH:MM:SS:FF."""
    total_seconds = frame / fps
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    frames = int(frame % int(fps))
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"


def timecode_to_frame(timecode: str, fps: float) -> int:
    """Convert timecode HH:MM:SS:FF to frame number."""
    parts = timecode.split(':')
    if len(parts) != 4:
        return 0
    
    hours, minutes, seconds, frames = map(int, parts)
    total_seconds = hours * 3600 + minutes * 60 + seconds + frames / fps
    return int(total_seconds * fps)


def format_bytes(bytes: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} TB"


def format_duration(seconds: float) -> str:
    """Format duration as HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max."""
    return max(min_val, min(max_val, value))


def ease_in_quad(t: float) -> float:
    """Ease-in quadratic interpolation."""
    return t * t


def ease_out_quad(t: float) -> float:
    """Ease-out quadratic interpolation."""
    return -t * (t - 2)


def ease_in_out_quad(t: float) -> float:
    """Ease-in-out quadratic interpolation."""
    if t < 0.5:
        return 2 * t * t
    return -1 + (4 - 2 * t) * t


def linear_interpolation(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b."""
    return a + (b - a) * t


def recursive_dict_update(target: Dict[str, Any], update: Dict[str, Any]) -> None:
    """Recursively update dictionary."""
    for key, value in update.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            recursive_dict_update(target[key], value)
        else:
            target[key] = value


def create_backup(file_path: Path, backup_dir: Path) -> Optional[Path]:
    """
    Create backup of file.
    
    Args:
        file_path: File to backup
        backup_dir: Directory to store backup
    
    Returns:
        Path to backup file
    """
    if not file_path.exists():
        return None
    
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Add timestamp to filename
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"
    
    import shutil
    shutil.copy2(file_path, backup_path)
    
    return backup_path
