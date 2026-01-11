"""
PropertiesPanel - Signature-driven parameter editing

Dynamically creates widgets based on MoviePy function signatures.
No hardcoded sliders. Updates markers in real-time.
Live preview on parameter change.
"""

import logging
from typing import Dict, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSpinBox,
    QDoubleSpinBox, QLineEdit, QComboBox, QCheckBox, QGroupBox,
    QScrollArea, QPushButton
)
from PySide6.QtCore import Qt, Signal

from core.timeline_markers import TimelineMarker
from core.moviepy_registry import MoviePyRegistry

logger = logging.getLogger(__name__)


class ParameterWidget(QWidget):
    """Single parameter widget."""
    
    value_changed = Signal(str, object)  # param_name, value
    
    def __init__(self, param_name: str, param_type: str, default_value: Any = None):
        super().__init__()
        
        self.param_name = param_name
        self.param_type = param_type
        self.is_updating = False
        
        layout = QHBoxLayout(self)
        
        # Label
        label = QLabel(param_name)
        label.setMinimumWidth(100)
        layout.addWidget(label)
        
        # Create appropriate widget
        if param_type == 'int':
            self.widget = QSpinBox()
            self.widget.setMinimum(-1000)
            self.widget.setMaximum(1000)
            if default_value is not None:
                self.widget.setValue(int(default_value))
            self.widget.valueChanged.connect(self._on_value_changed)
        
        elif param_type == 'float':
            self.widget = QDoubleSpinBox()
            self.widget.setMinimum(-1000.0)
            self.widget.setMaximum(1000.0)
            self.widget.setSingleStep(0.1)
            if default_value is not None:
                self.widget.setValue(float(default_value))
            self.widget.valueChanged.connect(self._on_value_changed)
        
        elif param_type == 'bool':
            self.widget = QCheckBox()
            if default_value is not None:
                self.widget.setChecked(bool(default_value))
            self.widget.stateChanged.connect(self._on_value_changed)
        
        elif param_type == 'str':
            self.widget = QLineEdit()
            if default_value is not None:
                self.widget.setText(str(default_value))
            self.widget.textChanged.connect(self._on_value_changed)
        
        else:
            # Default to text
            self.widget = QLineEdit()
            if default_value is not None:
                self.widget.setText(str(default_value))
            self.widget.textChanged.connect(self._on_value_changed)
        
        layout.addWidget(self.widget, 1)
        self.setLayout(layout)
    
    def _on_value_changed(self) -> None:
        """Handle value change."""
        if self.is_updating:
            return
        
        value = self.get_value()
        self.value_changed.emit(self.param_name, value)
    
    def get_value(self) -> Any:
        """Get widget value."""
        if isinstance(self.widget, QSpinBox):
            return self.widget.value()
        elif isinstance(self.widget, QDoubleSpinBox):
            return self.widget.value()
        elif isinstance(self.widget, QCheckBox):
            return self.widget.isChecked()
        elif isinstance(self.widget, (QLineEdit, QComboBox)):
            return self.widget.text()
        else:
            return None
    
    def set_value(self, value: Any) -> None:
        """Set widget value."""
        self.is_updating = True
        
        if isinstance(self.widget, QSpinBox):
            self.widget.setValue(int(value))
        elif isinstance(self.widget, QDoubleSpinBox):
            self.widget.setValue(float(value))
        elif isinstance(self.widget, QCheckBox):
            self.widget.setChecked(bool(value))
        elif isinstance(self.widget, (QLineEdit, QComboBox)):
            self.widget.setText(str(value))
        
        self.is_updating = False


class PropertiesPanel(QWidget):
    """
    Properties panel for selected marker.
    
    Auto-generates controls from MoviePy function signature.
    Updates marker parameters live.
    """
    
    parameter_changed = Signal()  # Trigger preview update
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.registry = MoviePyRegistry.instance()
        self.current_marker: Optional[TimelineMarker] = None
        self.param_widgets: Dict[str, ParameterWidget] = {}
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Properties")
        title.setObjectName("propertiesTitle")
        layout.addWidget(title)
        
        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll)
        
        # Preview button
        self.preview_btn = QPushButton("Preview")
        self.preview_btn.clicked.connect(self._on_preview_clicked)
        layout.addWidget(self.preview_btn)
        
        # Status
        self.status_label = QLabel("(No marker selected)")
        self.status_label.setObjectName("propertiesStatus")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def set_marker(self, marker: TimelineMarker) -> None:
        """Set and display properties for marker."""
        self.current_marker = marker
        self.param_widgets.clear()
        
        # Clear content
        while self.content_layout.count():
            self.content_layout.takeAt(0).widget().deleteLater()
        
        if not marker:
            self.status_label.setText("(No marker selected)")
            return
        
        # Create widgets for marker parameters
        if marker.marker_type == 'effect' and marker.moviepy_qualified_name:
            self._setup_effect_parameters(marker)
        else:
            self._setup_clip_parameters(marker)
        
        # Add stretch
        self.content_layout.addStretch()
        
        self.status_label.setText(f"Editing: {marker.name}")
    
    def _setup_effect_parameters(self, marker: TimelineMarker) -> None:
        """Setup parameters for effect."""
        sig = self.registry.get_signature(marker.moviepy_qualified_name)
        if not sig:
            logger.warning(f"No signature for {marker.moviepy_qualified_name}")
            return
        
        logger.info(f"Setting up parameters for {sig.name} ({len(sig.parameters)} params)")
        
        # Create group
        group = QGroupBox("Effect Parameters")
        group_layout = QVBoxLayout()
        
        # Create widget for each parameter
        for param_info in sig.parameters:
            # Determine type
            param_type = 'str'
            if param_info.annotation:
                if 'int' in param_info.annotation:
                    param_type = 'int'
                elif 'float' in param_info.annotation:
                    param_type = 'float'
                elif 'bool' in param_info.annotation:
                    param_type = 'bool'
            
            # Get current value
            current_param = marker.get_parameter(param_info.name)
            current_value = current_param.value if current_param else param_info.default
            
            # Create widget
            widget = ParameterWidget(
                param_info.name,
                param_type,
                current_value
            )
            widget.value_changed.connect(self._on_parameter_changed)
            
            group_layout.addWidget(widget)
            self.param_widgets[param_info.name] = widget
        
        group.setLayout(group_layout)
        self.content_layout.addWidget(group)
    
    def _setup_clip_parameters(self, marker: TimelineMarker) -> None:
        """Setup parameters for clip."""
        group = QGroupBox("Clip Properties")
        group_layout = QVBoxLayout()
        
        # Basic properties
        name_widget = ParameterWidget("Name", "str", marker.name)
        name_widget.value_changed.connect(
            lambda name, val: setattr(marker, 'name', val)
        )
        group_layout.addWidget(name_widget)
        
        group.setLayout(group_layout)
        self.content_layout.addWidget(group)
    
    def _on_parameter_changed(self, param_name: str, value: Any) -> None:
        """Handle parameter change."""
        if not self.current_marker:
            return
        
        logger.debug(f"Parameter changed: {param_name} = {value}")
        
        # Update marker parameter
        self.current_marker.add_parameter(
            param_name, value, 'auto', param_name
        )
        
        # Emit signal for preview
        self.parameter_changed.emit()
    
    def _on_preview_clicked(self) -> None:
        """Handle preview button."""
        if self.current_marker:
            logger.info(f"Preview: {self.current_marker.name}")
            # Will emit signal to trigger preview rendering
            self.parameter_changed.emit()
