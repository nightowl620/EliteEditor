"""
MoviePy Dynamic Registry

Inspects MoviePy at runtime and creates a registry of:
- All video clip functions
- All audio clip functions
- All compositing functions
- All video effects (from video.fx)
- All audio effects (from audio.fx)
- All tools and utilities

This is NOT a hardcoded list. It dynamically discovers what MoviePy actually exposes.
"""

import inspect
import logging
from typing import Dict, List, Callable, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

try:
    import moviepy
    from moviepy import VideoClip, AudioClip, CompositeVideoClip, CompositeAudioClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    VideoClip = None
    AudioClip = None

logger = logging.getLogger(__name__)


@dataclass
class EffectSignature:
    """Metadata about a MoviePy effect function."""
    name: str
    module: str
    category: str  # 'video', 'audio', 'compositing', 'tool', 'util'
    signature: inspect.Signature
    doc: str
    callable: Callable
    parameters: Dict[str, inspect.Parameter]
    
    def get_parameter_types(self) -> Dict[str, str]:
        """Extract parameter types from signature."""
        types = {}
        for pname, param in self.parameters.items():
            if param.annotation == inspect.Parameter.empty:
                types[pname] = 'any'
            else:
                types[pname] = str(param.annotation)
        return types
    
    def get_defaults(self) -> Dict[str, Any]:
        """Extract default values."""
        defaults = {}
        for pname, param in self.parameters.items():
            if param.default != inspect.Parameter.empty:
                defaults[pname] = param.default
        return defaults


