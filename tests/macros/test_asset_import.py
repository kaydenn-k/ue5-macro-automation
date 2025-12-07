"""
Tests for the asset_import module.
"""

from unittest.mock import MagicMock, patch

from src.macros.asset_import import (
    ImportOptions,
    batch_import,
    generate_lods,
    import_fbx,
    import_obj,
)


class TestImportOptions:
    """Tests for the ImportOptions class."""

    def test_default_options(self):
        """Test default import options."""
        options = ImportOptions()

        assert options.replace_existing is False
        assert options.auto_generate_collision is True
        assert options.import_materials is True
        assert options.import_textures is True
        assert options.generate_lods is False
        assert options.lod_count == 3

    def test_custom_options(self):
        """Test custom import options."""
        options = ImportOptions(
            replace_existing=True,
            auto_generate_collision=False,
            generate_lods=True,
            lod_count=5,
        )

        assert options.replace_existing is True
        assert options.auto_generate_collision is False
        assert options.generate_lods is True
        assert options.lod_count == 5


class TestImportFunctions:
    """Tests for import functions."""

    @patch("src.macros.asset_import.unreal")
    def test_import_fbx(self, mock_unreal):
        """Test FBX import."""
        mock_unreal.AssetImportTask.return_value = MagicMock()
        mock_unreal.AssetToolsHelpers.get_asset_tools.return_value = MagicMock()

        result = import_fbx(
            "/path/to/model.fbx",
            "/Game/Meshes",
        )

        assert result is not None

    @patch("src.macros.asset_import.unreal")
    def test_import_obj(self, mock_unreal):
        """Test OBJ import."""
        mock_unreal.AssetImportTask.return_value = MagicMock()
        mock_unreal.AssetToolsHelpers.get_asset_tools.return_value = MagicMock()

        result = import_obj(
            "/path/to/model.obj",
            "/Game/Meshes",
        )

        assert result is not None

    @patch("src.macros.asset_import.unreal")
    def test_batch_import(self, mock_unreal):
        """Test batch import."""
        mock_unreal.AssetImportTask.return_value = MagicMock()
        mock_unreal.AssetToolsHelpers.get_asset_tools.return_value = MagicMock()

        files = [
            "/path/to/model1.fbx",
            "/path/to/model2.fbx",
            "/path/to/model3.obj",
        ]

        results = batch_import(files, "/Game/Meshes")

        assert len(results) == 3

    @patch("src.macros.asset_import.unreal")
    def test_generate_lods(self, mock_unreal):
        """Test LOD generation."""
        mock_mesh = MagicMock()
        mock_unreal.EditorAssetLibrary.load_asset.return_value = mock_mesh

        result = generate_lods("/Game/Meshes/TestMesh", lod_count=3)

        assert result is not None

    @patch("src.macros.asset_import.unreal")
    def test_import_with_options(self, mock_unreal):
        """Test import with custom options."""
        mock_unreal.AssetImportTask.return_value = MagicMock()
        mock_unreal.AssetToolsHelpers.get_asset_tools.return_value = MagicMock()

        options = ImportOptions(
            replace_existing=True,
            generate_lods=True,
            lod_count=4,
        )

        result = import_fbx(
            "/path/to/model.fbx",
            "/Game/Meshes",
            options,
        )

        assert result is not None
