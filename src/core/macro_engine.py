"""
Macro Engine for UE5 Macro Automation.

The main engine that coordinates all components of the macro automation system.
Provides a unified interface for recording, replaying, and managing macros.

Example Usage:
    >>> engine = MacroEngine()
    >>> engine.initialize()
    >>>
    >>> # Load and execute a macro
    >>> engine.load_macro("/path/to/macro.json")
    >>> engine.execute_macro("my_macro")
    >>>
    >>> # Or use the quick execute
    >>> engine.quick_execute("/path/to/macro.json")
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from src.core.command_queue import Command, CommandPriority, CommandQueue, CommandResult
from src.core.macro_recorder import Macro, MacroRecorder, RecordedAction
from src.core.rollback import RollbackAction, RollbackManager
from src.core.task_executor import AsyncTaskExecutor, TaskConfig, TaskExecutor, TaskResult

logger = logging.getLogger(__name__)


@dataclass
class MacroExecutionResult:
    """Result of a macro execution."""
    success: bool
    macro_name: str
    total_actions: int = 0
    executed_actions: int = 0
    failed_actions: int = 0
    execution_time: float = 0.0
    errors: list[str] = field(default_factory=list)
    rollback_available: bool = False


@dataclass
class EngineConfig:
    """
    Configuration for the macro engine.

    Attributes:
        macro_library_path: Path to the macro library directory
        auto_save: Whether to auto-save macros after recording
        enable_rollback: Whether to enable rollback functionality
        max_rollback_steps: Maximum number of rollback steps to keep
        default_timeout: Default timeout for operations
        log_level: Logging level
    """
    macro_library_path: str = "./macros"
    auto_save: bool = True
    enable_rollback: bool = True
    max_rollback_steps: int = 50
    default_timeout: float = 60.0
    log_level: str = "INFO"


class MacroEngine:
    """
    Main engine for the UE5 Macro Automation System.

    Coordinates all components and provides a unified interface for:
    - Recording and replaying macros
    - Managing the macro library
    - Executing commands and tasks
    - Handling rollback operations

    Example:
        >>> engine = MacroEngine(EngineConfig(
        ...     macro_library_path="./my_macros",
        ...     enable_rollback=True
        ... ))
        >>> engine.initialize()
        >>>
        >>> # Record a macro
        >>> engine.start_recording("My Macro")
        >>> # ... perform actions ...
        >>> engine.stop_recording()
        >>>
        >>> # Execute a macro
        >>> result = engine.execute_macro("My Macro")
        >>> print(f"Success: {result.success}")
    """

    _instance: MacroEngine | None = None
    _lock = threading.Lock()

    def __new__(cls, config: EngineConfig | None = None) -> MacroEngine:
        """Singleton pattern for the engine."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, config: EngineConfig | None = None) -> None:
        """
        Initialize the macro engine.

        Args:
            config: Engine configuration
        """
        if self._initialized:
            return

        self._config = config or EngineConfig()
        self._command_queue = CommandQueue()
        self._task_executor = TaskExecutor()
        self._async_executor = AsyncTaskExecutor()
        self._macro_recorder = MacroRecorder()
        self._rollback_manager = RollbackManager(
            max_steps=self._config.max_rollback_steps
        )

        self._macro_library: dict[str, Macro] = {}
        self._hotkey_bindings: dict[str, str] = {}
        self._is_running = False

        self._on_progress: Callable[[float, str], None] | None = None
        self._on_macro_complete: Callable[[MacroExecutionResult], None] | None = None
        self._on_error: Callable[[str], None] | None = None

        self._setup_logging()
        self._initialized = True

    def _setup_logging(self) -> None:
        """Configure logging based on config."""
        logging.basicConfig(
            level=getattr(logging, self._config.log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    @classmethod
    def get_instance(cls) -> MacroEngine | None:
        """Get the singleton instance."""
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        with cls._lock:
            cls._instance = None

    @property
    def config(self) -> EngineConfig:
        """Get the engine configuration."""
        return self._config

    @property
    def is_recording(self) -> bool:
        """Check if currently recording a macro."""
        return self._macro_recorder.is_recording

    @property
    def is_running(self) -> bool:
        """Check if the engine is running."""
        return self._is_running

    @property
    def macro_library(self) -> dict[str, Macro]:
        """Get the loaded macro library."""
        return self._macro_library.copy()

    def set_progress_callback(self, callback: Callable[[float, str], None]) -> None:
        """Set callback for progress updates."""
        self._on_progress = callback

    def set_completion_callback(
        self, callback: Callable[[MacroExecutionResult], None]
    ) -> None:
        """Set callback for macro completion."""
        self._on_macro_complete = callback

    def set_error_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for errors."""
        self._on_error = callback

    def initialize(self) -> bool:
        """
        Initialize the engine and load the macro library.

        Returns:
            True if initialization was successful
        """
        try:
            library_path = Path(self._config.macro_library_path)
            library_path.mkdir(parents=True, exist_ok=True)

            self._load_macro_library()

            self._is_running = True
            logger.info("MacroEngine initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize MacroEngine: {e}")
            if self._on_error:
                self._on_error(str(e))
            return False

    def shutdown(self) -> None:
        """Shutdown the engine and cleanup resources."""
        self._is_running = False
        self._async_executor.shutdown(wait=True)
        self._command_queue.cancel_all()
        logger.info("MacroEngine shutdown complete")

    def _load_macro_library(self) -> None:
        """Load all macros from the library directory."""
        library_path = Path(self._config.macro_library_path)

        for macro_file in library_path.glob("*.json"):
            try:
                macro = self._macro_recorder.load_macro(macro_file)
                if macro:
                    self._macro_library[macro.name] = macro

                    if macro.hotkey:
                        self._hotkey_bindings[macro.hotkey] = macro.name

            except Exception as e:
                logger.warning(f"Failed to load macro {macro_file}: {e}")

        logger.info(f"Loaded {len(self._macro_library)} macros from library")

    def reload_library(self) -> int:
        """
        Reload the macro library from disk.

        Returns:
            Number of macros loaded
        """
        self._macro_library.clear()
        self._hotkey_bindings.clear()
        self._load_macro_library()
        return len(self._macro_library)

    def start_recording(
        self,
        name: str,
        description: str = "",
        author: str = "",
        tags: list[str] | None = None
    ) -> None:
        """
        Start recording a new macro.

        Args:
            name: Name for the macro
            description: Description of the macro
            author: Author name
            tags: Tags for categorization
        """
        if self._config.enable_rollback:
            self._rollback_manager.clear()

        self._macro_recorder.start_recording(name, description, author, tags)
        logger.info(f"Started recording macro: {name}")

    def stop_recording(self, save: bool = True) -> Macro | None:
        """
        Stop recording and optionally save the macro.

        Args:
            save: Whether to save the macro to the library

        Returns:
            The recorded macro
        """
        macro = self._macro_recorder.stop_recording()

        if macro and save and self._config.auto_save:
            self.save_macro(macro)

        return macro

    def record_action(self, action: RecordedAction) -> None:
        """
        Record an action to the current macro.

        Args:
            action: The action to record
        """
        self._macro_recorder.record_action(action)

        if self._config.enable_rollback:
            rollback_action = self._create_rollback_action(action)
            if rollback_action:
                self._rollback_manager.push(rollback_action)

    def _create_rollback_action(self, action: RecordedAction) -> RollbackAction | None:
        """Create a rollback action for the given action."""
        return RollbackAction(
            action_type=action.action_type.name,
            target=action.target,
            original_state=action.parameters.copy(),
            description=f"Undo {action.action_type.name} on {action.target}"
        )

    def save_macro(
        self,
        macro: Macro | None = None,
        filename: str | None = None
    ) -> bool:
        """
        Save a macro to the library.

        Args:
            macro: Macro to save (uses current if None)
            filename: Custom filename (uses macro name if None)

        Returns:
            True if saved successfully
        """
        macro = macro or self._macro_recorder.current_macro
        if not macro:
            logger.error("No macro to save")
            return False

        filename = filename or f"{macro.name.replace(' ', '_').lower()}.json"
        path = Path(self._config.macro_library_path) / filename

        if self._macro_recorder.save_macro(path, macro):
            self._macro_library[macro.name] = macro

            if macro.hotkey:
                self._hotkey_bindings[macro.hotkey] = macro.name

            return True

        return False

    def load_macro(self, path: str | Path) -> Macro | None:
        """
        Load a macro from a file.

        Args:
            path: Path to the macro file

        Returns:
            The loaded macro
        """
        macro = self._macro_recorder.load_macro(path)

        if macro:
            self._macro_library[macro.name] = macro

            if macro.hotkey:
                self._hotkey_bindings[macro.hotkey] = macro.name

        return macro

    def get_macro(self, name: str) -> Macro | None:
        """
        Get a macro by name.

        Args:
            name: Macro name

        Returns:
            The macro or None if not found
        """
        return self._macro_library.get(name)

    def delete_macro(self, name: str, delete_file: bool = True) -> bool:
        """
        Delete a macro from the library.

        Args:
            name: Macro name
            delete_file: Whether to delete the file from disk

        Returns:
            True if deleted successfully
        """
        if name not in self._macro_library:
            return False

        macro = self._macro_library[name]

        if macro.hotkey and macro.hotkey in self._hotkey_bindings:
            del self._hotkey_bindings[macro.hotkey]

        del self._macro_library[name]

        if delete_file:
            filename = f"{name.replace(' ', '_').lower()}.json"
            path = Path(self._config.macro_library_path) / filename
            if path.exists():
                path.unlink()

        logger.info(f"Deleted macro: {name}")
        return True

    def execute_macro(
        self,
        name: str,
        dry_run: bool = False,
        stop_on_error: bool = True
    ) -> MacroExecutionResult:
        """
        Execute a macro by name.

        Args:
            name: Macro name
            dry_run: If True, only simulate without executing
            stop_on_error: Stop execution on first error

        Returns:
            MacroExecutionResult with execution details
        """
        macro = self.get_macro(name)
        if not macro:
            return MacroExecutionResult(
                success=False,
                macro_name=name,
                errors=[f"Macro not found: {name}"]
            )

        return self._execute_macro_impl(macro, dry_run, stop_on_error)

    def quick_execute(
        self,
        path: str | Path,
        dry_run: bool = False
    ) -> MacroExecutionResult:
        """
        Load and execute a macro from a file.

        Args:
            path: Path to the macro file
            dry_run: If True, only simulate without executing

        Returns:
            MacroExecutionResult with execution details
        """
        macro = self.load_macro(path)
        if not macro:
            return MacroExecutionResult(
                success=False,
                macro_name=str(path),
                errors=[f"Failed to load macro: {path}"]
            )

        return self._execute_macro_impl(macro, dry_run, False)

    def _execute_macro_impl(
        self,
        macro: Macro,
        dry_run: bool,
        stop_on_error: bool
    ) -> MacroExecutionResult:
        """Internal implementation of macro execution."""
        start_time = time.time()

        if self._config.enable_rollback:
            self._rollback_manager.start_transaction()

        def progress_callback(current: int, total: int, message: str) -> None:
            if self._on_progress:
                progress = current / total if total > 0 else 0
                self._on_progress(progress, message)

        self._macro_recorder.set_replay_progress_callback(progress_callback)

        try:
            result = self._macro_recorder.replay(macro, dry_run, stop_on_error)

            execution_result = MacroExecutionResult(
                success=result.get("success", False),
                macro_name=macro.name,
                total_actions=result.get("total_actions", 0),
                executed_actions=result.get("executed", 0),
                failed_actions=result.get("failed", 0),
                execution_time=time.time() - start_time,
                errors=result.get("errors", []),
                rollback_available=self._config.enable_rollback
            )

            if self._config.enable_rollback:
                if execution_result.success:
                    self._rollback_manager.commit_transaction()
                else:
                    pass

            if self._on_macro_complete:
                self._on_macro_complete(execution_result)

            return execution_result

        except Exception as e:
            error_msg = f"Macro execution failed: {e}"
            logger.error(error_msg)

            if self._on_error:
                self._on_error(error_msg)

            return MacroExecutionResult(
                success=False,
                macro_name=macro.name,
                execution_time=time.time() - start_time,
                errors=[error_msg],
                rollback_available=self._config.enable_rollback
            )

    def execute_command(
        self,
        func: Callable[..., Any],
        *args: Any,
        priority: CommandPriority = CommandPriority.NORMAL,
        **kwargs: Any
    ) -> str:
        """
        Queue a command for execution.

        Args:
            func: Function to execute
            *args: Positional arguments
            priority: Command priority
            **kwargs: Keyword arguments

        Returns:
            Command ID
        """
        command = Command(
            name=func.__name__,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority
        )

        return self._command_queue.enqueue(command)

    def execute_task(
        self,
        func: Callable[..., Any],
        *args: Any,
        timeout: float | None = None,
        **kwargs: Any
    ) -> TaskResult[Any]:
        """
        Execute a task synchronously.

        Args:
            func: Function to execute
            *args: Positional arguments
            timeout: Timeout in seconds
            **kwargs: Keyword arguments

        Returns:
            TaskResult with execution result
        """
        config = TaskConfig(timeout=timeout or self._config.default_timeout)
        return self._task_executor.execute(func, *args, config=config, **kwargs)

    async def execute_task_async(
        self,
        func: Callable[..., Any],
        *args: Any,
        timeout: float | None = None,
        **kwargs: Any
    ) -> TaskResult[Any]:
        """
        Execute a task asynchronously.

        Args:
            func: Function to execute
            *args: Positional arguments
            timeout: Timeout in seconds
            **kwargs: Keyword arguments

        Returns:
            TaskResult with execution result
        """
        config = TaskConfig(timeout=timeout or self._config.default_timeout)
        return await self._async_executor.execute_async(
            func, *args, config=config, **kwargs
        )

    def process_queue(self) -> dict[str, CommandResult]:
        """
        Process all commands in the queue.

        Returns:
            Dictionary mapping command IDs to results
        """
        return self._command_queue.process_all()

    def undo(self) -> bool:
        """
        Undo the last action.

        Returns:
            True if undo was successful
        """
        if not self._config.enable_rollback:
            logger.warning("Rollback is disabled")
            return False

        return self._rollback_manager.undo()

    def redo(self) -> bool:
        """
        Redo the last undone action.

        Returns:
            True if redo was successful
        """
        if not self._config.enable_rollback:
            logger.warning("Rollback is disabled")
            return False

        return self._rollback_manager.redo()

    def rollback_all(self) -> int:
        """
        Rollback all actions in the current transaction.

        Returns:
            Number of actions rolled back
        """
        if not self._config.enable_rollback:
            logger.warning("Rollback is disabled")
            return 0

        return self._rollback_manager.rollback_transaction()

    def bind_hotkey(self, hotkey: str, macro_name: str) -> bool:
        """
        Bind a hotkey to a macro.

        Args:
            hotkey: Hotkey string (e.g., "Ctrl+Shift+M")
            macro_name: Name of the macro to bind

        Returns:
            True if binding was successful
        """
        if macro_name not in self._macro_library:
            logger.error(f"Macro not found: {macro_name}")
            return False

        if hotkey in self._hotkey_bindings:
            old_macro = self._hotkey_bindings[hotkey]
            logger.warning(f"Hotkey {hotkey} was bound to {old_macro}, rebinding to {macro_name}")

        self._hotkey_bindings[hotkey] = macro_name
        self._macro_library[macro_name].hotkey = hotkey

        self.save_macro(self._macro_library[macro_name])

        logger.info(f"Bound hotkey {hotkey} to macro {macro_name}")
        return True

    def unbind_hotkey(self, hotkey: str) -> bool:
        """
        Unbind a hotkey.

        Args:
            hotkey: Hotkey string to unbind

        Returns:
            True if unbinding was successful
        """
        if hotkey not in self._hotkey_bindings:
            return False

        macro_name = self._hotkey_bindings[hotkey]
        del self._hotkey_bindings[hotkey]

        if macro_name in self._macro_library:
            self._macro_library[macro_name].hotkey = None
            self.save_macro(self._macro_library[macro_name])

        logger.info(f"Unbound hotkey {hotkey}")
        return True

    def trigger_hotkey(self, hotkey: str) -> MacroExecutionResult | None:
        """
        Trigger a macro by hotkey.

        Args:
            hotkey: Hotkey string

        Returns:
            MacroExecutionResult or None if no macro bound
        """
        macro_name = self._hotkey_bindings.get(hotkey)
        if not macro_name:
            logger.debug(f"No macro bound to hotkey: {hotkey}")
            return None

        return self.execute_macro(macro_name)

    def get_statistics(self) -> dict[str, Any]:
        """
        Get engine statistics.

        Returns:
            Dictionary with engine statistics
        """
        return {
            "is_running": self._is_running,
            "is_recording": self.is_recording,
            "macros_loaded": len(self._macro_library),
            "hotkeys_bound": len(self._hotkey_bindings),
            "queue_stats": self._command_queue.get_statistics(),
            "rollback_available": self._rollback_manager.can_undo,
            "redo_available": self._rollback_manager.can_redo,
        }

    def list_macros(self) -> list[dict[str, Any]]:
        """
        List all macros in the library.

        Returns:
            List of macro information dictionaries
        """
        return [
            {
                "name": macro.name,
                "description": macro.description,
                "actions": len(macro.actions),
                "hotkey": macro.hotkey,
                "tags": macro.tags,
                "created_at": macro.created_at,
                "modified_at": macro.modified_at,
            }
            for macro in self._macro_library.values()
        ]
