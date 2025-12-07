"""
Tests for the CommandQueue module.
"""


from src.core.command_queue import (
    Command,
    CommandPriority,
    CommandQueue,
    CommandStatus,
)


class TestCommand:
    """Tests for the Command class."""

    def test_command_creation(self):
        """Test creating a command."""
        cmd = Command(
            id="test-001",
            name="Test Command",
            action=lambda: True,
            priority=CommandPriority.NORMAL,
        )

        assert cmd.id == "test-001"
        assert cmd.name == "Test Command"
        assert cmd.priority == CommandPriority.NORMAL
        assert cmd.status == CommandStatus.PENDING

    def test_command_priority_ordering(self):
        """Test that commands are ordered by priority."""
        high = Command(
            id="high",
            name="High Priority",
            action=lambda: True,
            priority=CommandPriority.HIGH,
        )
        normal = Command(
            id="normal",
            name="Normal Priority",
            action=lambda: True,
            priority=CommandPriority.NORMAL,
        )
        low = Command(
            id="low",
            name="Low Priority",
            action=lambda: True,
            priority=CommandPriority.LOW,
        )

        assert high < normal
        assert normal < low
        assert high < low

    def test_command_with_dependencies(self):
        """Test creating a command with dependencies."""
        cmd = Command(
            id="test-001",
            name="Test Command",
            action=lambda: True,
            dependencies=["dep-001", "dep-002"],
        )

        assert len(cmd.dependencies) == 2
        assert "dep-001" in cmd.dependencies


class TestCommandQueue:
    """Tests for the CommandQueue class."""

    def test_queue_creation(self):
        """Test creating a command queue."""
        queue = CommandQueue()

        assert queue.size == 0
        assert queue.is_empty

    def test_enqueue_command(self, command_queue, sample_command):
        """Test enqueueing a command."""
        command_queue.enqueue(sample_command)

        assert command_queue.size == 1
        assert not command_queue.is_empty

    def test_enqueue_batch(self, command_queue):
        """Test enqueueing multiple commands."""
        commands = [
            Command(id=f"cmd-{i}", name=f"Command {i}", action=lambda: True)
            for i in range(5)
        ]

        command_queue.enqueue_batch(commands)

        assert command_queue.size == 5

    def test_process_command(self, command_queue):
        """Test processing a command."""
        result_value = {"executed": False}

        def action():
            result_value["executed"] = True
            return True

        cmd = Command(id="test", name="Test", action=action)
        command_queue.enqueue(cmd)

        result = command_queue.process_next()

        assert result is not None
        assert result.success
        assert result_value["executed"]

    def test_process_all_commands(self, command_queue):
        """Test processing all commands."""
        executed = []

        for i in range(3):
            cmd = Command(
                id=f"cmd-{i}",
                name=f"Command {i}",
                action=lambda idx=i: executed.append(idx) or True,
            )
            command_queue.enqueue(cmd)

        results = command_queue.process_all()

        assert len(results) == 3
        assert all(r.success for r in results)
        assert len(executed) == 3

    def test_priority_ordering(self, command_queue):
        """Test that high priority commands are processed first."""
        order = []

        low = Command(
            id="low",
            name="Low",
            action=lambda: order.append("low") or True,
            priority=CommandPriority.LOW,
        )
        high = Command(
            id="high",
            name="High",
            action=lambda: order.append("high") or True,
            priority=CommandPriority.HIGH,
        )
        normal = Command(
            id="normal",
            name="Normal",
            action=lambda: order.append("normal") or True,
            priority=CommandPriority.NORMAL,
        )

        command_queue.enqueue(low)
        command_queue.enqueue(high)
        command_queue.enqueue(normal)

        command_queue.process_all()

        assert order[0] == "high"
        assert order[1] == "normal"
        assert order[2] == "low"

    def test_cancel_command(self, command_queue, sample_command):
        """Test cancelling a command."""
        command_queue.enqueue(sample_command)

        success = command_queue.cancel(sample_command.id)

        assert success
        status = command_queue.get_status(sample_command.id)
        assert status == CommandStatus.CANCELLED

    def test_get_statistics(self, command_queue):
        """Test getting queue statistics."""
        for i in range(3):
            cmd = Command(id=f"cmd-{i}", name=f"Command {i}", action=lambda: True)
            command_queue.enqueue(cmd)

        command_queue.process_next()

        stats = command_queue.get_statistics()

        assert stats["total_enqueued"] == 3
        assert stats["completed"] == 1
        assert stats["pending"] == 2

    def test_progress_callback(self, command_queue):
        """Test progress callback."""
        progress_updates = []

        def on_progress(progress, message):
            progress_updates.append((progress, message))

        command_queue.set_progress_callback(on_progress)

        cmd = Command(id="test", name="Test", action=lambda: True)
        command_queue.enqueue(cmd)
        command_queue.process_next()

        assert len(progress_updates) > 0

    def test_command_failure(self, command_queue):
        """Test handling command failure."""
        def failing_action():
            raise ValueError("Test error")

        cmd = Command(id="fail", name="Failing", action=failing_action)
        command_queue.enqueue(cmd)

        result = command_queue.process_next()

        assert not result.success
        assert result.error is not None
        assert "Test error" in result.error

    def test_clear_queue(self, command_queue):
        """Test clearing the queue."""
        for i in range(5):
            cmd = Command(id=f"cmd-{i}", name=f"Command {i}", action=lambda: True)
            command_queue.enqueue(cmd)

        command_queue.clear()

        assert command_queue.is_empty
