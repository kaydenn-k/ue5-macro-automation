"""
Tests for the watch_folder module.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.api.watch_folder import (
    MacroFileHandler,
    WatchConfig,
    WatchFolderAutomation,
)


class TestWatchConfig:
    """Tests for the WatchConfig class."""

    def test_default_config(self):
        """Test default watch configuration."""
        config = WatchConfig(
            path="/path/to/watch",
            macro_name="TestMacro",
        )

        assert config.path == "/path/to/watch"
        assert config.macro_name == "TestMacro"
        assert config.patterns == ["*"]
        assert config.recursive is True
        assert config.debounce_seconds == 1.0

    def test_custom_config(self):
        """Test custom watch configuration."""
        config = WatchConfig(
            path="/path/to/watch",
            macro_name="TestMacro",
            patterns=["*.fbx", "*.obj"],
            recursive=False,
            debounce_seconds=2.0,
        )

        assert config.patterns == ["*.fbx", "*.obj"]
        assert config.recursive is False
        assert config.debounce_seconds == 2.0


class TestMacroFileHandler:
    """Tests for the MacroFileHandler class."""

    @pytest.fixture
    def handler(self):
        """Create a MacroFileHandler instance."""
        config = WatchConfig(
            path="/path/to/watch",
            macro_name="TestMacro",
            patterns=["*.fbx"],
        )
        engine = MagicMock()
        return MacroFileHandler(config, engine)

    def test_handler_creation(self, handler):
        """Test creating a handler."""
        assert handler is not None

    def test_matches_patterns(self, handler):
        """Test pattern matching."""
        assert handler._matches_patterns("/path/to/file.fbx") is True
        assert handler._matches_patterns("/path/to/file.obj") is False

    def test_matches_wildcard(self):
        """Test wildcard pattern matching."""
        config = WatchConfig(
            path="/path/to/watch",
            macro_name="TestMacro",
            patterns=["*"],
        )
        engine = MagicMock()
        handler = MacroFileHandler(config, engine)

        assert handler._matches_patterns("/path/to/file.fbx") is True
        assert handler._matches_patterns("/path/to/file.txt") is True


class TestWatchFolderAutomation:
    """Tests for the WatchFolderAutomation class."""

    @pytest.fixture
    def watcher(self):
        """Create a WatchFolderAutomation instance."""
        with patch("src.api.watch_folder.MacroEngine"):
            watcher = WatchFolderAutomation()
            yield watcher
            if watcher.is_running:
                watcher.stop()

    def test_watcher_creation(self, watcher):
        """Test creating a watcher."""
        assert watcher is not None
        assert not watcher.is_running

    def test_add_watch(self, watcher, temp_directory):
        """Test adding a watch."""
        result = watcher.add_watch(
            str(temp_directory),
            "TestMacro",
            patterns=["*.fbx"],
        )

        assert result is True
        assert len(watcher.get_watches()) == 1

    def test_add_watch_nonexistent_path(self, watcher):
        """Test adding a watch for nonexistent path."""
        result = watcher.add_watch(
            "/nonexistent/path",
            "TestMacro",
        )

        assert result is False

    def test_add_duplicate_watch(self, watcher, temp_directory):
        """Test adding duplicate watch."""
        watcher.add_watch(str(temp_directory), "Macro1")
        result = watcher.add_watch(str(temp_directory), "Macro2")

        assert result is False

    def test_remove_watch(self, watcher, temp_directory):
        """Test removing a watch."""
        watcher.add_watch(str(temp_directory), "TestMacro")

        result = watcher.remove_watch(str(temp_directory))

        assert result is True
        assert len(watcher.get_watches()) == 0

    def test_remove_nonexistent_watch(self, watcher):
        """Test removing a nonexistent watch."""
        result = watcher.remove_watch("/nonexistent/path")

        assert result is False

    def test_start_stop(self, watcher, temp_directory):
        """Test starting and stopping the watcher."""
        watcher.add_watch(str(temp_directory), "TestMacro")

        watcher.start()
        assert watcher.is_running

        watcher.stop()
        assert not watcher.is_running

    def test_get_watches(self, watcher, temp_directory):
        """Test getting watches."""
        watcher.add_watch(
            str(temp_directory),
            "TestMacro",
            patterns=["*.fbx"],
        )

        watches = watcher.get_watches()

        assert len(watches) == 1
        assert watches[0]["macro_name"] == "TestMacro"
        assert watches[0]["patterns"] == ["*.fbx"]

    def test_set_file_callback(self, watcher, temp_directory):
        """Test setting file callback."""
        callback_called = []

        def callback(file_path, macro_name):
            callback_called.append((file_path, macro_name))

        watcher.add_watch(str(temp_directory), "TestMacro")
        watcher.set_file_callback(callback)

        assert watcher._file_callback is not None

    def test_save_load_config(self, watcher, temp_directory):
        """Test saving and loading configuration."""
        watcher.add_watch(
            str(temp_directory),
            "TestMacro",
            patterns=["*.fbx"],
        )

        config_file = temp_directory / "watch_config.json"
        watcher.save_config(str(config_file))

        assert config_file.exists()

        new_watcher = WatchFolderAutomation()
        loaded = new_watcher.load_config(str(config_file))

        assert loaded == 1
        assert len(new_watcher.get_watches()) == 1
