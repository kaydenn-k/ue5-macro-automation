"""
Unreal Engine helper utilities for UE5 Macro Automation.

Provides convenient wrappers around common Unreal Engine operations
and editor functionality.

Example Usage:
    >>> actors = get_selected_actors()
    >>> assets = get_selected_assets()
    >>> path = get_content_browser_path()
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _check_unreal() -> bool:
    """Check if Unreal Python API is available."""
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


UNREAL_AVAILABLE = _check_unreal()


def get_selected_actors() -> list[Any]:
    """
    Get currently selected actors in the level.

    Returns:
        List of selected actor objects

    Example:
        >>> actors = get_selected_actors()
        >>> for actor in actors:
        ...     print(actor.get_name())
    """
    if not UNREAL_AVAILABLE:
        logger.warning("Unreal not available - returning empty list")
        return []

    import unreal  # noqa: F401
    return list(unreal.EditorLevelLibrary.get_selected_level_actors())


def get_selected_assets() -> list[Any]:
    """
    Get currently selected assets in the Content Browser.

    Returns:
        List of selected asset data objects

    Example:
        >>> assets = get_selected_assets()
        >>> for asset in assets:
        ...     print(asset.asset_name)
    """
    if not UNREAL_AVAILABLE:
        logger.warning("Unreal not available - returning empty list")
        return []

    import unreal  # noqa: F401
    return list(unreal.EditorUtilityLibrary.get_selected_asset_data())


def get_content_browser_path() -> str:
    """
    Get the current path in the Content Browser.

    Returns:
        Current content browser path

    Example:
        >>> path = get_content_browser_path()
        '/Game/Meshes'
    """
    if not UNREAL_AVAILABLE:
        return "/Game"

    import unreal  # noqa: F401

    try:
        paths = unreal.EditorUtilityLibrary.get_current_content_browser_path()
        return paths if paths else "/Game"
    except Exception:
        return "/Game"


def is_valid_asset_path(path: str) -> bool:
    """
    Check if a path is a valid Unreal asset path.

    Args:
        path: Asset path to validate

    Returns:
        True if valid

    Example:
        >>> is_valid_asset_path("/Game/Meshes/Tree")
        True
        >>> is_valid_asset_path("C:/Users/file.fbx")
        False
    """
    if not path:
        return False

    if not path.startswith("/Game") and not path.startswith("/Engine"):
        return False

    invalid_chars = '<>:"|?*'
    return not any(char in path for char in invalid_chars)


def asset_exists(path: str) -> bool:
    """
    Check if an asset exists at the given path.

    Args:
        path: Asset path to check

    Returns:
        True if asset exists

    Example:
        >>> asset_exists("/Game/Meshes/Tree")
        True
    """
    if not UNREAL_AVAILABLE:
        return False

    import unreal  # noqa: F401
    return unreal.EditorAssetLibrary.does_asset_exist(path)


def load_asset(path: str) -> Any | None:
    """
    Load an asset from the given path.

    Args:
        path: Asset path

    Returns:
        Loaded asset or None

    Example:
        >>> mesh = load_asset("/Game/Meshes/Tree")
    """
    if not UNREAL_AVAILABLE:
        return None

    import unreal  # noqa: F401
    return unreal.load_asset(path)


def get_asset_class(path: str) -> str | None:
    """
    Get the class name of an asset.

    Args:
        path: Asset path

    Returns:
        Class name or None

    Example:
        >>> get_asset_class("/Game/Meshes/Tree")
        'StaticMesh'
    """
    if not UNREAL_AVAILABLE:
        return None

    import unreal  # noqa: F401

    asset = unreal.load_asset(path)
    if asset:
        return asset.get_class().get_name()
    return None


def get_all_actors_of_class(actor_class: str) -> list[Any]:
    """
    Get all actors of a specific class in the current level.

    Args:
        actor_class: Class name to filter by

    Returns:
        List of matching actors

    Example:
        >>> lights = get_all_actors_of_class("PointLight")
    """
    if not UNREAL_AVAILABLE:
        return []

    import unreal  # noqa: F401

    all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
    return [
        actor for actor in all_actors
        if actor.get_class().get_name() == actor_class
    ]


def spawn_actor(
    actor_class: str,
    location: tuple[float, float, float] = (0, 0, 0),
    rotation: tuple[float, float, float] = (0, 0, 0),
    scale: tuple[float, float, float] = (1, 1, 1)
) -> Any | None:
    """
    Spawn an actor in the current level.

    Args:
        actor_class: Class path of the actor
        location: World location (x, y, z)
        rotation: Rotation (pitch, yaw, roll)
        scale: Scale (x, y, z)

    Returns:
        Spawned actor or None

    Example:
        >>> actor = spawn_actor(
        ...     "/Script/Engine.PointLight",
        ...     location=(100, 200, 300)
        ... )
    """
    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Spawn actor: {actor_class} at {location}")
        return None

    import unreal  # noqa: F401

    actor_class_obj = unreal.load_class(None, actor_class)
    if not actor_class_obj:
        logger.error(f"Failed to load actor class: {actor_class}")
        return None

    loc = unreal.Vector(*location)
    rot = unreal.Rotator(*rotation)

    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        actor_class_obj, loc, rot
    )

    if actor and scale != (1, 1, 1):
        actor.set_actor_scale3d(unreal.Vector(*scale))

    return actor


def delete_actor(actor: Any) -> bool:
    """
    Delete an actor from the level.

    Args:
        actor: Actor to delete

    Returns:
        True if successful
    """
    if not UNREAL_AVAILABLE:
        return True

    try:
        actor.destroy_actor()
        return True
    except Exception as e:
        logger.error(f"Failed to delete actor: {e}")
        return False


def get_actor_transform(actor: Any) -> dict[str, tuple[float, float, float]]:
    """
    Get an actor's transform.

    Args:
        actor: Actor to get transform from

    Returns:
        Dictionary with location, rotation, scale

    Example:
        >>> transform = get_actor_transform(actor)
        >>> print(transform["location"])
        (100.0, 200.0, 300.0)
    """
    if not UNREAL_AVAILABLE:
        return {
            "location": (0, 0, 0),
            "rotation": (0, 0, 0),
            "scale": (1, 1, 1),
        }


    loc = actor.get_actor_location()
    rot = actor.get_actor_rotation()
    scale = actor.get_actor_scale3d()

    return {
        "location": (loc.x, loc.y, loc.z),
        "rotation": (rot.pitch, rot.yaw, rot.roll),
        "scale": (scale.x, scale.y, scale.z),
    }


def set_actor_transform(
    actor: Any,
    location: tuple[float, float, float] | None = None,
    rotation: tuple[float, float, float] | None = None,
    scale: tuple[float, float, float] | None = None
) -> bool:
    """
    Set an actor's transform.

    Args:
        actor: Actor to transform
        location: New location (or None to keep current)
        rotation: New rotation (or None to keep current)
        scale: New scale (or None to keep current)

    Returns:
        True if successful

    Example:
        >>> set_actor_transform(actor, location=(100, 200, 300))
    """
    if not UNREAL_AVAILABLE:
        return True

    import unreal  # noqa: F401

    try:
        if location:
            actor.set_actor_location(unreal.Vector(*location), False, False)
        if rotation:
            actor.set_actor_rotation(unreal.Rotator(*rotation), False)
        if scale:
            actor.set_actor_scale3d(unreal.Vector(*scale))
        return True
    except Exception as e:
        logger.error(f"Failed to set transform: {e}")
        return False


def select_actors(actors: list[Any], add_to_selection: bool = False) -> None:
    """
    Select actors in the editor.

    Args:
        actors: List of actors to select
        add_to_selection: Whether to add to current selection

    Example:
        >>> select_actors([actor1, actor2])
    """
    if not UNREAL_AVAILABLE:
        return

    import unreal  # noqa: F401

    if not add_to_selection:
        unreal.EditorLevelLibrary.set_selected_level_actors([])

    for actor in actors:
        unreal.EditorLevelLibrary.set_actor_selection_state(actor, True)


def focus_on_actors(actors: list[Any]) -> None:
    """
    Focus the viewport on selected actors.

    Args:
        actors: Actors to focus on
    """
    if not UNREAL_AVAILABLE:
        return

    import unreal  # noqa: F401

    select_actors(actors)
    unreal.EditorLevelLibrary.pilot_level_actor(actors[0] if actors else None)


def get_static_mesh_component(actor: Any) -> Any | None:
    """
    Get the static mesh component from an actor.

    Args:
        actor: Actor to get component from

    Returns:
        StaticMeshComponent or None
    """
    if not UNREAL_AVAILABLE:
        return None

    import unreal  # noqa: F401
    return actor.get_component_by_class(unreal.StaticMeshComponent)


def set_material(
    actor: Any,
    material_path: str,
    slot_index: int = 0
) -> bool:
    """
    Set material on an actor's mesh component.

    Args:
        actor: Actor to set material on
        material_path: Path to material asset
        slot_index: Material slot index

    Returns:
        True if successful

    Example:
        >>> set_material(actor, "/Game/Materials/Wood", 0)
    """
    if not UNREAL_AVAILABLE:
        return True

    import unreal  # noqa: F401

    material = unreal.load_asset(material_path)
    if not material:
        logger.error(f"Material not found: {material_path}")
        return False

    mesh_comp = get_static_mesh_component(actor)
    if mesh_comp:
        mesh_comp.set_material(slot_index, material)
        return True

    return False


def create_folder(path: str) -> bool:
    """
    Create a folder in the Content Browser.

    Args:
        path: Folder path (e.g., "/Game/NewFolder")

    Returns:
        True if successful

    Example:
        >>> create_folder("/Game/Meshes/Trees")
    """
    if not UNREAL_AVAILABLE:
        return True

    import unreal  # noqa: F401

    try:
        unreal.EditorAssetLibrary.make_directory(path)
        return True
    except Exception as e:
        logger.error(f"Failed to create folder: {e}")
        return False


def rename_asset(old_path: str, new_name: str) -> bool:
    """
    Rename an asset.

    Args:
        old_path: Current asset path
        new_name: New name for the asset

    Returns:
        True if successful

    Example:
        >>> rename_asset("/Game/Meshes/OldName", "NewName")
    """
    if not UNREAL_AVAILABLE:
        return True

    import unreal  # noqa: F401

    try:
        parent_path = str(Path(old_path).parent)
        new_path = f"{parent_path}/{new_name}"
        return unreal.EditorAssetLibrary.rename_asset(old_path, new_path)
    except Exception as e:
        logger.error(f"Failed to rename asset: {e}")
        return False


def move_asset(source_path: str, dest_path: str) -> bool:
    """
    Move an asset to a new location.

    Args:
        source_path: Current asset path
        dest_path: Destination path

    Returns:
        True if successful

    Example:
        >>> move_asset("/Game/Meshes/Tree", "/Game/Environment/Tree")
    """
    if not UNREAL_AVAILABLE:
        return True

    import unreal  # noqa: F401

    try:
        return unreal.EditorAssetLibrary.rename_asset(source_path, dest_path)
    except Exception as e:
        logger.error(f"Failed to move asset: {e}")
        return False


def duplicate_asset(source_path: str, dest_path: str) -> bool:
    """
    Duplicate an asset.

    Args:
        source_path: Source asset path
        dest_path: Destination path for the duplicate

    Returns:
        True if successful

    Example:
        >>> duplicate_asset("/Game/Meshes/Tree", "/Game/Meshes/Tree_Copy")
    """
    if not UNREAL_AVAILABLE:
        return True

    import unreal  # noqa: F401

    try:
        return unreal.EditorAssetLibrary.duplicate_asset(source_path, dest_path)
    except Exception as e:
        logger.error(f"Failed to duplicate asset: {e}")
        return False


def delete_asset(path: str) -> bool:
    """
    Delete an asset.

    Args:
        path: Asset path to delete

    Returns:
        True if successful

    Example:
        >>> delete_asset("/Game/Meshes/OldTree")
    """
    if not UNREAL_AVAILABLE:
        return True

    import unreal  # noqa: F401

    try:
        return unreal.EditorAssetLibrary.delete_asset(path)
    except Exception as e:
        logger.error(f"Failed to delete asset: {e}")
        return False


def save_asset(path: str) -> bool:
    """
    Save an asset.

    Args:
        path: Asset path to save

    Returns:
        True if successful
    """
    if not UNREAL_AVAILABLE:
        return True

    import unreal  # noqa: F401

    try:
        return unreal.EditorAssetLibrary.save_asset(path)
    except Exception as e:
        logger.error(f"Failed to save asset: {e}")
        return False


def save_all_dirty_packages() -> bool:
    """
    Save all modified packages.

    Returns:
        True if successful
    """
    if not UNREAL_AVAILABLE:
        return True

    import unreal  # noqa: F401

    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        return True
    except Exception as e:
        logger.error(f"Failed to save packages: {e}")
        return False


def execute_console_command(command: str) -> None:
    """
    Execute a console command.

    Args:
        command: Console command to execute

    Example:
        >>> execute_console_command("stat fps")
    """
    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Execute command: {command}")
        return

    import unreal  # noqa: F401
    unreal.SystemLibrary.execute_console_command(None, command)


def get_editor_world() -> Any | None:
    """
    Get the current editor world.

    Returns:
        World object or None
    """
    if not UNREAL_AVAILABLE:
        return None

    import unreal  # noqa: F401
    return unreal.EditorLevelLibrary.get_editor_world()


def begin_transaction(description: str) -> None:
    """
    Begin an editor transaction for undo support.

    Args:
        description: Transaction description
    """
    if not UNREAL_AVAILABLE:
        return

    import unreal  # noqa: F401
    unreal.SystemLibrary.begin_transaction(description)


def end_transaction() -> None:
    """End the current editor transaction."""
    if not UNREAL_AVAILABLE:
        return

    import unreal  # noqa: F401
    unreal.SystemLibrary.end_transaction()
