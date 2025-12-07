"""
Tests for the MacroRecorder module.
"""

import json

from src.core.macro_recorder import (
    ActionType,
    Macro,
    RecordedAction,
)


class TestRecordedAction:
    """Tests for the RecordedAction class."""

    def test_action_creation(self, sample_action):
        """Test creating a recorded action."""
        assert sample_action.action_type == ActionType.ASSET_IMPORT
        assert sample_action.target_path == "/Game/Test/Asset"
        assert "source" in sample_action.parameters

    def test_action_types(self):
        """Test all action types exist."""
        assert ActionType.ASSET_IMPORT is not None
        assert ActionType.ASSET_DELETE is not None
        assert ActionType.ACTOR_SPAWN is not None
        assert ActionType.MATERIAL_ASSIGN is not None
        assert ActionType.EDITOR_COMMAND is not None
        assert ActionType.PYTHON_EXEC is not None
        assert ActionType.CUSTOM is not None


class TestMacro:
    """Tests for the Macro class."""

    def test_macro_creation(self, sample_action):
        """Test creating a macro."""
        macro = Macro(
            name="Test Macro",
            actions=[sample_action],
            description="A test macro",
        )

        assert macro.name == "Test Macro"
        assert len(macro.actions) == 1
        assert macro.description == "A test macro"

    def test_macro_with_metadata(self, sample_action):
        """Test creating a macro with metadata."""
        macro = Macro(
            name="Test Macro",
            actions=[sample_action],
            metadata={"category": "import", "author": "test"},
        )

        assert macro.metadata["category"] == "import"
        assert macro.metadata["author"] == "test"


class TestMacroRecorder:
    """Tests for the MacroRecorder class."""

    def test_recorder_creation(self, macro_recorder):
        """Test creating a macro recorder."""
        assert macro_recorder is not None
        assert not macro_recorder.is_recording

    def test_start_recording(self, macro_recorder):
        """Test starting a recording."""
        macro_recorder.start_recording("Test Recording")

        assert macro_recorder.is_recording
        assert macro_recorder.current_macro_name == "Test Recording"

    def test_stop_recording(self, macro_recorder):
        """Test stopping a recording."""
        macro_recorder.start_recording("Test Recording")
        macro = macro_recorder.stop_recording()

        assert not macro_recorder.is_recording
        assert macro is not None
        assert macro.name == "Test Recording"

    def test_record_action(self, macro_recorder, sample_action):
        """Test recording an action."""
        macro_recorder.start_recording("Test Recording")
        macro_recorder.record_action(sample_action)
        macro = macro_recorder.stop_recording()

        assert len(macro.actions) == 1
        assert macro.actions[0].action_type == ActionType.ASSET_IMPORT

    def test_record_import(self, macro_recorder):
        """Test recording an import action."""
        macro_recorder.start_recording("Test Recording")
        macro_recorder.record_import("/path/to/file.fbx", "/Game/Meshes")
        macro = macro_recorder.stop_recording()

        assert len(macro.actions) == 1
        assert macro.actions[0].action_type == ActionType.ASSET_IMPORT

    def test_record_spawn(self, macro_recorder):
        """Test recording a spawn action."""
        macro_recorder.start_recording("Test Recording")
        macro_recorder.record_spawn("StaticMeshActor", (0, 0, 0))
        macro = macro_recorder.stop_recording()

        assert len(macro.actions) == 1
        assert macro.actions[0].action_type == ActionType.ACTOR_SPAWN

    def test_record_transform(self, macro_recorder):
        """Test recording a transform action."""
        macro_recorder.start_recording("Test Recording")
        macro_recorder.record_transform(
            "TestActor",
            location=(100, 200, 300),
            rotation=(0, 45, 0),
            scale=(1, 1, 1),
        )
        macro = macro_recorder.stop_recording()

        assert len(macro.actions) == 1
        assert macro.actions[0].action_type == ActionType.ACTOR_TRANSFORM

    def test_record_material_assign(self, macro_recorder):
        """Test recording a material assignment."""
        macro_recorder.start_recording("Test Recording")
        macro_recorder.record_material_assign(
            "/Game/Meshes/Cube",
            "/Game/Materials/M_Test",
        )
        macro = macro_recorder.stop_recording()

        assert len(macro.actions) == 1
        assert macro.actions[0].action_type == ActionType.MATERIAL_ASSIGN

    def test_record_command(self, macro_recorder):
        """Test recording an editor command."""
        macro_recorder.start_recording("Test Recording")
        macro_recorder.record_command("stat fps")
        macro = macro_recorder.stop_recording()

        assert len(macro.actions) == 1
        assert macro.actions[0].action_type == ActionType.EDITOR_COMMAND

    def test_record_python(self, macro_recorder):
        """Test recording Python execution."""
        macro_recorder.start_recording("Test Recording")
        macro_recorder.record_python("print('Hello')")
        macro = macro_recorder.stop_recording()

        assert len(macro.actions) == 1
        assert macro.actions[0].action_type == ActionType.PYTHON_EXEC

    def test_save_macro(self, macro_recorder, temp_directory):
        """Test saving a macro to file."""
        macro_recorder.start_recording("Test Recording")
        macro_recorder.record_command("test")
        macro = macro_recorder.stop_recording()

        file_path = temp_directory / "test_macro.json"
        result = macro_recorder.save_macro(str(file_path), macro)

        assert result
        assert file_path.exists()

        with open(file_path) as f:
            data = json.load(f)

        assert data["name"] == "Test Recording"
        assert len(data["actions"]) == 1

    def test_load_macro(self, macro_recorder, temp_directory):
        """Test loading a macro from file."""
        macro_data = {
            "name": "Loaded Macro",
            "description": "A loaded macro",
            "actions": [
                {
                    "action_type": "EDITOR_COMMAND",
                    "parameters": {"command": "test"},
                }
            ],
            "metadata": {},
        }

        file_path = temp_directory / "load_test.json"
        with open(file_path, "w") as f:
            json.dump(macro_data, f)

        macro = macro_recorder.load_macro(str(file_path))

        assert macro is not None
        assert macro.name == "Loaded Macro"
        assert len(macro.actions) == 1

    def test_replay_macro(self, macro_recorder):
        """Test replaying a macro."""
        executed = []

        def custom_handler(action):
            executed.append(action.action_type)
            return True

        macro_recorder.register_handler(ActionType.CUSTOM, custom_handler)

        macro = Macro(
            name="Replay Test",
            actions=[
                RecordedAction(
                    action_type=ActionType.CUSTOM,
                    parameters={"test": True},
                )
            ],
        )

        result = macro_recorder.replay(macro)

        assert result.success
        assert ActionType.CUSTOM in executed

    def test_replay_dry_run(self, macro_recorder):
        """Test replaying a macro in dry-run mode."""
        executed = []

        def custom_handler(action):
            executed.append(action.action_type)
            return True

        macro_recorder.register_handler(ActionType.CUSTOM, custom_handler)

        macro = Macro(
            name="Dry Run Test",
            actions=[
                RecordedAction(
                    action_type=ActionType.CUSTOM,
                    parameters={"test": True},
                )
            ],
        )

        result = macro_recorder.replay(macro, dry_run=True)

        assert result.success
        assert len(executed) == 0

    def test_register_handler(self, macro_recorder):
        """Test registering a custom handler."""
        def my_handler(action):
            return True

        macro_recorder.register_handler(ActionType.CUSTOM, my_handler)

        assert ActionType.CUSTOM in macro_recorder._handlers
