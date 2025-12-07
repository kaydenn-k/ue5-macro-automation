"""
Batch Rename Template for UE5 Macro Automation.

A pre-built macro template for smart renaming of assets and actors with
prefix/suffix patterns, numbering, and search/replace.

Example Usage:
    >>> from src.templates.batch_rename_assets import BatchRenameTemplate
    >>> template = BatchRenameTemplate()
    >>> result = template.execute(
    ...     targets=selected_assets,
    ...     prefix="SM_",
    ...     suffix="_LOD0"
    ... )
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from src.core.macro_recorder import ActionType, Macro, RecordedAction
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
class RenameConfig:
    """
    Configuration for batch renaming.

    Attributes:
        prefix: Prefix to add to names
        suffix: Suffix to add to names
        search: Text to search for (regex supported)
        replace: Text to replace with
        numbering: Whether to add numbering
        start_number: Starting number for numbering
        padding: Zero-padding for numbers
        case_mode: Case transformation (none, upper, lower, title)
        remove_spaces: Whether to remove spaces
        space_replacement: Character to replace spaces with
    """
    prefix: str = ""
    suffix: str = ""
    search: str = ""
    replace: str = ""
    numbering: bool = False
    start_number: int = 1
    padding: int = 2
    case_mode: str = "none"
    remove_spaces: bool = False
    space_replacement: str = "_"


@dataclass
class RenameResult:
    """
    Result of batch rename operation.

    Attributes:
        success: Whether rename was successful
        renamed_count: Number of items renamed
        failed_count: Number of items that failed
        rename_map: Map of old names to new names
        errors: List of error messages
    """
    success: bool
    renamed_count: int = 0
    failed_count: int = 0
    rename_map: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class BatchRenameTemplate:
    """
    Template for batch renaming assets and actors.

    This template performs:
    1. Apply prefix/suffix to names
    2. Search and replace text
    3. Add sequential numbering
    4. Transform case
    5. Handle spaces and special characters

    Example:
        >>> template = BatchRenameTemplate()
        >>> result = template.execute(
        ...     targets=get_selected_assets(),
        ...     prefix="SM_",
        ...     numbering=True,
        ...     padding=3
        ... )
        >>> print(f"Renamed {result.renamed_count} items")
    """

    NAME = "Batch Rename"
    DESCRIPTION = "Smart batch renaming with prefix/suffix and patterns"
    CATEGORY = "organization"

    def __init__(self) -> None:
        """Initialize the template."""
        self._config: RenameConfig | None = None

    def execute(
        self,
        targets: list[Any],
        **kwargs: Any
    ) -> RenameResult:
        """
        Execute the batch rename template.

        Args:
            targets: List of assets or actors to rename
            **kwargs: Rename configuration options

        Returns:
            RenameResult with rename details
        """
        self._config = RenameConfig(
            prefix=kwargs.get("prefix", ""),
            suffix=kwargs.get("suffix", ""),
            search=kwargs.get("search", ""),
            replace=kwargs.get("replace", ""),
            numbering=kwargs.get("numbering", False),
            start_number=kwargs.get("start_number", 1),
            padding=kwargs.get("padding", 2),
            case_mode=kwargs.get("case_mode", "none"),
            remove_spaces=kwargs.get("remove_spaces", False),
            space_replacement=kwargs.get("space_replacement", "_"),
        )

        result = RenameResult(success=True)

        if not targets:
            logger.warning("No targets provided for renaming")
            result.success = False
            return result

        logger.info(f"Starting batch rename of {len(targets)} items")

        with ProgressTracker("Batch Renaming", total=len(targets)) as tracker:
            for i, target in enumerate(targets):
                tracker.update(0, f"Renaming item {i + 1}/{len(targets)}")

                try:
                    old_name = self._get_name(target)
                    new_name = self._generate_new_name(old_name, i)

                    if old_name != new_name:
                        if self._rename_target(target, new_name):
                            result.rename_map[old_name] = new_name
                            result.renamed_count += 1
                        else:
                            result.failed_count += 1
                            result.errors.append(f"Failed to rename: {old_name}")

                except Exception as e:
                    result.failed_count += 1
                    result.errors.append(str(e))

                tracker.update(1)

        result.success = result.failed_count == 0

        logger.info(
            f"Batch rename complete: {result.renamed_count} renamed, "
            f"{result.failed_count} failed"
        )

        return result

    def _get_name(self, target: Any) -> str:
        """Get the name of a target."""
        if isinstance(target, str):
            return target.split("/")[-1]

        if UNREAL_AVAILABLE:
            if hasattr(target, "get_name"):
                return target.get_name()
            if hasattr(target, "get_asset_name"):
                return target.get_asset_name()

        return str(target)

    def _generate_new_name(self, old_name: str, index: int) -> str:
        """Generate a new name based on configuration."""
        if not self._config:
            return old_name

        new_name = old_name

        if self._config.search:
            try:
                new_name = re.sub(
                    self._config.search,
                    self._config.replace,
                    new_name
                )
            except re.error:
                new_name = new_name.replace(
                    self._config.search,
                    self._config.replace
                )

        if self._config.remove_spaces:
            new_name = new_name.replace(" ", self._config.space_replacement)

        if self._config.case_mode == "upper":
            new_name = new_name.upper()
        elif self._config.case_mode == "lower":
            new_name = new_name.lower()
        elif self._config.case_mode == "title":
            new_name = new_name.title()

        new_name = f"{self._config.prefix}{new_name}{self._config.suffix}"

        if self._config.numbering:
            number = self._config.start_number + index
            number_str = str(number).zfill(self._config.padding)
            new_name = f"{new_name}_{number_str}"

        return new_name

    def _rename_target(self, target: Any, new_name: str) -> bool:
        """Rename a target."""
        if not UNREAL_AVAILABLE:
            logger.info(f"[MOCK] Rename: {self._get_name(target)} -> {new_name}")
            return True

        import unreal  # noqa: F401

        try:
            if isinstance(target, str):
                old_path = target
                new_path = "/".join(old_path.split("/")[:-1]) + "/" + new_name
                return unreal.EditorAssetLibrary.rename_asset(old_path, new_path)

            if hasattr(target, "set_actor_label"):
                target.set_actor_label(new_name)
                return True

            if hasattr(target, "rename"):
                return target.rename(new_name)

            return False

        except Exception as e:
            logger.error(f"Rename failed: {e}")
            return False

    def preview(
        self,
        targets: list[Any],
        **kwargs: Any
    ) -> dict[str, str]:
        """
        Preview rename results without applying.

        Args:
            targets: List of targets to preview
            **kwargs: Rename configuration options

        Returns:
            Dictionary mapping old names to new names
        """
        self._config = RenameConfig(
            prefix=kwargs.get("prefix", ""),
            suffix=kwargs.get("suffix", ""),
            search=kwargs.get("search", ""),
            replace=kwargs.get("replace", ""),
            numbering=kwargs.get("numbering", False),
            start_number=kwargs.get("start_number", 1),
            padding=kwargs.get("padding", 2),
            case_mode=kwargs.get("case_mode", "none"),
            remove_spaces=kwargs.get("remove_spaces", False),
            space_replacement=kwargs.get("space_replacement", "_"),
        )

        preview_map: dict[str, str] = {}

        for i, target in enumerate(targets):
            old_name = self._get_name(target)
            new_name = self._generate_new_name(old_name, i)
            preview_map[old_name] = new_name

        return preview_map

    def to_macro(self) -> Macro:
        """Convert the template to a Macro object."""
        actions = [
            RecordedAction(
                action_type=ActionType.CUSTOM,
                parameters={
                    "template": "BatchRenameTemplate",
                    "config": self.get_default_config()
                },
                description="Execute Batch Rename template"
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
            "prefix": "",
            "suffix": "",
            "search": "",
            "replace": "",
            "numbering": False,
            "start_number": 1,
            "padding": 2,
            "case_mode": "none",
            "remove_spaces": False,
            "space_replacement": "_",
        }


def smart_rename(
    name: str,
    prefix: str = "",
    suffix: str = "",
    search: str = "",
    replace: str = "",
    case_mode: str = "none"
) -> str:
    """
    Apply smart renaming to a single name.

    Args:
        name: Original name
        prefix: Prefix to add
        suffix: Suffix to add
        search: Text to search for
        replace: Text to replace with
        case_mode: Case transformation

    Returns:
        Transformed name
    """
    result = name

    if search:
        result = result.replace(search, replace)

    if case_mode == "upper":
        result = result.upper()
    elif case_mode == "lower":
        result = result.lower()
    elif case_mode == "title":
        result = result.title()

    return f"{prefix}{result}{suffix}"
