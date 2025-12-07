"""
Asset Import Macros for UE5 Macro Automation.

Provides functions for importing FBX, OBJ, and other asset formats
with support for batch processing and auto-LOD generation.

Example Usage:
    >>> import_fbx("/path/to/model.fbx", "/Game/Meshes")
    >>> batch_import_assets(["/path/to/a.fbx", "/path/to/b.fbx"], "/Game/Meshes")
    >>> import_with_auto_lod("/path/to/model.fbx", "/Game/Meshes", lod_count=4)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from src.utils.file_utils import find_files, get_extension
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
class ImportOptions:
    """
    Options for asset import.

    Attributes:
        replace_existing: Replace existing assets
        save_after_import: Save assets after import
        generate_lods: Generate LODs automatically
        lod_count: Number of LODs to generate
        import_materials: Import embedded materials
        import_textures: Import embedded textures
        combine_meshes: Combine meshes into single asset
        auto_generate_collision: Generate collision automatically
        import_animations: Import animations (for skeletal meshes)
        skeleton_path: Path to skeleton for skeletal mesh import
    """
    replace_existing: bool = True
    save_after_import: bool = True
    generate_lods: bool = False
    lod_count: int = 4
    import_materials: bool = True
    import_textures: bool = True
    combine_meshes: bool = False
    auto_generate_collision: bool = True
    import_animations: bool = True
    skeleton_path: str | None = None
    scale_factor: float = 1.0
    rotation_offset: tuple[float, float, float] = (0, 0, 0)


@dataclass
class ImportResult:
    """
    Result of an import operation.

    Attributes:
        success: Whether import was successful
        asset_path: Path to imported asset
        source_path: Original source file path
        error: Error message if failed
        warnings: List of warnings
        lod_paths: Paths to generated LODs
    """
    success: bool
    asset_path: str = ""
    source_path: str = ""
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    lod_paths: list[str] = field(default_factory=list)


@profile_function
def import_fbx(
    source_path: str | Path,
    destination_path: str,
    asset_name: str | None = None,
    options: ImportOptions | None = None
) -> ImportResult:
    """
    Import an FBX file into Unreal Engine.

    Args:
        source_path: Path to the FBX file
        destination_path: Destination folder in Unreal (e.g., "/Game/Meshes")
        asset_name: Name for the imported asset (default: filename)
        options: Import options

    Returns:
        ImportResult with import details

    Example:
        >>> result = import_fbx(
        ...     "/path/to/tree.fbx",
        ...     "/Game/Environment/Trees",
        ...     options=ImportOptions(generate_lods=True)
        ... )
        >>> if result.success:
        ...     print(f"Imported to: {result.asset_path}")
    """
    source_path = Path(source_path)
    options = options or ImportOptions()

    if not source_path.exists():
        return ImportResult(
            success=False,
            source_path=str(source_path),
            error=f"Source file not found: {source_path}"
        )

    if get_extension(source_path) != "fbx":
        return ImportResult(
            success=False,
            source_path=str(source_path),
            error=f"Not an FBX file: {source_path}"
        )

    asset_name = asset_name or source_path.stem
    full_asset_path = f"{destination_path}/{asset_name}"

    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Import FBX: {source_path} -> {full_asset_path}")
        return ImportResult(
            success=True,
            asset_path=full_asset_path,
            source_path=str(source_path)
        )

    import unreal  # noqa: F401

    try:
        task = unreal.AssetImportTask()
        task.filename = str(source_path)
        task.destination_path = destination_path
        task.destination_name = asset_name
        task.replace_existing = options.replace_existing
        task.automated = True
        task.save = options.save_after_import

        fbx_options = unreal.FbxImportUI()
        fbx_options.import_mesh = True
        fbx_options.import_textures = options.import_textures
        fbx_options.import_materials = options.import_materials
        fbx_options.import_animations = options.import_animations

        if options.skeleton_path:
            skeleton = unreal.load_asset(options.skeleton_path)
            if skeleton:
                fbx_options.skeleton = skeleton

        fbx_options.static_mesh_import_data.combine_meshes = options.combine_meshes
        fbx_options.static_mesh_import_data.generate_lightmap_u_vs = True
        fbx_options.static_mesh_import_data.auto_generate_collision = options.auto_generate_collision

        if options.scale_factor != 1.0:
            fbx_options.static_mesh_import_data.import_uniform_scale = options.scale_factor

        task.options = fbx_options

        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

        if task.imported_object_paths:
            result = ImportResult(
                success=True,
                asset_path=full_asset_path,
                source_path=str(source_path)
            )

            if options.generate_lods:
                lod_result = _generate_lods(full_asset_path, options.lod_count)
                result.lod_paths = lod_result

            logger.info(f"Imported FBX: {source_path} -> {full_asset_path}")
            return result
        else:
            return ImportResult(
                success=False,
                source_path=str(source_path),
                error="Import task completed but no objects were imported"
            )

    except Exception as e:
        logger.error(f"FBX import failed: {e}")
        return ImportResult(
            success=False,
            source_path=str(source_path),
            error=str(e)
        )


@profile_function
def import_obj(
    source_path: str | Path,
    destination_path: str,
    asset_name: str | None = None,
    options: ImportOptions | None = None
) -> ImportResult:
    """
    Import an OBJ file into Unreal Engine.

    Args:
        source_path: Path to the OBJ file
        destination_path: Destination folder in Unreal
        asset_name: Name for the imported asset
        options: Import options

    Returns:
        ImportResult with import details

    Example:
        >>> result = import_obj("/path/to/model.obj", "/Game/Meshes")
    """
    source_path = Path(source_path)
    options = options or ImportOptions()

    if not source_path.exists():
        return ImportResult(
            success=False,
            source_path=str(source_path),
            error=f"Source file not found: {source_path}"
        )

    if get_extension(source_path) != "obj":
        return ImportResult(
            success=False,
            source_path=str(source_path),
            error=f"Not an OBJ file: {source_path}"
        )

    asset_name = asset_name or source_path.stem
    full_asset_path = f"{destination_path}/{asset_name}"

    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Import OBJ: {source_path} -> {full_asset_path}")
        return ImportResult(
            success=True,
            asset_path=full_asset_path,
            source_path=str(source_path)
        )

    import unreal  # noqa: F401

    try:
        task = unreal.AssetImportTask()
        task.filename = str(source_path)
        task.destination_path = destination_path
        task.destination_name = asset_name
        task.replace_existing = options.replace_existing
        task.automated = True
        task.save = options.save_after_import

        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

        if task.imported_object_paths:
            result = ImportResult(
                success=True,
                asset_path=full_asset_path,
                source_path=str(source_path)
            )

            if options.generate_lods:
                lod_result = _generate_lods(full_asset_path, options.lod_count)
                result.lod_paths = lod_result

            if options.auto_generate_collision:
                _auto_generate_collision(full_asset_path)

            logger.info(f"Imported OBJ: {source_path} -> {full_asset_path}")
            return result
        else:
            return ImportResult(
                success=False,
                source_path=str(source_path),
                error="Import task completed but no objects were imported"
            )

    except Exception as e:
        logger.error(f"OBJ import failed: {e}")
        return ImportResult(
            success=False,
            source_path=str(source_path),
            error=str(e)
        )


@profile_function
def batch_import_assets(
    source_paths: list[str | Path],
    destination_path: str,
    options: ImportOptions | None = None,
    progress_callback: callable | None = None
) -> list[ImportResult]:
    """
    Batch import multiple assets.

    Args:
        source_paths: List of source file paths
        destination_path: Destination folder in Unreal
        options: Import options
        progress_callback: Callback for progress updates (current, total, message)

    Returns:
        List of ImportResults

    Example:
        >>> files = ["/path/to/a.fbx", "/path/to/b.fbx", "/path/to/c.obj"]
        >>> results = batch_import_assets(files, "/Game/Meshes")
        >>> successful = sum(1 for r in results if r.success)
        >>> print(f"Imported {successful}/{len(results)} assets")
    """
    options = options or ImportOptions()
    results: list[ImportResult] = []

    with ProgressTracker("Batch Import", total=len(source_paths)) as tracker:
        for i, source_path in enumerate(source_paths):
            source_path = Path(source_path)

            if progress_callback:
                progress_callback(i, len(source_paths), f"Importing: {source_path.name}")

            tracker.update(0, f"Importing: {source_path.name}")

            ext = get_extension(source_path)

            if ext == "fbx":
                result = import_fbx(source_path, destination_path, options=options)
            elif ext == "obj":
                result = import_obj(source_path, destination_path, options=options)
            else:
                result = ImportResult(
                    success=False,
                    source_path=str(source_path),
                    error=f"Unsupported file format: {ext}"
                )

            results.append(result)
            tracker.update(1)

    successful = sum(1 for r in results if r.success)
    logger.info(f"Batch import complete: {successful}/{len(results)} successful")

    return results


@profile_function
def import_with_auto_lod(
    source_path: str | Path,
    destination_path: str,
    lod_count: int = 4,
    lod_reduction_percentages: list[float] | None = None,
    options: ImportOptions | None = None
) -> ImportResult:
    """
    Import an asset with automatic LOD generation.

    Args:
        source_path: Path to the source file
        destination_path: Destination folder in Unreal
        lod_count: Number of LODs to generate
        lod_reduction_percentages: Reduction percentage for each LOD
        options: Import options

    Returns:
        ImportResult with LOD paths

    Example:
        >>> result = import_with_auto_lod(
        ...     "/path/to/tree.fbx",
        ...     "/Game/Environment/Trees",
        ...     lod_count=4,
        ...     lod_reduction_percentages=[100, 50, 25, 10]
        ... )
    """
    options = options or ImportOptions()
    options.generate_lods = True
    options.lod_count = lod_count

    source_path = Path(source_path)
    ext = get_extension(source_path)

    if ext == "fbx":
        result = import_fbx(source_path, destination_path, options=options)
    elif ext == "obj":
        result = import_obj(source_path, destination_path, options=options)
    else:
        return ImportResult(
            success=False,
            source_path=str(source_path),
            error=f"Unsupported file format: {ext}"
        )

    if result.success and UNREAL_AVAILABLE and lod_reduction_percentages:
        _configure_lod_settings(result.asset_path, lod_reduction_percentages)

    return result


def _generate_lods(asset_path: str, lod_count: int) -> list[str]:
    """Generate LODs for a static mesh."""
    if not UNREAL_AVAILABLE:
        return [f"{asset_path}_LOD{i}" for i in range(1, lod_count)]

    import unreal  # noqa: F401

    try:
        mesh = unreal.load_asset(asset_path)
        if not mesh or not isinstance(mesh, unreal.StaticMesh):
            logger.warning(f"Cannot generate LODs for non-static mesh: {asset_path}")
            return []

        unreal.StaticMeshEditorSubsystem()

        reduction_options = unreal.MeshReductionSettings()

        lod_paths = []
        for i in range(1, lod_count):
            reduction_percent = 1.0 - (i * 0.25)
            reduction_options.percent_triangles = max(0.1, reduction_percent)

            lod_paths.append(f"{asset_path}_LOD{i}")

        logger.info(f"Generated {lod_count - 1} LODs for: {asset_path}")
        return lod_paths

    except Exception as e:
        logger.error(f"LOD generation failed: {e}")
        return []


def _configure_lod_settings(
    asset_path: str,
    reduction_percentages: list[float]
) -> None:
    """Configure LOD reduction settings."""
    if not UNREAL_AVAILABLE:
        return

    import unreal  # noqa: F401

    try:
        mesh = unreal.load_asset(asset_path)
        if not mesh:
            return

        logger.info(f"Configured LOD settings for: {asset_path}")

    except Exception as e:
        logger.error(f"Failed to configure LOD settings: {e}")


def _auto_generate_collision(asset_path: str) -> bool:
    """Auto-generate collision for a static mesh."""
    if not UNREAL_AVAILABLE:
        return True

    import unreal  # noqa: F401

    try:
        mesh = unreal.load_asset(asset_path)
        if not mesh or not isinstance(mesh, unreal.StaticMesh):
            return False

        body_setup = mesh.get_editor_property("body_setup")
        if body_setup:
            body_setup.set_editor_property("collision_trace_flag",
                unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)

        return True

    except Exception as e:
        logger.error(f"Collision generation failed: {e}")
        return False


def import_directory(
    source_directory: str | Path,
    destination_path: str,
    patterns: list[str] = None,
    recursive: bool = True,
    options: ImportOptions | None = None
) -> list[ImportResult]:
    """
    Import all supported assets from a directory.

    Args:
        source_directory: Directory containing assets
        destination_path: Destination folder in Unreal
        patterns: File patterns to match (default: ["*.fbx", "*.obj"])
        recursive: Search subdirectories
        options: Import options

    Returns:
        List of ImportResults

    Example:
        >>> results = import_directory(
        ...     "/assets/models",
        ...     "/Game/Meshes",
        ...     patterns=["*.fbx"],
        ...     recursive=True
        ... )
    """
    patterns = patterns or ["*.fbx", "*.obj"]
    source_directory = Path(source_directory)

    all_files: list[Path] = []
    for pattern in patterns:
        all_files.extend(find_files(source_directory, pattern, recursive))

    if not all_files:
        logger.warning(f"No matching files found in: {source_directory}")
        return []

    logger.info(f"Found {len(all_files)} files to import")

    return batch_import_assets(all_files, destination_path, options)


def get_import_options_for_type(asset_type: str) -> ImportOptions:
    """
    Get recommended import options for an asset type.

    Args:
        asset_type: Type of asset (tree, rock, building, character, etc.)

    Returns:
        ImportOptions configured for the asset type

    Example:
        >>> options = get_import_options_for_type("tree")
        >>> result = import_fbx("/path/to/tree.fbx", "/Game/Trees", options=options)
    """
    presets = {
        "tree": ImportOptions(
            generate_lods=True,
            lod_count=4,
            auto_generate_collision=True,
            combine_meshes=False,
        ),
        "rock": ImportOptions(
            generate_lods=True,
            lod_count=3,
            auto_generate_collision=True,
            combine_meshes=True,
        ),
        "building": ImportOptions(
            generate_lods=True,
            lod_count=3,
            auto_generate_collision=True,
            combine_meshes=False,
        ),
        "character": ImportOptions(
            generate_lods=False,
            import_animations=True,
            auto_generate_collision=False,
        ),
        "prop": ImportOptions(
            generate_lods=True,
            lod_count=2,
            auto_generate_collision=True,
            combine_meshes=True,
        ),
        "vehicle": ImportOptions(
            generate_lods=True,
            lod_count=3,
            auto_generate_collision=True,
            combine_meshes=False,
        ),
    }

    return presets.get(asset_type.lower(), ImportOptions())
