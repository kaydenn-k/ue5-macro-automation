"""
Hotkey Manager for UE5 Macro Automation.

Provides hotkey registration and management for triggering macros.

Example Usage:
    >>> from src.ui.hotkey_manager import HotkeyManager
    >>> manager = HotkeyManager()
    >>> manager.register_hotkey("Ctrl+Shift+M", my_callback)
"""

from __future__ import annotations

import logging
from typing import Callable

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class HotkeyManager(QObject):
    """
    Manager for global hotkey bindings.

    Provides:
    - Hotkey registration with callbacks
    - Hotkey unregistration
    - Conflict detection
    - Persistence of hotkey bindings

    Signals:
        hotkey_triggered: Emitted when a hotkey is triggered (hotkey string)
        hotkey_registered: Emitted when a hotkey is registered (hotkey string)
        hotkey_unregistered: Emitted when a hotkey is unregistered (hotkey string)
    """

    hotkey_triggered = Signal(str)
    hotkey_registered = Signal(str)
    hotkey_unregistered = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        """
        Initialize the hotkey manager.

        Args:
            parent: Parent QObject
        """
        super().__init__(parent)

        self._hotkeys: dict[str, tuple[Callable, QShortcut | None]] = {}
        self._parent_widget: QWidget | None = None

    def set_parent_widget(self, widget: QWidget) -> None:
        """
        Set the parent widget for shortcuts.

        Args:
            widget: Parent widget for QShortcut objects
        """
        self._parent_widget = widget

        for hotkey, (callback, _) in list(self._hotkeys.items()):
            self._create_shortcut(hotkey, callback)

    def register_hotkey(
        self,
        hotkey: str,
        callback: Callable[[], None],
        description: str = ""
    ) -> bool:
        """
        Register a hotkey with a callback.

        Args:
            hotkey: Hotkey string (e.g., "Ctrl+Shift+M")
            callback: Function to call when hotkey is triggered
            description: Optional description of the hotkey action

        Returns:
            True if registration was successful

        Example:
            >>> manager.register_hotkey("Ctrl+Shift+R", start_recording)
        """
        normalized = self._normalize_hotkey(hotkey)

        if normalized in self._hotkeys:
            logger.warning(f"Hotkey already registered: {normalized}")
            return False

        shortcut = self._create_shortcut(normalized, callback)
        self._hotkeys[normalized] = (callback, shortcut)

        logger.info(f"Registered hotkey: {normalized}")
        self.hotkey_registered.emit(normalized)

        return True

    def unregister_hotkey(self, hotkey: str) -> bool:
        """
        Unregister a hotkey.

        Args:
            hotkey: Hotkey string to unregister

        Returns:
            True if unregistration was successful
        """
        normalized = self._normalize_hotkey(hotkey)

        if normalized not in self._hotkeys:
            logger.warning(f"Hotkey not registered: {normalized}")
            return False

        _, shortcut = self._hotkeys[normalized]
        if shortcut:
            shortcut.setEnabled(False)
            shortcut.deleteLater()

        del self._hotkeys[normalized]

        logger.info(f"Unregistered hotkey: {normalized}")
        self.hotkey_unregistered.emit(normalized)

        return True

    def unregister_all(self) -> None:
        """Unregister all hotkeys."""
        for hotkey in list(self._hotkeys.keys()):
            self.unregister_hotkey(hotkey)

    def is_registered(self, hotkey: str) -> bool:
        """
        Check if a hotkey is registered.

        Args:
            hotkey: Hotkey string to check

        Returns:
            True if the hotkey is registered
        """
        normalized = self._normalize_hotkey(hotkey)
        return normalized in self._hotkeys

    def get_registered_hotkeys(self) -> list[str]:
        """
        Get list of all registered hotkeys.

        Returns:
            List of hotkey strings
        """
        return list(self._hotkeys.keys())

    def trigger_hotkey(self, hotkey: str) -> bool:
        """
        Manually trigger a hotkey callback.

        Args:
            hotkey: Hotkey string to trigger

        Returns:
            True if the hotkey was triggered
        """
        normalized = self._normalize_hotkey(hotkey)

        if normalized not in self._hotkeys:
            return False

        callback, _ = self._hotkeys[normalized]

        try:
            callback()
            self.hotkey_triggered.emit(normalized)
            return True
        except Exception as e:
            logger.error(f"Hotkey callback failed: {e}")
            return False

    def _normalize_hotkey(self, hotkey: str) -> str:
        """Normalize a hotkey string."""
        sequence = QKeySequence(hotkey)
        return sequence.toString()

    def _create_shortcut(
        self,
        hotkey: str,
        callback: Callable[[], None]
    ) -> QShortcut | None:
        """Create a QShortcut for a hotkey."""
        if not self._parent_widget:
            return None

        shortcut = QShortcut(QKeySequence(hotkey), self._parent_widget)
        shortcut.activated.connect(lambda: self._on_shortcut_activated(hotkey, callback))

        return shortcut

    def _on_shortcut_activated(
        self,
        hotkey: str,
        callback: Callable[[], None]
    ) -> None:
        """Handle shortcut activation."""
        logger.debug(f"Hotkey triggered: {hotkey}")

        try:
            callback()
            self.hotkey_triggered.emit(hotkey)
        except Exception as e:
            logger.error(f"Hotkey callback failed: {e}")

    def save_bindings(self, path: str) -> bool:
        """
        Save hotkey bindings to a file.

        Args:
            path: Path to save bindings

        Returns:
            True if save was successful
        """
        import json

        try:
            bindings = {
                hotkey: {
                    "callback_name": callback.__name__ if hasattr(callback, "__name__") else str(callback)
                }
                for hotkey, (callback, _) in self._hotkeys.items()
            }

            with open(path, "w") as f:
                json.dump(bindings, f, indent=2)

            logger.info(f"Saved hotkey bindings to: {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save hotkey bindings: {e}")
            return False

    def load_bindings(
        self,
        path: str,
        callback_map: dict[str, Callable[[], None]]
    ) -> int:
        """
        Load hotkey bindings from a file.

        Args:
            path: Path to load bindings from
            callback_map: Map of callback names to actual callbacks

        Returns:
            Number of bindings loaded
        """
        import json

        try:
            with open(path) as f:
                bindings = json.load(f)

            loaded = 0
            for hotkey, data in bindings.items():
                callback_name = data.get("callback_name")
                if callback_name and callback_name in callback_map:
                    if self.register_hotkey(hotkey, callback_map[callback_name]):
                        loaded += 1

            logger.info(f"Loaded {loaded} hotkey bindings from: {path}")
            return loaded

        except FileNotFoundError:
            logger.warning(f"Hotkey bindings file not found: {path}")
            return 0
        except Exception as e:
            logger.error(f"Failed to load hotkey bindings: {e}")
            return 0


