"""
Level Operations Macros for UE5 Macro Automation.

Provides functions for organizing actors in levels, including grouping,
renaming, and setting up parent-child hierarchies.

Example Usage:
    >>> group_actors(actors, "TreeGroup")
    >>> rename_actors(actors, prefix="SM_", suffix="_01")
    >>> set_parent_hierarchy(children, parent)
    >>> organize_by_type("/Game/Levels/Main")
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from src.utils.profiler import profile_function

logger = logging.getLogger(__name__)


def _check_unreal() -> bool:
    """Check if Unreal Python API is available."""
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


UNREAL_AVAILABLE = _check_unreal()


@dataclass
class LevelOpResult:
    """
    Result of a level operation.

    Attributes:
        success: Whether operation was successful
        affected_actors: List of affected actor names
        error: Error message if failed
        details: Additional operation details
    """
    success: bool
    affected_actors: list[str] = field(default_factory=list)
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@profile_function
def group_actors(
    actors: list[Any],
    group_name: str,
    create_folder: bool = True
) -> LevelOpResult:
    """
    Group actors together under a folder or group actor.

    Args:
        actors: List of actors to group
        group_name: Name for the group
        create_folder: Whether to create a folder in the World Outliner

    Returns:
        LevelOpResult with operation details

    Example:
        >>> actors = get_selected_actors()
        >>> result = group_actors(actors, "Environment_Trees")
    """
    if not actors:
        return LevelOpResult(
            success=False,
            error="No actors provided"
        )

    if not UNREAL_AVAILABLE:
        actor_names = [f"Actor_{i}" for i in range(len(actors))]
        logger.info(f"[MOCK] Group {len(actors)} actors into: {group_name}")
        return LevelOpResult(
            success=True,
            affected_actors=actor_names,
            details={"group_name": group_name}
        )

    import unreal  # noqa: F401

    try:
        affected = []

        if create_folder:
            for actor in actors:
                actor.set_folder_path(group_name)
                affected.append(actor.get_name())
        else:
            group_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.GroupActor,
                unreal.Vector(0, 0, 0)
            )
            group_actor.set_actor_label(group_name)

            for actor in actors:
                group_actor.add(actor)
                affected.append(actor.get_name())

        logger.info(f"Grouped {len(affected)} actors into: {group_name}")
        return LevelOpResult(
            success=True,
            affected_actors=affected,
            details={"group_name": group_name}
        )

    except Exception as e:
        logger.error(f"Grouping failed: {e}")
        return LevelOpResult(
            success=False,
            error=str(e)
        )


@profile_function
def rename_actors(
    actors: list[Any],
    prefix: str = "",
    suffix: str = "",
    base_name: str | None = None,
    start_index: int = 1,
    padding: int = 2
) -> LevelOpResult:
    """
    Rename actors with prefix, suffix, and numbering.

    Args:
        actors: List of actors to rename
        prefix: Prefix to add to names
        suffix: Suffix to add to names
        base_name: Base name (if None, keeps original name)
        start_index: Starting index for numbering
        padding: Zero-padding for numbers

    Returns:
        LevelOpResult with operation details

    Example:
        >>> actors = get_selected_actors()
        >>> result = rename_actors(
        ...     actors,
        ...     prefix="SM_",
        ...     suffix="_Tree",
        ...     start_index=1,
        ...     padding=3
        ... )
        >>> # Results in: SM_Actor_Tree_001, SM_Actor_Tree_002, etc.
    """
    if not actors:
        return LevelOpResult(
            success=False,
            error="No actors provided"
        )

    if not UNREAL_AVAILABLE:
        affected = []
        for i, _ in enumerate(actors):
            index = start_index + i
            name = base_name or "Actor"
            new_name = f"{prefix}{name}{suffix}_{str(index).zfill(padding)}"
            affected.append(new_name)

        logger.info(f"[MOCK] Renamed {len(actors)} actors")
        return LevelOpResult(
            success=True,
            affected_actors=affected
        )


    try:
        affected = []
        rename_map = {}

        for i, actor in enumerate(actors):
            index = start_index + i
            original_name = actor.get_name()

            if base_name:
                name = base_name
            else:
                name = original_name

            new_name = f"{prefix}{name}{suffix}"
            if len(actors) > 1:
                new_name += f"_{str(index).zfill(padding)}"

            actor.set_actor_label(new_name)
            affected.append(new_name)
            rename_map[original_name] = new_name

        logger.info(f"Renamed {len(affected)} actors")
        return LevelOpResult(
            success=True,
            affected_actors=affected,
            details={"rename_map": rename_map}
        )

    except Exception as e:
        logger.error(f"Renaming failed: {e}")
        return LevelOpResult(
            success=False,
            error=str(e)
        )


@profile_function
def set_parent_hierarchy(
    children: list[Any],
    parent: Any
) -> LevelOpResult:
    """
    Set parent-child hierarchy for actors.

    Args:
        children: List of child actors
        parent: Parent actor

    Returns:
        LevelOpResult with operation details

    Example:
        >>> parent = get_actor_by_name("TreeGroup")
        >>> children = get_selected_actors()
        >>> result = set_parent_hierarchy(children, parent)
    """
    if not children:
        return LevelOpResult(
            success=False,
            error="No child actors provided"
        )

    if parent is None:
        return LevelOpResult(
            success=False,
            error="No parent actor provided"
        )

    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Set parent for {len(children)} actors")
        return LevelOpResult(
            success=True,
            affected_actors=[f"Child_{i}" for i in range(len(children))]
        )

    import unreal  # noqa: F401

    try:
        affected = []

        for child in children:
            child.attach_to_actor(
                parent,
                "",
                unreal.AttachmentRule.KEEP_WORLD,
                unreal.AttachmentRule.KEEP_WORLD,
                unreal.AttachmentRule.KEEP_WORLD,
                False
            )
            affected.append(child.get_name())

        logger.info(f"Set parent for {len(affected)} actors")
        return LevelOpResult(
            success=True,
            affected_actors=affected,
            details={"parent": parent.get_name()}
        )

    except Exception as e:
        logger.error(f"Hierarchy setup failed: {e}")
        return LevelOpResult(
            success=False,
            error=str(e)
        )


@profile_function
def organize_by_type(
    actors: list[Any] | None = None,
    create_folders: bool = True
) -> LevelOpResult:
    """
    Organize actors into folders based on their type.

    Args:
        actors: List of actors (if None, uses all level actors)
        create_folders: Whether to create folders in World Outliner

    Returns:
        LevelOpResult with operation details

    Example:
        >>> result = organize_by_type()
        >>> # Creates folders: Lights, StaticMeshes, Cameras, etc.
    """
    if not UNREAL_AVAILABLE:
        logger.info("[MOCK] Organize actors by type")
        return LevelOpResult(
            success=True,
            details={"folders_created": ["Lights", "StaticMeshes", "Cameras"]}
        )

    import unreal  # noqa: F401

    try:
        if actors is None:
            actors = list(unreal.EditorLevelLibrary.get_all_level_actors())

        type_groups: dict[str, list[Any]] = {}

        for actor in actors:
            actor_class = actor.get_class().get_name()

            folder_name = _get_folder_for_class(actor_class)

            if folder_name not in type_groups:
                type_groups[folder_name] = []
            type_groups[folder_name].append(actor)

        affected = []
        if create_folders:
            for folder_name, folder_actors in type_groups.items():
                for actor in folder_actors:
                    actor.set_folder_path(folder_name)
                    affected.append(actor.get_name())

        logger.info(f"Organized {len(affected)} actors into {len(type_groups)} folders")
        return LevelOpResult(
            success=True,
            affected_actors=affected,
            details={"folders_created": list(type_groups.keys())}
        )

    except Exception as e:
        logger.error(f"Organization failed: {e}")
        return LevelOpResult(
            success=False,
            error=str(e)
        )


def _get_folder_for_class(class_name: str) -> str:
    """Get folder name for an actor class."""
    class_to_folder = {
        "StaticMeshActor": "StaticMeshes",
        "SkeletalMeshActor": "SkeletalMeshes",
        "PointLight": "Lights",
        "SpotLight": "Lights",
        "DirectionalLight": "Lights",
        "RectLight": "Lights",
        "SkyLight": "Lights",
        "CameraActor": "Cameras",
        "CineCameraActor": "Cameras",
        "PlayerStart": "Gameplay",
        "TriggerBox": "Triggers",
        "TriggerSphere": "Triggers",
        "TriggerCapsule": "Triggers",
        "DecalActor": "Decals",
        "ExponentialHeightFog": "Atmosphere",
        "SkyAtmosphere": "Atmosphere",
        "VolumetricCloud": "Atmosphere",
        "PostProcessVolume": "PostProcess",
        "ReflectionCapture": "Reflections",
        "SphereReflectionCapture": "Reflections",
        "BoxReflectionCapture": "Reflections",
        "AudioVolume": "Audio",
        "AmbientSound": "Audio",
        "Landscape": "Terrain",
        "LandscapeStreamingProxy": "Terrain",
        "Foliage": "Foliage",
        "InstancedFoliageActor": "Foliage",
    }

    return class_to_folder.get(class_name, "Other")


@profile_function
def move_actors_to_folder(
    actors: list[Any],
    folder_path: str
) -> LevelOpResult:
    """
    Move actors to a specific folder in the World Outliner.

    Args:
        actors: List of actors to move
        folder_path: Folder path (e.g., "Environment/Trees")

    Returns:
        LevelOpResult with operation details

    Example:
        >>> actors = get_selected_actors()
        >>> result = move_actors_to_folder(actors, "Environment/Trees")
    """
    if not actors:
        return LevelOpResult(
            success=False,
            error="No actors provided"
        )

    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Move {len(actors)} actors to folder: {folder_path}")
        return LevelOpResult(
            success=True,
            affected_actors=[f"Actor_{i}" for i in range(len(actors))]
        )

    try:
        affected = []

        for actor in actors:
            actor.set_folder_path(folder_path)
            affected.append(actor.get_name())

        logger.info(f"Moved {len(affected)} actors to: {folder_path}")
        return LevelOpResult(
            success=True,
            affected_actors=affected,
            details={"folder_path": folder_path}
        )

    except Exception as e:
        logger.error(f"Move to folder failed: {e}")
        return LevelOpResult(
            success=False,
            error=str(e)
        )


@profile_function
def align_actors(
    actors: list[Any],
    axis: str = "z",
    align_to: str = "min"
) -> LevelOpResult:
    """
    Align actors along an axis.

    Args:
        actors: List of actors to align
        axis: Axis to align on ("x", "y", "z")
        align_to: Alignment target ("min", "max", "center", "first")

    Returns:
        LevelOpResult with operation details

    Example:
        >>> actors = get_selected_actors()
        >>> result = align_actors(actors, axis="z", align_to="min")
    """
    if not actors or len(actors) < 2:
        return LevelOpResult(
            success=False,
            error="Need at least 2 actors to align"
        )

    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Align {len(actors)} actors on {axis} axis")
        return LevelOpResult(
            success=True,
            affected_actors=[f"Actor_{i}" for i in range(len(actors))]
        )

    import unreal  # noqa: F401

    try:
        axis_index = {"x": 0, "y": 1, "z": 2}.get(axis.lower(), 2)

        positions = []
        for actor in actors:
            loc = actor.get_actor_location()
            positions.append([loc.x, loc.y, loc.z])

        axis_values = [p[axis_index] for p in positions]

        if align_to == "min":
            target_value = min(axis_values)
        elif align_to == "max":
            target_value = max(axis_values)
        elif align_to == "center":
            target_value = sum(axis_values) / len(axis_values)
        elif align_to == "first":
            target_value = axis_values[0]
        else:
            target_value = min(axis_values)

        affected = []
        for actor, pos in zip(actors, positions):
            pos[axis_index] = target_value
            actor.set_actor_location(
                unreal.Vector(pos[0], pos[1], pos[2]),
                False, False
            )
            affected.append(actor.get_name())

        logger.info(f"Aligned {len(affected)} actors on {axis} axis")
        return LevelOpResult(
            success=True,
            affected_actors=affected,
            details={"axis": axis, "align_to": align_to, "value": target_value}
        )

    except Exception as e:
        logger.error(f"Alignment failed: {e}")
        return LevelOpResult(
            success=False,
            error=str(e)
        )


@profile_function
def distribute_actors(
    actors: list[Any],
    axis: str = "x",
    spacing: float | None = None
) -> LevelOpResult:
    """
    Distribute actors evenly along an axis.

    Args:
        actors: List of actors to distribute
        axis: Axis to distribute along ("x", "y", "z")
        spacing: Fixed spacing (if None, distributes evenly between first and last)

    Returns:
        LevelOpResult with operation details

    Example:
        >>> actors = get_selected_actors()
        >>> result = distribute_actors(actors, axis="x", spacing=100)
    """
    if not actors or len(actors) < 2:
        return LevelOpResult(
            success=False,
            error="Need at least 2 actors to distribute"
        )

    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Distribute {len(actors)} actors on {axis} axis")
        return LevelOpResult(
            success=True,
            affected_actors=[f"Actor_{i}" for i in range(len(actors))]
        )

    import unreal  # noqa: F401

    try:
        axis_index = {"x": 0, "y": 1, "z": 2}.get(axis.lower(), 0)

        actor_positions = []
        for actor in actors:
            loc = actor.get_actor_location()
            actor_positions.append((actor, [loc.x, loc.y, loc.z]))

        actor_positions.sort(key=lambda x: x[1][axis_index])

        if spacing is not None:
            start_value = actor_positions[0][1][axis_index]
            for i, (actor, pos) in enumerate(actor_positions):
                pos[axis_index] = start_value + (i * spacing)
                actor.set_actor_location(
                    unreal.Vector(pos[0], pos[1], pos[2]),
                    False, False
                )
        else:
            start_value = actor_positions[0][1][axis_index]
            end_value = actor_positions[-1][1][axis_index]
            total_distance = end_value - start_value
            step = total_distance / (len(actors) - 1) if len(actors) > 1 else 0

            for i, (actor, pos) in enumerate(actor_positions):
                pos[axis_index] = start_value + (i * step)
                actor.set_actor_location(
                    unreal.Vector(pos[0], pos[1], pos[2]),
                    False, False
                )

        affected = [actor.get_name() for actor, _ in actor_positions]

        logger.info(f"Distributed {len(affected)} actors on {axis} axis")
        return LevelOpResult(
            success=True,
            affected_actors=affected,
            details={"axis": axis, "spacing": spacing}
        )

    except Exception as e:
        logger.error(f"Distribution failed: {e}")
        return LevelOpResult(
            success=False,
            error=str(e)
        )


def get_actors_by_name_pattern(pattern: str) -> list[Any]:
    r"""
    Get actors matching a name pattern.

    Args:
        pattern: Regex pattern to match actor names

    Returns:
        List of matching actors

    Example:
        >>> trees = get_actors_by_name_pattern(r"Tree_\d+")
    """
    if not UNREAL_AVAILABLE:
        return []

    import unreal  # noqa: F401

    all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
    matching = []

    for actor in all_actors:
        if re.search(pattern, actor.get_name()):
            matching.append(actor)

    return matching


def get_actors_in_folder(folder_path: str) -> list[Any]:
    """
    Get all actors in a specific folder.

    Args:
        folder_path: Folder path in World Outliner

    Returns:
        List of actors in the folder

    Example:
        >>> trees = get_actors_in_folder("Environment/Trees")
    """
    if not UNREAL_AVAILABLE:
        return []

    import unreal  # noqa: F401

    all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
    matching = []

    for actor in all_actors:
        if actor.get_folder_path() == folder_path:
            matching.append(actor)

    return matching
