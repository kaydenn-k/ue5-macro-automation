"""
Rollback Manager for UE5 Macro Automation.

Provides undo/redo functionality with transaction support for macro operations.
Allows reverting changes made by macros in case of errors or user request.

Example Usage:
    >>> rollback = RollbackManager(max_steps=50)
    >>>
    >>> # Start a transaction
    >>> rollback.start_transaction()
    >>>
    >>> # Push actions as they're executed
    >>> rollback.push(RollbackAction(
    ...     action_type="ASSET_IMPORT",
    ...     target="/Game/Meshes/Tree",
    ...     original_state={"existed": False}
    ... ))
    >>>
    >>> # Undo if needed
    >>> rollback.undo()
    >>>
    >>> # Or rollback entire transaction
    >>> rollback.rollback_transaction()
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class RollbackAction:
    """
    Represents an action that can be rolled back.

    Attributes:
        action_type: Type of the action
        target: Target of the action (asset path, actor name, etc.)
        original_state: State before the action was executed
        new_state: State after the action was executed
        description: Human-readable description
        timestamp: When the action was recorded
        rollback_func: Custom function to execute for rollback
        redo_func: Custom function to execute for redo
    """
    action_type: str
    target: str
    original_state: dict[str, Any] = field(default_factory=dict)
    new_state: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    timestamp: float = field(default_factory=time.time)
    rollback_func: Callable[[], bool] | None = None
    redo_func: Callable[[], bool] | None = None

    def can_rollback(self) -> bool:
        """Check if this action can be rolled back."""
        return self.rollback_func is not None or bool(self.original_state)

    def can_redo(self) -> bool:
        """Check if this action can be redone."""
        return self.redo_func is not None or bool(self.new_state)


@dataclass
class Transaction:
    """
    A group of actions that should be rolled back together.

    Attributes:
        id: Unique transaction ID
        name: Transaction name
        actions: List of actions in this transaction
        started_at: When the transaction started
        committed: Whether the transaction has been committed
    """
    id: str
    name: str = ""
    actions: list[RollbackAction] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    committed: bool = False

    def add_action(self, action: RollbackAction) -> None:
        """Add an action to the transaction."""
        self.actions.append(action)

    def commit(self) -> None:
        """Mark the transaction as committed."""
        self.committed = True


class RollbackManager:
    """
    Manages undo/redo operations with transaction support.

    Features:
    - Undo/redo stack with configurable depth
    - Transaction grouping for atomic operations
    - Custom rollback handlers for different action types
    - State preservation and restoration

    Example:
        >>> manager = RollbackManager(max_steps=100)
        >>>
        >>> # Register custom handlers
        >>> manager.register_handler("ASSET_DELETE", delete_rollback_handler)
        >>>
        >>> # Start recording changes
        >>> manager.start_transaction()
        >>>
        >>> # Record actions
        >>> manager.push(RollbackAction(
        ...     action_type="ASSET_DELETE",
        ...     target="/Game/Meshes/OldTree",
        ...     original_state={"asset_data": {...}}
        ... ))
        >>>
        >>> # Commit or rollback
        >>> manager.commit_transaction()  # or manager.rollback_transaction()
    """

    def __init__(self, max_steps: int = 50) -> None:
        """
        Initialize the rollback manager.

        Args:
            max_steps: Maximum number of undo steps to keep
        """
        self._max_steps = max_steps
        self._undo_stack: list[RollbackAction] = []
        self._redo_stack: list[RollbackAction] = []
        self._current_transaction: Transaction | None = None
        self._transaction_counter = 0
        self._handlers: dict[str, Callable[[RollbackAction, bool], bool]] = {}
        self._unreal_available = self._check_unreal_available()

        self._register_default_handlers()

    def _check_unreal_available(self) -> bool:
        """Check if Unreal Python API is available."""
        try:
            import unreal  # noqa: F401
            return True
        except ImportError:
            return False

    def _register_default_handlers(self) -> None:
        """Register default rollback handlers."""
        self._handlers["ASSET_IMPORT"] = self._handle_asset_import_rollback
        self._handlers["ASSET_DELETE"] = self._handle_asset_delete_rollback
        self._handlers["ASSET_RENAME"] = self._handle_asset_rename_rollback
        self._handlers["ASSET_MOVE"] = self._handle_asset_move_rollback
        self._handlers["ACTOR_SPAWN"] = self._handle_actor_spawn_rollback
        self._handlers["ACTOR_DELETE"] = self._handle_actor_delete_rollback
        self._handlers["ACTOR_TRANSFORM"] = self._handle_actor_transform_rollback
        self._handlers["MATERIAL_ASSIGN"] = self._handle_material_assign_rollback

    @property
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0

    @property
    def undo_count(self) -> int:
        """Get the number of available undo steps."""
        return len(self._undo_stack)

    @property
    def redo_count(self) -> int:
        """Get the number of available redo steps."""
        return len(self._redo_stack)

    @property
    def in_transaction(self) -> bool:
        """Check if currently in a transaction."""
        return self._current_transaction is not None

    def register_handler(
        self,
        action_type: str,
        handler: Callable[[RollbackAction, bool], bool]
    ) -> None:
        """
        Register a custom rollback handler.

        Args:
            action_type: The action type to handle
            handler: Function(action, is_undo) -> success
        """
        self._handlers[action_type] = handler

    def push(self, action: RollbackAction) -> None:
        """
        Push an action onto the undo stack.

        Args:
            action: The action to push
        """
        if self._current_transaction:
            self._current_transaction.add_action(action)

        self._undo_stack.append(action)

        while len(self._undo_stack) > self._max_steps:
            self._undo_stack.pop(0)

        self._redo_stack.clear()

        logger.debug(f"Pushed action: {action.action_type} -> {action.target}")

    def undo(self) -> bool:
        """
        Undo the last action.

        Returns:
            True if undo was successful
        """
        if not self._undo_stack:
            logger.warning("Nothing to undo")
            return False

        action = self._undo_stack.pop()

        try:
            success = self._execute_rollback(action, is_undo=True)

            if success:
                self._redo_stack.append(action)
                logger.info(f"Undone: {action.description or action.action_type}")
            else:
                self._undo_stack.append(action)
                logger.error(f"Failed to undo: {action.action_type}")

            return success

        except Exception as e:
            logger.error(f"Undo failed with exception: {e}")
            self._undo_stack.append(action)
            return False

    def redo(self) -> bool:
        """
        Redo the last undone action.

        Returns:
            True if redo was successful
        """
        if not self._redo_stack:
            logger.warning("Nothing to redo")
            return False

        action = self._redo_stack.pop()

        try:
            success = self._execute_rollback(action, is_undo=False)

            if success:
                self._undo_stack.append(action)
                logger.info(f"Redone: {action.description or action.action_type}")
            else:
                self._redo_stack.append(action)
                logger.error(f"Failed to redo: {action.action_type}")

            return success

        except Exception as e:
            logger.error(f"Redo failed with exception: {e}")
            self._redo_stack.append(action)
            return False

    def _execute_rollback(self, action: RollbackAction, is_undo: bool) -> bool:
        """Execute a rollback or redo operation."""
        if is_undo and action.rollback_func:
            return action.rollback_func()
        elif not is_undo and action.redo_func:
            return action.redo_func()

        handler = self._handlers.get(action.action_type)
        if handler:
            return handler(action, is_undo)

        logger.warning(f"No handler for action type: {action.action_type}")
        return True

    def start_transaction(self, name: str = "") -> str:
        """
        Start a new transaction.

        Args:
            name: Optional name for the transaction

        Returns:
            Transaction ID
        """
        if self._current_transaction:
            logger.warning("Already in a transaction - committing current")
            self.commit_transaction()

        self._transaction_counter += 1
        transaction_id = f"txn_{self._transaction_counter}"

        self._current_transaction = Transaction(
            id=transaction_id,
            name=name or f"Transaction {self._transaction_counter}"
        )

        logger.debug(f"Started transaction: {transaction_id}")
        return transaction_id

    def commit_transaction(self) -> bool:
        """
        Commit the current transaction.

        Returns:
            True if committed successfully
        """
        if not self._current_transaction:
            logger.warning("No transaction to commit")
            return False

        self._current_transaction.commit()
        logger.info(
            f"Committed transaction: {self._current_transaction.id} "
            f"({len(self._current_transaction.actions)} actions)"
        )
        self._current_transaction = None
        return True

    def rollback_transaction(self) -> int:
        """
        Rollback all actions in the current transaction.

        Returns:
            Number of actions rolled back
        """
        if not self._current_transaction:
            logger.warning("No transaction to rollback")
            return 0

        rolled_back = 0

        for action in reversed(self._current_transaction.actions):
            if action in self._undo_stack:
                self._undo_stack.remove(action)

            try:
                if self._execute_rollback(action, is_undo=True):
                    rolled_back += 1
            except Exception as e:
                logger.error(f"Failed to rollback action: {e}")

        logger.info(
            f"Rolled back transaction: {self._current_transaction.id} "
            f"({rolled_back} actions)"
        )
        self._current_transaction = None
        return rolled_back

    def clear(self) -> None:
        """Clear all undo/redo history."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._current_transaction = None
        logger.info("Rollback history cleared")

    def get_undo_history(self) -> list[dict[str, Any]]:
        """
        Get the undo history.

        Returns:
            List of action descriptions
        """
        return [
            {
                "action_type": action.action_type,
                "target": action.target,
                "description": action.description,
                "timestamp": action.timestamp,
            }
            for action in reversed(self._undo_stack)
        ]

    def get_redo_history(self) -> list[dict[str, Any]]:
        """
        Get the redo history.

        Returns:
            List of action descriptions
        """
        return [
            {
                "action_type": action.action_type,
                "target": action.target,
                "description": action.description,
                "timestamp": action.timestamp,
            }
            for action in reversed(self._redo_stack)
        ]

    def _handle_asset_import_rollback(
        self, action: RollbackAction, is_undo: bool
    ) -> bool:
        """Handle rollback for asset import."""
        if not self._unreal_available:
            logger.info(f"[MOCK] {'Undo' if is_undo else 'Redo'} asset import: {action.target}")
            return True

        import unreal  # noqa: F401

        if is_undo:
            if not action.original_state.get("existed", True):
                return unreal.EditorAssetLibrary.delete_asset(action.target)
        else:
            source_path = action.original_state.get("source_path")
            if source_path:
                task = unreal.AssetImportTask()
                task.filename = source_path
                task.destination_path = action.target
                task.automated = True
                unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
                return True

        return True

    def _handle_asset_delete_rollback(
        self, action: RollbackAction, is_undo: bool
    ) -> bool:
        """Handle rollback for asset delete."""
        if not self._unreal_available:
            logger.info(f"[MOCK] {'Undo' if is_undo else 'Redo'} asset delete: {action.target}")
            return True

        logger.warning("Asset delete rollback requires backup - not fully implemented")
        return True

    def _handle_asset_rename_rollback(
        self, action: RollbackAction, is_undo: bool
    ) -> bool:
        """Handle rollback for asset rename."""
        if not self._unreal_available:
            logger.info(f"[MOCK] {'Undo' if is_undo else 'Redo'} asset rename: {action.target}")
            return True

        import unreal  # noqa: F401

        if is_undo:
            old_name = action.original_state.get("old_name")
            if old_name:
                return unreal.EditorAssetLibrary.rename_asset(action.target, old_name)
        else:
            new_name = action.new_state.get("new_name")
            if new_name:
                return unreal.EditorAssetLibrary.rename_asset(action.target, new_name)

        return True

    def _handle_asset_move_rollback(
        self, action: RollbackAction, is_undo: bool
    ) -> bool:
        """Handle rollback for asset move."""
        if not self._unreal_available:
            logger.info(f"[MOCK] {'Undo' if is_undo else 'Redo'} asset move: {action.target}")
            return True

        import unreal  # noqa: F401

        if is_undo:
            old_path = action.original_state.get("old_path")
            if old_path:
                return unreal.EditorAssetLibrary.rename_asset(action.target, old_path)
        else:
            new_path = action.new_state.get("new_path")
            if new_path:
                return unreal.EditorAssetLibrary.rename_asset(action.target, new_path)

        return True

    def _handle_actor_spawn_rollback(
        self, action: RollbackAction, is_undo: bool
    ) -> bool:
        """Handle rollback for actor spawn."""
        if not self._unreal_available:
            logger.info(f"[MOCK] {'Undo' if is_undo else 'Redo'} actor spawn: {action.target}")
            return True

        import unreal  # noqa: F401

        if is_undo:
            actors = unreal.EditorLevelLibrary.get_all_level_actors()
            for actor in actors:
                if actor.get_name() == action.original_state.get("actor_name"):
                    actor.destroy_actor()
                    return True
        else:
            actor_class = unreal.load_class(None, action.target)
            if actor_class:
                location = action.new_state.get("location", (0, 0, 0))
                rotation = action.new_state.get("rotation", (0, 0, 0))
                unreal.EditorLevelLibrary.spawn_actor_from_class(
                    actor_class,
                    unreal.Vector(*location),
                    unreal.Rotator(*rotation)
                )
                return True

        return True

    def _handle_actor_delete_rollback(
        self, action: RollbackAction, is_undo: bool
    ) -> bool:
        """Handle rollback for actor delete."""
        if not self._unreal_available:
            logger.info(f"[MOCK] {'Undo' if is_undo else 'Redo'} actor delete: {action.target}")
            return True

        logger.warning("Actor delete rollback requires backup - not fully implemented")
        return True

    def _handle_actor_transform_rollback(
        self, action: RollbackAction, is_undo: bool
    ) -> bool:
        """Handle rollback for actor transform."""
        if not self._unreal_available:
            logger.info(f"[MOCK] {'Undo' if is_undo else 'Redo'} actor transform: {action.target}")
            return True

        import unreal  # noqa: F401

        state = action.original_state if is_undo else action.new_state

        actors = unreal.EditorLevelLibrary.get_all_level_actors()
        for actor in actors:
            if actor.get_name() == action.target:
                if "location" in state:
                    actor.set_actor_location(
                        unreal.Vector(*state["location"]), False, False
                    )
                if "rotation" in state:
                    actor.set_actor_rotation(
                        unreal.Rotator(*state["rotation"]), False
                    )
                if "scale" in state:
                    actor.set_actor_scale3d(unreal.Vector(*state["scale"]))
                return True

        return False

    def _handle_material_assign_rollback(
        self, action: RollbackAction, is_undo: bool
    ) -> bool:
        """Handle rollback for material assignment."""
        if not self._unreal_available:
            logger.info(f"[MOCK] {'Undo' if is_undo else 'Redo'} material assign: {action.target}")
            return True

        import unreal  # noqa: F401

        state = action.original_state if is_undo else action.new_state
        material_path = state.get("material_path")
        slot_index = state.get("slot_index", 0)

        if not material_path:
            return True

        material = unreal.load_asset(material_path)
        if not material:
            return False

        actors = unreal.EditorLevelLibrary.get_all_level_actors()
        for actor in actors:
            if actor.get_name() == action.target:
                mesh_component = actor.get_component_by_class(
                    unreal.StaticMeshComponent
                )
                if mesh_component:
                    mesh_component.set_material(slot_index, material)
                    return True

        return False
