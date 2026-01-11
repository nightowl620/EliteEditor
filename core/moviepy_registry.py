"""
MoviePyRegistry - Dynamic reflection of all MoviePy symbols

Automatically introspects MoviePy modules to expose:
- All video effects (moviepy.video.fx.*)
- All audio effects (moviepy.audio.fx.*)
- All compositing functions (moviepy.video.compositing.*)
- All tools (moviepy.video.tools.*)
- All core classes and functions

Stores function signatures, metadata, and docstrings.
If MoviePy updates, this auto-updates.

NO hardcoded effect lists.
"""

import inspect
import logging
from typing import Dict, Any, Optional, Callable, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class EffectCategory(Enum):
    """Effect categories."""
    VIDEO_FX = "Video Effects"
    AUDIO_FX = "Audio Effects"
    COMPOSITING = "Compositing"
    TOOL = "Tool"
    CORE = "Core"


@dataclass
class ParameterInfo:
    """Information about a function parameter."""
    name: str
    annotation: Optional[str]
    default: Any
    is_optional: bool
    kind: str  # positional_only, positional_or_keyword, var_positional, keyword_only, var_keyword
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            'name': self.name,
            'annotation': self.annotation,
            'default': str(self.default) if self.default != inspect.Parameter.empty else None,
            'is_optional': self.is_optional,
            'kind': self.kind,
        }


@dataclass
class FunctionSignature:
    """Complete function signature with metadata."""
    name: str
    module: str
    category: EffectCategory
    parameters: List[ParameterInfo]
    return_annotation: Optional[str]
    docstring: Optional[str]
    callable_ref: Optional[Callable] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            'name': self.name,
            'module': self.module,
            'category': self.category.value,
            'parameters': [p.to_dict() for p in self.parameters],
            'return_annotation': self.return_annotation,
            'docstring': self.docstring[:500] if self.docstring else None,  # Truncate for size
        }


