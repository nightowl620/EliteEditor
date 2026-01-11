"""Effects System - Professional effects, transitions, and adjustments"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging


logger = logging.getLogger(__name__)


class EffectCategory(Enum):
    """Effect categories."""
    COLOR = 'color'
    BLUR = 'blur'
    DISTORTION = 'distortion'
    LIGHT = 'light'
    TRANSITION = 'transition'
    TIME = 'time'
    AUDIO = 'audio'
    KEYING = 'keying'
    UTILITY = 'utility'


class BlendMode(Enum):
    """Blend modes."""
    NORMAL = 'normal'
    ADD = 'add'
    SUBTRACT = 'subtract'
    MULTIPLY = 'multiply'
    SCREEN = 'screen'
    OVERLAY = 'overlay'
    SOFT_LIGHT = 'soft_light'
    HARD_LIGHT = 'hard_light'
    COLOR_DODGE = 'color_dodge'
    COLOR_BURN = 'color_burn'


@dataclass
class EffectParameter:
    """Effect parameter definition."""
    name: str
    param_type: str  # float, int, bool, string, choice
    default: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    options: Optional[List[str]] = None
    description: str = ""
    
    def validate(self, value: Any) -> bool:
        """Validate parameter value."""
        if self.param_type == 'float' or self.param_type == 'int':
            if self.min_value is not None and value < self.min_value:
                return False
            if self.max_value is not None and value > self.max_value:
                return False
        elif self.param_type == 'choice':
            if self.options and value not in self.options:
                return False
        return True


class Effect:
    """
    Single effect instance.
    
    Can be applied to clips or as adjustment layers.
    Supports keyframing of parameters.
    """
    
    def __init__(self, effect_id: str, effect_type: str, name: str = ""):
        self.id = effect_id
        self.type = effect_type
        self.name = name or effect_type
        
        # State
        self.enabled = True
        self.opacity = 1.0  # 0-1
        self.blend_mode = BlendMode.NORMAL
        
        # Parameters
        self.parameters: Dict[str, Any] = {}
        self._parameter_defs: Dict[str, EffectParameter] = {}
        
        # Keyframes
        self.keyframes: Dict[str, List[tuple]] = {}  # param -> [(frame, value), ...]
        
        # Observers
        self._changed_callbacks: List[Callable] = []
    
    def define_parameter(self, param: EffectParameter) -> None:
        """Define effect parameter."""
        self._parameter_defs[param.name] = param
        if param.name not in self.parameters:
            self.parameters[param.name] = param.default
    
    def set_parameter(self, name: str, value: Any) -> bool:
        """Set parameter value."""
        if name not in self._parameter_defs:
            logger.warning(f"Unknown parameter: {name}")
            return False
        
        param_def = self._parameter_defs[name]
        if not param_def.validate(value):
            logger.warning(f"Invalid value for {name}: {value}")
            return False
        
        self.parameters[name] = value
        self._notify_changed()
        return True
    
    def get_parameter(self, name: str) -> Any:
        """Get parameter value (accounting for keyframes if applicable)."""
        return self.parameters.get(name)
    
    def get_parameter_at_frame(self, name: str, frame: int) -> Any:
        """Get interpolated parameter value at frame."""
        # TODO: Implement keyframe interpolation
        return self.parameters.get(name)
    
    def add_keyframe(self, param_name: str, frame: int, value: Any) -> None:
        """Add keyframe for parameter."""
        if param_name not in self.keyframes:
            self.keyframes[param_name] = []
        
        # Remove existing keyframe at this frame
        self.keyframes[param_name] = [
            kf for kf in self.keyframes[param_name] if kf[0] != frame
        ]
        
        # Add new keyframe
        self.keyframes[param_name].append((frame, value))
        self.keyframes[param_name].sort(key=lambda x: x[0])
        self._notify_changed()
    
    def remove_keyframe(self, param_name: str, frame: int) -> None:
        """Remove keyframe."""
        if param_name in self.keyframes:
            self.keyframes[param_name] = [
                kf for kf in self.keyframes[param_name] if kf[0] != frame
            ]
            self._notify_changed()
    
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
                logger.error(f"Effect callback error: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            'id': self.id,
            'type': self.type,
            'name': self.name,
            'enabled': self.enabled,
            'opacity': self.opacity,
            'blend_mode': self.blend_mode.value,
            'parameters': self.parameters.copy(),
            'keyframes': self.keyframes.copy(),
        }


class EffectStack:
    """
    Stack of effects applied to a clip or adjustment layer.
    
    Effects are processed in order.
    """
    
    def __init__(self):
        self.effects: List[Effect] = []
        self._changed_callbacks: List[Callable] = []
    
    def add_effect(self, effect: Effect, position: int = -1) -> None:
        """Add effect to stack."""
        if position < 0:
            self.effects.append(effect)
        else:
            self.effects.insert(position, effect)
        
        effect.register_changed_callback(self._on_effect_changed)
        self._notify_changed()
    
    def remove_effect(self, effect: Effect) -> bool:
        """Remove effect from stack."""
        if effect in self.effects:
            self.effects.remove(effect)
            self._notify_changed()
            return True
        return False
    
    def move_effect(self, effect: Effect, position: int) -> None:
        """Reorder effect in stack."""
        if effect in self.effects:
            self.effects.remove(effect)
            self.effects.insert(position, effect)
            self._notify_changed()
    
    def get_enabled_effects(self) -> List[Effect]:
        """Get only enabled effects."""
        return [e for e in self.effects if e.enabled]
    
    def register_changed_callback(self, callback: Callable) -> None:
        """Register change callback."""
        if callback not in self._changed_callbacks:
            self._changed_callbacks.append(callback)
    
    def _on_effect_changed(self, effect: Effect) -> None:
        """Handle effect change."""
        self._notify_changed()
    
    def _notify_changed(self) -> None:
        """Notify observers."""
        for callback in self._changed_callbacks:
            try:
                callback(self)
            except Exception as e:
                logger.error(f"Effect stack callback error: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            'effects': [e.to_dict() for e in self.effects],
        }


class TransitionEffect(Effect):
    """
    Transition effect between clips.
    
    Typically applied to second clip or between clips.
    """
    
    def __init__(self, transition_id: str, transition_type: str):
        super().__init__(transition_id, transition_type)
        
        # Duration in frames
        self.duration = 30  # 1 second at 30fps
        
        # Easing function
        self.easing = 'ease_in_out'  # ease_in, ease_out, ease_in_out, linear
    
    def __repr__(self) -> str:
        return f"<Transition {self.type} {self.duration}f>"


class ColorCorrectionEffect(Effect):
    """Color correction effect."""
    
    def __init__(self):
        super().__init__('color_correction', 'color_correction')
        
        # Define parameters
        self.define_parameter(EffectParameter('brightness', 'float', 0.0, -100, 100))
        self.define_parameter(EffectParameter('contrast', 'float', 0.0, -100, 100))
        self.define_parameter(EffectParameter('saturation', 'float', 0.0, -100, 100))
        self.define_parameter(EffectParameter('hue', 'float', 0.0, -180, 180))
        self.define_parameter(EffectParameter('temperature', 'float', 0.0, -50, 50))
        self.define_parameter(EffectParameter('tint', 'float', 0.0, -50, 50))
    
    def __repr__(self) -> str:
        return "<ColorCorrectionEffect>"


class BlurEffect(Effect):
    """Blur effect."""
    
    def __init__(self):
        super().__init__('blur', 'blur')
        
        # Define parameters
        self.define_parameter(EffectParameter('amount', 'float', 0.0, 0.0, 100.0))
        self.define_parameter(EffectParameter('type', 'choice', 'gaussian', 
                                             options=['gaussian', 'motion', 'radial']))
    
    def __repr__(self) -> str:
        return "<BlurEffect>"


# Built-in effects library
BUILTIN_EFFECTS = {
    'color_correction': ColorCorrectionEffect,
    'blur': BlurEffect,
    'opacity': lambda: Effect('opacity', 'opacity', 'Opacity'),
    'scale': lambda: Effect('scale', 'scale', 'Scale'),
    'position': lambda: Effect('position', 'position', 'Position'),
    'rotation': lambda: Effect('rotation', 'rotation', 'Rotation'),
}
