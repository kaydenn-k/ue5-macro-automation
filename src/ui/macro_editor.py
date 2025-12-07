"""
Macro Editor Widget for UE5 Macro Automation.

Provides a macro editor with syntax highlighting for editing macro definitions.

Example Usage:
    >>> from src.ui.macro_editor import MacroEditorWidget
    >>> editor = MacroEditorWidget()
    >>> editor.set_macro(macro)
"""

from __future__ import annotations

import json
import logging

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.macro_recorder import ActionType, Macro, RecordedAction

logger = logging.getLogger(__name__)


class JsonSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for JSON content."""

    def __init__(self, document: QTextDocument) -> None:
        """Initialize the highlighter."""
        super().__init__(document)

        self._formats: dict[str, QTextCharFormat] = {}

        key_format = QTextCharFormat()
        key_format.setForeground(QColor("#569CD6"))
        key_format.setFontWeight(QFont.Weight.Bold)
        self._formats["key"] = key_format

        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))
        self._formats["string"] = string_format

        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8"))
        self._formats["number"] = number_format

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))
        self._formats["keyword"] = keyword_format

        bracket_format = QTextCharFormat()
        bracket_format.setForeground(QColor("#FFD700"))
        self._formats["bracket"] = bracket_format

    def highlightBlock(self, text: str) -> None:
        """Highlight a block of text."""
        import re

        key_pattern = r'"([^"]+)"\s*:'
        for match in re.finditer(key_pattern, text):
            self.setFormat(
                match.start(),
                match.end() - match.start(),
                self._formats["key"]
            )

        string_pattern = r':\s*"([^"]*)"'
        for match in re.finditer(string_pattern, text):
            start = match.start() + text[match.start():].index('"')
            end = match.end()
            self.setFormat(start, end - start, self._formats["string"])

        number_pattern = r':\s*(-?\d+\.?\d*)'
        for match in re.finditer(number_pattern, text):
            start = match.start(1)
            length = len(match.group(1))
            self.setFormat(start, length, self._formats["number"])

        for keyword in ["true", "false", "null"]:
            pattern = rf'\b{keyword}\b'
            for match in re.finditer(pattern, text):
                self.setFormat(
                    match.start(),
                    match.end() - match.start(),
                    self._formats["keyword"]
                )

        for bracket in "[]{}":
            index = 0
            while True:
                index = text.find(bracket, index)
                if index == -1:
                    break
                self.setFormat(index, 1, self._formats["bracket"])
                index += 1


class MacroEditorWidget(QWidget):
    """
    Widget for editing macro definitions.

    Provides:
    - Macro metadata editing (name, description, category)
    - Action list with add/remove/reorder
    - JSON view with syntax highlighting
    - Validation

    Signals:
        macro_modified: Emitted when the macro is modified
        macro_saved: Emitted when the macro is saved (macro name)
    """

    macro_modified = Signal()
    macro_saved = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the macro editor widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self._macro: Macro | None = None
        self._modified = False

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)

        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        metadata_group = QGroupBox("Macro Properties")
        metadata_layout = QFormLayout(metadata_group)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Macro name")
        metadata_layout.addRow("Name:", self._name_input)

        self._description_input = QLineEdit()
        self._description_input.setPlaceholderText("Description")
        metadata_layout.addRow("Description:", self._description_input)

        self._category_combo = QComboBox()
        self._category_combo.addItems([
            "custom", "import", "export", "organization",
            "materials", "lighting", "validation"
        ])
        metadata_layout.addRow("Category:", self._category_combo)

        top_layout.addWidget(metadata_group)

        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_group)

        self._actions_table = QTableWidget()
        self._actions_table.setColumnCount(4)
        self._actions_table.setHorizontalHeaderLabels([
            "Type", "Target", "Parameters", "Description"
        ])
        self._actions_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._actions_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        actions_layout.addWidget(self._actions_table)

        action_buttons = QHBoxLayout()

        self._add_action_btn = QPushButton("Add Action")
        action_buttons.addWidget(self._add_action_btn)

        self._remove_action_btn = QPushButton("Remove")
        self._remove_action_btn.setEnabled(False)
        action_buttons.addWidget(self._remove_action_btn)

        self._move_up_btn = QPushButton("Move Up")
        self._move_up_btn.setEnabled(False)
        action_buttons.addWidget(self._move_up_btn)

        self._move_down_btn = QPushButton("Move Down")
        self._move_down_btn.setEnabled(False)
        action_buttons.addWidget(self._move_down_btn)

        action_buttons.addStretch()

        actions_layout.addLayout(action_buttons)

        top_layout.addWidget(actions_group)

        splitter.addWidget(top_widget)

        json_group = QGroupBox("JSON View")
        json_layout = QVBoxLayout(json_group)

        self._json_editor = QPlainTextEdit()
        self._json_editor.setFont(QFont("Consolas", 10))
        self._json_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        json_layout.addWidget(self._json_editor)

        self._highlighter = JsonSyntaxHighlighter(self._json_editor.document())

        json_buttons = QHBoxLayout()

        self._apply_json_btn = QPushButton("Apply JSON")
        json_buttons.addWidget(self._apply_json_btn)

        self._format_json_btn = QPushButton("Format")
        json_buttons.addWidget(self._format_json_btn)

        self._validate_btn = QPushButton("Validate")
        json_buttons.addWidget(self._validate_btn)

        json_buttons.addStretch()

        json_layout.addLayout(json_buttons)

        splitter.addWidget(json_group)

        splitter.setSizes([400, 200])

    def _setup_connections(self) -> None:
        """Set up signal connections."""
        self._name_input.textChanged.connect(self._on_modified)
        self._description_input.textChanged.connect(self._on_modified)
        self._category_combo.currentIndexChanged.connect(self._on_modified)

        self._actions_table.itemSelectionChanged.connect(
            self._on_action_selection_changed
        )

        self._add_action_btn.clicked.connect(self._on_add_action)
        self._remove_action_btn.clicked.connect(self._on_remove_action)
        self._move_up_btn.clicked.connect(self._on_move_up)
        self._move_down_btn.clicked.connect(self._on_move_down)

        self._apply_json_btn.clicked.connect(self._on_apply_json)
        self._format_json_btn.clicked.connect(self._on_format_json)
        self._validate_btn.clicked.connect(self._on_validate)

    def new_macro(self) -> None:
        """Create a new empty macro."""
        self._macro = Macro(
            name="New Macro",
            actions=[],
            description="",
            metadata={"category": "custom"}
        )
        self._update_ui()
        self._modified = False

    def set_macro(self, macro: Macro) -> None:
        """
        Set the macro to edit.

        Args:
            macro: Macro to edit
        """
        self._macro = macro
        self._update_ui()
        self._modified = False

    def get_macro(self) -> Macro | None:
        """
        Get the current macro with any modifications.

        Returns:
            The edited macro or None
        """
        if not self._macro:
            return None

        self._macro.name = self._name_input.text()
        self._macro.description = self._description_input.text()
        self._macro.metadata["category"] = self._category_combo.currentText()

        return self._macro

    def _update_ui(self) -> None:
        """Update the UI from the current macro."""
        if not self._macro:
            self._name_input.clear()
            self._description_input.clear()
            self._category_combo.setCurrentIndex(0)
            self._actions_table.setRowCount(0)
            self._json_editor.clear()
            return

        self._name_input.setText(self._macro.name)
        self._description_input.setText(self._macro.description or "")

        category = self._macro.metadata.get("category", "custom")
        index = self._category_combo.findText(category)
        if index >= 0:
            self._category_combo.setCurrentIndex(index)

        self._update_actions_table()
        self._update_json_view()

    def _update_actions_table(self) -> None:
        """Update the actions table from the macro."""
        self._actions_table.setRowCount(0)

        if not self._macro:
            return

        for action in self._macro.actions:
            row = self._actions_table.rowCount()
            self._actions_table.insertRow(row)

            type_item = QTableWidgetItem(action.action_type.name)
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._actions_table.setItem(row, 0, type_item)

            target = action.target_path or action.target_name or "-"
            target_item = QTableWidgetItem(target)
            target_item.setFlags(target_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._actions_table.setItem(row, 1, target_item)

            params = json.dumps(action.parameters) if action.parameters else "-"
            params_item = QTableWidgetItem(params[:50] + "..." if len(params) > 50 else params)
            params_item.setFlags(params_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            params_item.setToolTip(params)
            self._actions_table.setItem(row, 2, params_item)

            desc_item = QTableWidgetItem(action.description or "-")
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._actions_table.setItem(row, 3, desc_item)

    def _update_json_view(self) -> None:
        """Update the JSON view from the macro."""
        if not self._macro:
            self._json_editor.clear()
            return

        macro_dict = {
            "name": self._macro.name,
            "description": self._macro.description,
            "metadata": self._macro.metadata,
            "actions": [
                {
                    "action_type": action.action_type.name,
                    "target_path": action.target_path,
                    "target_name": action.target_name,
                    "parameters": action.parameters,
                    "description": action.description,
                }
                for action in self._macro.actions
            ]
        }

        json_text = json.dumps(macro_dict, indent=2)
        self._json_editor.setPlainText(json_text)

    @Slot()
    def _on_modified(self) -> None:
        """Handle modification."""
        self._modified = True
        self.macro_modified.emit()

    @Slot()
    def _on_action_selection_changed(self) -> None:
        """Handle action selection change."""
        has_selection = len(self._actions_table.selectedItems()) > 0
        row = self._actions_table.currentRow()
        row_count = self._actions_table.rowCount()

        self._remove_action_btn.setEnabled(has_selection)
        self._move_up_btn.setEnabled(has_selection and row > 0)
        self._move_down_btn.setEnabled(has_selection and row < row_count - 1)

    @Slot()
    def _on_add_action(self) -> None:
        """Add a new action."""
        from src.ui.action_dialog import ActionDialog

        dialog = ActionDialog(self)
        if dialog.exec():
            action = dialog.get_action()
            if action and self._macro:
                self._macro.actions.append(action)
                self._update_actions_table()
                self._update_json_view()
                self._on_modified()

    @Slot()
    def _on_remove_action(self) -> None:
        """Remove the selected action."""
        row = self._actions_table.currentRow()
        if row >= 0 and self._macro:
            del self._macro.actions[row]
            self._update_actions_table()
            self._update_json_view()
            self._on_modified()

    @Slot()
    def _on_move_up(self) -> None:
        """Move the selected action up."""
        row = self._actions_table.currentRow()
        if row > 0 and self._macro:
            self._macro.actions[row], self._macro.actions[row - 1] = \
                self._macro.actions[row - 1], self._macro.actions[row]
            self._update_actions_table()
            self._update_json_view()
            self._actions_table.selectRow(row - 1)
            self._on_modified()

    @Slot()
    def _on_move_down(self) -> None:
        """Move the selected action down."""
        row = self._actions_table.currentRow()
        if row < self._actions_table.rowCount() - 1 and self._macro:
            self._macro.actions[row], self._macro.actions[row + 1] = \
                self._macro.actions[row + 1], self._macro.actions[row]
            self._update_actions_table()
            self._update_json_view()
            self._actions_table.selectRow(row + 1)
            self._on_modified()

    @Slot()
    def _on_apply_json(self) -> None:
        """Apply changes from the JSON editor."""
        try:
            json_text = self._json_editor.toPlainText()
            data = json.loads(json_text)

            self._name_input.setText(data.get("name", ""))
            self._description_input.setText(data.get("description", ""))

            if self._macro:
                self._macro.name = data.get("name", "")
                self._macro.description = data.get("description", "")
                self._macro.metadata = data.get("metadata", {})

                self._macro.actions = []
                for action_data in data.get("actions", []):
                    action = RecordedAction(
                        action_type=ActionType[action_data["action_type"]],
                        target_path=action_data.get("target_path"),
                        target_name=action_data.get("target_name"),
                        parameters=action_data.get("parameters", {}),
                        description=action_data.get("description"),
                    )
                    self._macro.actions.append(action)

                self._update_actions_table()
                self._on_modified()

                QMessageBox.information(self, "Apply JSON", "JSON applied successfully")

        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "JSON Error", f"Invalid JSON: {e}")
        except KeyError as e:
            QMessageBox.critical(self, "JSON Error", f"Missing key: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply JSON: {e}")

    @Slot()
    def _on_format_json(self) -> None:
        """Format the JSON in the editor."""
        try:
            json_text = self._json_editor.toPlainText()
            data = json.loads(json_text)
            formatted = json.dumps(data, indent=2)
            self._json_editor.setPlainText(formatted)
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "JSON Error", f"Invalid JSON: {e}")

    @Slot()
    def _on_validate(self) -> None:
        """Validate the current macro."""
        errors: list[str] = []

        if not self._name_input.text().strip():
            errors.append("Macro name is required")

        if self._macro and not self._macro.actions:
            errors.append("Macro has no actions")

        try:
            json_text = self._json_editor.toPlainText()
            json.loads(json_text)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {e}")

        if errors:
            QMessageBox.warning(
                self,
                "Validation Failed",
                "Validation errors:\n\n" + "\n".join(f"- {e}" for e in errors)
            )
        else:
            QMessageBox.information(
                self,
                "Validation Passed",
                "Macro is valid!"
            )
