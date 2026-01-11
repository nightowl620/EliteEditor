"""
ProjectManager - Elite Editor Project System (.eep format)

Format: ZIP-based container with project structure:
  project.json       - Metadata
  timeline.json      - Timeline structure
  tracks.json        - Track definitions
  clips.json         - Clip data
  keyframes.json     - Animation keyframes
  effects.json       - Effect stacks
  assets/            - Project assets (local + AI)
  scripts/           - Generated scripts
  ai/                - AI metadata
  settings_snapshot.json - Project-specific settings
"""

import json
import logging
import zipfile
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime
import shutil

from core.paths import PathManager


logger = logging.getLogger(__name__)


class ProjectMetadata:
    """Project metadata and properties."""
    
    def __init__(self, name: str, fps: int = 30, width: int = 1920, height: int = 1080):
        self.name = name
        self.fps = fps
        self.width = width
        self.height = height
        self.created_at = datetime.now().isoformat()
        self.modified_at = datetime.now().isoformat()
        self.version = '1.0.0'
        self.description = ''
        self.author = ''
        self.thumbnail: Optional[str] = None  # Path to thumbnail image
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            'name': self.name,
            'fps': self.fps,
            'width': self.width,
            'height': self.height,
            'created_at': self.created_at,
            'modified_at': self.modified_at,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'thumbnail': self.thumbnail,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectMetadata':
        """Deserialize from dict."""
        meta = cls(
            name=data.get('name', 'Untitled'),
            fps=data.get('fps', 30),
            width=data.get('width', 1920),
            height=data.get('height', 1080),
        )
        meta.created_at = data.get('created_at', meta.created_at)
        meta.modified_at = data.get('modified_at', meta.modified_at)
        meta.version = data.get('version', meta.version)
        meta.description = data.get('description', '')
        meta.author = data.get('author', '')
        meta.thumbnail = data.get('thumbnail')
        return meta


