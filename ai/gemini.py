"""
AI Module - Gemini integration for conversational editing, generation, and captions

Features:
- Text/code generation with gemini-3-flash-preview
- TTS audio generation with gemini-2.5-flash-preview-tts
- Image generation with gemini-2.5-flash-image
- Auto-captions with speech-to-text
- Conversational editing with context
"""

import os
import json
import logging
from typing import Any, Dict, Optional, List, Generator, Tuple
from pathlib import Path
from datetime import datetime
import tempfile
import threading
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Try to import google.genai
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google-genai not installed. AI features disabled.")


@dataclass
class AIGeneratedAsset:
    """Metadata for AI-generated asset."""
    id: str
    type: str  # 'text', 'audio', 'image', 'code'
    prompt: str
    model: str
    content_path: Optional[str] = None  # Path to generated file
    content: Optional[str] = None  # In-memory content for text
    timestamp: str = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        data = asdict(self)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIGeneratedAsset':
        """Deserialize from dict."""
        return cls(**data)


class AIContext:
    """Maintains conversation context for iterative editing."""
    
    def __init__(self, timeline_state: Optional[Dict[str, Any]] = None):
        """
        Initialize context.
        
        Args:
            timeline_state: Current timeline state for AI to reference
        """
        self.history: List[Dict[str, str]] = []
        self.timeline_state = timeline_state or {}
        self.scripts: Dict[str, str] = {}
        self.assets: List[AIGeneratedAsset] = []
    
    def add_message(self, role: str, content: str) -> None:
        """Add message to history."""
        self.history.append({
            'role': role,
            'content': content
        })
    
    def add_script(self, script_name: str, code: str) -> None:
        """Add/update script."""
        self.scripts[script_name] = code
    
    def add_asset(self, asset: AIGeneratedAsset) -> None:
        """Track generated asset."""
        self.assets.append(asset)
    
    def get_context_prompt(self) -> str:
        """Generate context for AI."""
        parts = [
            "Current Timeline State:",
            json.dumps(self.timeline_state, indent=2, default=str),
            "\nActive Scripts:",
        ]
        for name, code in self.scripts.items():
            parts.append(f"\n{name}:\n{code}")
        
        parts.append("\nPrevious Actions:")
        for msg in self.history[-5:]:  # Last 5 messages
            parts.append(f"{msg['role']}: {msg['content'][:200]}")
        
        return "\n".join(parts)


