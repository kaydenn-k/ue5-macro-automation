"""
Macro Library Widget for UE5 Macro Automation.

Provides a browsable library of saved macros with search and filtering.

Example Usage:
    >>> from src.ui.macro_library import MacroLibraryWidget
    >>> library = MacroLibraryWidget()
    >>> library.set_macros(macro_list)
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class MacroLibraryWidget(QWidget):
    """
    Widget for browsing and managing the macro library.

    Provides:
    - List view of all macros
    - Search filtering
    - Category filtering
    - Context menu for macro operations

    Signals:
        macro_selected: Emitted when a macro is selected (dict with macro info)
        macro_double_clicked: Emitted when a macro is double-clicked (macro name)
        macro_deleted: Emitted when a macro is deleted (macro name)
    """

    macro_selected = Signal(dict)
    macro_double_clicked = Signal(str)
    macro_deleted = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the macro library widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self._macros: list[dict[str, Any]] = []
        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        search_layout = QHBoxLayout()

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search macros...")
        self._search_input.setClearButtonEnabled(True)
        search_layout.addWidget(self._search_input)

        layout.addLayout(search_layout)

        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Category:"))

        self._category_combo = QComboBox()
        self._category_combo.addItem("All", "")
        self._category_combo.addItem("Import", "import")
        self._category_combo.addItem("Export", "export")
        self._category_combo.addItem("Organization", "organization")
        self._category_combo.addItem("Materials", "materials")
        self._category_combo.addItem("Lighting", "lighting")
        self._category_combo.addItem("Validation", "validation")
        self._category_combo.addItem("Custom", "custom")
        filter_layout.addWidget(self._category_combo)

        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        self._macro_list = QListWidget()
        self._macro_list.setAlternatingRowColors(True)
        self._macro_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        layout.addWidget(self._macro_list)

        info_group = QGroupBox("Macro Info")
        info_layout = QVBoxLayout(info_group)

        self._info_name = QLabel("Name: -")
        info_layout.addWidget(self._info_name)

        self._info_actions = QLabel("Actions: -")
        info_layout.addWidget(self._info_actions)

        self._info_description = QLabel("Description: -")
        self._info_description.setWordWrap(True)
        info_layout.addWidget(self._info_description)

        layout.addWidget(info_group)

        button_layout = QHBoxLayout()

        self._run_btn = QPushButton("Run")
        self._run_btn.setEnabled(False)
        button_layout.addWidget(self._run_btn)

        self._edit_btn = QPushButton("Edit")
        self._edit_btn.setEnabled(False)
        button_layout.addWidget(self._edit_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setEnabled(False)
        button_layout.addWidget(self._delete_btn)

        layout.addLayout(button_layout)

    def _setup_connections(self) -> None:
        """Set up signal connections."""
        self._search_input.textChanged.connect(self._filter_macros)
        self._category_combo.currentIndexChanged.connect(self._filter_macros)

        self._macro_list.itemSelectionChanged.connect(self._on_selection_changed)
        self._macro_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._macro_list.customContextMenuRequested.connect(self._show_context_menu)

        self._run_btn.clicked.connect(self._on_run_clicked)
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        self._delete_btn.clicked.connect(self._on_delete_clicked)

    def set_macros(self, macros: list[dict[str, Any]]) -> None:
        """
        Set the list of macros to display.

        Args:
            macros: List of macro info dictionaries
        """
        self._macros = macros
        self._filter_macros()

    def get_selected_macro_name(self) -> str | None:
        """
        Get the name of the currently selected macro.

        Returns:
            Macro name or None if nothing selected
        """
        item = self._macro_list.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    @Slot()
    def _filter_macros(self) -> None:
        """Filter macros based on search and category."""
        search_text = self._search_input.text().lower()
        category = self._category_combo.currentData()

        self._macro_list.clear()

        for macro in self._macros:
            name = macro.get("name", "")
            macro_category = macro.get("category", "custom")
            description = macro.get("description", "")

            if search_text and search_text not in name.lower():
                if search_text not in description.lower():
                    continue

            if category and macro_category != category:
                continue

            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setToolTip(description or "No description")

            self._macro_list.addItem(item)

    @Slot()
    def _on_selection_changed(self) -> None:
        """Handle selection change in the list."""
        item = self._macro_list.currentItem()
        has_selection = item is not None

        self._run_btn.setEnabled(has_selection)
        self._edit_btn.setEnabled(has_selection)
        self._delete_btn.setEnabled(has_selection)

        if has_selection:
            macro_name = item.data(Qt.ItemDataRole.UserRole)
            macro_info = self._get_macro_info(macro_name)

            if macro_info:
                self._info_name.setText(f"Name: {macro_info.get('name', '-')}")
                self._info_actions.setText(
                    f"Actions: {macro_info.get('action_count', 0)}"
                )
                self._info_description.setText(
                    f"Description: {macro_info.get('description', '-')}"
                )

                self.macro_selected.emit(macro_info)
        else:
            self._info_name.setText("Name: -")
            self._info_actions.setText("Actions: -")
            self._info_description.setText("Description: -")

    def _get_macro_info(self, name: str) -> dict[str, Any] | None:
        """Get macro info by name."""
        for macro in self._macros:
            if macro.get("name") == name:
                return macro
        return None

    @Slot(QListWidgetItem)
    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle item double-click."""
        macro_name = item.data(Qt.ItemDataRole.UserRole)
        self.macro_double_clicked.emit(macro_name)

    @Slot()
    def _show_context_menu(self, position) -> None:
        """Show context menu for macro operations."""
        item = self._macro_list.itemAt(position)
        if not item:
            return

        menu = QMenu(self)

        run_action = QAction("Run", self)
        run_action.triggered.connect(self._on_run_clicked)
        menu.addAction(run_action)

        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(self._on_edit_clicked)
        menu.addAction(edit_action)

        menu.addSeparator()

        duplicate_action = QAction("Duplicate", self)
        duplicate_action.triggered.connect(self._on_duplicate_clicked)
        menu.addAction(duplicate_action)

        rename_action = QAction("Rename", self)
        rename_action.triggered.connect(self._on_rename_clicked)
        menu.addAction(rename_action)

        menu.addSeparator()

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self._on_delete_clicked)
        menu.addAction(delete_action)

        menu.exec(self._macro_list.mapToGlobal(position))

    @Slot()
    def _on_run_clicked(self) -> None:
        """Handle run button click."""
        macro_name = self.get_selected_macro_name()
        if macro_name:
            self.macro_double_clicked.emit(macro_name)

    @Slot()
    def _on_edit_clicked(self) -> None:
        """Handle edit button click."""
        macro_name = self.get_selected_macro_name()
        if macro_name:
            self.macro_double_clicked.emit(macro_name)

    @Slot()
    def _on_delete_clicked(self) -> None:
        """Handle delete button click."""
        macro_name = self.get_selected_macro_name()
        if not macro_name:
            return

        reply = QMessageBox.question(
            self,
            "Delete Macro",
            f"Are you sure you want to delete '{macro_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.macro_deleted.emit(macro_name)

            self._macros = [m for m in self._macros if m.get("name") != macro_name]
            self._filter_macros()

    @Slot()
    def _on_duplicate_clicked(self) -> None:
        """Handle duplicate action."""
        macro_name = self.get_selected_macro_name()
        if macro_name:
            logger.info(f"Duplicate macro: {macro_name}")

    @Slot()
    def _on_rename_clicked(self) -> None:
        """Handle rename action."""
        macro_name = self.get_selected_macro_name()
        if macro_name:
            from PySide6.QtWidgets import QInputDialog

            new_name, ok = QInputDialog.getText(
                self,
                "Rename Macro",
                "New name:",
                text=macro_name
            )

            if ok and new_name and new_name != macro_name:
                logger.info(f"Rename macro: {macro_name} -> {new_name}")
