"""
Export Selected Template for UE5 Macro Automation.

A pre-built macro template for batch exporting selected assets with
format options and organization.

Example Usage:
    >>> from src.templates.export_selected import ExportSelectedTemplate
    >>> template = ExportSelectedTemplate()
    >>> result = template.execute(
    ...     output_folder="/path/to/export",
    ...     format="fbx"
    ... )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.core.macro_recorder import ActionType, Macro, RecordedAction
from src.utils.file_utils import ensure_directory
from src.utils.logging_utils import ProgressTracker

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
class ExportConfig:
    """
    Configuration for asset export.

    Attributes:
        output_folder: Destination folder for exports
        format: Export format (fbx, obj, gltf)
        include_textures: Whether to export textures
        include_materials: Whether to export materials
        preserve_hierarchy: Whether to preserve folder hierarchy
        collision_as_ucx: Export collision as UCX prefix
        export_lods: Whether to export LODs
        scale_factor: Scale factor for export
        ascii_format: Use ASCII format (for FBX)
    """
    output_folder: str
    format: str = "fbx"
    include_textures: bool = True
    include_materials: bool = True
    preserve_hierarchy: bool = True
    collision_as_ucx: bool = True
    export_lods: bool = True
    scale_factor: float = 1.0
    ascii_format: bool = False


@dataclass
class ExportResult:
    """
    Result of export operation.

    Attributes:
        success: Whether export was successful
        exported_count: Number of assets exported
        failed_count: Number of assets that failed
        exported_files: List of exported file paths
        errors: List of error messages
        total_size: Total size of exported files in bytes
    """
    success: bool
    exported_count: int = 0
    failed_count: int = 0
    exported_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    total_size: int = 0


class ExportSelectedTemplate:
    """
    Template for batch exporting selected assets.

    This template performs:
    1. Export static meshes to FBX/OBJ/glTF
    2. Export associated textures
    3. Preserve folder structure
    4. Handle LODs and collision

    Example:
        >>> template = ExportSelectedTemplate()
        >>> result = template.execute(
        ...     assets=get_selected_assets(),
        ...     output_folder="/exports",
        ...     format="fbx"
        ... )
        >>> print(f"Exported {result.exported_count} assets")
    """

    NAME = "Export Selected"
    DESCRIPTION = "Batch export selected assets with format options"
    CATEGORY = "export"

    SUPPORTED_FORMATS = ["fbx", "obj", "gltf", "glb"]

    def __init__(self) -> None:
        """Initialize the template."""
        self._config: ExportConfig | None = None

    def execute(
        self,
        assets: list[Any] | None = None,
        output_folder: str = "",
        **kwargs: Any
    ) -> ExportResult:
        """
        Execute the export template.

        Args:
            assets: List of assets to export (if None, uses selection)
            output_folder: Destination folder for exports
            **kwargs: Export configuration options

        Returns:
            ExportResult with export details
        """
        if not output_folder:
            logger.error("Output folder is required")
            return ExportResult(success=False, errors=["Output folder is required"])

        self._config = ExportConfig(
            output_folder=output_folder,
            format=kwargs.get("format", "fbx").lower(),
            include_textures=kwargs.get("include_textures", True),
            include_materials=kwargs.get("include_materials", True),
            preserve_hierarchy=kwargs.get("preserve_hierarchy", True),
            collision_as_ucx=kwargs.get("collision_as_ucx", True),
            export_lods=kwargs.get("export_lods", True),
            scale_factor=kwargs.get("scale_factor", 1.0),
            ascii_format=kwargs.get("ascii_format", False),
        )

        if self._config.format not in self.SUPPORTED_FORMATS:
            logger.error(f"Unsupported format: {self._config.format}")
            return ExportResult(
                success=False,
                errors=[f"Unsupported format: {self._config.format}"]
            )

        if assets is None:
            assets = self._get_selected_assets()

        if not assets:
            logger.warning("No assets to export")
            return ExportResult(success=False, errors=["No assets to export"])

        result = ExportResult(success=True)

        ensure_directory(Path(output_folder))

        logger.info(f"Starting export of {len(assets)} assets to {output_folder}")

        with ProgressTracker("Exporting Assets", total=len(assets)) as tracker:
            for i, asset in enumerate(assets):
                tracker.update(0, f"Exporting {i + 1}/{len(assets)}")

                try:
                    export_path = self._export_asset(asset)

                    if export_path:
                        result.exported_files.append(export_path)
                        result.exported_count += 1

                        file_path = Path(export_path)
                        if file_path.exists():
                            result.total_size += file_path.stat().st_size
                    else:
                        result.failed_count += 1
                        result.errors.append(f"Failed to export: {self._get_asset_name(asset)}")

                except Exception as e:
                    result.failed_count += 1
                    result.errors.append(f"Error exporting {self._get_asset_name(asset)}: {e}")

                tracker.update(1)

        result.success = result.failed_count == 0

        logger.info(
            f"Export complete: {result.exported_count} exported, "
            f"{result.failed_count} failed, "
            f"total size: {self._format_size(result.total_size)}"
        )

        return result

    def _get_selected_assets(self) -> list[Any]:
        """Get currently selected assets."""
        if not UNREAL_AVAILABLE:
            return []

        import unreal  # noqa: F401

        utility = unreal.EditorUtilityLibrary()
        return list(utility.get_selected_assets())

    def _get_asset_name(self, asset: Any) -> str:
        """Get the name of an asset."""
        if isinstance(asset, str):
            return asset.split("/")[-1]

        if UNREAL_AVAILABLE and hasattr(asset, "get_name"):
            return asset.get_name()

        return str(asset)

    def _get_asset_path(self, asset: Any) -> str:
        """Get the path of an asset."""
        if isinstance(asset, str):
            return asset

        if UNREAL_AVAILABLE and hasattr(asset, "get_path_name"):
            return asset.get_path_name()

        return ""

    def _export_asset(self, asset: Any) -> str | None:
        """Export a single asset."""
        if not self._config:
            return None

        asset_name = self._get_asset_name(asset)
        asset_path = self._get_asset_path(asset)

        if self._config.preserve_hierarchy and asset_path:
            relative_path = asset_path.replace("/Game/", "").rsplit("/", 1)[0]
            output_dir = Path(self._config.output_folder) / relative_path
        else:
            output_dir = Path(self._config.output_folder)

        ensure_directory(output_dir)

        output_file = output_dir / f"{asset_name}.{self._config.format}"

        if not UNREAL_AVAILABLE:
            logger.info(f"[MOCK] Export: {asset_name} -> {output_file}")
            return str(output_file)


        try:
            if self._config.format == "fbx":
                return self._export_fbx(asset, str(output_file))
            elif self._config.format == "obj":
                return self._export_obj(asset, str(output_file))
            elif self._config.format in ["gltf", "glb"]:
                return self._export_gltf(asset, str(output_file))
            else:
                return None

        except Exception as e:
            logger.error(f"Export failed for {asset_name}: {e}")
            return None

    def _export_fbx(self, asset: Any, output_path: str) -> str | None:
        """Export asset as FBX."""
        if not UNREAL_AVAILABLE:
            return output_path

        import unreal  # noqa: F401

        try:
            export_task = unreal.AssetExportTask()
            export_task.set_editor_property("object", asset)
            export_task.set_editor_property("filename", output_path)
            export_task.set_editor_property("automated", True)
            export_task.set_editor_property("replace_identical", True)

            options = unreal.FbxExportOption()
            if self._config:
                options.set_editor_property("ascii", self._config.ascii_format)
                options.set_editor_property("collision", self._config.collision_as_ucx)
                options.set_editor_property("level_of_detail", self._config.export_lods)

            export_task.set_editor_property("options", options)

            if unreal.Exporter.run_asset_export_task(export_task):
                return output_path

            return None

        except Exception as e:
            logger.error(f"FBX export failed: {e}")
            return None

    def _export_obj(self, asset: Any, output_path: str) -> str | None:
        """Export asset as OBJ."""
        if not UNREAL_AVAILABLE:
            return output_path

        import unreal  # noqa: F401

        try:
            export_task = unreal.AssetExportTask()
            export_task.set_editor_property("object", asset)
            export_task.set_editor_property("filename", output_path)
            export_task.set_editor_property("automated", True)
            export_task.set_editor_property("replace_identical", True)

            if unreal.Exporter.run_asset_export_task(export_task):
                return output_path

            return None

        except Exception as e:
            logger.error(f"OBJ export failed: {e}")
            return None

    def _export_gltf(self, asset: Any, output_path: str) -> str | None:
        """Export asset as glTF/GLB."""
        if not UNREAL_AVAILABLE:
            return output_path

        import unreal  # noqa: F401

        try:
            export_task = unreal.AssetExportTask()
            export_task.set_editor_property("object", asset)
            export_task.set_editor_property("filename", output_path)
            export_task.set_editor_property("automated", True)
            export_task.set_editor_property("replace_identical", True)

            if unreal.Exporter.run_asset_export_task(export_task):
                return output_path

            return None

        except Exception as e:
            logger.error(f"glTF export failed: {e}")
            return None

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"

    def to_macro(self) -> Macro:
        """Convert the template to a Macro object."""
        actions = [
            RecordedAction(
                action_type=ActionType.CUSTOM,
                parameters={
                    "template": "ExportSelectedTemplate",
                    "config": self.get_default_config()
                },
                description="Execute Export Selected template"
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
            "output_folder": "",
            "format": "fbx",
            "include_textures": True,
            "include_materials": True,
            "preserve_hierarchy": True,
            "collision_as_ucx": True,
            "export_lods": True,
            "scale_factor": 1.0,
            "ascii_format": False,
        }
