"""Audio System - Multi-track audio with waveform visualization and mixing"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
import logging
import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class AudioProperties:
    """Audio properties."""
    sample_rate: int = 48000
    channels: int = 2
    bit_depth: int = 24  # bits
    
    @property
    def bytes_per_sample(self) -> int:
        """Bytes per sample per channel."""
        return self.bit_depth // 8
    
    @property
    def frame_size(self) -> int:
        """Bytes per frame (all channels)."""
        return self.bytes_per_sample * self.channels


class AudioTrack:
    """
    Audio track with waveform and mixing properties.
    
    Supports:
    - Volume keyframing
    - Pan
    - Mute / Solo
    - Level metering
    """
    
    def __init__(self, track_id: str, name: str):
        self.id = track_id
        self.name = name
        
        # State
        self.enabled = True
        self.muted = False
        self.solo = False
        self.locked = False
        
        # Mixing
        self.volume = 1.0  # 0-2
        self.pan = 0.0  # -1 (left) to 1 (right)
        
        # Keyframes
        self.volume_keyframes: List[tuple] = []  # (frame, value)
        self.pan_keyframes: List[tuple] = []  # (frame, value)
        
        # Audio data
        self.waveform: Optional[np.ndarray] = None
        self.duration = 0.0  # seconds
        
        # Meters
        self.peak_level = 0.0  # dBFS
        self.rms_level = 0.0  # dBFS
        
        # Observers
        self._changed_callbacks: List[Callable] = []
    
    def set_volume(self, volume: float) -> None:
        """Set volume."""
        self.volume = max(0.0, min(volume, 2.0))
        self._notify_changed()
    
    def set_pan(self, pan: float) -> None:
        """Set pan."""
        self.pan = max(-1.0, min(pan, 1.0))
        self._notify_changed()
    
    def add_volume_keyframe(self, frame: int, value: float) -> None:
        """Add volume keyframe."""
        # Remove existing
        self.volume_keyframes = [(f, v) for f, v in self.volume_keyframes if f != frame]
        # Add new
        self.volume_keyframes.append((frame, value))
        self.volume_keyframes.sort(key=lambda x: x[0])
        self._notify_changed()
    
    def add_pan_keyframe(self, frame: int, value: float) -> None:
        """Add pan keyframe."""
        # Remove existing
        self.pan_keyframes = [(f, v) for f, v in self.pan_keyframes if f != frame]
        # Add new
        self.pan_keyframes.append((frame, value))
        self.pan_keyframes.sort(key=lambda x: x[0])
        self._notify_changed()
    
    def get_volume_at_frame(self, frame: int) -> float:
        """Get interpolated volume at frame."""
        if not self.volume_keyframes:
            return self.volume
        # TODO: Implement interpolation
        return self.volume
    
    def get_pan_at_frame(self, frame: int) -> float:
        """Get interpolated pan at frame."""
        if not self.pan_keyframes:
            return self.pan
        # TODO: Implement interpolation
        return self.pan
    
    def load_waveform_data(self, audio_data: np.ndarray, 
                          sample_rate: int = 48000) -> None:
        """Load raw audio data and generate waveform visualization."""
        # Downsample for visualization (one pixel per 512 samples)
        downsample_factor = 512
        if len(audio_data) > 0:
            # Handle mono/stereo
            if len(audio_data.shape) == 1:
                # Mono
                downsampled = audio_data[::downsample_factor]
            else:
                # Stereo - take RMS of channels
                rms = np.sqrt(np.mean(audio_data ** 2, axis=1))
                downsampled = rms[::downsample_factor]
            
            self.waveform = downsampled
            self.duration = len(audio_data) / sample_rate
    
    def register_changed_callback(self, callback: Callable) -> None:
        """Register change callback."""
        if callback not in self._changed_callbacks:
            self._changed_callbacks.append(callback)
    
    def _notify_changed(self) -> None:
        """Notify observers."""
        for callback in self._changed_callbacks:
            try:
                callback(self)
            except Exception as e:
                logger.error(f"Audio track callback error: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            'id': self.id,
            'name': self.name,
            'enabled': self.enabled,
            'muted': self.muted,
            'solo': self.solo,
            'locked': self.locked,
            'volume': self.volume,
            'pan': self.pan,
            'volume_keyframes': self.volume_keyframes,
            'pan_keyframes': self.pan_keyframes,
        }


class AudioMixer:
    """
    Audio mixer for multiple tracks.
    
    Handles:
    - Level metering
    - Ducking
    - Normalization
    - Master volume
    """
    
    def __init__(self):
        self.master_volume = 1.0
        self.limiter_enabled = True
        self.limiter_threshold = -1.0  # dBFS
        
        # Compressor settings
        self.compressor_enabled = False
        self.compressor_threshold = -20.0
        self.compressor_ratio = 4.0
        
        # Loudness targeting (LUFS)
        self.target_loudness = -23.0
        self.auto_normalize_enabled = False
    
    def calculate_db(self, linear: float) -> float:
        """Convert linear to dB."""
        if linear <= 0:
            return -np.inf
        return 20.0 * np.log10(linear)
    
    def calculate_linear(self, db: float) -> float:
        """Convert dB to linear."""
        return 10.0 ** (db / 20.0)
    
    def mix_tracks(self, tracks: List[AudioTrack], 
                   duration_frames: int, fps: int = 30) -> np.ndarray:
        """
        Mix multiple audio tracks.
        
        Returns:
            Mixed audio array
        """
        sample_rate = 48000
        num_samples = int(duration_frames / fps * sample_rate)
        
        # Initialize output
        output = np.zeros((num_samples, 2))  # Stereo
        
        for track in tracks:
            if not track.enabled or track.muted:
                continue
            
            # This is a simplified mixer
            # In production, would properly mix audio data
            logger.debug(f"Mixing track: {track.name}")
        
        return output
    
    def normalize(self, audio: np.ndarray, target_db: float = -23.0) -> np.ndarray:
        """Normalize audio to target loudness."""
        # TODO: Implement LUFS normalization
        return audio


class AudioClip:
    """Audio clip with effects and properties."""
    
    def __init__(self, clip_id: str, name: str):
        self.id = clip_id
        self.name = name
        
        # Position
        self.timeline_in_frame = 0
        self.timeline_out_frame = 0
        
        # Source
        self.source_file = ""
        
        # Properties
        self.volume = 1.0
        self.pan = 0.0
        self.muted = False
        self.locked = False
        
        # Effects
        self.effects: List[str] = []
        
        # Waveform
        self.waveform: Optional[np.ndarray] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            'id': self.id,
            'name': self.name,
            'timeline_in': self.timeline_in_frame,
            'timeline_out': self.timeline_out_frame,
            'source': self.source_file,
            'volume': self.volume,
            'pan': self.pan,
            'muted': self.muted,
            'effects': self.effects,
        }
