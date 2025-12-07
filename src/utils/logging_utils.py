"""
Logging utilities for UE5 Macro Automation.

Provides logging configuration, progress tracking, and log formatting
for the macro automation system.

Example Usage:
    >>> setup_logging(level="DEBUG", log_file="macro.log")
    >>> logger = get_logger("my_module")
    >>> logger.info("Processing started")
    >>>
    >>> with ProgressTracker("Importing assets", total=100) as tracker:
    ...     for i in range(100):
    ...         tracker.update(1, f"Processing item {i}")
"""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable


class ColoredFormatter(logging.Formatter):
    """Colored log formatter for console output."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors."""
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class UnrealLogHandler(logging.Handler):
    """Log handler that outputs to Unreal's log system."""

    def __init__(self) -> None:
        """Initialize the Unreal log handler."""
        super().__init__()
        self._unreal_available = self._check_unreal()

    def _check_unreal(self) -> bool:
        """Check if Unreal is available."""
        try:
            import unreal  # noqa: F401
            return True
        except ImportError:
            return False

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to Unreal's log system."""
        if not self._unreal_available:
            return

        try:
            import unreal  # noqa: F401

            msg = self.format(record)

            if record.levelno >= logging.ERROR:
                unreal.log_error(msg)
            elif record.levelno >= logging.WARNING:
                unreal.log_warning(msg)
            else:
                unreal.log(msg)

        except Exception:
            pass


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    use_colors: bool = True,
    use_unreal_log: bool = True,
    format_string: str | None = None
) -> None:
    """
    Configure logging for the macro automation system.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        use_colors: Whether to use colored console output
        use_unreal_log: Whether to output to Unreal's log system
        format_string: Custom format string for log messages

    Example:
        >>> setup_logging(level="DEBUG", log_file="macro_debug.log")
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    root_logger.handlers.clear()

    format_string = format_string or "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))

    if use_colors:
        console_handler.setFormatter(ColoredFormatter(format_string))
    else:
        console_handler.setFormatter(logging.Formatter(format_string))

    root_logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(format_string))
        root_logger.addHandler(file_handler)

    if use_unreal_log:
        unreal_handler = UnrealLogHandler()
        unreal_handler.setLevel(getattr(logging, level.upper()))
        unreal_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
        root_logger.addHandler(unreal_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Module initialized")
    """
    return logging.getLogger(f"ue5_macro.{name}")


@dataclass
class ProgressTracker:
    """
    Track and report progress for long-running operations.

    Attributes:
        name: Name of the operation
        total: Total number of items to process
        current: Current progress
        start_time: When tracking started
        on_progress: Callback for progress updates

    Example:
        >>> tracker = ProgressTracker("Importing assets", total=100)
        >>> tracker.start()
        >>> for i in range(100):
        ...     # Do work
        ...     tracker.update(1, f"Processing {i}")
        >>> tracker.finish()
    """
    name: str
    total: int = 0
    current: int = 0
    start_time: float = field(default_factory=time.time)
    on_progress: Callable[[float, str], None] | None = None
    _logger: logging.Logger = field(default_factory=lambda: get_logger("progress"))

    def __enter__(self) -> ProgressTracker:
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        if exc_type is None:
            self.finish()
        else:
            self.fail(str(exc_val))

    def start(self) -> None:
        """Start progress tracking."""
        self.start_time = time.time()
        self.current = 0
        self._logger.info(f"Started: {self.name}")
        self._report_progress(f"Starting {self.name}")

    def update(self, increment: int = 1, message: str = "") -> None:
        """
        Update progress.

        Args:
            increment: Amount to increment progress by
            message: Optional status message
        """
        self.current += increment

        if self.total > 0:
            percentage = (self.current / self.total) * 100
            elapsed = time.time() - self.start_time

            if self.current > 0:
                eta = (elapsed / self.current) * (self.total - self.current)
                eta_str = f", ETA: {eta:.1f}s"
            else:
                eta_str = ""

            status = f"{self.name}: {percentage:.1f}% ({self.current}/{self.total}){eta_str}"

            if message:
                status += f" - {message}"

            self._report_progress(status)

    def set_total(self, total: int) -> None:
        """Set the total number of items."""
        self.total = total

    def finish(self) -> None:
        """Mark progress as complete."""
        elapsed = time.time() - self.start_time
        self._logger.info(f"Completed: {self.name} in {elapsed:.2f}s")
        self._report_progress(f"Completed: {self.name}")

    def fail(self, error: str) -> None:
        """Mark progress as failed."""
        elapsed = time.time() - self.start_time
        self._logger.error(f"Failed: {self.name} after {elapsed:.2f}s - {error}")
        self._report_progress(f"Failed: {self.name} - {error}")

    def _report_progress(self, message: str) -> None:
        """Report progress to callback and logger."""
        if self.on_progress:
            progress = self.current / self.total if self.total > 0 else 0
            self.on_progress(progress, message)

        if self.total > 0:
            percentage = (self.current / self.total) * 100
            self._logger.debug(f"[{percentage:.1f}%] {message}")


class LogCapture:
    """
    Capture log output for later retrieval.

    Example:
        >>> with LogCapture() as capture:
        ...     logger.info("Test message")
        >>> print(capture.get_logs())
    """

    def __init__(self, level: int = logging.DEBUG) -> None:
        """Initialize log capture."""
        self._level = level
        self._handler: logging.Handler | None = None
        self._logs: list[str] = []

    def __enter__(self) -> LogCapture:
        """Start capturing logs."""
        self._handler = logging.Handler()
        self._handler.setLevel(self._level)
        self._handler.emit = lambda record: self._logs.append(
            self._handler.format(record)
        )
        self._handler.setFormatter(logging.Formatter(
            "%(levelname)s - %(name)s - %(message)s"
        ))
        logging.getLogger().addHandler(self._handler)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Stop capturing logs."""
        if self._handler:
            logging.getLogger().removeHandler(self._handler)

    def get_logs(self) -> list[str]:
        """Get captured log messages."""
        return self._logs.copy()

    def clear(self) -> None:
        """Clear captured logs."""
        self._logs.clear()


@contextmanager
def log_operation(
    name: str,
    logger: logging.Logger | None = None
) -> Generator[None, None, None]:
    """
    Context manager for logging operation start/end.

    Args:
        name: Operation name
        logger: Logger to use (default: root logger)

    Example:
        >>> with log_operation("Import assets"):
        ...     # Do import
        ...     pass
    """
    logger = logger or logging.getLogger()
    start_time = time.time()

    logger.info(f"Starting: {name}")

    try:
        yield
        elapsed = time.time() - start_time
        logger.info(f"Completed: {name} ({elapsed:.2f}s)")
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Failed: {name} ({elapsed:.2f}s) - {e}")
        raise
