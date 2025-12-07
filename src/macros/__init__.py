"""
Macro implementations for UE5 Macro Automation System.

Contains macro functions for:
- Asset import and batch processing
- Material assignment and creation
- Collision generation
- Level organization
- Asset validation and cleanup
"""

from src.macros.asset_import import (
    batch_import_assets,
    import_fbx,
    import_obj,
    import_with_auto_lod,
)
from src.macros.collision_ops import (
    batch_generate_collision,
    generate_collision,
    set_collision_complexity,
)
from src.macros.level_ops import (
    group_actors,
    organize_by_type,
    rename_actors,
    set_parent_hierarchy,
)
from src.macros.lighting_ops import (
    build_lighting,
    set_lighting_quality,
    setup_basic_lighting,
)
from src.macros.material_ops import (
    assign_material_by_convention,
    batch_create_material_instances,
    create_material_instance,
    import_textures_and_create_materials,
)
from src.macros.validation import (
    cleanup_unused_assets,
    find_broken_references,
    fix_asset_redirectors,
    validate_assets,
)

__all__ = [
    "import_fbx",
    "import_obj",
    "batch_import_assets",
    "import_with_auto_lod",
    "assign_material_by_convention",
    "create_material_instance",
    "batch_create_material_instances",
    "import_textures_and_create_materials",
    "generate_collision",
    "batch_generate_collision",
    "set_collision_complexity",
    "group_actors",
    "rename_actors",
    "set_parent_hierarchy",
    "organize_by_type",
    "build_lighting",
    "set_lighting_quality",
    "setup_basic_lighting",
    "validate_assets",
    "cleanup_unused_assets",
    "find_broken_references",
    "fix_asset_redirectors",
]
