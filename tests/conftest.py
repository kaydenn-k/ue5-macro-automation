"""
Pytest configuration and fixtures for UE5 Macro Automation tests.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path.parent))


@pytest.fixture
def mock_unreal():
    """Mock the unreal module for testing without Unreal Engine."""
    mock = MagicMock()

    mock.Vector = MagicMock(return_value=MagicMock(x=0, y=0, z=0))
    mock.Rotator = MagicMock(return_value=MagicMock(pitch=0, yaw=0, roll=0))
    mock.LinearColor = MagicMock()

    mock.EditorLevelLibrary = MagicMock()
    mock.EditorLevelLibrary.get_all_level_actors.return_value = []
    mock.EditorLevelLibrary.spawn_actor_from_class.return_value = MagicMock()

    mock.EditorAssetLibrary = MagicMock()
    mock.EditorAssetLibrary.does_asset_exist.return_value = True
    mock.EditorAssetLibrary.list_assets.return_value = []

    mock.AssetImportTask = MagicMock()
    mock.AssetTools = MagicMock()

    with patch.dict(sys.modules, {"unreal": mock}):
        yield mock


@pytest.fixture
def temp_directory(tmp_path):
    """Create a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def sample_macro_data():
    """Sample macro data for testing."""
    return {
        "name": "Test Macro",
        "description": "A test macro",
        "actions": [
            {
                "action_type": "ASSET_IMPORT",
                "target_path": "/Game/Test",
                "parameters": {"source": "/path/to/file.fbx"},
            },
            {
                "action_type": "MATERIAL_ASSIGN",
                "target_path": "/Game/Test/Mesh",
                "parameters": {"material": "/Game/Materials/M_Test"},
            },
        ],
        "metadata": {"category": "import"},
    }


@pytest.fixture
def sample_command():
    """Sample command for testing."""
    from src.core.command_queue import Command, CommandPriority

    return Command(
        id="test-cmd-001",
        name="Test Command",
        action=lambda: True,
        priority=CommandPriority.NORMAL,
    )


@pytest.fixture
def sample_action():
    """Sample recorded action for testing."""
    from src.core.macro_recorder import ActionType, RecordedAction

    return RecordedAction(
        action_type=ActionType.ASSET_IMPORT,
        target_path="/Game/Test/Asset",
        parameters={"source": "/path/to/source.fbx"},
        description="Import test asset",
    )


@pytest.fixture
def macro_engine():
    """Create a MacroEngine instance for testing."""
    from src.core.macro_engine import MacroEngine

    engine = MacroEngine()
    engine.initialize()
    yield engine
    engine.shutdown()


@pytest.fixture
def command_queue():
    """Create a CommandQueue instance for testing."""
    from src.core.command_queue import CommandQueue

    queue = CommandQueue()
    yield queue
    queue.stop()


@pytest.fixture
def task_executor():
    """Create a TaskExecutor instance for testing."""
    from src.core.task_executor import TaskExecutor

    executor = TaskExecutor()
    yield executor


@pytest.fixture
def macro_recorder():
    """Create a MacroRecorder instance for testing."""
    from src.core.macro_recorder import MacroRecorder

    recorder = MacroRecorder()
    yield recorder
