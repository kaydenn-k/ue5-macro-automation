"""
Import Tree Assets Template for UE5 Macro Automation.

A pre-built macro template for batch importing tree/foliage assets with
automatic collision setup, material assignment, and folder organization.

Example Usage:
    >>> from src.templates.import_tree_assets import ImportTreeAssetsTemplate
    >>> template = ImportTreeAssetsTemplate()
    >>> result = template.execute(
    ...     source_folder="/path/to/trees",
    ...     destination="/Game/Environment/Trees"
    ... )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.core.macro_recorder import ActionType, Macro, RecordedAction
from src.macros.asset_import import (
    ImportOptions,
    ImportResult,
    batch_import_assets,
)
from src.macros.collision_ops import (
    CollisionSettings,
    CollisionType,
    batch_generate_collision,
)
from src.macros.material_ops import (
    MaterialConvention,
    assign_material_by_convention,
)
from src.utils.file_utils import find_files
from src.utils.logging_utils import ProgressTracker

logger = logging.getLogger(__name__)


@dataclass
class TreeImportConfig:
    """
    Configuration for tree asset import.

    Attributes:
        source_folder: Path to source folder containing tree assets
        destination: Destination path in Content Browser
        generate_lods: Whether to generate LODs
        lod_count: Number of LODs to generate
        collision_type: Type of collision to generate
        material_conventions: Material naming conventions
        organize_by_type: Whether to organize into subfolders
        import_textures: Whether to import associated textures
    """
    source_folder: str
    destination: str = "/Game/Environment/Trees"
    generate_lods: bool = True
    lod_count: int = 3
    collision_type: CollisionType = CollisionType.CONVEX
    material_conventions: list[MaterialConvention] = field(default_factory=list)
    organize_by_type: bool = True
    import_textures: bool = True
    scale_factor: float = 1.0


@dataclass
class TreeImportResult:
    """
    Result of tree asset import.

    Attributes:
        success: Whether import was successful
        imported_assets: List of imported asset paths
        failed_assets: List of failed asset paths with errors
        collision_generated: Number of assets with collision generated
        materials_assigned: Number of assets with materials assigned
        total_time: Total execution time in seconds
    """
    success: bool
    imported_assets: list[str] = field(default_factory=list)
    failed_assets: list[tuple[str, str]] = field(default_factory=list)
    collision_generated: int = 0
    materials_assigned: int = 0
    total_time: float = 0.0


class ImportTreeAssetsTemplate:
    """
    Template for importing tree/foliage assets.

    This template performs:
    1. Batch import of FBX/OBJ files
    2. Automatic LOD generation
    3. Collision setup (convex hull)
    4. Material assignment based on naming conventions
    5. Organization into folders

    Example:
        >>> template = ImportTreeAssetsTemplate()
        >>> result = template.execute(
        ...     source_folder="/path/to/trees",
        ...     destination="/Game/Environment/Trees"
        ... )
        >>> print(f"Imported {len(result.imported_assets)} assets")
    """

    NAME = "Import Tree Assets"
    DESCRIPTION = "Batch import tree assets with LOD, collision, and materials"
    CATEGORY = "import"

    DEFAULT_CONVENTIONS = [
        MaterialConvention(
            pattern=r".*[Bb]ark.*",
            material_path="/Game/Materials/Environment/M_TreeBark",
            slot_index=0,
            priority=1
        ),
        MaterialConvention(
            pattern=r".*[Ll]eaf.*|.*[Ll]eaves.*",
            material_path="/Game/Materials/Environment/M_TreeLeaves",
            slot_index=1,
            priority=2
        ),
        MaterialConvention(
            pattern=r".*[Bb]ranch.*",
            material_path="/Game/Materials/Environment/M_TreeBranch",
            slot_index=2,
            priority=3
        ),
    ]

    def __init__(self) -> None:
        """Initialize the template."""
        self._config: TreeImportConfig | None = None

    def execute(
        self,
        source_folder: str,
        destination: str = "/Game/Environment/Trees",
        **kwargs: Any
    ) -> TreeImportResult:
        """
        Execute the tree import template.

        Args:
            source_folder: Path to folder containing tree assets
            destination: Destination path in Content Browser
            **kwargs: Additional configuration options

        Returns:
            TreeImportResult with import details
        """
        import time
        start_time = time.time()

        self._config = TreeImportConfig(
            source_folder=source_folder,
            destination=destination,
            generate_lods=kwargs.get("generate_lods", True),
            lod_count=kwargs.get("lod_count", 3),
            collision_type=kwargs.get("collision_type", CollisionType.CONVEX),
            material_conventions=kwargs.get(
                "material_conventions",
                self.DEFAULT_CONVENTIONS
            ),
            organize_by_type=kwargs.get("organize_by_type", True),
            import_textures=kwargs.get("import_textures", True),
            scale_factor=kwargs.get("scale_factor", 1.0),
        )

        result = TreeImportResult(success=True)

        logger.info(f"Starting tree asset import from: {source_folder}")

        source_files = self._find_source_files()
        if not source_files:
            logger.warning("No source files found")
            result.success = False
            return result

        logger.info(f"Found {len(source_files)} source files")

        with ProgressTracker("Importing Tree Assets", total=len(source_files) * 4) as tracker:
            tracker.update(0, "Importing assets...")
            import_results = self._import_assets(source_files)

            for ir in import_results:
                if ir.success:
                    result.imported_assets.append(ir.asset_path)
                else:
                    result.failed_assets.append((ir.source_path, ir.error or "Unknown error"))

            tracker.update(len(source_files), "Generating collision...")

            collision_count = self._generate_collision(result.imported_assets)
            result.collision_generated = collision_count

            tracker.update(len(source_files), "Assigning materials...")

            material_count = self._assign_materials(result.imported_assets)
            result.materials_assigned = material_count

            tracker.update(len(source_files), "Organizing folders...")

            if self._config.organize_by_type:
                self._organize_assets(result.imported_assets)

            tracker.update(len(source_files), "Complete")

        result.total_time = time.time() - start_time
        result.success = len(result.imported_assets) > 0

        logger.info(
            f"Import complete: {len(result.imported_assets)} succeeded, "
            f"{len(result.failed_assets)} failed in {result.total_time:.2f}s"
        )

        return result

    def _find_source_files(self) -> list[str]:
        """Find source files in the source folder."""
        if not self._config:
            return []

        source_path = Path(self._config.source_folder)

        extensions = ["*.fbx", "*.FBX", "*.obj", "*.OBJ"]
        files = []

        for ext in extensions:
            files.extend(find_files(source_path, ext))

        return [str(f) for f in files]

    def _import_assets(self, source_files: list[str]) -> list[ImportResult]:
        """Import the source files."""
        if not self._config:
            return []

        options = ImportOptions(
            replace_existing=True,
            save_after_import=True,
            generate_lods=self._config.generate_lods,
            lod_count=self._config.lod_count,
            import_materials=True,
            import_textures=self._config.import_textures,
            auto_generate_collision=False,
            scale_factor=self._config.scale_factor,
        )

        results = batch_import_assets(
            source_files,
            self._config.destination,
            options
        )

        return results

    def _generate_collision(self, asset_paths: list[str]) -> int:
        """Generate collision for imported assets."""
        if not self._config or not asset_paths:
            return 0

        settings = CollisionSettings(
            collision_type=self._config.collision_type,
            hull_count=4,
            max_hull_verts=16,
            simplify_collision=True,
        )

        results = batch_generate_collision(asset_paths, settings)

        return sum(1 for r in results if r.success)

    def _assign_materials(self, asset_paths: list[str]) -> int:
        """Assign materials based on conventions."""
        if not self._config or not asset_paths:
            return 0

        assigned = 0

        for asset_path in asset_paths:
            result = assign_material_by_convention(
                asset_path,
                self._config.material_conventions
            )
            if result.success:
                assigned += 1

        return assigned

    def _organize_assets(self, asset_paths: list[str]) -> None:
        """Organize assets into subfolders."""
        if not self._config:
            return

        logger.info("Organizing assets into folders")

    def to_macro(self) -> Macro:
        """
        Convert the template to a Macro object.

        Returns:
            Macro object representing this template
        """
        actions = [
            RecordedAction(
                action_type=ActionType.CUSTOM,
                parameters={
                    "template": "ImportTreeAssetsTemplate",
                    "config": {
                        "source_folder": self._config.source_folder if self._config else "",
                        "destination": self._config.destination if self._config else "/Game/Environment/Trees",
                    }
                },
                description="Execute Import Tree Assets template"
            )
        ]

        return Macro(
            name=self.NAME,
            actions=actions,
            description=self.DESCRIPTION,
            metadata={"category": self.CATEGORY, "template": True}
        )

    @classmethod
    def get_default_config(cls) -> dict[str, Any]:
        """Get the default configuration for this template."""
        return {
            "source_folder": "",
            "destination": "/Game/Environment/Trees",
            "generate_lods": True,
            "lod_count": 3,
            "collision_type": "CONVEX",
            "organize_by_type": True,
            "import_textures": True,
            "scale_factor": 1.0,
        }