class MoviePyRegistry:
    """Dynamic registry of all MoviePy functions."""
    
    def __init__(self):
        self.video_effects: Dict[str, EffectSignature] = {}
        self.audio_effects: Dict[str, EffectSignature] = {}
        self.compositing: Dict[str, EffectSignature] = {}
        self.tools: Dict[str, EffectSignature] = {}
        self.clips: Dict[str, EffectSignature] = {}
        self.available = MOVIEPY_AVAILABLE
        
        if self.available:
            self._discover_all()
    
    def _discover_all(self):
        """Discover all MoviePy functions."""
        logger.info("Discovering MoviePy API...")
        
        # Discover video effects
        try:
            import moviepy.video.fx as video_fx_module
            self._discover_module(video_fx_module, 'video', self.video_effects)
            logger.info(f"Discovered {len(self.video_effects)} video effects")
        except Exception as e:
            logger.warning(f"Failed to discover video effects: {e}")
        
        # Discover audio effects
        try:
            import moviepy.audio.fx as audio_fx_module
            self._discover_module(audio_fx_module, 'audio', self.audio_effects)
            logger.info(f"Discovered {len(self.audio_effects)} audio effects")
        except Exception as e:
            logger.warning(f"Failed to discover audio effects: {e}")
        
        # Discover compositing functions
        try:
            import moviepy.video.compositing as compositing_module
            self._discover_module(compositing_module, 'compositing', self.compositing)
            logger.info(f"Discovered {len(self.compositing)} compositing functions")
        except Exception as e:
            logger.warning(f"Failed to discover compositing: {e}")
        
        # Discover clip types
        try:
            import moviepy.video.io.VideoFileClip as vfc
            import moviepy.audio.io.AudioFileClip as afc
            
            # These are classes, not functions, but we expose them
            if hasattr(moviepy, 'VideoFileClip'):
                self.clips['VideoFileClip'] = self._create_effect_sig(
                    'VideoFileClip', 'moviepy', 'clip',
                    moviepy.VideoFileClip
                )
            if hasattr(moviepy, 'AudioFileClip'):
                self.clips['AudioFileClip'] = self._create_effect_sig(
                    'AudioFileClip', 'moviepy', 'clip',
                    moviepy.AudioFileClip
                )
            if hasattr(moviepy, 'ImageClip'):
                self.clips['ImageClip'] = self._create_effect_sig(
                    'ImageClip', 'moviepy', 'clip',
                    moviepy.ImageClip
                )
            if hasattr(moviepy, 'TextClip'):
                self.clips['TextClip'] = self._create_effect_sig(
                    'TextClip', 'moviepy', 'clip',
                    moviepy.TextClip
                )
            if hasattr(moviepy, 'ColorClip'):
                self.clips['ColorClip'] = self._create_effect_sig(
                    'ColorClip', 'moviepy', 'clip',
                    moviepy.ColorClip
                )
            if hasattr(moviepy, 'CompositeVideoClip'):
                self.clips['CompositeVideoClip'] = self._create_effect_sig(
                    'CompositeVideoClip', 'moviepy', 'clip',
                    moviepy.CompositeVideoClip
                )
            if hasattr(moviepy, 'CompositeAudioClip'):
                self.clips['CompositeAudioClip'] = self._create_effect_sig(
                    'CompositeAudioClip', 'moviepy', 'clip',
                    moviepy.CompositeAudioClip
                )
            
            logger.info(f"Discovered {len(self.clips)} clip types")
        except Exception as e:
            logger.warning(f"Failed to discover clip types: {e}")
    
    def _discover_module(self, module, category: str, target_dict: Dict):
        """Recursively discover functions in a module."""
        if not hasattr(module, '__all__'):
            logger.warning(f"Module {module.__name__} has no __all__")
            return
        
        for name in module.__all__:
            try:
                obj = getattr(module, name)
                if callable(obj) and not isinstance(obj, type):
                    sig = self._create_effect_sig(name, module.__name__, category, obj)
                    target_dict[name] = sig
            except Exception as e:
                logger.debug(f"Failed to discover {name} from {module.__name__}: {e}")
    
    def _create_effect_sig(self, name: str, module: str, category: str, 
                          callable_obj: Callable) -> EffectSignature:
        """Create an EffectSignature from a callable."""
        try:
            sig = inspect.signature(callable_obj)
        except ValueError:
            sig = inspect.Signature()
        
        try:
            doc = inspect.getdoc(callable_obj) or ""
        except:
            doc = ""
        
        # Filter out 'self' and 'cls' parameters
        parameters = {
            name: param for name, param in sig.parameters.items()
            if name not in ('self', 'cls')
        }
        
        return EffectSignature(
            name=name,
            module=module,
            category=category,
            signature=sig,
            doc=doc,
            callable=callable_obj,
            parameters=parameters
        )
    
    def get_all_effects(self) -> Dict[str, EffectSignature]:
        """Get all effects combined."""
        return {
            **self.video_effects,
            **self.audio_effects,
            **self.compositing,
            **self.clips,
            **self.tools
        }
    
    def get_effects_by_category(self, category: str) -> Dict[str, EffectSignature]:
        """Get effects by category."""
        if category == 'video':
            return self.video_effects
        elif category == 'audio':
            return self.audio_effects
        elif category == 'compositing':
            return self.compositing
        elif category == 'clip':
            return self.clips
        elif category == 'tool':
            return self.tools
        return {}
    
    def get_effect(self, name: str) -> EffectSignature:
        """Get a specific effect by name."""
        all_effects = self.get_all_effects()
        return all_effects.get(name)
    
    def export_to_dict(self) -> Dict[str, Any]:
        """Export registry as JSON-serializable dict."""
        def sig_to_dict(sig: EffectSignature) -> Dict:
            return {
                'name': sig.name,
                'module': sig.module,
                'category': sig.category,
                'doc': sig.doc,
                'parameters': {
                    pname: {
                        'annotation': str(param.annotation),
                        'default': str(param.default) if param.default != inspect.Parameter.empty else None,
                        'kind': str(param.kind)
                    }
                    for pname, param in sig.parameters.items()
                }
            }
        
        return {
            'video_effects': {k: sig_to_dict(v) for k, v in self.video_effects.items()},
            'audio_effects': {k: sig_to_dict(v) for k, v in self.audio_effects.items()},
            'compositing': {k: sig_to_dict(v) for k, v in self.compositing.items()},
            'clips': {k: sig_to_dict(v) for k, v in self.clips.items()},
            'tools': {k: sig_to_dict(v) for k, v in self.tools.items()},
        }


# Global singleton
_registry = None


def get_registry() -> MoviePyRegistry:
    """Get or create the global MoviePy registry."""
    global _registry
    if _registry is None:
        _registry = MoviePyRegistry()
    return _registry


def list_all_effects() -> Dict[str, List[str]]:
    """List all available effects by category."""
    registry = get_registry()
    return {
        'video': list(registry.video_effects.keys()),
        'audio': list(registry.audio_effects.keys()),
        'compositing': list(registry.compositing.keys()),
        'clips': list(registry.clips.keys()),
        'tools': list(registry.tools.keys()),
    }
