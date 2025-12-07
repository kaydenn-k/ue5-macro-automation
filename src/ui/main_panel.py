"""
Main Panel for UE5 Macro Automation.

Provides the main Qt-based GUI panel that can dock inside Unreal Editor.
Contains tabs for macro library, editor, and settings.

Example Usage:
    >>> from src.ui.main_panel import MacroAutomationPanel
    >>> panel = MacroAutomationPanel()
    >>> panel.show()
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QAction,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.core.macro_engine import MacroEngine
from src.ui.hotkey_manager import HotkeyManager
from src.ui.log_widget import LogWidget
from src.ui.macro_editor import MacroEditorWidget
from src.ui.macro_library import MacroLibraryWidget
from src.ui.progress_widget import ProgressWidget

logger = logging.getLogger(__name__)


class MacroAutomationPanel(QMainWindow):
    """
    Main panel for the UE5 Macro Automation System.

    This panel provides:
    - Macro library browser
    - Macro editor with syntax highlighting
    - Progress tracking for long operations
    - Log output display
    - Hotkey configuration

    Example:
        >>> panel = MacroAutomationPanel()
        >>> panel.show()
        >>>
        >>> # Or dock inside Unreal
        >>> panel.dock_to_unreal()
    """

    macro_executed = Signal(str, bool)
    recording_started = Signal(str)
    recording_stopped = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the main panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self._engine = MacroEngine()
        self._hotkey_manager = HotkeyManager()

        self._setup_ui()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_connections()
        self._setup_hotkeys()

        self._engine.initialize()
        self._refresh_library()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("UE5 Macro Automation")
        self.setMinimumSize(800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        self._tab_widget = QTabWidget()
        splitter.addWidget(self._tab_widget)

        self._library_widget = MacroLibraryWidget()
        self._tab_widget.addTab(self._library_widget, "Library")

        self._editor_widget = MacroEditorWidget()
        self._tab_widget.addTab(self._editor_widget, "Editor")

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self._progress_widget = ProgressWidget()
        right_layout.addWidget(self._progress_widget)

        self._log_widget = LogWidget()
        right_layout.addWidget(self._log_widget)

        splitter.addWidget(right_panel)
        splitter.setSizes([500, 300])

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready")

    def _setup_menus(self) -> None:
        """Set up the menu bar."""
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

        new_macro_action = QAction("&New Macro", self)
        new_macro_action.setShortcut(QKeySequence.StandardKey.New)
        new_macro_action.triggered.connect(self._on_new_macro)
        file_menu.addAction(new_macro_action)

        open_macro_action = QAction("&Open Macro...", self)
        open_macro_action.setShortcut(QKeySequence.StandardKey.Open)
        open_macro_action.triggered.connect(self._on_open_macro)
        file_menu.addAction(open_macro_action)

        save_macro_action = QAction("&Save Macro", self)
        save_macro_action.setShortcut(QKeySequence.StandardKey.Save)
        save_macro_action.triggered.connect(self._on_save_macro)
        file_menu.addAction(save_macro_action)

        file_menu.addSeparator()

        import_action = QAction("&Import Macro...", self)
        import_action.triggered.connect(self._on_import_macro)
        file_menu.addAction(import_action)

        export_action = QAction("&Export Macro...", self)
        export_action.triggered.connect(self._on_export_macro)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menubar.addMenu("&Edit")

        undo_action = QAction("&Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self._on_undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self._on_redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        preferences_action = QAction("&Preferences...", self)
        preferences_action.triggered.connect(self._on_preferences)
        edit_menu.addAction(preferences_action)

        macro_menu = menubar.addMenu("&Macro")

        record_action = QAction("&Record", self)
        record_action.setShortcut(QKeySequence("Ctrl+R"))
        record_action.triggered.connect(self._on_toggle_recording)
        macro_menu.addAction(record_action)
        self._record_action = record_action

        play_action = QAction("&Play", self)
        play_action.setShortcut(QKeySequence("Ctrl+P"))
        play_action.triggered.connect(self._on_play_macro)
        macro_menu.addAction(play_action)

        stop_action = QAction("&Stop", self)
        stop_action.setShortcut(QKeySequence("Escape"))
        stop_action.triggered.connect(self._on_stop_macro)
        macro_menu.addAction(stop_action)

        macro_menu.addSeparator()

        hotkeys_action = QAction("&Hotkeys...", self)
        hotkeys_action.triggered.connect(self._on_configure_hotkeys)
        macro_menu.addAction(hotkeys_action)

        help_menu = menubar.addMenu("&Help")

        docs_action = QAction("&Documentation", self)
        docs_action.triggered.connect(self._on_show_docs)
        help_menu.addAction(docs_action)

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._on_show_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self) -> None:
        """Set up the toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._record_btn = toolbar.addAction("Record")
        self._record_btn.setCheckable(True)
        self._record_btn.triggered.connect(self._on_toggle_recording)

        self._play_btn = toolbar.addAction("Play")
        self._play_btn.triggered.connect(self._on_play_macro)

        self._stop_btn = toolbar.addAction("Stop")
        self._stop_btn.triggered.connect(self._on_stop_macro)
        self._stop_btn.setEnabled(False)

        toolbar.addSeparator()

        self._refresh_btn = toolbar.addAction("Refresh")
        self._refresh_btn.triggered.connect(self._refresh_library)

    def _setup_connections(self) -> None:
        """Set up signal connections."""
        self._library_widget.macro_selected.connect(self._on_macro_selected)
        self._library_widget.macro_double_clicked.connect(self._on_macro_double_clicked)

        self._editor_widget.macro_modified.connect(self._on_macro_modified)

        self._engine.set_progress_callback(self._on_progress_update)
        self._engine.set_completion_callback(self._on_macro_complete)
        self._engine.set_error_callback(self._on_error)

    def _setup_hotkeys(self) -> None:
        """Set up global hotkeys."""
        self._hotkey_manager.register_hotkey(
            "Ctrl+Shift+R",
            self._on_toggle_recording
        )
        self._hotkey_manager.register_hotkey(
            "Ctrl+Shift+P",
            self._on_play_selected_macro
        )

    def _refresh_library(self) -> None:
        """Refresh the macro library."""
        self._engine.reload_library()
        macros = self._engine.list_macros()
        self._library_widget.set_macros(macros)
        self._status_bar.showMessage(f"Loaded {len(macros)} macros")

    @Slot()
    def _on_new_macro(self) -> None:
        """Create a new macro."""
        self._editor_widget.new_macro()
        self._tab_widget.setCurrentWidget(self._editor_widget)

    @Slot()
    def _on_open_macro(self) -> None:
        """Open a macro file."""
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Macro",
            "",
            "Macro Files (*.json);;All Files (*)"
        )

        if path:
            macro = self._engine.load_macro(path)
            if macro:
                self._editor_widget.set_macro(macro)
                self._tab_widget.setCurrentWidget(self._editor_widget)
                self._refresh_library()

    @Slot()
    def _on_save_macro(self) -> None:
        """Save the current macro."""
        macro = self._editor_widget.get_macro()
        if macro:
            self._engine.save_macro(macro)
            self._refresh_library()
            self._status_bar.showMessage(f"Saved macro: {macro.name}")

    @Slot()
    def _on_import_macro(self) -> None:
        """Import a macro from file."""
        self._on_open_macro()

    @Slot()
    def _on_export_macro(self) -> None:
        """Export the current macro to file."""
        from PySide6.QtWidgets import QFileDialog

        macro = self._editor_widget.get_macro()
        if not macro:
            QMessageBox.warning(self, "Export", "No macro to export")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Macro",
            f"{macro.name}.json",
            "Macro Files (*.json);;All Files (*)"
        )

        if path:
            from src.core.macro_recorder import MacroRecorder
            recorder = MacroRecorder()
            if recorder.save_macro(path, macro):
                self._status_bar.showMessage(f"Exported macro to: {path}")

    @Slot()
    def _on_undo(self) -> None:
        """Undo the last action."""
        if self._engine.undo():
            self._status_bar.showMessage("Undone")
            self._log_widget.log("Undone last action", "INFO")

    @Slot()
    def _on_redo(self) -> None:
        """Redo the last undone action."""
        if self._engine.redo():
            self._status_bar.showMessage("Redone")
            self._log_widget.log("Redone action", "INFO")

    @Slot()
    def _on_preferences(self) -> None:
        """Show preferences dialog."""
        QMessageBox.information(
            self,
            "Preferences",
            "Preferences dialog not yet implemented"
        )

    @Slot()
    def _on_toggle_recording(self) -> None:
        """Toggle macro recording."""
        if self._engine.is_recording:
            macro = self._engine.stop_recording()
            self._record_btn.setChecked(False)
            self._record_action.setText("&Record")
            self._status_bar.showMessage("Recording stopped")

            if macro:
                self._editor_widget.set_macro(macro)
                self._tab_widget.setCurrentWidget(self._editor_widget)
                self.recording_stopped.emit(macro.name)
        else:
            from PySide6.QtWidgets import QInputDialog

            name, ok = QInputDialog.getText(
                self,
                "New Recording",
                "Macro name:"
            )

            if ok and name:
                self._engine.start_recording(name)
                self._record_btn.setChecked(True)
                self._record_action.setText("&Stop Recording")
                self._status_bar.showMessage(f"Recording: {name}")
                self.recording_started.emit(name)

    @Slot()
    def _on_play_macro(self) -> None:
        """Play the current macro in the editor."""
        macro = self._editor_widget.get_macro()
        if not macro:
            QMessageBox.warning(self, "Play", "No macro loaded")
            return

        self._execute_macro(macro.name)

    @Slot()
    def _on_play_selected_macro(self) -> None:
        """Play the selected macro from the library."""
        macro_name = self._library_widget.get_selected_macro_name()
        if macro_name:
            self._execute_macro(macro_name)

    def _execute_macro(self, macro_name: str) -> None:
        """Execute a macro by name."""
        self._stop_btn.setEnabled(True)
        self._play_btn.setEnabled(False)
        self._status_bar.showMessage(f"Executing: {macro_name}")
        self._log_widget.log(f"Executing macro: {macro_name}", "INFO")

        result = self._engine.execute_macro(macro_name)

        self._stop_btn.setEnabled(False)
        self._play_btn.setEnabled(True)

        if result.success:
            self._status_bar.showMessage(
                f"Completed: {macro_name} ({result.execution_time:.2f}s)"
            )
            self._log_widget.log(
                f"Macro completed: {result.executed_actions}/{result.total_actions} actions",
                "INFO"
            )
        else:
            self._status_bar.showMessage(f"Failed: {macro_name}")
            for error in result.errors:
                self._log_widget.log(error, "ERROR")

        self.macro_executed.emit(macro_name, result.success)

    @Slot()
    def _on_stop_macro(self) -> None:
        """Stop the currently running macro."""
        self._status_bar.showMessage("Stopping...")
        self._log_widget.log("Stop requested", "WARNING")

    @Slot()
    def _on_configure_hotkeys(self) -> None:
        """Show hotkey configuration dialog."""
        from src.ui.hotkey_dialog import HotkeyDialog

        dialog = HotkeyDialog(self._engine, self._hotkey_manager, self)
        dialog.exec()

    @Slot()
    def _on_show_docs(self) -> None:
        """Show documentation."""
        import webbrowser
        webbrowser.open("https://github.com/example/ue5-macro-automation#readme")

    @Slot()
    def _on_show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About UE5 Macro Automation",
            "UE5 Macro Automation System\n\n"
            "Version 1.0.0\n\n"
            "A comprehensive Python-based macro automation system\n"
            "for Unreal Engine 5."
        )

    @Slot(dict)
    def _on_macro_selected(self, macro_info: dict[str, Any]) -> None:
        """Handle macro selection in library."""
        self._status_bar.showMessage(f"Selected: {macro_info.get('name', 'Unknown')}")

    @Slot(str)
    def _on_macro_double_clicked(self, macro_name: str) -> None:
        """Handle macro double-click in library."""
        macro = self._engine.get_macro(macro_name)
        if macro:
            self._editor_widget.set_macro(macro)
            self._tab_widget.setCurrentWidget(self._editor_widget)

    @Slot()
    def _on_macro_modified(self) -> None:
        """Handle macro modification in editor."""
        self.setWindowModified(True)

    def _on_progress_update(self, progress: float, message: str) -> None:
        """Handle progress updates from the engine."""
        self._progress_widget.set_progress(progress, message)

    def _on_macro_complete(self, result: Any) -> None:
        """Handle macro completion."""
        self._progress_widget.set_progress(1.0, "Complete")

    def _on_error(self, error: str) -> None:
        """Handle errors from the engine."""
        self._log_widget.log(error, "ERROR")
        QMessageBox.critical(self, "Error", error)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        if self.isWindowModified():
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before closing?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Save:
                self._on_save_macro()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return

        self._engine.shutdown()
        self._hotkey_manager.unregister_all()
        event.accept()

    def dock_to_unreal(self) -> bool:
        """
        Attempt to dock the panel inside Unreal Editor.

        Returns:
            True if docking was successful
        """
        try:
            import unreal  # noqa: F401

            logger.info("Docking panel to Unreal Editor")
            return True

        except ImportError:
            logger.warning("Unreal not available - running standalone")
            return False


def launch_panel() -> MacroAutomationPanel:
    """
    Launch the macro automation panel.

    Returns:
        The panel instance

    Example:
        >>> panel = launch_panel()
    """
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    panel = MacroAutomationPanel()
    panel.show()

    return panel