class MoviePyRegistry:
    """
    Dynamic MoviePy function registry.
    
    Reflects all MoviePy symbols, stores metadata, provides lookup.
    """
    
    _instance: Optional['MoviePyRegistry'] = None
    
    def __init__(self):
        """Initialize registry and scan MoviePy."""
        self._signatures: Dict[str, FunctionSignature] = {}
        self._by_category: Dict[EffectCategory, List[str]] = {
            cat: [] for cat in EffectCategory
        }
        self._module_cache: Dict[str, Any] = {}
        self._scan_moviepy()
    
    def _scan_moviepy(self) -> None:
        """Scan and reflect all MoviePy modules."""
        logger.info("Scanning MoviePy modules...")
        
        try:
            # Scan video effects
            self._scan_module('moviepy.video.fx', EffectCategory.VIDEO_FX)
        except Exception as e:
            logger.warning(f"Failed to scan moviepy.video.fx: {e}")
        
        try:
            # Scan audio effects
            self._scan_module('moviepy.audio.fx', EffectCategory.AUDIO_FX)
        except Exception as e:
            logger.warning(f"Failed to scan moviepy.audio.fx: {e}")
        
        try:
            # Scan compositing
            self._scan_module('moviepy.video.compositing', EffectCategory.COMPOSITING)
        except Exception as e:
            logger.warning(f"Failed to scan moviepy.video.compositing: {e}")
        
        try:
            # Scan tools
            self._scan_module('moviepy.video.tools', EffectCategory.TOOL)
        except Exception as e:
            logger.warning(f"Failed to scan moviepy.video.tools: {e}")
        
        try:
            # Scan core
            self._scan_module('moviepy.editor', EffectCategory.CORE)
        except Exception as e:
            logger.warning(f"Failed to scan moviepy.editor: {e}")
        
        logger.info(f"Registry loaded: {len(self._signatures)} callables")
        for cat, names in self._by_category.items():
            if names:
                logger.debug(f"  {cat.value}: {len(names)} items")
    
    def _scan_module(self, module_name: str, category: EffectCategory) -> None:
        """Scan a single MoviePy module for callables."""
        try:
            module = __import__(module_name, fromlist=[''])
            self._module_cache[module_name] = module
            
            # Try to get __all__ first
            if hasattr(module, '__all__'):
                names = module.__all__
            else:
                # Fall back to public members
                names = [n for n in dir(module) if not n.startswith('_')]
            
            for name in names:
                try:
                    obj = getattr(module, name)
                    
                    # Process both functions and classes that can be called
                    if callable(obj) and (inspect.isfunction(obj) or inspect.isclass(obj)):
                        self._register_function(name, obj, module_name, category)
                except Exception as e:
                    logger.debug(f"Skipped {module_name}.{name}: {e}")
        
        except ImportError as e:
            logger.debug(f"Could not import {module_name}: {e}")
    
    def _register_function(self, name: str, func: Callable, module_name: str,
                          category: EffectCategory) -> None:
        """Register a single function."""
        try:
            sig = inspect.signature(func)
            params = self._extract_parameters(sig)
            
            return_annotation = None
            if sig.return_annotation != inspect.Signature.empty:
                return_annotation = str(sig.return_annotation)
            
            docstring = inspect.getdoc(func)
            
            func_sig = FunctionSignature(
                name=name,
                module=module_name,
                category=category,
                parameters=params,
                return_annotation=return_annotation,
                docstring=docstring,
                callable_ref=func,
            )
            
            key = f"{module_name}.{name}"
            self._signatures[key] = func_sig
            self._by_category[category].append(name)
            
            logger.debug(f"Registered: {key}")
        
        except Exception as e:
            logger.debug(f"Failed to register {module_name}.{name}: {e}")
    
    def _extract_parameters(self, sig: inspect.Signature) -> List[ParameterInfo]:
        """Extract parameter information from signature."""
        params = []
        
        for param_name, param in sig.parameters.items():
            if param_name in ('self', 'cls'):
                continue
            
            annotation = None
            if param.annotation != inspect.Parameter.empty:
                annotation = str(param.annotation)
            
            is_optional = param.default != inspect.Parameter.empty
            
            param_info = ParameterInfo(
                name=param_name,
                annotation=annotation,
                default=param.default,
                is_optional=is_optional,
                kind=param.kind.name.lower(),
            )
            params.append(param_info)
        
        return params
    
    # ===== PUBLIC API =====
    
    def get_signature(self, qualified_name: str) -> Optional[FunctionSignature]:
        """Get function signature by qualified name (module.name)."""
        return self._signatures.get(qualified_name)
    
    def get_all_signatures(self) -> Dict[str, FunctionSignature]:
        """Get all registered signatures."""
        return self._signatures.copy()
    
    def get_by_category(self, category: EffectCategory) -> List[str]:
        """Get all function names in a category."""
        return self._by_category[category].copy()
    
    def get_all_categories(self) -> Dict[EffectCategory, List[str]]:
        """Get all categories with their functions."""
        return {
            cat: names.copy()
            for cat, names in self._by_category.items()
            if names
        }
    
    def call_function(self, qualified_name: str, *args, **kwargs) -> Any:
        """
        Call a registered function dynamically.
        
        Args:
            qualified_name: Module.function name
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Function result
        """
        sig = self.get_signature(qualified_name)
        if not sig or not sig.callable_ref:
            raise ValueError(f"Unknown function: {qualified_name}")
        
        return sig.callable_ref(*args, **kwargs)
    
    def validate_parameters(self, qualified_name: str,
                           **kwargs) -> Tuple[bool, str]:
        """
        Validate parameters for a function.
        
        Args:
            qualified_name: Module.function name
            **kwargs: Parameters to validate
        
        Returns:
            (is_valid, message)
        """
        sig = self.get_signature(qualified_name)
        if not sig:
            return False, f"Unknown function: {qualified_name}"
        
        required_params = [
            p.name for p in sig.parameters
            if not p.is_optional and p.kind not in ('var_keyword', 'var_positional')
        ]
        provided_params = set(kwargs.keys())
        
        missing = set(required_params) - provided_params
        if missing:
            return False, f"Missing required parameters: {', '.join(missing)}"
        
        return True, ""
    
    def get_category_info(self, category: EffectCategory) -> Dict[str, Any]:
        """Get detailed info for all functions in a category."""
        names = self._by_category[category]
        info = {}
        
        for name in names:
            # Find the full key
            for key, sig in self._signatures.items():
                if sig.name == name and sig.category == category:
                    info[key] = sig.to_dict()
                    break
        
        return info
    
    def search_functions(self, query: str) -> List[Tuple[str, FunctionSignature]]:
        """
        Search functions by name or docstring.
        
        Args:
            query: Search string (case-insensitive)
        
        Returns:
            List of (qualified_name, signature) tuples
        """
        query_lower = query.lower()
        results = []
        
        for key, sig in self._signatures.items():
            # Search name
            if query_lower in sig.name.lower():
                results.append((key, sig))
            # Search docstring
            elif sig.docstring and query_lower in sig.docstring.lower():
                results.append((key, sig))
        
        return results
    
    @classmethod
    def instance(cls) -> 'MoviePyRegistry':
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __repr__(self) -> str:
        total = len(self._signatures)
        return f"<MoviePyRegistry {total} functions>"
