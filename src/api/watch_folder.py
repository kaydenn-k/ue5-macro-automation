"""
Watch Folder Automation for UE5 Macro Automation.

Provides automatic macro execution when files are added to watched folders.

Example Usage:
    >>> from src.api.watch_folder import WatchFolderAutomation
    >>> watcher = WatchFolderAutomation()
    >>> watcher.add_watch("/path/to/folder", "ImportTreeAssets")
    >>> watcher.start()
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from watchdog.events import (
    FileCreatedEvent,
    FileModifiedEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from src.core.macro_engine import MacroEngine

logger = logging.getLogger(__name__)


@dataclass
class WatchConfig:
    """
    Configuration for a watched folder.

    Attributes:
        path: Path to watch
        macro_name: Name of macro to execute
        patterns: File patterns to match (e.g., ["*.fbx", "*.obj"])
        recursive: Whether to watch subdirectories
        debounce_seconds: Debounce time for rapid file changes
        auto_import: Whether to auto-import detected files
        destination: Destination path for imports
    """
    path: str
    macro_name: str
    patterns: list[str] = field(default_factory=lambda: ["*"])
    recursive: bool = True
    debounce_seconds: float = 1.0
    auto_import: bool = True
    destination: str = "/Game/Imports"


class MacroFileHandler(FileSystemEventHandler):
    """File system event handler that triggers macros."""

    def __init__(
        self,
        config: WatchConfig,
        engine: MacroEngine,
        callback: Callable[[str, str], None] | None = None
    ) -> None:
        """
        Initialize the handler.

        Args:
            config: Watch configuration
            engine: MacroEngine instance
            callback: Optional callback for file events
        """
        super().__init__()
        self._config = config
        self._engine = engine
        self._callback = callback
        self._pending_files: dict[str, float] = {}
        self._processed_files: set[str] = set()
        self._lock = threading.Lock()

    def on_created(self, event: FileCreatedEvent) -> None:
        """Handle file created event."""
        if event.is_directory:
            return

        self._handle_file_event(event.src_path)

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modified event."""
        if event.is_directory:
            return

        self._handle_file_event(event.src_path)

    def _handle_file_event(self, file_path: str) -> None:
        """Handle a file event with debouncing."""
        if not self._matches_patterns(file_path):
            return

        with self._lock:
            self._pending_files[file_path] = time.time()

        threading.Timer(
            self._config.debounce_seconds,
            self._process_pending_file,
            args=[file_path]
        ).start()

    def _matches_patterns(self, file_path: str) -> bool:
        """Check if file matches configured patterns."""
        import fnmatch

        filename = Path(file_path).name

        for pattern in self._config.patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True

        return False

    def _process_pending_file(self, file_path: str) -> None:
        """Process a pending file after debounce."""
        with self._lock:
            if file_path not in self._pending_files:
                return

            pending_time = self._pending_files[file_path]
            current_time = time.time()

            if current_time - pending_time < self._config.debounce_seconds:
                return

            del self._pending_files[file_path]

            if file_path in self._processed_files:
                return

            self._processed_files.add(file_path)

        logger.info(f"Processing file: {file_path}")

        if self._callback:
            self._callback(file_path, self._config.macro_name)

        try:
            if self._config.auto_import:
                self._auto_import_file(file_path)
            else:
                self._engine.execute_macro(
                    self._config.macro_name,
                    context={"file_path": file_path}
                )
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")

    def _auto_import_file(self, file_path: str) -> None:
        """Auto-import a file."""
        from src.macros.asset_import import ImportOptions, import_fbx, import_obj

        path = Path(file_path)
        ext = path.suffix.lower()

        options = ImportOptions(
            replace_existing=True,
            save_after_import=True,
        )

        if ext == ".fbx":
            import_fbx(file_path, self._config.destination, options)
        elif ext == ".obj":
            import_obj(file_path, self._config.destination, options)
        else:
            logger.warning(f"Unsupported file type: {ext}")


