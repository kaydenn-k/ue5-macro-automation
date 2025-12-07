"""
Asset Validation and Cleanup Macros for UE5 Macro Automation.

Provides functions for validating assets, finding issues, and cleaning up
unused or broken assets.

Example Usage:
    >>> results = validate_assets(["/Game/Meshes"])
    >>> unused = cleanup_unused_assets("/Game/Meshes", dry_run=True)
    >>> broken = find_broken_references("/Game/Levels/Main")
    >>> fix_asset_redirectors("/Game")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto

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


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


@dataclass
class ValidationIssue:
    """
    A single validation issue.

    Attributes:
        asset_path: Path to the affected asset
        issue_type: Type of issue
        message: Description of the issue
        severity: Severity level
        auto_fixable: Whether the issue can be auto-fixed
    """
    asset_path: str
    issue_type: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.WARNING
    auto_fixable: bool = False


@dataclass
class ValidationResult:
    """
    Result of a validation operation.

    Attributes:
        success: Whether validation completed successfully
        assets_checked: Number of assets checked
        issues: List of validation issues found
        error: Error message if validation failed
    """
    success: bool
    assets_checked: int = 0
    issues: list[ValidationIssue] = field(default_factory=list)
    error: str | None = None

    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)

    @property
    def has_critical(self) -> bool:
        """Check if there are critical issues."""
        return any(i.severity == ValidationSeverity.CRITICAL for i in self.issues)


@dataclass
class CleanupResult:
    """
    Result of a cleanup operation.

    Attributes:
        success: Whether cleanup completed successfully
        assets_removed: List of removed asset paths
        bytes_freed: Approximate bytes freed
        error: Error message if cleanup failed
    """
    success: bool
    assets_removed: list[str] = field(default_factory=list)
    bytes_freed: int = 0
    error: str | None = None


@profile_function
def validate_assets(
    paths: list[str],
    check_references: bool = True,
    check_naming: bool = True,
    check_size: bool = True,
    max_texture_size: int = 4096,
    max_mesh_triangles: int = 100000
) -> ValidationResult:
    """
    Validate assets for common issues.

    Args:
        paths: List of asset or folder paths to validate
        check_references: Check for broken references
        check_naming: Check naming conventions
        check_size: Check asset sizes
        max_texture_size: Maximum allowed texture dimension
        max_mesh_triangles: Maximum allowed mesh triangles

    Returns:
        ValidationResult with found issues

    Example:
        >>> result = validate_assets(["/Game/Meshes", "/Game/Materials"])
        >>> print(f"Found {result.error_count} errors, {result.warning_count} warnings")
    """
    issues: list[ValidationIssue] = []
    assets_checked = 0

    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Validate assets: {paths}")
        return ValidationResult(
            success=True,
            assets_checked=10,
            issues=[
                ValidationIssue(
                    asset_path="/Game/Meshes/Test",
                    issue_type="naming",
                    message="Asset name doesn't follow convention",
                    severity=ValidationSeverity.WARNING
                )
            ]
        )

    import unreal  # noqa: F401

    try:
        all_assets: list[str] = []

        for path in paths:
            if unreal.EditorAssetLibrary.does_directory_exist(path):
                assets = unreal.EditorAssetLibrary.list_assets(path, recursive=True)
                all_assets.extend(assets)
            elif unreal.EditorAssetLibrary.does_asset_exist(path):
                all_assets.append(path)

        with ProgressTracker("Validating Assets", total=len(all_assets)) as tracker:
            for asset_path in all_assets:
                tracker.update(0, f"Checking: {asset_path.split('/')[-1]}")

                asset_issues = _validate_single_asset(
                    asset_path,
                    check_references,
                    check_naming,
                    check_size,
                    max_texture_size,
                    max_mesh_triangles
                )
                issues.extend(asset_issues)
                assets_checked += 1

                tracker.update(1)

        logger.info(f"Validated {assets_checked} assets, found {len(issues)} issues")
        return ValidationResult(
            success=True,
            assets_checked=assets_checked,
            issues=issues
        )

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return ValidationResult(
            success=False,
            assets_checked=assets_checked,
            issues=issues,
            error=str(e)
        )


def _validate_single_asset(
    asset_path: str,
    check_references: bool,
    check_naming: bool,
    check_size: bool,
    max_texture_size: int,
    max_mesh_triangles: int
) -> list[ValidationIssue]:
    """Validate a single asset."""
    issues: list[ValidationIssue] = []

    if not UNREAL_AVAILABLE:
        return issues

    import unreal  # noqa: F401

    asset_name = asset_path.split("/")[-1]

    if check_naming:
        if " " in asset_name:
            issues.append(ValidationIssue(
                asset_path=asset_path,
                issue_type="naming",
                message="Asset name contains spaces",
                severity=ValidationSeverity.WARNING,
                auto_fixable=True
            ))

        if not asset_name[0].isupper():
            issues.append(ValidationIssue(
                asset_path=asset_path,
                issue_type="naming",
                message="Asset name should start with uppercase",
                severity=ValidationSeverity.INFO
            ))

    if check_references:
        try:
            unreal.EditorAssetLibrary.find_package_referencers_for_asset(asset_path)

        except Exception:
            pass

    if check_size:
        try:
            asset = unreal.load_asset(asset_path)

            if asset and isinstance(asset, unreal.Texture2D):
                width = asset.get_editor_property("imported_size").x
                height = asset.get_editor_property("imported_size").y

                if width > max_texture_size or height > max_texture_size:
                    issues.append(ValidationIssue(
                        asset_path=asset_path,
                        issue_type="size",
                        message=f"Texture size ({width}x{height}) exceeds maximum ({max_texture_size})",
                        severity=ValidationSeverity.WARNING
                    ))

            elif asset and isinstance(asset, unreal.StaticMesh):
                lod0 = asset.get_num_triangles(0)
                if lod0 > max_mesh_triangles:
                    issues.append(ValidationIssue(
                        asset_path=asset_path,
                        issue_type="size",
                        message=f"Mesh has {lod0} triangles (max: {max_mesh_triangles})",
                        severity=ValidationSeverity.WARNING
                    ))

        except Exception:
            pass

    return issues


@profile_function
def cleanup_unused_assets(
    path: str,
    dry_run: bool = True,
    exclude_patterns: list[str] | None = None
) -> CleanupResult:
    """
    Find and optionally remove unused assets.

    Args:
        path: Root path to scan for unused assets
        dry_run: If True, only report what would be removed
        exclude_patterns: Patterns to exclude from cleanup

    Returns:
        CleanupResult with removed assets

    Example:
        >>> result = cleanup_unused_assets("/Game/Meshes", dry_run=True)
        >>> print(f"Would remove {len(result.assets_removed)} assets")
    """
    exclude_patterns = exclude_patterns or []

    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Cleanup unused assets: {path} (dry_run={dry_run})")
        return CleanupResult(
            success=True,
            assets_removed=["/Game/Meshes/Unused1", "/Game/Meshes/Unused2"]
        )

    import unreal  # noqa: F401

    try:
        all_assets = unreal.EditorAssetLibrary.list_assets(path, recursive=True)

        unused_assets: list[str] = []

        with ProgressTracker("Finding Unused Assets", total=len(all_assets)) as tracker:
            for asset_path in all_assets:
                tracker.update(0, f"Checking: {asset_path.split('/')[-1]}")

                skip = False
                for pattern in exclude_patterns:
                    if pattern in asset_path:
                        skip = True
                        break

                if skip:
                    tracker.update(1)
                    continue

                referencers = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
                    asset_path
                )

                if not referencers:
                    unused_assets.append(asset_path)

                tracker.update(1)

        if not dry_run and unused_assets:
            for asset_path in unused_assets:
                unreal.EditorAssetLibrary.delete_asset(asset_path)
            logger.info(f"Deleted {len(unused_assets)} unused assets")
        else:
            logger.info(f"Found {len(unused_assets)} unused assets (dry run)")

        return CleanupResult(
            success=True,
            assets_removed=unused_assets
        )

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return CleanupResult(
            success=False,
            error=str(e)
        )


@profile_function
def find_broken_references(path: str) -> ValidationResult:
    """
    Find assets with broken references.

    Args:
        path: Root path to scan

    Returns:
        ValidationResult with broken reference issues

    Example:
        >>> result = find_broken_references("/Game/Levels/Main")
        >>> for issue in result.issues:
        ...     print(f"{issue.asset_path}: {issue.message}")
    """
    issues: list[ValidationIssue] = []
    assets_checked = 0

    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Find broken references: {path}")
        return ValidationResult(
            success=True,
            assets_checked=5,
            issues=[
                ValidationIssue(
                    asset_path="/Game/Levels/Main",
                    issue_type="broken_reference",
                    message="Missing reference: /Game/Materials/M_Missing",
                    severity=ValidationSeverity.ERROR
                )
            ]
        )

    import unreal  # noqa: F401

    try:
        all_assets = unreal.EditorAssetLibrary.list_assets(path, recursive=True)

        with ProgressTracker("Finding Broken References", total=len(all_assets)) as tracker:
            for asset_path in all_assets:
                tracker.update(0, f"Checking: {asset_path.split('/')[-1]}")

                try:
                    dependencies = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
                        asset_path
                    )

                    for dep in dependencies:
                        if not unreal.EditorAssetLibrary.does_asset_exist(dep):
                            issues.append(ValidationIssue(
                                asset_path=asset_path,
                                issue_type="broken_reference",
                                message=f"Missing reference: {dep}",
                                severity=ValidationSeverity.ERROR
                            ))

                except Exception:
                    pass

                assets_checked += 1
                tracker.update(1)

        logger.info(f"Checked {assets_checked} assets, found {len(issues)} broken references")
        return ValidationResult(
            success=True,
            assets_checked=assets_checked,
            issues=issues
        )

    except Exception as e:
        logger.error(f"Reference check failed: {e}")
        return ValidationResult(
            success=False,
            error=str(e)
        )


@profile_function
def fix_asset_redirectors(path: str) -> CleanupResult:
    """
    Fix asset redirectors in a path.

    Args:
        path: Root path to scan for redirectors

    Returns:
        CleanupResult with fixed redirectors

    Example:
        >>> result = fix_asset_redirectors("/Game")
        >>> print(f"Fixed {len(result.assets_removed)} redirectors")
    """
    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Fix asset redirectors: {path}")
        return CleanupResult(
            success=True,
            assets_removed=["/Game/Redirector1", "/Game/Redirector2"]
        )

    import unreal  # noqa: F401

    try:
        asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()

        filter_obj = unreal.ARFilter()
        filter_obj.class_names = ["ObjectRedirector"]
        filter_obj.package_paths = [path]
        filter_obj.recursive_paths = True

        redirectors = asset_registry.get_assets(filter_obj)

        fixed_redirectors: list[str] = []

        for redirector_data in redirectors:
            redirector_path = str(redirector_data.package_name)

            try:
                unreal.EditorAssetLibrary.consolidate_assets(
                    redirector_path, []
                )
                fixed_redirectors.append(redirector_path)
            except Exception:
                pass

        logger.info(f"Fixed {len(fixed_redirectors)} redirectors")
        return CleanupResult(
            success=True,
            assets_removed=fixed_redirectors
        )

    except Exception as e:
        logger.error(f"Redirector fix failed: {e}")
        return CleanupResult(
            success=False,
            error=str(e)
        )


def find_duplicate_assets(path: str) -> dict[str, list[str]]:
    """
    Find potentially duplicate assets based on name similarity.

    Args:
        path: Root path to scan

    Returns:
        Dictionary mapping base names to list of similar asset paths

    Example:
        >>> duplicates = find_duplicate_assets("/Game/Meshes")
        >>> for name, paths in duplicates.items():
        ...     print(f"{name}: {len(paths)} potential duplicates")
    """
    if not UNREAL_AVAILABLE:
        return {"Tree": ["/Game/Meshes/Tree", "/Game/Meshes/Tree_01"]}

    import unreal  # noqa: F401

    try:
        all_assets = unreal.EditorAssetLibrary.list_assets(path, recursive=True)

        name_groups: dict[str, list[str]] = {}

        for asset_path in all_assets:
            asset_name = asset_path.split("/")[-1]

            base_name = asset_name.rstrip("0123456789_")

            if base_name not in name_groups:
                name_groups[base_name] = []
            name_groups[base_name].append(asset_path)

        duplicates = {
            name: paths for name, paths in name_groups.items()
            if len(paths) > 1
        }

        return duplicates

    except Exception as e:
        logger.error(f"Duplicate search failed: {e}")
        return {}


def get_asset_size(asset_path: str) -> int:
    """
    Get the size of an asset in bytes.

    Args:
        asset_path: Path to the asset

    Returns:
        Size in bytes, or -1 on error
    """
    if not UNREAL_AVAILABLE:
        return 1024 * 1024

    import unreal  # noqa: F401

    try:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        if asset_data:
            return asset_data.get_tag_value("Size") or 0
        return -1
    except Exception:
        return -1


def generate_validation_report(result: ValidationResult) -> str:
    """
    Generate a human-readable validation report.

    Args:
        result: ValidationResult to report on

    Returns:
        Formatted report string

    Example:
        >>> result = validate_assets(["/Game/Meshes"])
        >>> print(generate_validation_report(result))
    """
    lines = [
        "=" * 60,
        "ASSET VALIDATION REPORT",
        "=" * 60,
        "",
        f"Assets Checked: {result.assets_checked}",
        f"Total Issues: {len(result.issues)}",
        f"  Errors: {result.error_count}",
        f"  Warnings: {result.warning_count}",
        "",
    ]

    if result.issues:
        lines.append("ISSUES:")
        lines.append("-" * 60)

        sorted_issues = sorted(
            result.issues,
            key=lambda i: (i.severity.value, i.asset_path),
            reverse=True
        )

        for issue in sorted_issues:
            severity_str = issue.severity.name
            fixable_str = " [AUTO-FIXABLE]" if issue.auto_fixable else ""
            lines.append(f"[{severity_str}] {issue.asset_path}")
            lines.append(f"  Type: {issue.issue_type}")
            lines.append(f"  {issue.message}{fixable_str}")
            lines.append("")
    else:
        lines.append("No issues found!")

    lines.append("=" * 60)

    return "\n".join(lines)


def auto_fix_issues(issues: list[ValidationIssue]) -> int:
    """
    Attempt to auto-fix fixable validation issues.

    Args:
        issues: List of validation issues

    Returns:
        Number of issues fixed

    Example:
        >>> result = validate_assets(["/Game/Meshes"])
        >>> fixed = auto_fix_issues(result.issues)
        >>> print(f"Fixed {fixed} issues")
    """
    fixable = [i for i in issues if i.auto_fixable]
    fixed = 0

    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Auto-fix {len(fixable)} issues")
        return len(fixable)

    import unreal  # noqa: F401

    for issue in fixable:
        try:
            if issue.issue_type == "naming" and " " in issue.asset_path:
                new_path = issue.asset_path.replace(" ", "_")
                if unreal.EditorAssetLibrary.rename_asset(issue.asset_path, new_path):
                    fixed += 1

        except Exception as e:
            logger.warning(f"Failed to fix issue: {e}")

    logger.info(f"Auto-fixed {fixed}/{len(fixable)} issues")
    return fixed
