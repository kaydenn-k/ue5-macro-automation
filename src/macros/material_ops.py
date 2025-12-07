"""
Material Operations Macros for UE5 Macro Automation.

Provides functions for material assignment, creation, and batch processing
based on naming conventions.

Example Usage:
    >>> assign_material_by_convention("/Game/Meshes/Tree_Wood", "/Game/Materials")
    >>> create_material_instance("/Game/Materials/M_Wood", "MI_Wood_Dark")
    >>> import_textures_and_create_materials("/textures", "/Game/Materials")
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.utils.file_utils import find_files
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


@dataclass
class MaterialConvention:
    """
    Naming convention for automatic material assignment.

    Attributes:
        pattern: Regex pattern to match in asset names
        material_path: Path to the material to assign
        slot_index: Material slot index
        priority: Priority for matching (higher = checked first)
    """
    pattern: str
    material_path: str
    slot_index: int = 0
    priority: int = 0


@dataclass
class MaterialResult:
    """
    Result of a material operation.

    Attributes:
        success: Whether operation was successful
        asset_path: Path to the affected asset
        material_path: Path to the material
        error: Error message if failed
    """
    success: bool
    asset_path: str = ""
    material_path: str = ""
    error: str | None = None


DEFAULT_CONVENTIONS = [
    MaterialConvention(r"_wood|_bark|_trunk", "/Game/Materials/M_Wood", priority=10),
    MaterialConvention(r"_leaf|_leaves|_foliage", "/Game/Materials/M_Foliage", priority=10),
    MaterialConvention(r"_metal|_steel|_iron", "/Game/Materials/M_Metal", priority=10),
    MaterialConvention(r"_glass|_window", "/Game/Materials/M_Glass", priority=10),
    MaterialConvention(r"_concrete|_cement", "/Game/Materials/M_Concrete", priority=10),
    MaterialConvention(r"_brick|_stone|_rock", "/Game/Materials/M_Stone", priority=10),
    MaterialConvention(r"_fabric|_cloth", "/Game/Materials/M_Fabric", priority=10),
    MaterialConvention(r"_plastic", "/Game/Materials/M_Plastic", priority=10),
    MaterialConvention(r"_skin|_flesh", "/Game/Materials/M_Skin", priority=10),
    MaterialConvention(r"_water|_liquid", "/Game/Materials/M_Water", priority=10),
]


@profile_function
def assign_material_by_convention(
    asset_path: str,
    materials_folder: str,
    conventions: list[MaterialConvention] | None = None,
    fallback_material: str | None = None
) -> MaterialResult:
    """
    Assign material to an asset based on naming conventions.

    Args:
        asset_path: Path to the asset
        materials_folder: Folder containing materials
        conventions: List of naming conventions (default: DEFAULT_CONVENTIONS)
        fallback_material: Material to use if no convention matches

    Returns:
        MaterialResult with operation details

    Example:
        >>> result = assign_material_by_convention(
        ...     "/Game/Meshes/Tree_Wood_01",
        ...     "/Game/Materials"
        ... )
        >>> # Will assign M_Wood based on "_wood" in the name
    """
    conventions = conventions or DEFAULT_CONVENTIONS
    conventions = sorted(conventions, key=lambda c: c.priority, reverse=True)

    asset_name = Path(asset_path).stem.lower()
    matched_material: str | None = None
    matched_slot = 0

    for convention in conventions:
        if re.search(convention.pattern, asset_name, re.IGNORECASE):
            matched_material = convention.material_path
            matched_slot = convention.slot_index
            break

    if not matched_material:
        if fallback_material:
            matched_material = fallback_material
        else:
            return MaterialResult(
                success=False,
                asset_path=asset_path,
                error="No matching convention found and no fallback specified"
            )

    return assign_material(asset_path, matched_material, matched_slot)


@profile_function
def assign_material(
    asset_path: str,
    material_path: str,
    slot_index: int = 0
) -> MaterialResult:
    """
    Assign a material to an asset.

    Args:
        asset_path: Path to the asset
        material_path: Path to the material
        slot_index: Material slot index

    Returns:
        MaterialResult with operation details

    Example:
        >>> result = assign_material(
        ...     "/Game/Meshes/Tree",
        ...     "/Game/Materials/M_Wood",
        ...     slot_index=0
        ... )
    """
    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Assign material: {material_path} -> {asset_path}[{slot_index}]")
        return MaterialResult(
            success=True,
            asset_path=asset_path,
            material_path=material_path
        )

    import unreal  # noqa: F401

    try:
        mesh = unreal.load_asset(asset_path)
        if not mesh:
            return MaterialResult(
                success=False,
                asset_path=asset_path,
                error=f"Asset not found: {asset_path}"
            )

        material = unreal.load_asset(material_path)
        if not material:
            return MaterialResult(
                success=False,
                asset_path=asset_path,
                material_path=material_path,
                error=f"Material not found: {material_path}"
            )

        if isinstance(mesh, unreal.StaticMesh):
            materials = mesh.get_editor_property("static_materials")
            if slot_index < len(materials):
                materials[slot_index].material_interface = material
                mesh.set_editor_property("static_materials", materials)

        unreal.EditorAssetLibrary.save_asset(asset_path)

        logger.info(f"Assigned material: {material_path} -> {asset_path}[{slot_index}]")
        return MaterialResult(
            success=True,
            asset_path=asset_path,
            material_path=material_path
        )

    except Exception as e:
        logger.error(f"Material assignment failed: {e}")
        return MaterialResult(
            success=False,
            asset_path=asset_path,
            material_path=material_path,
            error=str(e)
        )


@profile_function
def create_material_instance(
    parent_material_path: str,
    instance_name: str,
    destination_path: str | None = None,
    scalar_parameters: dict[str, float] | None = None,
    vector_parameters: dict[str, tuple[float, float, float, float]] | None = None,
    texture_parameters: dict[str, str] | None = None
) -> MaterialResult:
    """
    Create a material instance from a parent material.

    Args:
        parent_material_path: Path to the parent material
        instance_name: Name for the new instance
        destination_path: Destination folder (default: same as parent)
        scalar_parameters: Scalar parameter overrides
        vector_parameters: Vector parameter overrides (RGBA)
        texture_parameters: Texture parameter overrides (parameter_name: texture_path)

    Returns:
        MaterialResult with the created instance path

    Example:
        >>> result = create_material_instance(
        ...     "/Game/Materials/M_Wood",
        ...     "MI_Wood_Dark",
        ...     scalar_parameters={"Roughness": 0.8},
        ...     vector_parameters={"BaseColor": (0.2, 0.1, 0.05, 1.0)}
        ... )
    """
    if destination_path is None:
        destination_path = str(Path(parent_material_path).parent)

    instance_path = f"{destination_path}/{instance_name}"

    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Create material instance: {instance_path} from {parent_material_path}")
        return MaterialResult(
            success=True,
            asset_path=instance_path,
            material_path=parent_material_path
        )

    import unreal  # noqa: F401

    try:
        parent_material = unreal.load_asset(parent_material_path)
        if not parent_material:
            return MaterialResult(
                success=False,
                material_path=parent_material_path,
                error=f"Parent material not found: {parent_material_path}"
            )

        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

        factory = unreal.MaterialInstanceConstantFactoryNew()
        factory.set_editor_property("initial_parent", parent_material)

        instance = asset_tools.create_asset(
            instance_name,
            destination_path,
            unreal.MaterialInstanceConstant,
            factory
        )

        if not instance:
            return MaterialResult(
                success=False,
                material_path=parent_material_path,
                error="Failed to create material instance"
            )

        if scalar_parameters:
            for param_name, value in scalar_parameters.items():
                instance.set_scalar_parameter_value_editor_only(param_name, value)

        if vector_parameters:
            for param_name, value in vector_parameters.items():
                color = unreal.LinearColor(value[0], value[1], value[2], value[3])
                instance.set_vector_parameter_value_editor_only(param_name, color)

        if texture_parameters:
            for param_name, texture_path in texture_parameters.items():
                texture = unreal.load_asset(texture_path)
                if texture:
                    instance.set_texture_parameter_value_editor_only(param_name, texture)

        unreal.EditorAssetLibrary.save_asset(instance_path)

        logger.info(f"Created material instance: {instance_path}")
        return MaterialResult(
            success=True,
            asset_path=instance_path,
            material_path=parent_material_path
        )

    except Exception as e:
        logger.error(f"Material instance creation failed: {e}")
        return MaterialResult(
            success=False,
            material_path=parent_material_path,
            error=str(e)
        )


@profile_function
def batch_create_material_instances(
    parent_material_path: str,
    instance_configs: list[dict[str, Any]],
    destination_path: str | None = None
) -> list[MaterialResult]:
    """
    Create multiple material instances from a parent material.

    Args:
        parent_material_path: Path to the parent material
        instance_configs: List of instance configurations
        destination_path: Destination folder

    Returns:
        List of MaterialResults

    Example:
        >>> configs = [
        ...     {"name": "MI_Wood_Light", "scalar_parameters": {"Roughness": 0.3}},
        ...     {"name": "MI_Wood_Dark", "scalar_parameters": {"Roughness": 0.8}},
        ... ]
        >>> results = batch_create_material_instances(
        ...     "/Game/Materials/M_Wood",
        ...     configs
        ... )
    """
    results: list[MaterialResult] = []

    with ProgressTracker("Creating Material Instances", total=len(instance_configs)) as tracker:
        for config in instance_configs:
            tracker.update(0, f"Creating: {config.get('name', 'Unknown')}")

            result = create_material_instance(
                parent_material_path,
                config.get("name", "MI_Unnamed"),
                destination_path,
                config.get("scalar_parameters"),
                config.get("vector_parameters"),
                config.get("texture_parameters")
            )

            results.append(result)
            tracker.update(1)

    successful = sum(1 for r in results if r.success)
    logger.info(f"Created {successful}/{len(results)} material instances")

    return results


@profile_function
def import_textures_and_create_materials(
    source_directory: str | Path,
    destination_path: str,
    base_material_path: str | None = None,
    texture_patterns: dict[str, str] | None = None
) -> list[MaterialResult]:
    """
    Import textures and create materials with proper texture assignments.

    Args:
        source_directory: Directory containing textures
        destination_path: Destination folder in Unreal
        base_material_path: Base material to create instances from
        texture_patterns: Patterns to identify texture types

    Returns:
        List of MaterialResults

    Example:
        >>> results = import_textures_and_create_materials(
        ...     "/textures/wood",
        ...     "/Game/Materials/Wood",
        ...     base_material_path="/Game/Materials/M_Base"
        ... )
    """
    source_directory = Path(source_directory)

    texture_patterns = texture_patterns or {
        "BaseColor": r"_(?:diffuse|albedo|basecolor|color|d)(?:\.|_)",
        "Normal": r"_(?:normal|nrm|n)(?:\.|_)",
        "Roughness": r"_(?:roughness|rough|r)(?:\.|_)",
        "Metallic": r"_(?:metallic|metal|m)(?:\.|_)",
        "AO": r"_(?:ao|ambient|occlusion)(?:\.|_)",
        "Height": r"_(?:height|displacement|disp|h)(?:\.|_)",
    }

    texture_files = find_files(source_directory, "*.png") + \
                   find_files(source_directory, "*.tga") + \
                   find_files(source_directory, "*.jpg")

    if not texture_files:
        logger.warning(f"No texture files found in: {source_directory}")
        return []

    texture_groups: dict[str, dict[str, Path]] = {}

    for texture_file in texture_files:
        base_name = texture_file.stem

        for tex_type, pattern in texture_patterns.items():
            if re.search(pattern, base_name, re.IGNORECASE):
                group_name = re.sub(pattern, "", base_name, flags=re.IGNORECASE)
                group_name = group_name.strip("_")

                if group_name not in texture_groups:
                    texture_groups[group_name] = {}

                texture_groups[group_name][tex_type] = texture_file
                break

    results: list[MaterialResult] = []

    with ProgressTracker("Creating Materials", total=len(texture_groups)) as tracker:
        for group_name, textures in texture_groups.items():
            tracker.update(0, f"Processing: {group_name}")

            imported_textures = _import_texture_group(textures, destination_path)

            if base_material_path and imported_textures:
                result = create_material_instance(
                    base_material_path,
                    f"MI_{group_name}",
                    destination_path,
                    texture_parameters=imported_textures
                )
                results.append(result)

            tracker.update(1)

    return results


def _import_texture_group(
    textures: dict[str, Path],
    destination_path: str
) -> dict[str, str]:
    """Import a group of textures and return their Unreal paths."""
    imported: dict[str, str] = {}

    if not UNREAL_AVAILABLE:
        for tex_type, tex_path in textures.items():
            imported[tex_type] = f"{destination_path}/T_{tex_path.stem}"
        return imported

    import unreal  # noqa: F401

    for tex_type, tex_path in textures.items():
        try:
            task = unreal.AssetImportTask()
            task.filename = str(tex_path)
            task.destination_path = destination_path
            task.destination_name = f"T_{tex_path.stem}"
            task.replace_existing = True
            task.automated = True
            task.save = True

            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

            if task.imported_object_paths:
                imported[tex_type] = task.imported_object_paths[0]

        except Exception as e:
            logger.error(f"Failed to import texture {tex_path}: {e}")

    return imported


def batch_assign_materials(
    asset_material_pairs: list[tuple[str, str, int]],
    progress_callback: callable | None = None
) -> list[MaterialResult]:
    """
    Batch assign materials to multiple assets.

    Args:
        asset_material_pairs: List of (asset_path, material_path, slot_index)
        progress_callback: Progress callback function

    Returns:
        List of MaterialResults

    Example:
        >>> pairs = [
        ...     ("/Game/Meshes/Tree", "/Game/Materials/M_Wood", 0),
        ...     ("/Game/Meshes/Rock", "/Game/Materials/M_Stone", 0),
        ... ]
        >>> results = batch_assign_materials(pairs)
    """
    results: list[MaterialResult] = []

    with ProgressTracker("Assigning Materials", total=len(asset_material_pairs)) as tracker:
        for i, (asset_path, material_path, slot_index) in enumerate(asset_material_pairs):
            if progress_callback:
                progress_callback(i, len(asset_material_pairs), f"Assigning to: {asset_path}")

            tracker.update(0, f"Assigning to: {Path(asset_path).stem}")

            result = assign_material(asset_path, material_path, slot_index)
            results.append(result)

            tracker.update(1)

    successful = sum(1 for r in results if r.success)
    logger.info(f"Assigned materials: {successful}/{len(results)} successful")

    return results


def get_material_slots(asset_path: str) -> list[dict[str, Any]]:
    """
    Get material slot information for an asset.

    Args:
        asset_path: Path to the asset

    Returns:
        List of material slot information

    Example:
        >>> slots = get_material_slots("/Game/Meshes/Tree")
        >>> for slot in slots:
        ...     print(f"Slot {slot['index']}: {slot['material']}")
    """
    if not UNREAL_AVAILABLE:
        return [{"index": 0, "name": "Default", "material": None}]

    import unreal  # noqa: F401

    try:
        mesh = unreal.load_asset(asset_path)
        if not mesh or not isinstance(mesh, unreal.StaticMesh):
            return []

        materials = mesh.get_editor_property("static_materials")

        slots = []
        for i, mat_slot in enumerate(materials):
            slots.append({
                "index": i,
                "name": mat_slot.material_slot_name,
                "material": str(mat_slot.material_interface.get_path_name())
                           if mat_slot.material_interface else None
            })

        return slots

    except Exception as e:
        logger.error(f"Failed to get material slots: {e}")
        return []