class GeminiAI:
    """
    Gemini AI integration for Elite Editor.
    """
    
    # Available models
    MODEL_TEXT = "gemini-3-flash-preview"
    MODEL_AUDIO = "gemini-2.5-flash-preview-tts"
    MODEL_IMAGE = "gemini-2.5-flash-image"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize AI client.
        
        Args:
            api_key: Google Gemini API key (from env or config)
        """
        if not GENAI_AVAILABLE:
            raise RuntimeError("google-genai not installed")
        
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set")
        
        self.client = genai.Client(api_key=self.api_key)
        self.context: Optional[AIContext] = None
    
    def set_context(self, context: AIContext) -> None:
        """Set conversation context."""
        self.context = context
    
    # ===== TEXT & CODE GENERATION =====
    
    def generate_text(self, prompt: str, stream: bool = False,
                     thinking_level: str = "HIGH") -> str:
        """
        Generate text using Gemini.
        
        Args:
            prompt: User prompt
            stream: Stream output character by character
            thinking_level: "HIGH" for extended thinking
        
        Returns:
            Generated text
        """
        full_prompt = prompt
        if self.context:
            full_prompt = f"{self.context.get_context_prompt()}\n\nUser Request: {prompt}"
            self.context.add_message("user", prompt)
        
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=full_prompt)])]
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=thinking_level)
        )
        
        result = ""
        if stream:
            for chunk in self.client.models.generate_content_stream(
                model=self.MODEL_TEXT,
                contents=contents,
                config=config
            ):
                if chunk.text:
                    result += chunk.text
                    yield chunk.text
        else:
            response = self.client.models.generate_content(
                model=self.MODEL_TEXT,
                contents=contents,
                config=config
            )
            result = response.text
        
        if self.context:
            self.context.add_message("assistant", result)
        
        return result
    
    def generate_code(self, prompt: str, language: str = "python") -> str:
        """
        Generate code snippet.
        
        Args:
            prompt: Code generation prompt
            language: Programming language
        
        Returns:
            Generated code
        """
        full_prompt = f"Generate {language} code for: {prompt}\n\nReturn only the code, no explanations."
        
        result = ""
        for chunk in self.generate_text(full_prompt, stream=True):
            result += chunk
        
        # Extract code from markdown if present
        if "```" in result:
            parts = result.split("```")
            if len(parts) >= 2:
                result = parts[1].replace(f"{language}\n", "", 1)
        
        return result.strip()
    
    # ===== AUDIO & TTS =====
    
    def generate_speech(self, text: str, voice: str = "Zephyr",
                       output_path: Optional[str] = None) -> Optional[str]:
        """
        Generate speech audio using TTS.
        
        Args:
            text: Text to speak
            voice: Voice name (Zephyr, Sage, Puck, Charon, Kore, Orion)
            output_path: Optional path to save audio
        
        Returns:
            Path to generated audio file
        """
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=text)])]
        config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice
                    )
                )
            )
        )
        
        try:
            audio_data = b""
            for chunk in self.client.models.generate_content_stream(
                model=self.MODEL_AUDIO,
                contents=contents,
                config=config
            ):
                if chunk.data:
                    audio_data += chunk.data
            
            if not output_path:
                output_path = tempfile.mktemp(suffix=".wav")
            
            with open(output_path, 'wb') as f:
                f.write(audio_data)
            
            asset = AIGeneratedAsset(
                id=f"tts_{int(datetime.now().timestamp())}",
                type="audio",
                prompt=text,
                model=self.MODEL_AUDIO,
                content_path=output_path
            )
            
            if self.context:
                self.context.add_asset(asset)
            
            return output_path
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            return None
    
    # ===== IMAGE GENERATION =====
    
    def generate_image(self, prompt: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        Generate image using Gemini.
        
        Args:
            prompt: Image description
            output_path: Optional path to save image
        
        Returns:
            Path to generated image
        """
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        config = types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"]
        )
        
        try:
            image_data = None
            for chunk in self.client.models.generate_content_stream(
                model=self.MODEL_IMAGE,
                contents=contents,
                config=config
            ):
                if chunk.data:
                    image_data = chunk.data
            
            if not image_data:
                logger.error("No image data received")
                return None
            
            if not output_path:
                output_path = tempfile.mktemp(suffix=".png")
            
            with open(output_path, 'wb') as f:
                f.write(image_data)
            
            asset = AIGeneratedAsset(
                id=f"image_{int(datetime.now().timestamp())}",
                type="image",
                prompt=prompt,
                model=self.MODEL_IMAGE,
                content_path=output_path
            )
            
            if self.context:
                self.context.add_asset(asset)
            
            return output_path
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return None
    
    # ===== CAPTIONS =====
    
    def generate_captions(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Generate captions from audio (speech-to-text).
        
        Args:
            audio_path: Path to audio file
        
        Returns:
            List of caption segments: [{'start': 0.0, 'end': 2.5, 'text': '...'}]
        """
        # This would require speech-to-text API
        # For now, return placeholder
        try:
            prompt = f"Transcribe the audio file and return JSON with segments: [{{'start': time_in_seconds, 'end': time_in_seconds, 'text': 'transcribed text'}}]"
            
            response = self.generate_text(prompt)
            
            # Try to parse JSON
            try:
                captions = json.loads(response)
                return captions
            except json.JSONDecodeError:
                logger.warning("Failed to parse caption JSON")
                return []
        except Exception as e:
            logger.error(f"Caption generation failed: {e}")
            return []
    
    # ===== SCRIPT MODIFICATION =====
    
    def modify_script(self, current_code: str, modification_prompt: str) -> str:
        """
        Modify existing script incrementally without overwriting.
        
        Args:
            current_code: Current code
            modification_prompt: What to modify
        
        Returns:
            Modified code
        """
        prompt = f"""
Current code:
```python
{current_code}
```

Modification request: {modification_prompt}

Return the FULL modified code, preserving all existing functionality while applying the requested changes.
"""
        result = self.generate_code(prompt, language="python")
        
        if self.context:
            self.context.add_script("modified_script", result)
        
        return result
    
    # ===== TIMELINE ANALYSIS =====
    
    def analyze_timeline(self, timeline_data: Dict[str, Any]) -> str:
        """
        Analyze timeline and suggest improvements.
        
        Args:
            timeline_data: Timeline serialized data
        
        Returns:
            Analysis and suggestions
        """
        prompt = f"""
Analyze this video timeline and provide professional editing suggestions:

{json.dumps(timeline_data, indent=2, default=str)}

Consider: pacing, transitions, audio, effects, color grading, narrative flow.
"""
        return self.generate_text(prompt)


# Singleton AI instance
_ai_instance: Optional[GeminiAI] = None

def get_ai(api_key: Optional[str] = None) -> Optional[GeminiAI]:
    """Get or create AI instance."""
    global _ai_instance
    if _ai_instance is None and GENAI_AVAILABLE:
        try:
            _ai_instance = GeminiAI(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize AI: {e}")
            return None
    return _ai_instance
