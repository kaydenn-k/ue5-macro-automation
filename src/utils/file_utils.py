"""
File utilities for UE5 Macro Automation.

Provides file system operations with safety checks and Unreal-specific
path handling.

Example Usage:
    >>> ensure_directory("/Game/Meshes/Trees")
    >>> files = find_files("/path/to/assets", "*.fbx")
    >>> safe_copy("/source/model.fbx", "/dest/model.fbx")
"""

from __future__ import annotations

import hashlib
import logging
import shutil
from collections.abc import Generator
from pathlib import Path

logger = logging.getLogger(__name__)


def ensure_directory(path: str | Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists

    Returns:
        Path object for the directory

    Example:
        >>> ensure_directory("/path/to/new/directory")
        PosixPath('/path/to/new/directory')
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_path(path: str | Path) -> Path:
    """
    Convert a path to a safe, normalized Path object.

    Args:
        path: Path string or Path object

    Returns:
        Normalized Path object

    Example:
        >>> safe_path("./relative/../path/to/file.txt")
        PosixPath('/absolute/path/to/file.txt')
    """
    path = Path(path)
    return path.resolve()


def find_files(
    directory: str | Path,
    pattern: str = "*",
    recursive: bool = True
) -> list[Path]:
    """
    Find files matching a pattern in a directory.

    Args:
        directory: Directory to search
        pattern: Glob pattern to match (e.g., "*.fbx", "*.obj")
        recursive: Whether to search subdirectories

    Returns:
        List of matching file paths

    Example:
        >>> find_files("/assets", "*.fbx")
        [PosixPath('/assets/model1.fbx'), PosixPath('/assets/model2.fbx')]
    """
    directory = Path(directory)

    if not directory.exists():
        logger.warning(f"Directory does not exist: {directory}")
        return []

    if recursive:
        return list(directory.rglob(pattern))
    else:
        return list(directory.glob(pattern))


def find_files_generator(
    directory: str | Path,
    pattern: str = "*",
    recursive: bool = True
) -> Generator[Path, None, None]:
    """
    Generator version of find_files for memory efficiency.

    Args:
        directory: Directory to search
        pattern: Glob pattern to match
        recursive: Whether to search subdirectories

    Yields:
        Matching file paths
    """
    directory = Path(directory)

    if not directory.exists():
        return

    if recursive:
        yield from directory.rglob(pattern)
    else:
        yield from directory.glob(pattern)


def copy_file(
    source: str | Path,
    destination: str | Path,
    overwrite: bool = False
) -> bool:
    """
    Copy a file safely.

    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Whether to overwrite existing files

    Returns:
        True if copy was successful

    Example:
        >>> copy_file("/source/model.fbx", "/dest/model.fbx")
        True
    """
    source = Path(source)
    destination = Path(destination)

    if not source.exists():
        logger.error(f"Source file does not exist: {source}")
        return False

    if destination.exists() and not overwrite:
        logger.warning(f"Destination exists and overwrite=False: {destination}")
        return False

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        logger.debug(f"Copied: {source} -> {destination}")
        return True
    except Exception as e:
        logger.error(f"Failed to copy file: {e}")
        return False


def move_file(
    source: str | Path,
    destination: str | Path,
    overwrite: bool = False
) -> bool:
    """
    Move a file safely.

    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Whether to overwrite existing files

    Returns:
        True if move was successful

    Example:
        >>> move_file("/source/model.fbx", "/dest/model.fbx")
        True
    """
    source = Path(source)
    destination = Path(destination)

    if not source.exists():
        logger.error(f"Source file does not exist: {source}")
        return False

    if destination.exists():
        if overwrite:
            destination.unlink()
        else:
            logger.warning(f"Destination exists and overwrite=False: {destination}")
            return False

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        logger.debug(f"Moved: {source} -> {destination}")
        return True
    except Exception as e:
        logger.error(f"Failed to move file: {e}")
        return False


def delete_file(path: str | Path) -> bool:
    """
    Delete a file safely.

    Args:
        path: File path to delete

    Returns:
        True if deletion was successful
    """
    path = Path(path)

    if not path.exists():
        return True

    try:
        path.unlink()
        logger.debug(f"Deleted: {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete file: {e}")
        return False


def get_file_hash(path: str | Path, algorithm: str = "md5") -> str | None:
    """
    Calculate hash of a file.

    Args:
        path: File path
        algorithm: Hash algorithm (md5, sha1, sha256)

    Returns:
        Hash string or None on error

    Example:
        >>> get_file_hash("/path/to/file.fbx")
        'd41d8cd98f00b204e9800998ecf8427e'
    """
    path = Path(path)

    if not path.exists():
        return None

    try:
        hasher = hashlib.new(algorithm)
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Failed to hash file: {e}")
        return None


def get_file_size(path: str | Path) -> int:
    """
    Get file size in bytes.

    Args:
        path: File path

    Returns:
        File size in bytes, or -1 on error
    """
    path = Path(path)

    if not path.exists():
        return -1

    return path.stat().st_size


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string

    Example:
        >>> format_file_size(1024 * 1024)
        '1.00 MB'
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def is_valid_filename(filename: str) -> bool:
    """
    Check if a filename is valid.

    Args:
        filename: Filename to check

    Returns:
        True if valid
    """
    invalid_chars = '<>:"/\\|?*'
    return not any(char in filename for char in invalid_chars)


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """
    Sanitize a filename by replacing invalid characters.

    Args:
        filename: Filename to sanitize
        replacement: Character to replace invalid chars with

    Returns:
        Sanitized filename

    Example:
        >>> sanitize_filename("my:file<name>.txt")
        'my_file_name_.txt'
    """
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, replacement)
    return filename


