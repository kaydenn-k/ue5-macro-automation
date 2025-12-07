"""
Tests for the file_utils module.
"""


from src.utils.file_utils import (
    copy_file,
    delete_file,
    ensure_directory,
    get_file_hash,
    get_files_by_extension,
    is_valid_asset_path,
    move_file,
    normalize_path,
)


class TestEnsureDirectory:
    """Tests for ensure_directory function."""

    def test_create_new_directory(self, temp_directory):
        """Test creating a new directory."""
        new_dir = temp_directory / "new_folder"

        result = ensure_directory(str(new_dir))

        assert result is True
        assert new_dir.exists()

    def test_existing_directory(self, temp_directory):
        """Test with existing directory."""
        result = ensure_directory(str(temp_directory))

        assert result is True

    def test_nested_directory(self, temp_directory):
        """Test creating nested directories."""
        nested = temp_directory / "a" / "b" / "c"

        result = ensure_directory(str(nested))

        assert result is True
        assert nested.exists()


class TestGetFilesByExtension:
    """Tests for get_files_by_extension function."""

    def test_find_files(self, temp_directory):
        """Test finding files by extension."""
        (temp_directory / "file1.fbx").touch()
        (temp_directory / "file2.fbx").touch()
        (temp_directory / "file3.obj").touch()

        fbx_files = get_files_by_extension(str(temp_directory), ".fbx")

        assert len(fbx_files) == 2

    def test_recursive_search(self, temp_directory):
        """Test recursive file search."""
        subdir = temp_directory / "subdir"
        subdir.mkdir()

        (temp_directory / "file1.fbx").touch()
        (subdir / "file2.fbx").touch()

        files = get_files_by_extension(str(temp_directory), ".fbx", recursive=True)

        assert len(files) == 2

    def test_no_matches(self, temp_directory):
        """Test when no files match."""
        (temp_directory / "file.txt").touch()

        files = get_files_by_extension(str(temp_directory), ".fbx")

        assert len(files) == 0


class TestCopyFile:
    """Tests for copy_file function."""

    def test_copy_file(self, temp_directory):
        """Test copying a file."""
        source = temp_directory / "source.txt"
        source.write_text("test content")
        dest = temp_directory / "dest.txt"

        result = copy_file(str(source), str(dest))

        assert result is True
        assert dest.exists()
        assert dest.read_text() == "test content"

    def test_copy_to_new_directory(self, temp_directory):
        """Test copying to a new directory."""
        source = temp_directory / "source.txt"
        source.write_text("test")
        dest = temp_directory / "new_dir" / "dest.txt"

        result = copy_file(str(source), str(dest))

        assert result is True
        assert dest.exists()


class TestMoveFile:
    """Tests for move_file function."""

    def test_move_file(self, temp_directory):
        """Test moving a file."""
        source = temp_directory / "source.txt"
        source.write_text("test content")
        dest = temp_directory / "dest.txt"

        result = move_file(str(source), str(dest))

        assert result is True
        assert not source.exists()
        assert dest.exists()


class TestDeleteFile:
    """Tests for delete_file function."""

    def test_delete_file(self, temp_directory):
        """Test deleting a file."""
        file_path = temp_directory / "to_delete.txt"
        file_path.touch()

        result = delete_file(str(file_path))

        assert result is True
        assert not file_path.exists()

    def test_delete_nonexistent(self, temp_directory):
        """Test deleting a nonexistent file."""
        result = delete_file(str(temp_directory / "nonexistent.txt"))

        assert result is False


class TestGetFileHash:
    """Tests for get_file_hash function."""

    def test_file_hash(self, temp_directory):
        """Test getting file hash."""
        file_path = temp_directory / "test.txt"
        file_path.write_text("test content")

        hash1 = get_file_hash(str(file_path))
        hash2 = get_file_hash(str(file_path))

        assert hash1 is not None
        assert hash1 == hash2

    def test_different_content_different_hash(self, temp_directory):
        """Test that different content produces different hash."""
        file1 = temp_directory / "file1.txt"
        file2 = temp_directory / "file2.txt"
        file1.write_text("content 1")
        file2.write_text("content 2")

        hash1 = get_file_hash(str(file1))
        hash2 = get_file_hash(str(file2))

        assert hash1 != hash2


class TestIsValidAssetPath:
    """Tests for is_valid_asset_path function."""

    def test_valid_game_path(self):
        """Test valid game path."""
        assert is_valid_asset_path("/Game/Meshes/TestMesh") is True

    def test_valid_engine_path(self):
        """Test valid engine path."""
        assert is_valid_asset_path("/Engine/Content/Test") is True

    def test_invalid_path(self):
        """Test invalid path."""
        assert is_valid_asset_path("C:/Users/Test") is False

    def test_empty_path(self):
        """Test empty path."""
        assert is_valid_asset_path("") is False


class TestNormalizePath:
    """Tests for normalize_path function."""

    def test_normalize_backslashes(self):
        """Test normalizing backslashes."""
        result = normalize_path("C:\\Users\\Test\\File.txt")

        assert "\\" not in result
        assert "/" in result

    def test_normalize_double_slashes(self):
        """Test normalizing double slashes."""
        result = normalize_path("/Game//Meshes///Test")

        assert "//" not in result
