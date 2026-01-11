"""
Real Gemini AI Integration

Real features that use Google Gemini API:
- Explain timeline
- Suggest transitions
- Generate MoviePy code
- Optimize render settings

Detects API key from environment or config, shows dialog if missing.
"""

import logging
import os
import json
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class AIFeatures:
    """Real AI features using Gemini API."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GENAI_API_KEY')
        self.available = GENAI_AVAILABLE and bool(self.api_key)
        
        if self.available:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-3-flash-preview')
                logger.info("Gemini API configured successfully")
            except Exception as e:
                logger.error(f"Failed to configure Gemini: {e}")
                self.available = False
    
    def explain_timeline(self, timeline_data: Dict[str, Any]) -> str:
        """
        Use AI to explain what's in the timeline.
        
        Args:
            timeline_data: Dictionary with timeline information
            
        Returns:
            Explanation string
        """
        if not self.available:
            return "AI not available"
        
        try:
            prompt = f"""Analyze this video timeline and provide a brief explanation of what it contains.

Timeline data:
{json.dumps(timeline_data, indent=2)}

Provide a 2-3 sentence description of the video project."""
            
            response = self.model.generate_content(prompt)
            return response.text
        
        except Exception as e:
            logger.error(f"AI explanation failed: {e}")
            return f"Error: {e}"
    
    def suggest_transitions(self, clips: List[Dict[str, Any]]) -> List[str]:
        """
        Suggest transitions between clips.
        
        Args:
            clips: List of clip information
            
        Returns:
            List of suggested transitions
        """
        if not self.available:
            return []
        
        try:
            clip_descriptions = "\n".join([
                f"- {clip.get('name', 'Clip')}: {clip.get('duration', 0)}s"
                for clip in clips
            ])
            
            prompt = f"""Given these video clips, suggest appropriate transitions between them:

{clip_descriptions}

Suggest 3-5 transition effects (like 'fade', 'dissolve', 'wipe', etc.) that would work well.
Return only the transition names, one per line."""
            
            response = self.model.generate_content(prompt)
            transitions = [t.strip() for t in response.text.strip().split('\n') if t.strip()]
            return transitions
        
        except Exception as e:
            logger.error(f"Transition suggestion failed: {e}")
            return []
    
    def generate_moviepy_code(self, effect_description: str) -> str:
        """
        Generate MoviePy code from description.
        
        Args:
            effect_description: English description of desired effect
            
        Returns:
            Python code using MoviePy
        """
        if not self.available:
            return "AI not available"
        
        try:
            prompt = f"""Generate MoviePy Python code for the following effect: {effect_description}

The code should:
1. Use 'from moviepy import *'
2. Create a VideoClip or apply an effect to a clip
3. Be complete and runnable
4. Include comments

Return only the Python code, no explanations."""
            
            response = self.model.generate_content(prompt)
            return response.text
        
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            return f"Error: {e}"
    
    def optimize_render_settings(self, current_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get AI suggestions for optimal render settings.
        
        Args:
            current_settings: Current render configuration
            
        Returns:
            Suggested optimized settings
        """
        if not self.available:
            return current_settings
        
        try:
            prompt = f"""Analyze these video render settings and suggest optimizations for quality/performance balance:

Current settings:
{json.dumps(current_settings, indent=2)}

Suggest optimized values for:
- bitrate (as string like '8M', '12M')
- codec (libx264, libx265, etc.)
- preset (ultrafast, superfast, fast, medium, slow, slower)
- crf (0-51, lower is better quality)

Return as JSON object with only the changed values."""
            
            response = self.model.generate_content(prompt)
            
            # Try to parse JSON response
            try:
                suggestions = json.loads(response.text)
                return suggestions
            except json.JSONDecodeError:
                logger.warning("Could not parse AI suggestions as JSON")
                return current_settings
        
        except Exception as e:
            logger.error(f"Settings optimization failed: {e}")
            return current_settings
    
    def analyze_clips(self, clip_list: List[Dict[str, Any]]) -> str:
        """
        Analyze clips and provide insights.
        
        Args:
            clip_list: List of clip metadata
            
        Returns:
            Analysis string
        """
        if not self.available:
            return "AI not available"
        
        try:
            prompt = f"""Analyze these video clips and provide editing insights:

Clips:
{json.dumps(clip_list, indent=2)}

Provide suggestions for:
1. Overall pacing
2. Effects or color grading
3. Audio considerations
4. Export format recommendations"""
            
            response = self.model.generate_content(prompt)
            return response.text
        
        except Exception as e:
            logger.error(f"Clip analysis failed: {e}")
            return f"Error: {e}"


def load_api_key() -> Optional[str]:
    """
    Load API key from environment or config file.
    
    Returns:
        API key string or None
    """
    # Check environment
    api_key = os.getenv('GENAI_API_KEY')
    if api_key:
        return api_key
    
    # Check config file
    try:
        config_dir = Path.home() / '.eliteeditor' / 'config'
        config_file = config_dir / 'ai.json'
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
                api_key = config.get('api_key')
                if api_key:
                    return api_key
    except Exception as e:
        logger.debug(f"Could not load config: {e}")
    
    return None


def save_api_key(api_key: str) -> bool:
    """
    Save API key to config file.
    
    Args:
        api_key: Key to save
        
    Returns:
        True if successful
    """
    try:
        config_dir = Path.home() / '.eliteeditor' / 'config'
        config_dir.mkdir(parents=True, exist_ok=True)
        
        config_file = config_dir / 'ai.json'
        
        config = {}
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
        
        config['api_key'] = api_key
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info("API key saved to config")
        return True
    
    except Exception as e:
        logger.error(f"Failed to save API key: {e}")
        return False


# Global instance
_ai_features = None


def get_ai_features() -> AIFeatures:
    """Get or create AI features instance."""
    global _ai_features
    if _ai_features is None:
        api_key = load_api_key()
        _ai_features = AIFeatures(api_key)
    return _ai_features


def request_api_key_dialog() -> Optional[str]:
    """
    Show dialog to request API key from user.
    (Implementation uses PySide6 - called from UI)
    """
    try:
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QLabel, QLineEdit, 
            QPushButton, QMessageBox
        )
        from PySide6.QtCore import Qt
        
        dialog = QDialog()
        dialog.setWindowTitle("Gemini API Key")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Instructions
        label = QLabel(
            "Enter your Google Gemini API key.\n"
            "Get one from: https://aistudio.google.com/app/apikey"
        )
        layout.addWidget(label)
        
        # Input field
        line_edit = QLineEdit()
        line_edit.setEchoMode(QLineEdit.Password)
        layout.addWidget(line_edit)
        
        # Buttons
        button_layout = QVBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        
        def on_ok():
            api_key = line_edit.text().strip()
            if api_key:
                save_api_key(api_key)
                dialog.accept()
            else:
                QMessageBox.warning(dialog, "Error", "API key cannot be empty")
        
        ok_button.clicked.connect(on_ok)
        cancel_button.clicked.connect(dialog.reject)
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.Accepted:
            return line_edit.text().strip()
        
        return None
    
    except ImportError:
        logger.error("PySide6 not available for dialog")
        return None
