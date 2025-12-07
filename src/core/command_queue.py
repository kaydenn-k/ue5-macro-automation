"""
Command Queue System for UE5 Macro Automation.

Provides a priority-based queue system for batch operations with support for
command dependencies, cancellation, and status tracking.

Example Usage:
    >>> queue = CommandQueue()
    >>> cmd = Command(
    ...     name="import_asset",
    ...     func=import_fbx,
    ...     args=("/path/to/model.fbx",),
    ...     priority=CommandPriority.HIGH
    ... )
    >>> queue.enqueue(cmd)
    >>> queue.process_all()
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from queue import PriorityQueue
from typing import Any, Callable

logger = logging.getLogger(__name__)


class CommandStatus(Enum):
    """Status of a command in the queue."""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    SKIPPED = auto()


class CommandPriority(Enum):
    """Priority levels for commands."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class CommandResult:
    """Result of a command execution."""
    success: bool
    data: Any = None
    error: str | None = None
    execution_time: float = 0.0


@dataclass(order=True)
class Command:
    """
    Represents a single command to be executed.

    Attributes:
        name: Human-readable name for the command
        func: The callable to execute
        args: Positional arguments for the function
        kwargs: Keyword arguments for the function
        priority: Execution priority
        dependencies: List of command IDs that must complete first
        timeout: Maximum execution time in seconds
        retries: Number of retry attempts on failure
        on_success: Callback for successful execution
        on_failure: Callback for failed execution

    Example:
        >>> def my_func(path: str, optimize: bool = True) -> bool:
        ...     return True
        >>> cmd = Command(
        ...     name="process_asset",
        ...     func=my_func,
        ...     args=("/path/to/asset",),
        ...     kwargs={"optimize": False},
        ...     priority=CommandPriority.HIGH
        ... )
    """
    priority: CommandPriority = field(compare=True)
    name: str = field(compare=False)
    func: Callable[..., Any] = field(compare=False)
    args: tuple[Any, ...] = field(default_factory=tuple, compare=False)
    kwargs: dict[str, Any] = field(default_factory=dict, compare=False)
    id: str = field(default_factory=lambda: str(uuid.uuid4()), compare=False)
    dependencies: list[str] = field(default_factory=list, compare=False)
    timeout: float | None = field(default=None, compare=False)
    retries: int = field(default=0, compare=False)
    on_success: Callable[[CommandResult], None] | None = field(default=None, compare=False)
    on_failure: Callable[[CommandResult], None] | None = field(default=None, compare=False)
    status: CommandStatus = field(default=CommandStatus.PENDING, compare=False)
    result: CommandResult | None = field(default=None, compare=False)
    created_at: float = field(default_factory=time.time, compare=False)

    def __post_init__(self) -> None:
        """Ensure priority is used for comparison."""
        if isinstance(self.priority, CommandPriority):
            self._sort_key = self.priority.value
        else:
            self._sort_key = self.priority

    def __lt__(self, other: Command) -> bool:
        """Compare commands by priority value."""
        return self._sort_key < other._sort_key


