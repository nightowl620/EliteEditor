"""
Real Config & Project System

- All configs stored in ~/.eliteeditor/
- Home page on startup showing recent projects
- Load .eep files completely
- No blank editor on launch
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ProjectManager:
    """Manages Elite Editor projects (.eep files)."""
    
    def __init__(self):
        self.config_dir = Path.home() / '.eliteeditor'
        self.projects_dir = self.config_dir / 'projects'
        self.recent_file = self.config_dir / 'config' / 'recent.json'
        
        # Create directories
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.recent_file.parent.mkdir(parents=True, exist_ok=True)
    
    def create_new_project(self, name: str, fps: int = 30, 
                          width: int = 1920, height: int = 1080) -> Dict[str, Any]:
        """
        Create a new project.
        
        Args:
            name: Project name
            fps: Frames per second
            width: Video width
            height: Video height
            
        Returns:
            Project metadata dict
        """
        project = {
            'id': Path(name).stem,
            'name': name,
            'fps': fps,
            'width': width,
            'height': height,
            'created': datetime.now().isoformat(),
            'modified': datetime.now().isoformat(),
            'filepath': None
        }
        
        logger.info(f"Created project: {name}")
        return project
    
    def save_project(self, project: Dict[str, Any], filepath: Optional[str] = None) -> bool:
        """
        Save project to .eep file.
        
        Args:
            project: Project dict
            filepath: Output path (default: ~/projects/<name>.eep)
            
        Returns:
            True if successful
        """
        try:
            if filepath is None:
                filepath = self.projects_dir / f"{project['name']}.eep"
            
            filepath = Path(filepath)
            
            # For now, save as JSON (can be zipped later)
            project_data = {
                'metadata': project,
                'timeline': {},
                'tracks': [],
                'clips': [],
                'effects': [],
                'assets': {}
            }
            
            with open(filepath, 'w') as f:
                json.dump(project_data, f, indent=2)
            
            # Update recent
            self._add_to_recent(str(filepath))
            
            logger.info(f"Saved project: {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save project: {e}")
            return False
    
    def load_project(self, filepath: str) -> Optional[Dict[str, Any]]:
        """
        Load project from .eep file.
        
        Args:
            filepath: Project file path
            
        Returns:
            Project data dict or None
        """
        try:
            filepath = Path(filepath)
            
            if not filepath.exists():
                logger.error(f"Project not found: {filepath}")
                return None
            
            with open(filepath, 'r') as f:
                project_data = json.load(f)
            
            # Update recent
            self._add_to_recent(str(filepath))
            
            logger.info(f"Loaded project: {filepath}")
            return project_data
        
        except Exception as e:
            logger.error(f"Failed to load project: {e}")
            return None
    
    def get_recent_projects(self, limit: int = 10) -> List[str]:
        """
        Get list of recently opened projects.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of project filepaths
        """
        try:
            if self.recent_file.exists():
                with open(self.recent_file, 'r') as f:
                    recent = json.load(f)
                    return recent.get('recent', [])[:limit]
            return []
        
        except Exception as e:
            logger.warning(f"Could not load recent projects: {e}")
            return []
    
    def _add_to_recent(self, filepath: str):
        """Add project to recent list."""
        try:
            recent_list = []
            
            if self.recent_file.exists():
                with open(self.recent_file, 'r') as f:
                    data = json.load(f)
                    recent_list = data.get('recent', [])
            
            # Remove if already in list
            if filepath in recent_list:
                recent_list.remove(filepath)
            
            # Add to front
            recent_list.insert(0, filepath)
            
            # Keep only last 20
            recent_list = recent_list[:20]
            
            # Save
            with open(self.recent_file, 'w') as f:
                json.dump({'recent': recent_list}, f, indent=2)
        
        except Exception as e:
            logger.debug(f"Failed to add to recent: {e}")


class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self):
        self.config_dir = Path.home() / '.eliteeditor' / 'config'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.config = {
            'app': {},
            'ui': {},
            'ai': {},
            'keybinds': {},
            'settings': {}
        }
        
        self._load_all()
    
    def _load_all(self):
        """Load all config files."""
        for section in self.config.keys():
            filepath = self.config_dir / f'{section}.json'
            if filepath.exists():
                try:
                    with open(filepath, 'r') as f:
                        self.config[section] = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not load {section}.json: {e}")
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get config value."""
        return self.config.get(section, {}).get(key, default)
    
    def set(self, section: str, key: str, value: Any):
        """Set config value."""
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][key] = value
        self._save_section(section)
    
    def _save_section(self, section: str):
        """Save config section to file."""
        try:
            filepath = self.config_dir / f'{section}.json'
            with open(filepath, 'w') as f:
                json.dump(self.config[section], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")


class HomePage:
    """Home page widget showing recent projects."""
    
    def __init__(self, project_manager: ProjectManager):
        self.project_manager = project_manager
    
    def get_recent_projects_info(self) -> List[Dict[str, Any]]:
        """
        Get information about recent projects for display.
        
        Returns:
            List of project info dicts
        """
        projects = []
        
        for filepath in self.project_manager.get_recent_projects():
            try:
                project_data = self.project_manager.load_project(filepath)
                if project_data:
                    projects.append({
                        'name': project_data['metadata']['name'],
                        'path': filepath,
                        'fps': project_data['metadata'].get('fps', 30),
                        'size': f"{project_data['metadata'].get('width', 1920)}x{project_data['metadata'].get('height', 1080)}",
                        'modified': project_data['metadata'].get('modified', ''),
                    })
            except Exception as e:
                logger.debug(f"Could not load project info: {e}")
        
        return projects
    
    def new_project_action(self) -> Dict[str, Any]:
        """Create new blank project."""
        project = self.project_manager.create_new_project('Untitled Project')
        self.project_manager.save_project(project)
        return project


# Global instances
_project_manager = None
_config_manager = None


def get_project_manager() -> ProjectManager:
    """Get or create project manager."""
    global _project_manager
    if _project_manager is None:
        _project_manager = ProjectManager()
    return _project_manager


def get_config_manager() -> ConfigManager:
    """Get or create config manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