class WatchFolderAutomation:
    """
    Watch folder automation system.

    Monitors folders for new files and automatically executes macros.

    Example:
        >>> watcher = WatchFolderAutomation()
        >>> watcher.add_watch(
        ...     "/path/to/assets",
        ...     "ImportTreeAssets",
        ...     patterns=["*.fbx", "*.obj"]
        ... )
        >>> watcher.start()
        >>> # ... files are automatically processed ...
        >>> watcher.stop()
    """

    def __init__(self, engine: MacroEngine | None = None) -> None:
        """
        Initialize the watch folder automation.

        Args:
            engine: MacroEngine instance
        """
        self._engine = engine or MacroEngine()
        self._observer = Observer()
        self._watches: dict[str, WatchConfig] = {}
        self._handlers: dict[str, MacroFileHandler] = {}
        self._running = False
        self._file_callback: Callable[[str, str], None] | None = None

    def add_watch(
        self,
        path: str,
        macro_name: str,
        patterns: list[str] | None = None,
        recursive: bool = True,
        debounce_seconds: float = 1.0,
        auto_import: bool = True,
        destination: str = "/Game/Imports"
    ) -> bool:
        """
        Add a folder to watch.

        Args:
            path: Path to watch
            macro_name: Name of macro to execute
            patterns: File patterns to match
            recursive: Whether to watch subdirectories
            debounce_seconds: Debounce time
            auto_import: Whether to auto-import files
            destination: Destination for imports

        Returns:
            True if watch was added successfully
        """
        if path in self._watches:
            logger.warning(f"Path already being watched: {path}")
            return False

        if not Path(path).exists():
            logger.error(f"Path does not exist: {path}")
            return False

        config = WatchConfig(
            path=path,
            macro_name=macro_name,
            patterns=patterns or ["*"],
            recursive=recursive,
            debounce_seconds=debounce_seconds,
            auto_import=auto_import,
            destination=destination,
        )

        handler = MacroFileHandler(config, self._engine, self._file_callback)

        self._watches[path] = config
        self._handlers[path] = handler

        if self._running:
            self._observer.schedule(handler, path, recursive=recursive)

        logger.info(f"Added watch: {path} -> {macro_name}")
        return True

    def remove_watch(self, path: str) -> bool:
        """
        Remove a watched folder.

        Args:
            path: Path to stop watching

        Returns:
            True if watch was removed
        """
        if path not in self._watches:
            return False

        del self._watches[path]
        del self._handlers[path]

        logger.info(f"Removed watch: {path}")
        return True

    def start(self) -> None:
        """Start watching all configured folders."""
        if self._running:
            return

        self._engine.initialize()

        for path, config in self._watches.items():
            handler = self._handlers[path]
            self._observer.schedule(handler, path, recursive=config.recursive)

        self._observer.start()
        self._running = True

        logger.info(f"Started watching {len(self._watches)} folders")

    def stop(self) -> None:
        """Stop watching all folders."""
        if not self._running:
            return

        self._observer.stop()
        self._observer.join()

        self._running = False

        logger.info("Stopped watching folders")

    def set_file_callback(
        self,
        callback: Callable[[str, str], None]
    ) -> None:
        """
        Set callback for file events.

        Args:
            callback: Function called with (file_path, macro_name)
        """
        self._file_callback = callback

        for handler in self._handlers.values():
            handler._callback = callback

    def get_watches(self) -> list[dict[str, Any]]:
        """
        Get list of current watches.

        Returns:
            List of watch configurations
        """
        return [
            {
                "path": config.path,
                "macro_name": config.macro_name,
                "patterns": config.patterns,
                "recursive": config.recursive,
            }
            for config in self._watches.values()
        ]

    @property
    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._running

    def save_config(self, path: str) -> bool:
        """
        Save watch configuration to file.

        Args:
            path: Path to save configuration

        Returns:
            True if save was successful
        """
        import json

        try:
            config = {
                "watches": [
                    {
                        "path": c.path,
                        "macro_name": c.macro_name,
                        "patterns": c.patterns,
                        "recursive": c.recursive,
                        "debounce_seconds": c.debounce_seconds,
                        "auto_import": c.auto_import,
                        "destination": c.destination,
                    }
                    for c in self._watches.values()
                ]
            }

            with open(path, "w") as f:
                json.dump(config, f, indent=2)

            logger.info(f"Saved watch config to: {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def load_config(self, path: str) -> int:
        """
        Load watch configuration from file.

        Args:
            path: Path to load configuration from

        Returns:
            Number of watches loaded
        """
        import json

        try:
            with open(path) as f:
                config = json.load(f)

            loaded = 0
            for watch in config.get("watches", []):
                if self.add_watch(
                    watch["path"],
                    watch["macro_name"],
                    patterns=watch.get("patterns"),
                    recursive=watch.get("recursive", True),
                    debounce_seconds=watch.get("debounce_seconds", 1.0),
                    auto_import=watch.get("auto_import", True),
                    destination=watch.get("destination", "/Game/Imports"),
                ):
                    loaded += 1

            logger.info(f"Loaded {loaded} watches from: {path}")
            return loaded

        except FileNotFoundError:
            logger.warning(f"Config file not found: {path}")
            return 0
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return 0
