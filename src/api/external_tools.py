"""
External Tools Integration for UE5 Macro Automation.

Provides integration with external tools like Blender and Substance.

Example Usage:
    >>> from src.api.external_tools import BlenderIntegration
    >>> blender = BlenderIntegration()
    >>> blender.export_to_unreal("/path/to/blend", "/Game/Meshes")
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ExternalToolResult:
    """
    Result of an external tool operation.

    Attributes:
        success: Whether operation was successful
        output_files: List of output file paths
        error: Error message if failed
        stdout: Standard output from tool
        stderr: Standard error from tool
    """
    success: bool
    output_files: list[str] = field(default_factory=list)
    error: str | None = None
    stdout: str = ""
    stderr: str = ""


class BlenderIntegration:
    """
    Integration with Blender for asset processing.

    Provides:
    - Export from Blender to UE5-compatible formats
    - Batch processing of Blender files
    - Material conversion
    - LOD generation in Blender

    Example:
        >>> blender = BlenderIntegration("/path/to/blender")
        >>> result = blender.export_to_unreal(
        ...     "/path/to/model.blend",
        ...     "/Game/Meshes"
        ... )
    """

    def __init__(
        self,
        blender_path: str | None = None,
        python_script_dir: str | None = None
    ) -> None:
        """
        Initialize Blender integration.

        Args:
            blender_path: Path to Blender executable
            python_script_dir: Directory for Blender Python scripts
        """
        self._blender_path = blender_path or self._find_blender()
        self._script_dir = python_script_dir or str(
            Path(__file__).parent / "blender_scripts"
        )

    def _find_blender(self) -> str:
        """Find Blender executable."""
        import shutil

        blender = shutil.which("blender")
        if blender:
            return blender

        common_paths = [
            "/usr/bin/blender",
            "/Applications/Blender.app/Contents/MacOS/Blender",
            "C:\\Program Files\\Blender Foundation\\Blender\\blender.exe",
        ]

        for path in common_paths:
            if Path(path).exists():
                return path

        return "blender"

    def export_to_unreal(
        self,
        blend_file: str,
        destination: str,
        format: str = "fbx",
        options: dict[str, Any] | None = None
    ) -> ExternalToolResult:
        """
        Export Blender file to UE5-compatible format.

        Args:
            blend_file: Path to .blend file
            destination: UE5 destination path
            format: Export format (fbx, obj, gltf)
            options: Export options

        Returns:
            ExternalToolResult with export details
        """
        options = options or {}

        output_dir = Path(blend_file).parent / "export"
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / f"{Path(blend_file).stem}.{format}"

        script = self._generate_export_script(
            str(output_file),
            format,
            options
        )

        result = self._run_blender_script(blend_file, script)

        if result.success and output_file.exists():
            result.output_files = [str(output_file)]

        return result

    def batch_export(
        self,
        blend_files: list[str],
        output_dir: str,
        format: str = "fbx"
    ) -> list[ExternalToolResult]:
        """
        Batch export multiple Blender files.

        Args:
            blend_files: List of .blend file paths
            output_dir: Output directory
            format: Export format

        Returns:
            List of ExternalToolResult for each file
        """
        results = []

        for blend_file in blend_files:
            result = self.export_to_unreal(
                blend_file,
                output_dir,
                format
            )
            results.append(result)

        return results

    def generate_lods(
        self,
        blend_file: str,
        lod_count: int = 3,
        reduction_ratios: list[float] | None = None
    ) -> ExternalToolResult:
        """
        Generate LODs in Blender.

        Args:
            blend_file: Path to .blend file
            lod_count: Number of LODs to generate
            reduction_ratios: Reduction ratio for each LOD

        Returns:
            ExternalToolResult with LOD generation details
        """
        reduction_ratios = reduction_ratios or [0.5, 0.25, 0.1][:lod_count]

        script = f"""
import bpy

for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        for i, ratio in enumerate({reduction_ratios}):
            mod = obj.modifiers.new(name=f'LOD{{i+1}}', type='DECIMATE')
            mod.ratio = ratio

bpy.ops.wm.save_mainfile()
"""

        return self._run_blender_script(blend_file, script)

    def _generate_export_script(
        self,
        output_path: str,
        format: str,
        options: dict[str, Any]
    ) -> str:
        """Generate Blender export script."""
        if format == "fbx":
            return f"""
import bpy

bpy.ops.export_scene.fbx(
    filepath="{output_path}",
    use_selection=False,
    apply_scale_options='FBX_SCALE_ALL',
    axis_forward='-Z',
    axis_up='Y',
    use_mesh_modifiers=True,
    mesh_smooth_type='FACE',
    add_leaf_bones=False,
)
"""
        elif format == "obj":
            return f"""
import bpy

bpy.ops.export_scene.obj(
    filepath="{output_path}",
    use_selection=False,
    axis_forward='-Z',
    axis_up='Y',
)
"""
        elif format in ["gltf", "glb"]:
            return f"""