class CommandQueue:
    """
    Thread-safe priority queue for managing and executing commands.

    Features:
    - Priority-based execution
    - Dependency resolution
    - Cancellation support
    - Progress tracking
    - Event callbacks

    Example:
        >>> queue = CommandQueue()
        >>>
        >>> # Add commands
        >>> cmd1 = Command(name="step1", func=step1_func, priority=CommandPriority.HIGH)
        >>> cmd2 = Command(name="step2", func=step2_func, dependencies=[cmd1.id])
        >>>
        >>> queue.enqueue(cmd1)
        >>> queue.enqueue(cmd2)
        >>>
        >>> # Process all commands
        >>> results = queue.process_all()
    """

    def __init__(self, max_workers: int = 1) -> None:
        """
        Initialize the command queue.

        Args:
            max_workers: Maximum number of concurrent workers (default: 1 for Unreal safety)
        """
        self._queue: PriorityQueue[Command] = PriorityQueue()
        self._commands: dict[str, Command] = {}
        self._completed: dict[str, CommandResult] = {}
        self._lock = threading.RLock()
        self._max_workers = max_workers
        self._is_processing = False
        self._should_stop = False
        self._on_progress: Callable[[int, int, str], None] | None = None
        self._on_command_complete: Callable[[Command, CommandResult], None] | None = None

    @property
    def size(self) -> int:
        """Return the number of pending commands."""
        with self._lock:
            return self._queue.qsize()

    @property
    def is_empty(self) -> bool:
        """Check if the queue is empty."""
        return self.size == 0

    @property
    def is_processing(self) -> bool:
        """Check if the queue is currently processing."""
        return self._is_processing

    def set_progress_callback(
        self, callback: Callable[[int, int, str], None]
    ) -> None:
        """
        Set callback for progress updates.

        Args:
            callback: Function(current, total, message) called on progress
        """
        self._on_progress = callback

    def set_completion_callback(
        self, callback: Callable[[Command, CommandResult], None]
    ) -> None:
        """
        Set callback for command completion.

        Args:
            callback: Function(command, result) called when command completes
        """
        self._on_command_complete = callback

    def enqueue(self, command: Command) -> str:
        """
        Add a command to the queue.

        Args:
            command: The command to add

        Returns:
            The command ID

        Example:
            >>> cmd = Command(name="test", func=lambda: print("Hello"))
            >>> cmd_id = queue.enqueue(cmd)
        """
        with self._lock:
            self._commands[command.id] = command
            self._queue.put(command)
            logger.debug(f"Enqueued command: {command.name} (ID: {command.id})")
        return command.id

    def enqueue_batch(self, commands: list[Command]) -> list[str]:
        """
        Add multiple commands to the queue.

        Args:
            commands: List of commands to add

        Returns:
            List of command IDs
        """
        return [self.enqueue(cmd) for cmd in commands]

    def cancel(self, command_id: str) -> bool:
        """
        Cancel a pending command.

        Args:
            command_id: ID of the command to cancel

        Returns:
            True if cancelled, False if not found or already executed
        """
        with self._lock:
            if command_id in self._commands:
                cmd = self._commands[command_id]
                if cmd.status == CommandStatus.PENDING:
                    cmd.status = CommandStatus.CANCELLED
                    logger.info(f"Cancelled command: {cmd.name}")
                    return True
        return False

    def cancel_all(self) -> int:
        """
        Cancel all pending commands.

        Returns:
            Number of commands cancelled
        """
        cancelled = 0
        with self._lock:
            for cmd in self._commands.values():
                if cmd.status == CommandStatus.PENDING:
                    cmd.status = CommandStatus.CANCELLED
                    cancelled += 1
        logger.info(f"Cancelled {cancelled} commands")
        return cancelled

    def stop(self) -> None:
        """Signal the queue to stop processing after current command."""
        self._should_stop = True
        logger.info("Queue stop requested")

    def get_command(self, command_id: str) -> Command | None:
        """
        Get a command by ID.

        Args:
            command_id: The command ID

        Returns:
            The command or None if not found
        """
        return self._commands.get(command_id)

    def get_status(self, command_id: str) -> CommandStatus | None:
        """
        Get the status of a command.

        Args:
            command_id: The command ID

        Returns:
            The command status or None if not found
        """
        cmd = self.get_command(command_id)
        return cmd.status if cmd else None

    def _check_dependencies(self, command: Command) -> bool:
        """Check if all dependencies are satisfied."""
        for dep_id in command.dependencies:
            if dep_id not in self._completed:
                return False
            if not self._completed[dep_id].success:
                return False
        return True

    def _execute_command(self, command: Command) -> CommandResult:
        """Execute a single command with error handling."""
        start_time = time.time()

        if command.status == CommandStatus.CANCELLED:
            return CommandResult(success=False, error="Command was cancelled")

        if not self._check_dependencies(command):
            command.status = CommandStatus.SKIPPED
            return CommandResult(
                success=False,
                error="Dependencies not satisfied"
            )

        command.status = CommandStatus.RUNNING
        attempts = 0
        max_attempts = command.retries + 1
        last_error: str | None = None

        while attempts < max_attempts:
            try:
                logger.debug(f"Executing command: {command.name} (attempt {attempts + 1})")
                result_data = command.func(*command.args, **command.kwargs)
                execution_time = time.time() - start_time

                result = CommandResult(
                    success=True,
                    data=result_data,
                    execution_time=execution_time
                )
                command.status = CommandStatus.COMPLETED
                command.result = result

                if command.on_success:
                    command.on_success(result)

                return result

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Command {command.name} failed (attempt {attempts + 1}): {last_error}"
                )
                attempts += 1

        execution_time = time.time() - start_time
        result = CommandResult(
            success=False,
            error=last_error,
            execution_time=execution_time
        )
        command.status = CommandStatus.FAILED
        command.result = result

        if command.on_failure:
            command.on_failure(result)

        return result

    def process_next(self) -> CommandResult | None:
        """
        Process the next command in the queue.

        Returns:
            The result of the command or None if queue is empty
        """
        if self._queue.empty():
            return None

        with self._lock:
            command = self._queue.get()

        result = self._execute_command(command)

        with self._lock:
            self._completed[command.id] = result

        if self._on_command_complete:
            self._on_command_complete(command, result)

        return result

    def process_all(self) -> dict[str, CommandResult]:
        """
        Process all commands in the queue.

        Returns:
            Dictionary mapping command IDs to their results

        Example:
            >>> results = queue.process_all()
            >>> for cmd_id, result in results.items():
            ...     print(f"{cmd_id}: {'Success' if result.success else 'Failed'}")
        """
        self._is_processing = True
        self._should_stop = False
        results: dict[str, CommandResult] = {}

        total = self.size
        processed = 0

        try:
            while not self._queue.empty() and not self._should_stop:
                with self._lock:
                    if self._queue.empty():
                        break
                    command = self._queue.get()

                if self._on_progress:
                    self._on_progress(processed, total, f"Processing: {command.name}")

                result = self._execute_command(command)
                results[command.id] = result

                with self._lock:
                    self._completed[command.id] = result

                if self._on_command_complete:
                    self._on_command_complete(command, result)

                processed += 1

        finally:
            self._is_processing = False

        if self._on_progress:
            self._on_progress(processed, total, "Complete")

        logger.info(f"Processed {processed}/{total} commands")
        return results

    def clear(self) -> None:
        """Clear all pending commands from the queue."""
        with self._lock:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except Exception:
                    break
            self._commands.clear()
            self._completed.clear()
        logger.info("Queue cleared")

    def get_statistics(self) -> dict[str, Any]:
        """
        Get queue statistics.

        Returns:
            Dictionary with queue statistics
        """
        with self._lock:
            status_counts = dict.fromkeys(CommandStatus, 0)
            for cmd in self._commands.values():
                status_counts[cmd.status] += 1

            return {
                "total_commands": len(self._commands),
                "pending": status_counts[CommandStatus.PENDING],
                "running": status_counts[CommandStatus.RUNNING],
                "completed": status_counts[CommandStatus.COMPLETED],
                "failed": status_counts[CommandStatus.FAILED],
                "cancelled": status_counts[CommandStatus.CANCELLED],
                "skipped": status_counts[CommandStatus.SKIPPED],
                "is_processing": self._is_processing,
            }
