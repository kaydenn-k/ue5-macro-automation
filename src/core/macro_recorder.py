"""
Macro Recorder for UE5 Macro Automation.

Captures editor actions and allows them to be replayed. Supports recording
of asset operations, actor manipulations, and editor commands.

Example Usage:
    >>> recorder = MacroRecorder()
    >>> recorder.start_recording("my_macro")
    >>> # Perform actions in the editor...
    >>> recorder.stop_recording()
    >>> recorder.save_macro("/path/to/macro.json")
    >>>
    >>> # Later, replay the macro
    >>> recorder.load_macro("/path/to/macro.json")
    >>> recorder.replay()
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of recordable actions."""
    ASSET_IMPORT = auto()
    ASSET_DELETE = auto()
    ASSET_RENAME = auto()
    ASSET_MOVE = auto()
    ASSET_DUPLICATE = auto()

    ACTOR_SPAWN = auto()
    ACTOR_DELETE = auto()
    ACTOR_TRANSFORM = auto()
    ACTOR_RENAME = auto()
    ACTOR_PARENT = auto()
    ACTOR_SELECT = auto()

    MATERIAL_ASSIGN = auto()
    MATERIAL_CREATE = auto()
    MATERIAL_INSTANCE = auto()

    LEVEL_LOAD = auto()
    LEVEL_SAVE = auto()
    LEVEL_NEW = auto()

    EDITOR_COMMAND = auto()
    PYTHON_EXEC = auto()
    CUSTOM = auto()


