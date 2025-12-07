"""
Tests for the RollbackManager module.
"""

from unittest.mock import MagicMock

import pytest

from src.core.rollback import RollbackManager, Transaction


class TestTransaction:
    """Tests for the Transaction class."""

    def test_transaction_creation(self):
        """Test creating a transaction."""
        tx = Transaction(name="Test Transaction")

        assert tx.name == "Test Transaction"
        assert len(tx.actions) == 0

    def test_add_action(self):
        """Test adding an action to a transaction."""
        tx = Transaction(name="Test")

        do_action = MagicMock()
        undo_action = MagicMock()

        tx.add_action(do_action, undo_action)

        assert len(tx.actions) == 1

    def test_undo_transaction(self):
        """Test undoing a transaction."""
        tx = Transaction(name="Test")

        value = [0]

        def do_action():
            value[0] += 1

        def undo_action():
            value[0] -= 1

        do_action()
        tx.add_action(do_action, undo_action)

        assert value[0] == 1

        tx.undo()

        assert value[0] == 0

    def test_redo_transaction(self):
        """Test redoing a transaction."""
        tx = Transaction(name="Test")

        value = [0]

        def do_action():
            value[0] += 1

        def undo_action():
            value[0] -= 1

        do_action()
        tx.add_action(do_action, undo_action)
        tx.undo()

        assert value[0] == 0

        tx.redo()

        assert value[0] == 1


class TestRollbackManager:
    """Tests for the RollbackManager class."""

    @pytest.fixture
    def rollback_manager(self):
        """Create a RollbackManager instance."""
        return RollbackManager()

    def test_manager_creation(self, rollback_manager):
        """Test creating a rollback manager."""
        assert rollback_manager is not None
        assert not rollback_manager.can_undo
        assert not rollback_manager.can_redo

    def test_begin_transaction(self, rollback_manager):
        """Test beginning a transaction."""
        rollback_manager.begin_transaction("Test")

        assert rollback_manager._current_transaction is not None

    def test_commit_transaction(self, rollback_manager):
        """Test committing a transaction."""
        rollback_manager.begin_transaction("Test")

        value = [0]

        def do_action():
            value[0] += 1

        def undo_action():
            value[0] -= 1

        do_action()
        rollback_manager.record_action(do_action, undo_action)
        rollback_manager.commit_transaction()

        assert rollback_manager._current_transaction is None
        assert rollback_manager.can_undo

    def test_rollback_transaction(self, rollback_manager):
        """Test rolling back a transaction."""
        rollback_manager.begin_transaction("Test")

        value = [0]

        def do_action():
            value[0] += 1

        def undo_action():
            value[0] -= 1

        do_action()
        rollback_manager.record_action(do_action, undo_action)

        assert value[0] == 1

        rollback_manager.rollback_transaction()

        assert value[0] == 0
        assert rollback_manager._current_transaction is None

    def test_undo(self, rollback_manager):
        """Test undo functionality."""
        rollback_manager.begin_transaction("Test")

        value = [0]

        def do_action():
            value[0] += 1

        def undo_action():
            value[0] -= 1

        do_action()
        rollback_manager.record_action(do_action, undo_action)
        rollback_manager.commit_transaction()

        assert value[0] == 1

        rollback_manager.undo()

        assert value[0] == 0

    def test_redo(self, rollback_manager):
        """Test redo functionality."""
        rollback_manager.begin_transaction("Test")

        value = [0]

        def do_action():
            value[0] += 1

        def undo_action():
            value[0] -= 1

        do_action()
        rollback_manager.record_action(do_action, undo_action)
        rollback_manager.commit_transaction()

        rollback_manager.undo()

        assert value[0] == 0

        rollback_manager.redo()

        assert value[0] == 1

    def test_multiple_transactions(self, rollback_manager):
        """Test multiple transactions."""
        value = [0]

        def do_action():
            value[0] += 1

        def undo_action():
            value[0] -= 1

        for i in range(3):
            rollback_manager.begin_transaction(f"Transaction {i}")
            do_action()
            rollback_manager.record_action(do_action, undo_action)
            rollback_manager.commit_transaction()

        assert value[0] == 3

        rollback_manager.undo()
        assert value[0] == 2

        rollback_manager.undo()
        assert value[0] == 1

        rollback_manager.redo()
        assert value[0] == 2

    def test_clear_history(self, rollback_manager):
        """Test clearing history."""
        rollback_manager.begin_transaction("Test")
        rollback_manager.record_action(lambda: None, lambda: None)
        rollback_manager.commit_transaction()

        assert rollback_manager.can_undo

        rollback_manager.clear_history()

        assert not rollback_manager.can_undo
        assert not rollback_manager.can_redo

    def test_max_history_size(self):
        """Test maximum history size."""
        manager = RollbackManager(max_history=3)

        for i in range(5):
            manager.begin_transaction(f"Transaction {i}")
            manager.record_action(lambda: None, lambda: None)
            manager.commit_transaction()

        assert len(manager._undo_stack) == 3

    def test_get_undo_history(self, rollback_manager):
        """Test getting undo history."""
        for i in range(3):
            rollback_manager.begin_transaction(f"Transaction {i}")
            rollback_manager.record_action(lambda: None, lambda: None)
            rollback_manager.commit_transaction()

        history = rollback_manager.get_undo_history()

        assert len(history) == 3
        assert "Transaction 2" in history[0]
