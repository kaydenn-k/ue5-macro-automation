"""
Progress Widget for UE5 Macro Automation.

Provides progress tracking display for long-running operations.

Example Usage:
    >>> from src.ui.progress_widget import ProgressWidget
    >>> progress = ProgressWidget()
    >>> progress.set_progress(0.5, "Processing...")
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class ProgressWidget(QWidget):
    """
    Widget for displaying operation progress.

    Provides:
    - Progress bar with percentage
    - Current operation label
    - Elapsed time display
    - Cancel button

    Signals:
        cancel_requested: Emitted when cancel is clicked
    """

    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the progress widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self._elapsed_seconds = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_elapsed)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        group = QGroupBox("Progress")
        group_layout = QVBoxLayout(group)

        self._operation_label = QLabel("Ready")
        self._operation_label.setWordWrap(True)
        group_layout.addWidget(self._operation_label)

        progress_layout = QHBoxLayout()

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        progress_layout.addWidget(self._progress_bar)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.setFixedWidth(80)
        self._cancel_btn.clicked.connect(self._on_cancel)
        progress_layout.addWidget(self._cancel_btn)

        group_layout.addLayout(progress_layout)

        info_layout = QHBoxLayout()

        self._elapsed_label = QLabel("Elapsed: 0:00")
        info_layout.addWidget(self._elapsed_label)

        info_layout.addStretch()

        self._eta_label = QLabel("ETA: --:--")
        info_layout.addWidget(self._eta_label)

        group_layout.addLayout(info_layout)

        layout.addWidget(group)

    def set_progress(self, progress: float, message: str = "") -> None:
        """
        Set the current progress.

        Args:
            progress: Progress value between 0.0 and 1.0
            message: Optional status message
        """
        percentage = int(progress * 100)
        self._progress_bar.setValue(percentage)

        if message:
            self._operation_label.setText(message)

        if progress > 0 and progress < 1:
            if not self._timer.isActive():
                self._elapsed_seconds = 0
                self._timer.start(1000)
            self._cancel_btn.setEnabled(True)

            if progress > 0.01:
                eta_seconds = int(
                    (self._elapsed_seconds / progress) * (1 - progress)
                )
                self._eta_label.setText(f"ETA: {self._format_time(eta_seconds)}")
        else:
            self._timer.stop()
            self._cancel_btn.setEnabled(False)
            self._eta_label.setText("ETA: --:--")

            if progress >= 1:
                self._operation_label.setText("Complete")

    def reset(self) -> None:
        """Reset the progress display."""
        self._progress_bar.setValue(0)
        self._operation_label.setText("Ready")
        self._elapsed_label.setText("Elapsed: 0:00")
        self._eta_label.setText("ETA: --:--")
        self._elapsed_seconds = 0
        self._timer.stop()
        self._cancel_btn.setEnabled(False)

    def start_indeterminate(self, message: str = "Processing...") -> None:
        """
        Start indeterminate progress mode.

        Args:
            message: Status message to display
        """
        self._progress_bar.setRange(0, 0)
        self._operation_label.setText(message)
        self._cancel_btn.setEnabled(True)
        self._elapsed_seconds = 0
        self._timer.start(1000)

    def stop_indeterminate(self) -> None:
        """Stop indeterminate progress mode."""
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._timer.stop()
        self._cancel_btn.setEnabled(False)

    @Slot()
    def _update_elapsed(self) -> None:
        """Update the elapsed time display."""
        self._elapsed_seconds += 1
        self._elapsed_label.setText(
            f"Elapsed: {self._format_time(self._elapsed_seconds)}"
        )

    @Slot()
    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        self._cancel_btn.setEnabled(False)
        self._operation_label.setText("Cancelling...")
        self.cancel_requested.emit()

    @staticmethod
    def _format_time(seconds: int) -> str:
        """Format seconds as MM:SS or HH:MM:SS."""
        if seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}:{secs:02d}"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours}:{minutes:02d}:{secs:02d}"


class MultiProgressWidget(QWidget):
    """
    Widget for displaying multiple concurrent progress bars.

    Useful for batch operations where multiple tasks run in parallel.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the multi-progress widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self._progress_bars: dict[str, tuple[QLabel, QProgressBar]] = {}

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)

        group = QGroupBox("Batch Progress")
        self._group_layout = QVBoxLayout(group)

        self._overall_label = QLabel("Overall Progress")
        self._group_layout.addWidget(self._overall_label)

        self._overall_progress = QProgressBar()
        self._overall_progress.setRange(0, 100)
        self._overall_progress.setValue(0)
        self._group_layout.addWidget(self._overall_progress)

        self._separator = QFrame()
        self._separator.setFrameShape(QFrame.Shape.HLine)
        self._separator.setFrameShadow(QFrame.Shadow.Sunken)
        self._group_layout.addWidget(self._separator)

        self._layout.addWidget(group)

    def add_task(self, task_id: str, label: str) -> None:
        """
        Add a new task progress bar.

        Args:
            task_id: Unique task identifier
            label: Display label for the task
        """
        if task_id in self._progress_bars:
            return

        task_label = QLabel(label)
        task_progress = QProgressBar()
        task_progress.setRange(0, 100)
        task_progress.setValue(0)

        self._group_layout.addWidget(task_label)
        self._group_layout.addWidget(task_progress)

        self._progress_bars[task_id] = (task_label, task_progress)

    def update_task(self, task_id: str, progress: float, label: str = "") -> None:
        """
        Update a task's progress.

        Args:
            task_id: Task identifier
            progress: Progress value between 0.0 and 1.0
            label: Optional new label
        """
        if task_id not in self._progress_bars:
            return

        task_label, task_progress = self._progress_bars[task_id]
        task_progress.setValue(int(progress * 100))

        if label:
            task_label.setText(label)

        self._update_overall()

    def remove_task(self, task_id: str) -> None:
        """
        Remove a task progress bar.

        Args:
            task_id: Task identifier
        """
        if task_id not in self._progress_bars:
            return

        task_label, task_progress = self._progress_bars[task_id]

        self._group_layout.removeWidget(task_label)
        self._group_layout.removeWidget(task_progress)

        task_label.deleteLater()
        task_progress.deleteLater()

        del self._progress_bars[task_id]

        self._update_overall()

    def clear_all(self) -> None:
        """Remove all task progress bars."""
        for task_id in list(self._progress_bars.keys()):
            self.remove_task(task_id)

        self._overall_progress.setValue(0)

    def _update_overall(self) -> None:
        """Update the overall progress bar."""
        if not self._progress_bars:
            self._overall_progress.setValue(0)
            return

        total = sum(
            progress.value()
            for _, progress in self._progress_bars.values()
        )
        average = total / len(self._progress_bars)
        self._overall_progress.setValue(int(average))
