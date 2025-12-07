"""
Log Widget for UE5 Macro Automation.

Provides a log output display with filtering and export capabilities.

Example Usage:
    >>> from src.ui.log_widget import LogWidget
    >>> log = LogWidget()
    >>> log.log("Operation completed", "INFO")
"""

from __future__ import annotations

import logging
from datetime import datetime

from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class LogWidget(QWidget):
    """
    Widget for displaying log messages.

    Provides:
    - Color-coded log levels
    - Level filtering
    - Auto-scroll
    - Export to file
    - Clear functionality

    Signals:
        log_added: Emitted when a log entry is added (message, level)
    """

    log_added = Signal(str, str)

    LOG_COLORS = {
        "DEBUG": "#808080",
        "INFO": "#FFFFFF",
        "WARNING": "#FFA500",
        "ERROR": "#FF4444",
        "CRITICAL": "#FF0000",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the log widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self._log_entries: list[tuple[datetime, str, str]] = []
        self._auto_scroll = True

        self._setup_ui()
        self._setup_logging_handler()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        group = QGroupBox("Log Output")
        group_layout = QVBoxLayout(group)

        controls_layout = QHBoxLayout()

        controls_layout.addWidget(QComboBox())
        self._level_combo = controls_layout.itemAt(0).widget()
        self._level_combo.addItems(["All", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self._level_combo.setCurrentText("INFO")
        self._level_combo.currentTextChanged.connect(self._filter_logs)

        self._auto_scroll_check = QCheckBox("Auto-scroll")
        self._auto_scroll_check.setChecked(True)
        self._auto_scroll_check.toggled.connect(self._on_auto_scroll_toggled)
        controls_layout.addWidget(self._auto_scroll_check)

        controls_layout.addStretch()

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.clicked.connect(self.clear)
        controls_layout.addWidget(self._clear_btn)

        self._export_btn = QPushButton("Export")
        self._export_btn.clicked.connect(self._export_logs)
        controls_layout.addWidget(self._export_btn)

        group_layout.addLayout(controls_layout)

        self._log_display = QTextEdit()
        self._log_display.setReadOnly(True)
        self._log_display.setFont(QFont("Consolas", 9))
        self._log_display.setStyleSheet(
            "QTextEdit { background-color: #1E1E1E; color: #FFFFFF; }"
        )
        group_layout.addWidget(self._log_display)

        layout.addWidget(group)

    def _setup_logging_handler(self) -> None:
        """Set up a logging handler to capture log messages."""
        handler = LogWidgetHandler(self)
        handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)

        root_logger = logging.getLogger("src")
        root_logger.addHandler(handler)

    def log(self, message: str, level: str = "INFO") -> None:
        """
        Add a log entry.

        Args:
            message: Log message
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        timestamp = datetime.now()
        self._log_entries.append((timestamp, level.upper(), message))

        current_filter = self._level_combo.currentText()
        if self._should_show(level.upper(), current_filter):
            self._append_log_entry(timestamp, level.upper(), message)

        self.log_added.emit(message, level)

    def _append_log_entry(
        self,
        timestamp: datetime,
        level: str,
        message: str
    ) -> None:
        """Append a log entry to the display."""
        cursor = self._log_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        time_format = QTextCharFormat()
        time_format.setForeground(QColor("#808080"))

        cursor.insertText(f"[{timestamp.strftime('%H:%M:%S')}] ", time_format)

        level_format = QTextCharFormat()
        level_format.setForeground(QColor(self.LOG_COLORS.get(level, "#FFFFFF")))
        level_format.setFontWeight(QFont.Weight.Bold)

        cursor.insertText(f"[{level}] ", level_format)

        message_format = QTextCharFormat()
        message_format.setForeground(QColor(self.LOG_COLORS.get(level, "#FFFFFF")))

        cursor.insertText(f"{message}\n", message_format)

        if self._auto_scroll:
            self._log_display.setTextCursor(cursor)
            self._log_display.ensureCursorVisible()

    def _should_show(self, entry_level: str, filter_level: str) -> bool:
        """Check if an entry should be shown based on filter."""
        if filter_level == "All":
            return True

        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        try:
            entry_index = levels.index(entry_level)
            filter_index = levels.index(filter_level)
            return entry_index >= filter_index
        except ValueError:
            return True

    @Slot()
    def _filter_logs(self) -> None:
        """Filter logs based on selected level."""
        self._log_display.clear()

        filter_level = self._level_combo.currentText()

        for timestamp, level, message in self._log_entries:
            if self._should_show(level, filter_level):
                self._append_log_entry(timestamp, level, message)

    @Slot(bool)
    def _on_auto_scroll_toggled(self, checked: bool) -> None:
        """Handle auto-scroll toggle."""
        self._auto_scroll = checked

    @Slot()
    def clear(self) -> None:
        """Clear all log entries."""
        self._log_entries.clear()
        self._log_display.clear()

    @Slot()
    def _export_logs(self) -> None:
        """Export logs to a file."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Logs",
            f"macro_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )

        if path:
            try:
                with open(path, "w") as f:
                    for timestamp, level, message in self._log_entries:
                        f.write(
                            f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] "
                            f"[{level}] {message}\n"
                        )
                self.log(f"Logs exported to: {path}", "INFO")
            except Exception as e:
                self.log(f"Failed to export logs: {e}", "ERROR")

    def get_logs(self, level: str | None = None) -> list[str]:
        """
        Get log entries as strings.

        Args:
            level: Optional level filter

        Returns:
            List of log entry strings
        """
        result = []
        for timestamp, entry_level, message in self._log_entries:
            if level is None or entry_level == level.upper():
                result.append(
                    f"[{timestamp.strftime('%H:%M:%S')}] [{entry_level}] {message}"
                )
        return result


class LogWidgetHandler(logging.Handler):
    """Logging handler that sends logs to a LogWidget."""

    def __init__(self, widget: LogWidget) -> None:
        """
        Initialize the handler.

        Args:
            widget: LogWidget to send logs to
        """
        super().__init__()
        self._widget = widget

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record."""
        try:
            msg = self.format(record)
            self._widget.log(msg, record.levelname)
        except Exception:
            self.handleError(record)
