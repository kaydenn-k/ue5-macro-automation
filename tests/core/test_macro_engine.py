"""
Tests for the MacroEngine module.
"""


from src.core.macro_engine import MacroEngine
from src.core.macro_recorder import ActionType, Macro, RecordedAction


class TestMacroEngine:
    """Tests for the MacroEngine class."""

    def test_engine_creation(self):
        """Test creating a macro engine."""
        engine = MacroEngine()
        assert engine is not None

    def test_engine_initialization(self, macro_engine):
        """Test initializing the engine."""
        assert macro_engine._initialized

    def test_engine_shutdown(self):
        """Test shutting down the engine."""
        engine = MacroEngine()
        engine.initialize()
        engine.shutdown()

        assert not engine._initialized

    def test_register_macro(self, macro_engine):
        """Test registering a macro."""
        macro = Macro(
            name="Test Macro",
            actions=[
                RecordedAction(
                    action_type=ActionType.CUSTOM,
                    parameters={"test": True},
                )
            ],
        )

        macro_engine.register_macro(macro)

        assert "Test Macro" in macro_engine.get_macro_names()

    def test_get_macro(self, macro_engine):
        """Test getting a registered macro."""
        macro = Macro(
            name="Test Macro",
            actions=[],
        )

        macro_engine.register_macro(macro)
        retrieved = macro_engine.get_macro("Test Macro")

        assert retrieved is not None
        assert retrieved.name == "Test Macro"

    def test_unregister_macro(self, macro_engine):
        """Test unregistering a macro."""
        macro = Macro(name="Test Macro", actions=[])

        macro_engine.register_macro(macro)
        macro_engine.unregister_macro("Test Macro")

        assert "Test Macro" not in macro_engine.get_macro_names()

    def test_execute_macro(self, macro_engine):
        """Test executing a macro."""
        executed = []

        def custom_handler(action):
            executed.append(action)
            return True

        macro_engine.recorder.register_handler(ActionType.CUSTOM, custom_handler)

        macro = Macro(
            name="Test Macro",
            actions=[
                RecordedAction(
                    action_type=ActionType.CUSTOM,
                    parameters={"test": True},
                )
            ],
        )

        macro_engine.register_macro(macro)
        result = macro_engine.execute_macro("Test Macro")

        assert result.success
        assert len(executed) == 1

    def test_execute_macro_with_context(self, macro_engine):
        """Test executing a macro with context."""
        context_received = {}

        def custom_handler(action):
            context_received.update(action.parameters)
            return True

        macro_engine.recorder.register_handler(ActionType.CUSTOM, custom_handler)

        macro = Macro(
            name="Test Macro",
            actions=[
                RecordedAction(
                    action_type=ActionType.CUSTOM,
                    parameters={"test": True},
                )
            ],
        )

        macro_engine.register_macro(macro)
        macro_engine.execute_macro("Test Macro", context={"extra": "data"})

        assert "test" in context_received

    def test_start_recording(self, macro_engine):
        """Test starting recording through engine."""
        macro_engine.start_recording("Test Recording")

        assert macro_engine.is_recording

    def test_stop_recording(self, macro_engine):
        """Test stopping recording through engine."""
        macro_engine.start_recording("Test Recording")
        macro = macro_engine.stop_recording()

        assert not macro_engine.is_recording
        assert macro is not None

    def test_queue_command(self, macro_engine):
        """Test queuing a command."""
        executed = []

        def action():
            executed.append(True)
            return True

        macro_engine.queue_command("Test Command", action)
        macro_engine.process_queue()

        assert len(executed) == 1

    def test_undo_redo(self, macro_engine):
        """Test undo/redo functionality."""
        value = [0]

        def do_action():
            value[0] += 1

        def undo_action():
            value[0] -= 1

        macro_engine.rollback.begin_transaction("Test")
        do_action()
        macro_engine.rollback.record_action(do_action, undo_action)
        macro_engine.rollback.commit_transaction()

        assert value[0] == 1

        macro_engine.undo()
        assert value[0] == 0

        macro_engine.redo()
        assert value[0] == 1

    def test_get_status(self, macro_engine):
        """Test getting engine status."""
        status = macro_engine.get_status()

        assert "initialized" in status
        assert "recording" in status
        assert "queue_size" in status
        assert "macro_count" in status
