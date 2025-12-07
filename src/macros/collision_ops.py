"""
Collision Operations Macros for UE5 Macro Automation.

Provides functions for generating and configuring collision for static meshes.

Example Usage:
    >>> generate_collision("/Game/Meshes/Tree", CollisionType.CONVEX_DECOMPOSITION)
    >>> batch_generate_collision(["/Game/Meshes/Rock1", "/Game/Meshes/Rock2"])
    >>> set_collision_complexity("/Game/Meshes/Building", "complex")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from src.utils.logging_utils import ProgressTracker
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


class CollisionType(Enum):
    """Types of collision generation."""
    BOX = auto()
    SPHERE = auto()
    CAPSULE = auto()
    CONVEX = auto()
    CONVEX_DECOMPOSITION = auto()
    AUTO_CONVEX = auto()
    USE_COMPLEX_AS_SIMPLE = auto()
    USE_SIMPLE_AS_COMPLEX = auto()


@dataclass
class CollisionSettings:
    """
    Settings for collision generation.

    Attributes:
        collision_type: Type of collision to generate
        hull_count: Number of convex hulls for decomposition
        max_hull_verts: Maximum vertices per hull
        hull_precision: Precision for hull generation (0-100)
        simplify_collision: Whether to simplify the collision
        remove_degenerates: Remove degenerate triangles
    """
    collision_type: CollisionType = CollisionType.AUTO_CONVEX
    hull_count: int = 4
    max_hull_verts: int = 16
    hull_precision: int = 100
    simplify_collision: bool = True
    remove_degenerates: bool = True


@dataclass
class CollisionResult:
    """
    Result of a collision operation.

    Attributes:
        success: Whether operation was successful
        asset_path: Path to the affected asset
        collision_type: Type of collision generated
        error: Error message if failed
        hull_count: Number of hulls generated
    """
    success: bool
    asset_path: str = ""
    collision_type: CollisionType | None = None
    error: str | None = None
    hull_count: int = 0


@profile_function
def generate_collision(
    asset_path: str,
    collision_type: CollisionType = CollisionType.AUTO_CONVEX,
    settings: CollisionSettings | None = None
) -> CollisionResult:
    """
    Generate collision for a static mesh.

    Args:
        asset_path: Path to the static mesh
        collision_type: Type of collision to generate
        settings: Collision generation settings

    Returns:
        CollisionResult with operation details

    Example:
        >>> result = generate_collision(
        ...     "/Game/Meshes/Tree",
        ...     CollisionType.CONVEX_DECOMPOSITION,
        ...     settings=CollisionSettings(hull_count=8)
        ... )
    """
    settings = settings or CollisionSettings(collision_type=collision_type)

    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Generate collision: {asset_path} ({collision_type.name})")
        return CollisionResult(
            success=True,
            asset_path=asset_path,
            collision_type=collision_type,
            hull_count=settings.hull_count
        )

    import unreal  # noqa: F401

    try:
        mesh = unreal.load_asset(asset_path)
        if not mesh or not isinstance(mesh, unreal.StaticMesh):
            return CollisionResult(
                success=False,
                asset_path=asset_path,
                error=f"Asset is not a static mesh: {asset_path}"
            )

        body_setup = mesh.get_editor_property("body_setup")
        if not body_setup:
            return CollisionResult(
                success=False,
                asset_path=asset_path,
                error="No body setup found on mesh"
            )

        if collision_type == CollisionType.BOX:
            _generate_box_collision(mesh)
        elif collision_type == CollisionType.SPHERE:
            _generate_sphere_collision(mesh)
        elif collision_type == CollisionType.CAPSULE:
            _generate_capsule_collision(mesh)
        elif collision_type == CollisionType.CONVEX:
            _generate_convex_collision(mesh, settings)
        elif collision_type == CollisionType.CONVEX_DECOMPOSITION:
            _generate_convex_decomposition(mesh, settings)
        elif collision_type == CollisionType.AUTO_CONVEX:
            _generate_auto_convex(mesh, settings)
        elif collision_type == CollisionType.USE_COMPLEX_AS_SIMPLE:
            body_setup.set_editor_property(
                "collision_trace_flag",
                unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
            )
        elif collision_type == CollisionType.USE_SIMPLE_AS_COMPLEX:
            body_setup.set_editor_property(
                "collision_trace_flag",
                unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX
            )

        unreal.EditorAssetLibrary.save_asset(asset_path)

        logger.info(f"Generated collision: {asset_path} ({collision_type.name})")
        return CollisionResult(
            success=True,
            asset_path=asset_path,
            collision_type=collision_type,
            hull_count=settings.hull_count
        )

    except Exception as e:
        logger.error(f"Collision generation failed: {e}")
        return CollisionResult(
            success=False,
            asset_path=asset_path,
            error=str(e)
        )


def _generate_box_collision(mesh: Any) -> None:
    """Generate box collision for a mesh."""
    if not UNREAL_AVAILABLE:
        return

    import unreal  # noqa: F401

    static_mesh_editor = unreal.StaticMeshEditorSubsystem()
    static_mesh_editor.add_simple_collisions(
        mesh,
        unreal.ScriptingCollisionShapeType.BOX
    )


def _generate_sphere_collision(mesh: Any) -> None:
    """Generate sphere collision for a mesh."""
    if not UNREAL_AVAILABLE:
        return

    import unreal  # noqa: F401

    static_mesh_editor = unreal.StaticMeshEditorSubsystem()
    static_mesh_editor.add_simple_collisions(
        mesh,
        unreal.ScriptingCollisionShapeType.SPHERE
    )


def _generate_capsule_collision(mesh: Any) -> None:
    """Generate capsule collision for a mesh."""
    if not UNREAL_AVAILABLE:
        return

    import unreal  # noqa: F401

    static_mesh_editor = unreal.StaticMeshEditorSubsystem()
    static_mesh_editor.add_simple_collisions(
        mesh,
        unreal.ScriptingCollisionShapeType.CAPSULE
    )


def _generate_convex_collision(mesh: Any, settings: CollisionSettings) -> None:
    """Generate convex collision for a mesh."""
    if not UNREAL_AVAILABLE:
        return

    import unreal  # noqa: F401

    static_mesh_editor = unreal.StaticMeshEditorSubsystem()
    static_mesh_editor.set_convex_decomposition_collisions(
        mesh,
        settings.hull_count,
        settings.max_hull_verts,
        settings.hull_precision
    )


def _generate_convex_decomposition(mesh: Any, settings: CollisionSettings) -> None:
    """Generate convex decomposition collision for a mesh."""
    if not UNREAL_AVAILABLE:
        return

    import unreal  # noqa: F401

    static_mesh_editor = unreal.StaticMeshEditorSubsystem()
    static_mesh_editor.set_convex_decomposition_collisions(
        mesh,
        settings.hull_count,
        settings.max_hull_verts,
        settings.hull_precision
    )


def _generate_auto_convex(mesh: Any, settings: CollisionSettings) -> None:
    """Generate auto convex collision for a mesh."""
    if not UNREAL_AVAILABLE:
        return

    import unreal  # noqa: F401

    static_mesh_editor = unreal.StaticMeshEditorSubsystem()
    static_mesh_editor.set_convex_decomposition_collisions(
        mesh,
        settings.hull_count,
        settings.max_hull_verts,
        settings.hull_precision
    )


@profile_function
def batch_generate_collision(
    asset_paths: list[str],
    collision_type: CollisionType = CollisionType.AUTO_CONVEX,
    settings: CollisionSettings | None = None,
    progress_callback: callable | None = None
) -> list[CollisionResult]:
    """
    Generate collision for multiple static meshes.

    Args:
        asset_paths: List of asset paths
        collision_type: Type of collision to generate
        settings: Collision generation settings
        progress_callback: Progress callback function

    Returns:
        List of CollisionResults

    Example:
        >>> paths = ["/Game/Meshes/Rock1", "/Game/Meshes/Rock2"]
        >>> results = batch_generate_collision(paths, CollisionType.CONVEX)
    """
    results: list[CollisionResult] = []

    with ProgressTracker("Generating Collision", total=len(asset_paths)) as tracker:
        for i, asset_path in enumerate(asset_paths):
            if progress_callback:
                progress_callback(i, len(asset_paths), f"Processing: {asset_path}")

            tracker.update(0, f"Processing: {asset_path.split('/')[-1]}")

            result = generate_collision(asset_path, collision_type, settings)
            results.append(result)

            tracker.update(1)

    successful = sum(1 for r in results if r.success)
    logger.info(f"Generated collision: {successful}/{len(results)} successful")

    return results


@profile_function
def set_collision_complexity(
    asset_path: str,
    complexity: str = "simple"
) -> CollisionResult:
    """
    Set collision complexity for a static mesh.

    Args:
        asset_path: Path to the static mesh
        complexity: Complexity level ("simple", "complex", "default")

    Returns:
        CollisionResult with operation details

    Example:
        >>> result = set_collision_complexity("/Game/Meshes/Building", "complex")
    """
    complexity_map = {
        "simple": CollisionType.USE_SIMPLE_AS_COMPLEX,
        "complex": CollisionType.USE_COMPLEX_AS_SIMPLE,
        "default": CollisionType.AUTO_CONVEX,
    }

    collision_type = complexity_map.get(complexity.lower(), CollisionType.AUTO_CONVEX)

    return generate_collision(asset_path, collision_type)


@profile_function
def remove_collision(asset_path: str) -> CollisionResult:
    """
    Remove all collision from a static mesh.

    Args:
        asset_path: Path to the static mesh

    Returns:
        CollisionResult with operation details

    Example:
        >>> result = remove_collision("/Game/Meshes/Decoration")
    """
    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Remove collision: {asset_path}")
        return CollisionResult(success=True, asset_path=asset_path)

    import unreal  # noqa: F401

    try:
        mesh = unreal.load_asset(asset_path)
        if not mesh or not isinstance(mesh, unreal.StaticMesh):
            return CollisionResult(
                success=False,
                asset_path=asset_path,
                error=f"Asset is not a static mesh: {asset_path}"
            )

        static_mesh_editor = unreal.StaticMeshEditorSubsystem()
        static_mesh_editor.remove_collisions(mesh)

        unreal.EditorAssetLibrary.save_asset(asset_path)

        logger.info(f"Removed collision: {asset_path}")
        return CollisionResult(success=True, asset_path=asset_path)

    except Exception as e:
        logger.error(f"Collision removal failed: {e}")
        return CollisionResult(
            success=False,
            asset_path=asset_path,
            error=str(e)
        )


def get_collision_info(asset_path: str) -> dict[str, Any]:
    """
    Get collision information for a static mesh.

    Args:
        asset_path: Path to the static mesh

    Returns:
        Dictionary with collision information

    Example:
        >>> info = get_collision_info("/Game/Meshes/Tree")
        >>> print(f"Has collision: {info['has_collision']}")
    """
    if not UNREAL_AVAILABLE:
        return {
            "has_collision": True,
            "collision_type": "unknown",
            "hull_count": 0,
        }

    import unreal  # noqa: F401

    try:
        mesh = unreal.load_asset(asset_path)
        if not mesh or not isinstance(mesh, unreal.StaticMesh):
            return {"error": "Not a static mesh"}

        body_setup = mesh.get_editor_property("body_setup")
        if not body_setup:
            return {"has_collision": False}

        collision_flag = body_setup.get_editor_property("collision_trace_flag")

        return {
            "has_collision": True,
            "collision_trace_flag": str(collision_flag),
            "convex_elements": len(body_setup.get_editor_property("agg_geom").convex_elems),
            "box_elements": len(body_setup.get_editor_property("agg_geom").box_elems),
            "sphere_elements": len(body_setup.get_editor_property("agg_geom").sphere_elems),
        }

    except Exception as e:
        logger.error(f"Failed to get collision info: {e}")
        return {"error": str(e)}


def copy_collision(source_path: str, target_path: str) -> CollisionResult:
    """
    Copy collision from one mesh to another.

    Args:
        source_path: Path to source mesh
        target_path: Path to target mesh

    Returns:
        CollisionResult with operation details

    Example:
        >>> result = copy_collision("/Game/Meshes/Tree1", "/Game/Meshes/Tree2")
    """
    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Copy collision: {source_path} -> {target_path}")
        return CollisionResult(success=True, asset_path=target_path)

    import unreal  # noqa: F401

    try:
        source_mesh = unreal.load_asset(source_path)
        target_mesh = unreal.load_asset(target_path)

        if not source_mesh or not target_mesh:
            return CollisionResult(
                success=False,
                asset_path=target_path,
                error="Source or target mesh not found"
            )

        static_mesh_editor = unreal.StaticMeshEditorSubsystem()
        static_mesh_editor.set_collisions_from_mesh(target_mesh, source_mesh)

        unreal.EditorAssetLibrary.save_asset(target_path)

        logger.info(f"Copied collision: {source_path} -> {target_path}")
        return CollisionResult(success=True, asset_path=target_path)

    except Exception as e:
        logger.error(f"Collision copy failed: {e}")
        return CollisionResult(
            success=False,
            asset_path=target_path,
            error=str(e)
        )