def get_unique_filename(path: str | Path) -> Path:
    """
    Get a unique filename by appending a number if necessary.

    Args:
        path: Desired file path

    Returns:
        Unique file path

    Example:
        >>> get_unique_filename("/path/to/file.txt")
        PosixPath('/path/to/file_1.txt')  # if file.txt exists
    """
    path = Path(path)

    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent

    counter = 1
    while True:
        new_path = parent / f"{stem}_{counter}{suffix}"
        if not new_path.exists():
            return new_path
        counter += 1


def list_directory(
    directory: str | Path,
    include_hidden: bool = False
) -> list[Path]:
    """
    List contents of a directory.

    Args:
        directory: Directory to list
        include_hidden: Whether to include hidden files

    Returns:
        List of paths in the directory
    """
    directory = Path(directory)

    if not directory.exists():
        return []

    items = list(directory.iterdir())

    if not include_hidden:
        items = [item for item in items if not item.name.startswith(".")]

    return sorted(items)


def get_extension(path: str | Path) -> str:
    """
    Get file extension without the dot.

    Args:
        path: File path

    Returns:
        Extension string (lowercase)

    Example:
        >>> get_extension("/path/to/model.FBX")
        'fbx'
    """
    return Path(path).suffix.lstrip(".").lower()


def change_extension(path: str | Path, new_extension: str) -> Path:
    """
    Change file extension.

    Args:
        path: File path
        new_extension: New extension (with or without dot)

    Returns:
        Path with new extension

    Example:
        >>> change_extension("/path/to/model.fbx", "obj")
        PosixPath('/path/to/model.obj')
    """
    path = Path(path)
    new_extension = new_extension.lstrip(".")
    return path.with_suffix(f".{new_extension}")


def backup_file(
    path: str | Path,
    backup_dir: str | Path | None = None,
    suffix: str = ".bak"
) -> Path | None:
    """
    Create a backup of a file.

    Args:
        path: File to backup
        backup_dir: Directory for backup (default: same directory)
        suffix: Suffix to add to backup filename

    Returns:
        Path to backup file or None on error

    Example:
        >>> backup_file("/path/to/file.txt")
        PosixPath('/path/to/file.txt.bak')
    """
    path = Path(path)

    if not path.exists():
        logger.error(f"File does not exist: {path}")
        return None

    if backup_dir:
        backup_path = Path(backup_dir) / f"{path.name}{suffix}"
    else:
        backup_path = path.with_suffix(path.suffix + suffix)

    backup_path = get_unique_filename(backup_path)

    if copy_file(path, backup_path, overwrite=False):
        return backup_path

    return None
