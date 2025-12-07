"""
Action Dialog for UE5 Macro Automation.

Provides a dialog for creating and editing macro actions.

Example Usage:
    >>> from src.ui.action_dialog import ActionDialog
    >>> dialog = ActionDialog(parent)
    >>> if dialog.exec():
    ...     action = dialog.get_action()
"""

from __future__ import annotations

import json
import logging

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from src.core.macro_recorder import ActionType, RecordedAction

logger = logging.getLogger(__name__)


class ActionDialog(QDialog):
    """
    Dialog for creating or editing a macro action.

    Provides:
    - Action type selection
    - Target path/name input
    - Parameters editor (JSON)
    - Description field
    """

    def __init__(
        self,
        parent: QDialog | None = None,
        action: RecordedAction | None = None
    ) -> None:
        """
        Initialize the action dialog.

        Args:
            parent: Parent widget
            action: Existing action to edit (None for new action)
        """
        super().__init__(parent)

        self._action = action
        self._setup_ui()

        if action:
            self._populate_from_action(action)

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("Add Action" if not self._action else "Edit Action")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        type_group = QGroupBox("Action Type")
        type_layout = QFormLayout(type_group)

        self._type_combo = QComboBox()
        for action_type in ActionType:
            self._type_combo.addItem(action_type.name, action_type)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_layout.addRow("Type:", self._type_combo)

        self._type_description = QLabel()
        self._type_description.setWordWrap(True)
        self._type_description.setStyleSheet("color: gray;")
        type_layout.addRow("", self._type_description)

        layout.addWidget(type_group)

        target_group = QGroupBox("Target")
        target_layout = QFormLayout(target_group)

        self._target_path = QLineEdit()
        self._target_path.setPlaceholderText("/Game/Path/To/Asset")
        target_layout.addRow("Path:", self._target_path)

        self._target_name = QLineEdit()
        self._target_name.setPlaceholderText("ActorName")
        target_layout.addRow("Name:", self._target_name)

        layout.addWidget(target_group)

        params_group = QGroupBox("Parameters")
        params_layout = QVBoxLayout(params_group)

        self._params_editor = QTextEdit()
        self._params_editor.setPlaceholderText('{\n  "key": "value"\n}')
        self._params_editor.setMaximumHeight(150)
        params_layout.addWidget(self._params_editor)

        params_buttons = QHBoxLayout()

        format_btn = QPushButton("Format JSON")
        format_btn.clicked.connect(self._format_json)
        params_buttons.addWidget(format_btn)

        validate_btn = QPushButton("Validate")
        validate_btn.clicked.connect(self._validate_json)
        params_buttons.addWidget(validate_btn)

        params_buttons.addStretch()

        params_layout.addLayout(params_buttons)

        layout.addWidget(params_group)

        desc_group = QGroupBox("Description")
        desc_layout = QVBoxLayout(desc_group)

        self._description = QLineEdit()
        self._description.setPlaceholderText("Optional description of this action")
        desc_layout.addWidget(self._description)

        layout.addWidget(desc_group)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self._on_type_changed()

    def _populate_from_action(self, action: RecordedAction) -> None:
        """Populate the dialog from an existing action."""
        index = self._type_combo.findData(action.action_type)
        if index >= 0:
            self._type_combo.setCurrentIndex(index)

        if action.target_path:
            self._target_path.setText(action.target_path)

        if action.target_name:
            self._target_name.setText(action.target_name)

        if action.parameters:
            self._params_editor.setText(json.dumps(action.parameters, indent=2))

        if action.description:
            self._description.setText(action.description)

    def _on_type_changed(self) -> None:
        """Handle action type change."""
        action_type = self._type_combo.currentData()

        descriptions = {
            ActionType.ASSET_IMPORT: "Import an asset file (FBX, OBJ, etc.)",
            ActionType.ASSET_DELETE: "Delete an asset from the project",
            ActionType.ASSET_RENAME: "Rename an asset",
            ActionType.ASSET_MOVE: "Move an asset to a new location",
            ActionType.ASSET_DUPLICATE: "Duplicate an asset",
            ActionType.ACTOR_SPAWN: "Spawn an actor in the level",
            ActionType.ACTOR_DELETE: "Delete an actor from the level",
            ActionType.ACTOR_TRANSFORM: "Transform an actor (move, rotate, scale)",
            ActionType.ACTOR_PROPERTY: "Set a property on an actor",
            ActionType.MATERIAL_ASSIGN: "Assign a material to a mesh",
            ActionType.MATERIAL_CREATE: "Create a new material",
            ActionType.MATERIAL_INSTANCE: "Create a material instance",
            ActionType.TEXTURE_IMPORT: "Import a texture file",
            ActionType.LEVEL_LOAD: "Load a level",
            ActionType.LEVEL_SAVE: "Save the current level",
            ActionType.LEVEL_NEW: "Create a new level",
            ActionType.EDITOR_COMMAND: "Execute an editor console command",
            ActionType.PYTHON_EXEC: "Execute Python code",
            ActionType.BLUEPRINT_COMPILE: "Compile a Blueprint",
            ActionType.CUSTOM: "Custom action with user-defined handler",
        }

        self._type_description.setText(
            descriptions.get(action_type, "No description available")
        )

        path_types = {
            ActionType.ASSET_IMPORT,
            ActionType.ASSET_DELETE,
            ActionType.ASSET_RENAME,
            ActionType.ASSET_MOVE,
            ActionType.ASSET_DUPLICATE,
            ActionType.MATERIAL_ASSIGN,
            ActionType.MATERIAL_CREATE,
            ActionType.MATERIAL_INSTANCE,
            ActionType.TEXTURE_IMPORT,
            ActionType.LEVEL_LOAD,
            ActionType.LEVEL_SAVE,
            ActionType.BLUEPRINT_COMPILE,
        }

        name_types = {
            ActionType.ACTOR_SPAWN,
            ActionType.ACTOR_DELETE,
            ActionType.ACTOR_TRANSFORM,
            ActionType.ACTOR_PROPERTY,
        }

        self._target_path.setEnabled(action_type in path_types)
        self._target_name.setEnabled(action_type in name_types)

    def _format_json(self) -> None:
        """Format the JSON in the parameters editor."""
        try:
            text = self._params_editor.toPlainText()
            if text.strip():
                data = json.loads(text)
                formatted = json.dumps(data, indent=2)
                self._params_editor.setText(formatted)
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "JSON Error", f"Invalid JSON: {e}")

    def _validate_json(self) -> None:
        """Validate the JSON in the parameters editor."""
        try:
            text = self._params_editor.toPlainText()
            if text.strip():
                json.loads(text)
            QMessageBox.information(self, "Validation", "JSON is valid!")
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "JSON Error", f"Invalid JSON: {e}")

    def _on_accept(self) -> None:
        """Handle dialog acceptance."""
        params_text = self._params_editor.toPlainText()
        if params_text.strip():
            try:
                json.loads(params_text)
            except json.JSONDecodeError as e:
                QMessageBox.warning(
                    self,
                    "Invalid Parameters",
                    f"Parameters must be valid JSON: {e}"
                )
                return

        self.accept()

    def get_action(self) -> RecordedAction | None:
        """
        Get the action from the dialog.

        Returns:
            RecordedAction or None if dialog was cancelled
        """
        action_type = self._type_combo.currentData()

        target_path = self._target_path.text().strip() or None
        target_name = self._target_name.text().strip() or None

        params_text = self._params_editor.toPlainText().strip()
        parameters = json.loads(params_text) if params_text else {}

        description = self._description.text().strip() or None

        return RecordedAction(
            action_type=action_type,
            target_path=target_path,
            target_name=target_name,
            parameters=parameters,
            description=description,
        )