class HotkeyDialog:
    """Dialog for configuring hotkey bindings."""

    def __init__(
        self,
        engine,
        hotkey_manager: HotkeyManager,
        parent: QWidget | None = None
    ) -> None:
        """
        Initialize the hotkey dialog.

        Args:
            engine: MacroEngine instance
            hotkey_manager: HotkeyManager instance
            parent: Parent widget
        """
        from PySide6.QtWidgets import (
            QDialog,
            QHBoxLayout,
            QHeaderView,
            QPushButton,
            QTableWidget,
            QVBoxLayout,
        )

        self._dialog = QDialog(parent)
        self._dialog.setWindowTitle("Configure Hotkeys")
        self._dialog.setMinimumSize(500, 400)

        self._engine = engine
        self._hotkey_manager = hotkey_manager

        layout = QVBoxLayout(self._dialog)

        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["Macro", "Hotkey", "Actions"])
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self._table)

        button_layout = QHBoxLayout()

        assign_btn = QPushButton("Assign Hotkey")
        assign_btn.clicked.connect(self._on_assign)
        button_layout.addWidget(assign_btn)

        remove_btn = QPushButton("Remove Hotkey")
        remove_btn.clicked.connect(self._on_remove)
        button_layout.addWidget(remove_btn)

        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self._dialog.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        self._refresh_table()

    def exec(self) -> int:
        """Show the dialog."""
        return self._dialog.exec()

    def _refresh_table(self) -> None:
        """Refresh the table with current bindings."""
        from PySide6.QtWidgets import QTableWidgetItem

        self._table.setRowCount(0)

        macros = self._engine.list_macros()
        registered = self._hotkey_manager.get_registered_hotkeys()

        for macro in macros:
            row = self._table.rowCount()
            self._table.insertRow(row)

            name = macro.get("name", "Unknown")
            self._table.setItem(row, 0, QTableWidgetItem(name))

            hotkey = ""
            for _hk in registered:
                pass
            self._table.setItem(row, 1, QTableWidgetItem(hotkey))

            self._table.setItem(row, 2, QTableWidgetItem(
                str(macro.get("action_count", 0))
            ))

    def _on_assign(self) -> None:
        """Handle assign hotkey button."""
        from PySide6.QtWidgets import QInputDialog, QMessageBox

        row = self._table.currentRow()
        if row < 0:
            QMessageBox.warning(
                self._dialog,
                "No Selection",
                "Please select a macro first"
            )
            return

        macro_name = self._table.item(row, 0).text()

        hotkey, ok = QInputDialog.getText(
            self._dialog,
            "Assign Hotkey",
            f"Enter hotkey for '{macro_name}':\n(e.g., Ctrl+Shift+M)"
        )

        if ok and hotkey:
            def execute_macro():
                self._engine.execute_macro(macro_name)

            if self._hotkey_manager.register_hotkey(hotkey, execute_macro):
                self._table.item(row, 1).setText(hotkey)
                QMessageBox.information(
                    self._dialog,
                    "Hotkey Assigned",
                    f"Hotkey '{hotkey}' assigned to '{macro_name}'"
                )
            else:
                QMessageBox.warning(
                    self._dialog,
                    "Assignment Failed",
                    f"Could not assign hotkey '{hotkey}'"
                )

    def _on_remove(self) -> None:
        """Handle remove hotkey button."""

        row = self._table.currentRow()
        if row < 0:
            return

        hotkey = self._table.item(row, 1).text()
        if hotkey:
            self._hotkey_manager.unregister_hotkey(hotkey)
            self._table.item(row, 1).setText("")