class ProjectManager:
    """
    Manages Elite Editor projects (.eep format).
    
    Handles:
    - Project creation
    - Save/load
    - Autosave
    - Crash recovery
    - Asset management
    - Recent projects tracking
    """
    
    _instance: Optional['ProjectManager'] = None
    
    def __init__(self):
        self.paths = PathManager.instance()
        self._current_project: Optional['Project'] = None
        self._autosave_enabled = True
    
    @classmethod
    def instance(cls) -> 'ProjectManager':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = ProjectManager()
        return cls._instance
    
    def create_project(self, name: str, fps: int = 30, 
                      width: int = 1920, height: int = 1080) -> 'Project':
        """Create new project."""
        meta = ProjectMetadata(name, fps, width, height)
        project = Project(meta)
        self._current_project = project
        logger.info(f"Created project: {name}")
        return project
    
    def load_project(self, project_path: Path) -> Optional['Project']:
        """Load project from .eep file."""
        try:
            project = Project.load_from_file(project_path)
            self._current_project = project
            self._add_to_recent(project_path)
            logger.info(f"Loaded project: {project.metadata.name}")
            return project
        except Exception as e:
            logger.error(f"Failed to load project: {e}")
            return None
    
    def save_project(self, project: Optional['Project'] = None) -> bool:
        """Save project to .eep file."""
        target = project or self._current_project
        if not target:
            logger.warning("No project to save")
            return False
        
        try:
            target.save_to_file()
            self._add_to_recent(target.file_path)
            logger.info(f"Saved project: {target.metadata.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save project: {e}")
            return False
    
    def get_recent_projects(self) -> List[Dict[str, Any]]:
        """Get list of recent projects."""
        recent_file = self.paths.recent_projects_file
        if not recent_file.exists():
            return []
        
        try:
            with open(recent_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('projects', [])
        except Exception as e:
            logger.error(f"Failed to load recent projects: {e}")
            return []
    
    def _add_to_recent(self, project_path: Path) -> None:
        """Add project to recent list."""
        recent_file = self.paths.recent_projects_file
        
        try:
            data = {}
            if recent_file.exists():
                with open(recent_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            projects = data.get('projects', [])
            
            # Remove if already exists
            projects = [p for p in projects if p['path'] != str(project_path)]
            
            # Add to front
            projects.insert(0, {
                'path': str(project_path),
                'name': project_path.stem,
                'opened_at': datetime.now().isoformat(),
            })
            
            # Keep only recent N
            limit = 10
            projects = projects[:limit]
            
            data['projects'] = projects
            
            recent_file.parent.mkdir(parents=True, exist_ok=True)
            with open(recent_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to update recent projects: {e}")
    
    @property
    def current_project(self) -> Optional['Project']:
        """Get current project."""
        return self._current_project


class Project:
    """
    Represents a single Elite Editor project.
    
    Serializes to .eep (ZIP) format containing:
    - project.json: Metadata
    - timeline.json: Timeline structure
    - tracks.json: Track data
    - clips.json: Clip definitions
    - keyframes.json: Animation data
    - effects.json: Effect stacks
    - assets/: Project media
    - scripts/: Generated scripts
    - ai/: AI asset metadata
    """
    
    def __init__(self, metadata: ProjectMetadata, file_path: Optional[Path] = None):
        self.metadata = metadata
        self.file_path = file_path or PathManager.instance().projects_dir / f'{metadata.name}.eep'
        
        # Project structure
        self.timeline: Dict[str, Any] = {'duration': 0.0, 'tracks': []}
        self.tracks: List[Dict[str, Any]] = []
        self.clips: List[Dict[str, Any]] = []
        self.keyframes: Dict[str, Any] = {}
        self.effects: Dict[str, Any] = {}
        self.assets: List[Dict[str, Any]] = []
        self.scripts: List[Dict[str, Any]] = []
        self.ai_metadata: Dict[str, Any] = {}
        self.settings_snapshot: Dict[str, Any] = {}
        
        # Temporary working directory
        self._temp_dir: Optional[Path] = None
    
    def save_to_file(self) -> None:
        """Save project to .eep file."""
        self.metadata.modified_at = datetime.now().isoformat()
        
        # Create ZIP file
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(self.file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Write project.json
            zf.writestr('project.json', json.dumps(self.metadata.to_dict(), indent=2))
            
            # Write timeline structure
            zf.writestr('timeline.json', json.dumps(self.timeline, indent=2))
            zf.writestr('tracks.json', json.dumps(self.tracks, indent=2))
            zf.writestr('clips.json', json.dumps(self.clips, indent=2))
            zf.writestr('keyframes.json', json.dumps(self.keyframes, indent=2))
            zf.writestr('effects.json', json.dumps(self.effects, indent=2))
            zf.writestr('assets.json', json.dumps(self.assets, indent=2))
            zf.writestr('scripts.json', json.dumps(self.scripts, indent=2))
            zf.writestr('ai_metadata.json', json.dumps(self.ai_metadata, indent=2))
            zf.writestr('settings_snapshot.json', json.dumps(self.settings_snapshot, indent=2))
            
            logger.info(f"Saved project to {self.file_path}")
    
    @classmethod
    def load_from_file(cls, file_path: Path) -> 'Project':
        """Load project from .eep file."""
        with zipfile.ZipFile(file_path, 'r') as zf:
            # Load metadata
            with zf.open('project.json') as f:
                meta_data = json.load(f)
                metadata = ProjectMetadata.from_dict(meta_data)
            
            project = cls(metadata, file_path)
            
            # Load structure files
            project.timeline = json.loads(zf.read('timeline.json'))
            project.tracks = json.loads(zf.read('tracks.json'))
            project.clips = json.loads(zf.read('clips.json'))
            project.keyframes = json.loads(zf.read('keyframes.json'))
            project.effects = json.loads(zf.read('effects.json'))
            project.assets = json.loads(zf.read('assets.json'))
            project.scripts = json.loads(zf.read('scripts.json'))
            project.ai_metadata = json.loads(zf.read('ai_metadata.json'))
            project.settings_snapshot = json.loads(zf.read('settings_snapshot.json'))
            
            logger.info(f"Loaded project from {file_path}")
            return project
    
    def export_assets(self, dest_dir: Path) -> None:
        """Export all assets to directory."""
        # This would extract assets from the ZIP if embedded
        pass
    
    def add_asset(self, asset_path: Path, source: str = 'local', 
                  prompt: str = '', model: str = '') -> None:
        """Register asset in project."""
        asset_info = {
            'id': hash(asset_path),
            'path': str(asset_path),
            'name': asset_path.name,
            'source': source,  # local | ai
            'prompt': prompt,
            'model': model,
            'timestamp': datetime.now().isoformat(),
        }
        self.assets.append(asset_info)
        logger.debug(f"Added asset: {asset_path.name}")
    
    def __repr__(self) -> str:
        return f"<Project '{self.metadata.name}' {self.metadata.width}x{self.metadata.height}@{self.metadata.fps}fps>"
