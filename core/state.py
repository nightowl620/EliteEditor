"""
StateManager - Application state and undo/redo system
Implements dirty-state tracking, version history, and crash recovery
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
from core.paths import PathManager


logger = logging.getLogger(__name__)


class UndoRedoCommand:
    """Base class for undo/redo commands."""
    
    def __init__(self, name: str):
        self.name = name
        self.timestamp = datetime.now()
    
    def execute(self) -> None:
        """Execute the command."""
        raise NotImplementedError
    
    def undo(self) -> None:
        """Undo the command."""
        raise NotImplementedError
    
    def redo(self) -> None:
        """Redo the command."""
        raise NotImplementedError
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} '{self.name}'>"


class StateChange(UndoRedoCommand):
    """Generic state change command."""
    
    def __init__(self, name: str, target: Any, attribute: str, 
                 old_value: Any, new_value: Any):
        super().__init__(name)
        self.target = target
        self.attribute = attribute
        self.old_value = old_value
        self.new_value = new_value
    
    def execute(self) -> None:
        setattr(self.target, self.attribute, self.new_value)
    
    def undo(self) -> None:
        setattr(self.target, self.attribute, self.old_value)
    
    def redo(self) -> None:
        setattr(self.target, self.attribute, self.new_value)


class StateManager:
    """
    Manages application state, undo/redo, dirty tracking, and crash recovery.
    
    Features:
    - Full undo/redo stack
    - Dirty state tracking
    - Version history
    - Crash recovery snapshots
    - Command grouping
    """
    
    _instance: Optional['StateManager'] = None
    
    def __init__(self):
        self.paths = PathManager.instance()
        
        # Undo/redo
        self._undo_stack: List[UndoRedoCommand] = []
        self._redo_stack: List[UndoRedoCommand] = []
        self._command_group: Optional[List[UndoRedoCommand]] = None
        
        # State tracking
        self._dirty = False
        self._state_callbacks: List[Callable] = []
        
        # Versioning
        self._version = 0
        self._version_history: List[Dict[str, Any]] = []
        self._max_versions = 20
    
    @classmethod
    def instance(cls) -> 'StateManager':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = StateManager()
        return cls._instance
    
    # ===== UNDO/REDO =====
    
    def execute_command(self, command: UndoRedoCommand) -> None:
        """Execute and record command for undo."""
        command.execute()
        
        if self._command_group is not None:
            # Inside a group
            self._command_group.append(command)
        else:
            # Single command
            self._undo_stack.append(command)
            self._redo_stack.clear()
        
        self._mark_dirty()
        logger.debug(f"Executed: {command.name}")
    
    def undo(self) -> bool:
        """Undo last command."""
        if not self._undo_stack:
            return False
        
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        self._mark_dirty()
        logger.debug(f"Undone: {command.name}")
        return True
    
    def redo(self) -> bool:
        """Redo last undone command."""
        if not self._redo_stack:
            return False
        
        command = self._redo_stack.pop()
        command.redo()
        self._undo_stack.append(command)
        self._mark_dirty()
        logger.debug(f"Redone: {command.name}")
        return True
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0
    
    def get_undo_name(self) -> Optional[str]:
        """Get name of last undoable command."""
        if self._undo_stack:
            return self._undo_stack[-1].name
        return None
    
    def get_redo_name(self) -> Optional[str]:
        """Get name of last redoable command."""
        if self._redo_stack:
            return self._redo_stack[-1].name
        return None
    
    # ===== COMMAND GROUPING =====
    
    def begin_command_group(self, name: str) -> None:
        """Begin grouping commands for atomic undo."""
        if self._command_group is not None:
            logger.warning("Command group already open")
            return
        self._command_group = []
        logger.debug(f"Started command group: {name}")
    
    def end_command_group(self) -> None:
        """End command group and push to undo stack."""
        if self._command_group is None:
            logger.warning("No command group open")
            return
        
        if self._command_group:
            # Create a composite command
            commands = self._command_group
            self._undo_stack.append(CompositeCommand(commands))
            self._redo_stack.clear()
        
        self._command_group = None
        self._mark_dirty()
        logger.debug("Ended command group")
    
    # ===== DIRTY STATE TRACKING =====
    
    def _mark_dirty(self) -> None:
        """Mark state as dirty."""
        was_dirty = self._dirty
        self._dirty = True
        
        if not was_dirty:
            self._notify_state_change()
    
    def mark_clean(self) -> None:
        """Mark state as clean (saved)."""
        self._dirty = False
        self._notify_state_change()
    
    def is_dirty(self) -> bool:
        """Check if state has unsaved changes."""
        return self._dirty
    
    # ===== STATE CALLBACKS =====
    
    def register_state_callback(self, callback: Callable) -> None:
        """Register callback for state changes."""
        if callback not in self._state_callbacks:
            self._state_callbacks.append(callback)
    
    def unregister_state_callback(self, callback: Callable) -> None:
        """Unregister state callback."""
        if callback in self._state_callbacks:
            self._state_callbacks.remove(callback)
    
    def _notify_state_change(self) -> None:
        """Notify all callbacks of state change."""
        for callback in self._state_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"State callback error: {e}")
    
    # ===== VERSION HISTORY =====
    
    def create_version_snapshot(self, name: str, data: Dict[str, Any]) -> None:
        """Create a named version snapshot."""
        snapshot = {
            'version': self._version,
            'name': name,
            'timestamp': datetime.now().isoformat(),
            'data': data,
        }
        self._version_history.append(snapshot)
        self._version += 1
        
        # Keep only recent versions
        if len(self._version_history) > self._max_versions:
            self._version_history.pop(0)
        
        logger.debug(f"Created version: {name}")
    
    def get_version_snapshots(self) -> List[Dict[str, Any]]:
        """Get all version snapshots."""
        return self._version_history.copy()
    
    def restore_version(self, version: int) -> Optional[Dict[str, Any]]:
        """Restore from version snapshot."""
        for snapshot in self._version_history:
            if snapshot['version'] == version:
                logger.debug(f"Restored version: {snapshot['name']}")
                return snapshot.get('data')
        return None
    
    # ===== CRASH RECOVERY =====
    
    def save_recovery_point(self, project_data: Dict[str, Any]) -> None:
        """Save crash recovery snapshot."""
        recovery_file = self.paths.backups_dir / 'recovery.json'
        try:
            with open(recovery_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'data': project_data,
                }, f)
            logger.debug(f"Saved recovery point")
        except Exception as e:
            logger.error(f"Failed to save recovery point: {e}")
    
    def load_recovery_point(self) -> Optional[Dict[str, Any]]:
        """Load crash recovery snapshot if available."""
        recovery_file = self.paths.backups_dir / 'recovery.json'
        if not recovery_file.exists():
            return None
        
        try:
            with open(recovery_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.debug(f"Loaded recovery point from {recovery_file}")
                return data.get('data')
        except Exception as e:
            logger.error(f"Failed to load recovery point: {e}")
            return None
    
    def clear_recovery_point(self) -> None:
        """Clear recovery snapshot after successful load."""
        recovery_file = self.paths.backups_dir / 'recovery.json'
        try:
            recovery_file.unlink(missing_ok=True)
        except Exception as e:
            logger.error(f"Failed to clear recovery point: {e}")
    
    # ===== UTILITY =====
    
    def clear_undo_redo(self) -> None:
        """Clear all undo/redo history."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        logger.debug("Cleared undo/redo stacks")
    
    def __repr__(self) -> str:
        return (f"<StateManager dirty={self._dirty} "
                f"undo={len(self._undo_stack)} redo={len(self._redo_stack)}>")


class CompositeCommand(UndoRedoCommand):
    """Groups multiple commands as one atomic operation."""
    
    def __init__(self, commands: List[UndoRedoCommand]):
        super().__init__(f"Composite ({len(commands)} commands)")
        self.commands = commands
    
    def execute(self) -> None:
        for cmd in self.commands:
            cmd.execute()
    
    def undo(self) -> None:
        for cmd in reversed(self.commands):
            cmd.undo()
    
    def redo(self) -> None:
        for cmd in self.commands:
            cmd.redo()