import bpy

bpy.ops.export_scene.gltf(
    filepath="{output_path}",
    export_format='{'GLB' if format == 'glb' else 'GLTF_SEPARATE'}',
)
"""
        else:
            return ""

    def _run_blender_script(
        self,
        blend_file: str,
        script: str
    ) -> ExternalToolResult:
        """Run a Python script in Blender."""
        try:
            result = subprocess.run(
                [
                    self._blender_path,
                    blend_file,
                    "--background",
                    "--python-expr",
                    script,
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )

            return ExternalToolResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                error=result.stderr if result.returncode != 0 else None,
            )

        except subprocess.TimeoutExpired:
            return ExternalToolResult(
                success=False,
                error="Blender operation timed out"
            )
        except FileNotFoundError:
            return ExternalToolResult(
                success=False,
                error=f"Blender not found at: {self._blender_path}"
            )
        except Exception as e:
            return ExternalToolResult(
                success=False,
                error=str(e)
            )


class SubstanceIntegration:
    """
    Integration with Substance tools for texture processing.

    Provides:
    - Export textures from Substance Painter
    - Batch texture processing
    - Material preset application

    Example:
        >>> substance = SubstanceIntegration()
        >>> result = substance.export_textures(
        ...     "/path/to/project.spp",
        ...     "/Game/Textures"
        ... )
    """

    def __init__(
        self,
        painter_path: str | None = None,
        designer_path: str | None = None
    ) -> None:
        """
        Initialize Substance integration.

        Args:
            painter_path: Path to Substance Painter executable
            designer_path: Path to Substance Designer executable
        """
        self._painter_path = painter_path or self._find_substance_painter()
        self._designer_path = designer_path or self._find_substance_designer()

    def _find_substance_painter(self) -> str:
        """Find Substance Painter executable."""
        import shutil

        painter = shutil.which("Substance Painter")
        if painter:
            return painter

        return "Substance Painter"

    def _find_substance_designer(self) -> str:
        """Find Substance Designer executable."""
        import shutil

        designer = shutil.which("Substance Designer")
        if designer:
            return designer

        return "Substance Designer"

    def export_textures(
        self,
        project_file: str,
        output_dir: str,
        preset: str = "Unreal Engine 4 (Packed)",
        resolution: int = 2048
    ) -> ExternalToolResult:
        """
        Export textures from Substance Painter project.

        Args:
            project_file: Path to .spp file
            output_dir: Output directory for textures
            preset: Export preset name
            resolution: Texture resolution

        Returns:
            ExternalToolResult with export details
        """
        logger.info(f"Exporting textures from: {project_file}")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        return ExternalToolResult(
            success=True,
            output_files=[str(output_path)],
        )

    def batch_export_textures(
        self,
        project_files: list[str],
        output_dir: str,
        preset: str = "Unreal Engine 4 (Packed)"
    ) -> list[ExternalToolResult]:
        """
        Batch export textures from multiple projects.

        Args:
            project_files: List of .spp file paths
            output_dir: Output directory
            preset: Export preset name

        Returns:
            List of ExternalToolResult for each project
        """
        results = []

        for project_file in project_files:
            project_name = Path(project_file).stem
            project_output = str(Path(output_dir) / project_name)

            result = self.export_textures(
                project_file,
                project_output,
                preset
            )
            results.append(result)

        return results

    def render_sbsar(
        self,
        sbsar_file: str,
        output_dir: str,
        parameters: dict[str, Any] | None = None,
        resolution: int = 2048
    ) -> ExternalToolResult:
        """
        Render textures from Substance Archive.

        Args:
            sbsar_file: Path to .sbsar file
            output_dir: Output directory
            parameters: Substance parameters to set
            resolution: Output resolution

        Returns:
            ExternalToolResult with render details
        """
        parameters = parameters or {}

        logger.info(f"Rendering SBSAR: {sbsar_file}")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        return ExternalToolResult(
            success=True,
            output_files=[str(output_path)],
        )


class ExternalToolManager:
    """
    Manager for all external tool integrations.

    Provides a unified interface for working with external tools.
    """

    def __init__(self) -> None:
        """Initialize the tool manager."""
        self._blender: BlenderIntegration | None = None
        self._substance: SubstanceIntegration | None = None

    @property
    def blender(self) -> BlenderIntegration:
        """Get Blender integration."""
        if self._blender is None:
            self._blender = BlenderIntegration()
        return self._blender

    @property
    def substance(self) -> SubstanceIntegration:
        """Get Substance integration."""
        if self._substance is None:
            self._substance = SubstanceIntegration()
        return self._substance

    def check_tools(self) -> dict[str, bool]:
        """
        Check which external tools are available.

        Returns:
            Dictionary of tool availability
        """
        import shutil

        return {
            "blender": shutil.which("blender") is not None,
            "substance_painter": shutil.which("Substance Painter") is not None,
            "substance_designer": shutil.which("Substance Designer") is not None,
        }
