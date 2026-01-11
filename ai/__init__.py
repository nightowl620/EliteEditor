"""
AI Integration Module - Google Gemini API Integration
Handles text, code, audio, and image generation with streaming
"""

import os
import logging
from typing import Optional, Iterator, Dict, Any, List
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class GeminiAIClient:
    """
    Wrapper around Google Gemini API.
    
    Supports:
    - Text and code generation with extended thinking
    - Text-to-speech (TTS)
    - Image generation
    - Streaming responses
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize AI client."""
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        self._client = None
        self._initialized = False
        
        if self.api_key:
            self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Gemini client."""
        if self._initialized:
            return
        
        try:
            from google import genai
            from google.genai import types
            
            self.genai = genai
            self.types = types
            
            self._client = genai.Client(api_key=self.api_key)
            self._initialized = True
            logger.info("Gemini client initialized")
        except ImportError:
            logger.error("google-genai not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
    
    def is_ready(self) -> bool:
        """Check if AI is ready to use."""
        return self._initialized and self.api_key
    
    # ===== TEXT / CODE GENERATION =====
    
    def generate_text(self, prompt: str, thinking_enabled: bool = True,
                     temperature: float = 0.7, max_tokens: int = 4096) -> str:
        """
        Generate text or code using Gemini.
        
        Args:
            prompt: Input text
            thinking_enabled: Use extended thinking
            temperature: Creativity (0-1)
            max_tokens: Max response length
        
        Returns:
            Generated text
        """
        if not self.is_ready():
            raise RuntimeError("AI client not initialized")
        
        try:
            thinking_level = "HIGH" if thinking_enabled else "OFF"
            
            contents = [
                self.types.Content(
                    role="user",
                    parts=[self.types.Part.from_text(text=prompt)],
                )
            ]
            
            config = self.types.GenerateContentConfig(
                thinking_config=self.types.ThinkingConfig(
                    thinking_level=thinking_level
                ) if thinking_enabled else None,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            response = self._client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=contents,
                config=config,
            )
            
            return response.text
        
        except Exception as e:
            logger.error(f"Text generation error: {e}")
            raise
    
    def generate_text_stream(self, prompt: str, thinking_enabled: bool = True,
                            temperature: float = 0.7,
                            max_tokens: int = 4096) -> Iterator[str]:
        """
        Stream text generation.
        
        Yields:
            Text chunks as they arrive
        """
        if not self.is_ready():
            raise RuntimeError("AI client not initialized")
        
        try:
            thinking_level = "HIGH" if thinking_enabled else "OFF"
            
            contents = [
                self.types.Content(
                    role="user",
                    parts=[self.types.Part.from_text(text=prompt)],
                )
            ]
            
            config = self.types.GenerateContentConfig(
                thinking_config=self.types.ThinkingConfig(
                    thinking_level=thinking_level
                ) if thinking_enabled else None,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            for chunk in self._client.models.generate_content_stream(
                model="gemini-3-flash-preview",
                contents=contents,
                config=config,
            ):
                if chunk.text:
                    yield chunk.text
        
        except Exception as e:
            logger.error(f"Stream generation error: {e}")
            raise
    
    # ===== TEXT-TO-SPEECH =====
    
    def generate_speech(self, text: str, voice: str = "Zephyr") -> Optional[bytes]:
        """
        Generate speech audio.
        
        Args:
            text: Text to convert to speech
            voice: Voice name (Zephyr, Sage, etc.)
        
        Returns:
            Audio data in WAV format
        """
        if not self.is_ready():
            raise RuntimeError("AI client not initialized")
        
        try:
            contents = [
                self.types.Content(
                    role="user",
                    parts=[self.types.Part.from_text(text=text)],
                )
            ]
            
            config = self.types.GenerateContentConfig(
                response_modalities=["audio"],
                speech_config=self.types.SpeechConfig(
                    voice_config=self.types.VoiceConfig(
                        prebuilt_voice_config=self.types.PrebuiltVoiceConfig(
                            voice_name=voice
                        )
                    )
                ),
            )
            
            response = self._client.models.generate_content(
                model="gemini-2.5-flash-preview-tts",
                contents=contents,
                config=config,
            )
            
            # Extract audio data from response
            if hasattr(response, 'data') and response.data:
                return response.data
            
            return None
        
        except Exception as e:
            logger.error(f"Speech generation error: {e}")
            raise
    
    # ===== IMAGE GENERATION =====
    
    def generate_image(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Generate image.
        
        Args:
            prompt: Image description
        
        Returns:
            Dict with 'image' (bytes) and 'metadata' keys
        """
        if not self.is_ready():
            raise RuntimeError("AI client not initialized")
        
        try:
            contents = [
                self.types.Content(
                    role="user",
                    parts=[self.types.Part.from_text(text=prompt)],
                )
            ]
            
            config = self.types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            )
            
            response = self._client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=contents,
                config=config,
            )
            
            # Extract image data
            if hasattr(response, 'data') and response.data:
                return {
                    'image': response.data,
                    'metadata': {
                        'prompt': prompt,
                        'model': 'gemini-2.5-flash-image',
                        'timestamp': datetime.now().isoformat(),
                    }
                }
            
            return None
        
        except Exception as e:
            logger.error(f"Image generation error: {e}")
            raise
    
    # ===== CONVERSATION CONTEXT =====
    
    def create_conversation(self, system_prompt: str = "") -> 'AIConversation':
        """Create stateful conversation."""
        return AIConversation(self, system_prompt)


