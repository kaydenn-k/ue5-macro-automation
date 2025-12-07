"""
Pre-built Macro Templates for UE5 Macro Automation.

Contains ready-to-use macro templates for common tasks:
- Import Tree Assets
- Optimize Scene
- Setup Environment
- Batch Rename
- Export Selected
"""

from src.templates.batch_rename_assets import BatchRenameTemplate
from src.templates.export_selected_assets import ExportSelectedTemplate
from src.templates.import_tree_assets import ImportTreeAssetsTemplate
from src.templates.optimize_scene import OptimizeSceneTemplate
from src.templates.setup_environment import SetupEnvironmentTemplate

__all__ = [
    "ImportTreeAssetsTemplate",
    "OptimizeSceneTemplate",
    "SetupEnvironmentTemplate",
    "BatchRenameTemplate",
    "ExportSelectedTemplate",
]