@dataclass
class RecordedAction:
    """
    Represents a single recorded action.

    Attributes:
        action_type: The type of action
        target: The target object (asset path, actor name, etc.)
        parameters: Action-specific parameters
        timestamp: When the action was recorded
        duration: How long the action took (if applicable)
        metadata: Additional metadata

    Example:
        >>> action = RecordedAction(
        ...     action_type=ActionType.ASSET_IMPORT,
        ...     target="/Game/Meshes/Tree",
        ...     parameters={
        ...         "source_path": "/path/to/tree.fbx",
        ...         "import_options": {"generate_lods": True}
        ...     }
        ... )
    """
    action_type: ActionType
    target: str
    parameters: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "action_type": self.action_type.name,
            "target": self.target,
            "parameters": self.parameters,
            "timestamp": self.timestamp,
            "duration": self.duration,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecordedAction:
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            action_type=ActionType[data["action_type"]],
            target=data["target"],
            parameters=data.get("parameters", {}),
            timestamp=data.get("timestamp", time.time()),
            duration=data.get("duration", 0.0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Macro:
    """
    A collection of recorded actions that can be replayed.

    Attributes:
        name: Human-readable name for the macro
        description: Description of what the macro does
        actions: List of recorded actions
        version: Macro format version
        created_at: Creation timestamp
        modified_at: Last modification timestamp
        author: Author of the macro
        tags: Tags for categorization
        hotkey: Optional hotkey binding
    """
    name: str
    description: str = ""
    actions: list[RecordedAction] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    author: str = ""
    tags: list[str] = field(default_factory=list)
    hotkey: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "author": self.author,
            "tags": self.tags,
            "hotkey": self.hotkey,
            "actions": [action.to_dict() for action in self.actions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Macro:
        """Create from dictionary."""
        actions = [
            RecordedAction.from_dict(action_data)
            for action_data in data.get("actions", [])
        ]
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            modified_at=data.get("modified_at", datetime.now().isoformat()),
            author=data.get("author", ""),
            tags=data.get("tags", []),
            hotkey=data.get("hotkey"),
            actions=actions,
        )

    def add_action(self, action: RecordedAction) -> None:
        """Add an action to the macro."""
        self.actions.append(action)
        self.modified_at = datetime.now().isoformat()

    def remove_action(self, action_id: str) -> bool:
        """Remove an action by ID."""
        for i, action in enumerate(self.actions):
            if action.id == action_id:
                del self.actions[i]
                self.modified_at = datetime.now().isoformat()
                return True
        return False

    def clear_actions(self) -> None:
        """Remove all actions."""
        self.actions.clear()
        self.modified_at = datetime.now().isoformat()


class MacroRecorder:
    """
    Records and replays editor actions.

    The recorder can capture various editor operations and save them
    as macros that can be replayed later.

    Example:
        >>> recorder = MacroRecorder()
        >>>
        >>> # Start recording
        >>> recorder.start_recording("Import Assets Macro")
        >>>
        >>> # Record some actions manually
        >>> recorder.record_action(RecordedAction(
        ...     action_type=ActionType.ASSET_IMPORT,
        ...     target="/Game/Meshes/Tree",
        ...     parameters={"source": "/path/to/tree.fbx"}
        ... ))
        >>>
        >>> # Stop and save
        >>> recorder.stop_recording()
        >>> recorder.save_macro("macros/import_assets.json")
    """

    def __init__(self) -> None:
        """Initialize the macro recorder."""
        self._is_recording = False
        self._current_macro: Macro | None = None
        self._action_handlers: dict[ActionType, Callable[..., Any]] = {}
        self._on_action_recorded: Callable[[RecordedAction], None] | None = None
        self._on_replay_progress: Callable[[int, int, str], None] | None = None
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
        """Register default action handlers."""
        self._action_handlers[ActionType.ASSET_IMPORT] = self._handle_asset_import
        self._action_handlers[ActionType.ASSET_DELETE] = self._handle_asset_delete
        self._action_handlers[ActionType.ASSET_RENAME] = self._handle_asset_rename
        self._action_handlers[ActionType.ASSET_MOVE] = self._handle_asset_move
        self._action_handlers[ActionType.ACTOR_SPAWN] = self._handle_actor_spawn
        self._action_handlers[ActionType.ACTOR_DELETE] = self._handle_actor_delete
        self._action_handlers[ActionType.ACTOR_TRANSFORM] = self._handle_actor_transform
        self._action_handlers[ActionType.MATERIAL_ASSIGN] = self._handle_material_assign
        self._action_handlers[ActionType.EDITOR_COMMAND] = self._handle_editor_command
        self._action_handlers[ActionType.PYTHON_EXEC] = self._handle_python_exec
        self._action_handlers[ActionType.CUSTOM] = self._handle_custom

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording

    @property
    def current_macro(self) -> Macro | None:
        """Get the current macro being recorded."""
        return self._current_macro

    def set_action_recorded_callback(
        self, callback: Callable[[RecordedAction], None]
    ) -> None:
        """Set callback for when an action is recorded."""
        self._on_action_recorded = callback

    def set_replay_progress_callback(
        self, callback: Callable[[int, int, str], None]
    ) -> None:
        """Set callback for replay progress updates."""
        self._on_replay_progress = callback

    def register_handler(
        self, action_type: ActionType, handler: Callable[..., Any]
    ) -> None:
        """
        Register a custom handler for an action type.

        Args:
            action_type: The action type to handle
            handler: Function to execute for this action type
        """
        self._action_handlers[action_type] = handler

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
        if self._is_recording:
            logger.warning("Already recording - stopping current recording")
            self.stop_recording()

        self._current_macro = Macro(
            name=name,
            description=description,
            author=author,
            tags=tags or [],
        )
        self._is_recording = True
        logger.info(f"Started recording macro: {name}")

    def stop_recording(self) -> Macro | None:
        """
        Stop recording and return the macro.

        Returns:
            The recorded macro or None if not recording
        """
        if not self._is_recording:
            logger.warning("Not currently recording")
            return None

        self._is_recording = False
        macro = self._current_macro
        logger.info(
            f"Stopped recording macro: {macro.name if macro else 'Unknown'} "
            f"({len(macro.actions) if macro else 0} actions)"
        )
        return macro

    def record_action(self, action: RecordedAction) -> None:
        """
        Record an action to the current macro.

        Args:
            action: The action to record
        """
        if not self._is_recording or not self._current_macro:
            logger.warning("Not recording - action not captured")
            return

        self._current_macro.add_action(action)
        logger.debug(f"Recorded action: {action.action_type.name} -> {action.target}")

        if self._on_action_recorded:
            self._on_action_recorded(action)

    def record_import(
        self,
        target_path: str,
        source_path: str,
        import_options: dict[str, Any] | None = None
    ) -> None:
        """
        Record an asset import action.

        Args:
            target_path: Destination path in Unreal
            source_path: Source file path
            import_options: Import settings
        """
        action = RecordedAction(
            action_type=ActionType.ASSET_IMPORT,
            target=target_path,
            parameters={
                "source_path": source_path,
                "import_options": import_options or {},
            }
        )
        self.record_action(action)

    def record_spawn(
        self,
        actor_class: str,
        location: tuple[float, float, float],
        rotation: tuple[float, float, float] = (0, 0, 0),
        scale: tuple[float, float, float] = (1, 1, 1),
        name: str | None = None
    ) -> None:
        """
        Record an actor spawn action.

        Args:
            actor_class: Class path of the actor to spawn
            location: World location (x, y, z)
            rotation: Rotation (pitch, yaw, roll)
            scale: Scale (x, y, z)
            name: Optional actor name
        """
        action = RecordedAction(
            action_type=ActionType.ACTOR_SPAWN,
            target=actor_class,
            parameters={
                "location": location,
                "rotation": rotation,
                "scale": scale,
                "name": name,
            }
        )
        self.record_action(action)

    def record_transform(
        self,
        actor_name: str,
        location: tuple[float, float, float] | None = None,
        rotation: tuple[float, float, float] | None = None,
        scale: tuple[float, float, float] | None = None
    ) -> None:
        """
        Record an actor transform action.

        Args:
            actor_name: Name of the actor to transform
            location: New location (or None to keep current)
            rotation: New rotation (or None to keep current)
            scale: New scale (or None to keep current)
        """
        action = RecordedAction(
            action_type=ActionType.ACTOR_TRANSFORM,
            target=actor_name,
            parameters={
                "location": location,
                "rotation": rotation,
                "scale": scale,
            }
        )
        self.record_action(action)

    def record_material_assign(
        self,
        target: str,
        material_path: str,
        slot_index: int = 0
    ) -> None:
        """
        Record a material assignment action.

        Args:
            target: Actor or mesh to assign material to
            material_path: Path to the material asset
            slot_index: Material slot index
        """
        action = RecordedAction(
            action_type=ActionType.MATERIAL_ASSIGN,
            target=target,
            parameters={
                "material_path": material_path,
                "slot_index": slot_index,
            }
        )
        self.record_action(action)

    def record_command(self, command: str, parameters: dict[str, Any] | None = None) -> None:
        """
        Record an editor command.

        Args:
            command: The command to execute
            parameters: Command parameters
        """
        action = RecordedAction(
            action_type=ActionType.EDITOR_COMMAND,
            target=command,
            parameters=parameters or {},
        )
        self.record_action(action)

    def record_python(self, code: str, context: dict[str, Any] | None = None) -> None:
        """
        Record Python code execution.

        Args:
            code: Python code to execute
            context: Variables to inject into execution context
        """
        action = RecordedAction(
            action_type=ActionType.PYTHON_EXEC,
            target="python_exec",
            parameters={
                "code": code,
                "context": context or {},
            }
        )
        self.record_action(action)

    def save_macro(self, path: str | Path, macro: Macro | None = None) -> bool:
        """
        Save a macro to a JSON file.

        Args:
            path: File path to save to
            macro: Macro to save (uses current if None)

        Returns:
            True if saved successfully
        """
        macro = macro or self._current_macro
        if not macro:
            logger.error("No macro to save")
            return False

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(macro.to_dict(), f, indent=2)
            logger.info(f"Saved macro to: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save macro: {e}")
            return False

    def load_macro(self, path: str | Path) -> Macro | None:
        """
        Load a macro from a JSON file.

        Args:
            path: File path to load from

        Returns:
            The loaded macro or None on failure
        """
        path = Path(path)

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            macro = Macro.from_dict(data)
            logger.info(f"Loaded macro: {macro.name} ({len(macro.actions)} actions)")
            return macro
        except Exception as e:
            logger.error(f"Failed to load macro: {e}")
            return None

    def replay(
        self,
        macro: Macro | None = None,
        dry_run: bool = False,
        stop_on_error: bool = True
    ) -> dict[str, Any]:
        """
        Replay a macro.

        Args:
            macro: Macro to replay (uses current if None)
            dry_run: If True, only simulate without executing
            stop_on_error: Stop replay on first error

        Returns:
            Dictionary with replay results
        """
        macro = macro or self._current_macro
        if not macro:
            logger.error("No macro to replay")
            return {"success": False, "error": "No macro to replay"}

        results = {
            "success": True,
            "macro_name": macro.name,
            "total_actions": len(macro.actions),
            "executed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }

        logger.info(f"Replaying macro: {macro.name} ({len(macro.actions)} actions)")

        for i, action in enumerate(macro.actions):
            if self._on_replay_progress:
                self._on_replay_progress(
                    i, len(macro.actions),
                    f"Executing: {action.action_type.name}"
                )

            if dry_run:
                logger.info(f"[DRY RUN] Would execute: {action.action_type.name} -> {action.target}")
                results["executed"] += 1
                continue

            try:
                handler = self._action_handlers.get(action.action_type)
                if handler:
                    handler(action)
                    results["executed"] += 1
                else:
                    logger.warning(f"No handler for action type: {action.action_type.name}")
                    results["skipped"] += 1

            except Exception as e:
                error_msg = f"Action {action.action_type.name} failed: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                results["failed"] += 1

                if stop_on_error:
                    results["success"] = False
                    break

        if self._on_replay_progress:
            self._on_replay_progress(
                len(macro.actions), len(macro.actions),
                "Replay complete"
            )

        results["success"] = results["failed"] == 0
        return results

    def _handle_asset_import(self, action: RecordedAction) -> None:
        """Handle asset import action."""
        if not self._unreal_available:
            logger.info(f"[MOCK] Import asset: {action.parameters.get('source_path')} -> {action.target}")
            return

        import unreal  # noqa: F401

        source_path = action.parameters.get("source_path", "")
        import_options = action.parameters.get("import_options", {})

        task = unreal.AssetImportTask()
        task.filename = source_path
        task.destination_path = str(Path(action.target).parent)
        task.destination_name = Path(action.target).name
        task.replace_existing = import_options.get("replace_existing", True)
        task.automated = True
        task.save = import_options.get("save", True)

        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    def _handle_asset_delete(self, action: RecordedAction) -> None:
        """Handle asset delete action."""
        if not self._unreal_available:
            logger.info(f"[MOCK] Delete asset: {action.target}")
            return

        import unreal  # noqa: F401
        unreal.EditorAssetLibrary.delete_asset(action.target)

    def _handle_asset_rename(self, action: RecordedAction) -> None:
        """Handle asset rename action."""
        if not self._unreal_available:
            logger.info(f"[MOCK] Rename asset: {action.target} -> {action.parameters.get('new_name')}")
            return

        import unreal  # noqa: F401
        new_name = action.parameters.get("new_name", "")
        unreal.EditorAssetLibrary.rename_asset(action.target, new_name)

    def _handle_asset_move(self, action: RecordedAction) -> None:
        """Handle asset move action."""
        if not self._unreal_available:
            logger.info(f"[MOCK] Move asset: {action.target} -> {action.parameters.get('destination')}")
            return

        import unreal  # noqa: F401
        destination = action.parameters.get("destination", "")
        unreal.EditorAssetLibrary.rename_asset(action.target, destination)

    def _handle_actor_spawn(self, action: RecordedAction) -> None:
        """Handle actor spawn action."""
        if not self._unreal_available:
            logger.info(f"[MOCK] Spawn actor: {action.target}")
            return

        import unreal  # noqa: F401

        location = action.parameters.get("location", (0, 0, 0))
        rotation = action.parameters.get("rotation", (0, 0, 0))

        actor_class = unreal.load_class(None, action.target)
        if actor_class:
            loc = unreal.Vector(*location)
            rot = unreal.Rotator(*rotation)
            unreal.EditorLevelLibrary.spawn_actor_from_class(actor_class, loc, rot)

    def _handle_actor_delete(self, action: RecordedAction) -> None:
        """Handle actor delete action."""
        if not self._unreal_available:
            logger.info(f"[MOCK] Delete actor: {action.target}")
            return

        import unreal  # noqa: F401

        actors = unreal.EditorLevelLibrary.get_all_level_actors()
        for actor in actors:
            if actor.get_name() == action.target:
                actor.destroy_actor()
                break

    def _handle_actor_transform(self, action: RecordedAction) -> None:
        """Handle actor transform action."""
        if not self._unreal_available:
            logger.info(f"[MOCK] Transform actor: {action.target}")
            return

        import unreal  # noqa: F401

        actors = unreal.EditorLevelLibrary.get_all_level_actors()
        for actor in actors:
            if actor.get_name() == action.target:
                location = action.parameters.get("location")
                rotation = action.parameters.get("rotation")
                scale = action.parameters.get("scale")

                if location:
                    actor.set_actor_location(unreal.Vector(*location), False, False)
                if rotation:
                    actor.set_actor_rotation(unreal.Rotator(*rotation), False)
                if scale:
                    actor.set_actor_scale3d(unreal.Vector(*scale))
                break

    def _handle_material_assign(self, action: RecordedAction) -> None:
        """Handle material assignment action."""
        if not self._unreal_available:
            logger.info(f"[MOCK] Assign material to: {action.target}")
            return

        import unreal  # noqa: F401

        material_path = action.parameters.get("material_path", "")
        slot_index = action.parameters.get("slot_index", 0)

        material = unreal.load_asset(material_path)
        if not material:
            raise ValueError(f"Material not found: {material_path}")

        actors = unreal.EditorLevelLibrary.get_all_level_actors()
        for actor in actors:
            if actor.get_name() == action.target:
                mesh_component = actor.get_component_by_class(unreal.StaticMeshComponent)
                if mesh_component:
                    mesh_component.set_material(slot_index, material)
                break

    def _handle_editor_command(self, action: RecordedAction) -> None:
        """Handle editor command action."""
        if not self._unreal_available:
            logger.info(f"[MOCK] Execute command: {action.target}")
            return

        import unreal  # noqa: F401
        unreal.SystemLibrary.execute_console_command(None, action.target)

    def _handle_python_exec(self, action: RecordedAction) -> None:
        """Handle Python execution action."""
        code = action.parameters.get("code", "")
        context = action.parameters.get("context", {})

        if self._unreal_available:
            import unreal  # noqa: F401
            context["unreal"] = unreal

        exec(code, context)

    def _handle_custom(self, action: RecordedAction) -> None:
        """Handle custom action."""
        handler_name = action.parameters.get("handler")
        if handler_name and hasattr(self, handler_name):
            handler = getattr(self, handler_name)
            handler(action)
        else:
            logger.warning(f"No custom handler found: {handler_name}")