class AIConversation:
    """
    Stateful conversation with AI.
    
    Maintains message history and context.
    """
    
    def __init__(self, client: GeminiAIClient, system_prompt: str = ""):
        self.client = client
        self.system_prompt = system_prompt
        self.messages: List[Dict[str, str]] = []
    
    def send(self, message: str) -> str:
        """Send message and get response."""
        if not self.client.is_ready():
            raise RuntimeError("AI client not ready")
        
        self.messages.append({'role': 'user', 'content': message})
        
        # Build context
        prompt = self.system_prompt + "\n\n" if self.system_prompt else ""
        for msg in self.messages:
            role = "You" if msg['role'] == 'user' else "Assistant"
            prompt += f"{role}: {msg['content']}\n\n"
        
        response = self.client.generate_text(prompt)
        self.messages.append({'role': 'assistant', 'content': response})
        
        return response
    
    def stream(self, message: str) -> Iterator[str]:
        """Stream response."""
        if not self.client.is_ready():
            raise RuntimeError("AI client not ready")
        
        self.messages.append({'role': 'user', 'content': message})
        
        # Build context
        prompt = self.system_prompt + "\n\n" if self.system_prompt else ""
        for msg in self.messages:
            role = "You" if msg['role'] == 'user' else "Assistant"
            prompt += f"{role}: {msg['content']}\n\n"
        
        full_response = ""
        for chunk in self.client.generate_text_stream(prompt):
            full_response += chunk
            yield chunk
        
        self.messages.append({'role': 'assistant', 'content': full_response})
    
    def clear_history(self) -> None:
        """Clear message history."""
        self.messages.clear()
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history."""
        return self.messages.copy()


class ScriptExtractor:
    """Extract and validate Python scripts from AI responses."""
    
    @staticmethod
    def extract_code(text: str) -> Optional[str]:
        """
        Extract Python code from markdown code blocks.
        
        Looks for ```python ... ``` blocks.
        """
        import re
        
        # Match markdown python code blocks
        pattern = r'```python\s*(.*?)\s*```'
        matches = re.findall(pattern, text, re.DOTALL)
        
        if matches:
            return matches[0]
        
        return None
    
    @staticmethod
    def validate_code(code: str) -> bool:
        """Check if code is valid Python."""
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError:
            return False
    
    @staticmethod
    def extract_and_validate(text: str) -> Optional[str]:
        """Extract and validate code in one step."""
        code = ScriptExtractor.extract_code(text)
        if code and ScriptExtractor.validate_code(code):
            return code
        return None
