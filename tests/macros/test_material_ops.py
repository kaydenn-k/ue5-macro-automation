"""
Tests for the material_ops module.
"""

from unittest.mock import MagicMock, patch

from src.macros.material_ops import (
    MaterialConvention,
    assign_material,
    assign_material_by_convention,
    batch_assign_materials,
    create_material_instance,
)


class TestMaterialConvention:
    """Tests for the MaterialConvention class."""

    def test_default_convention(self):
        """Test default material convention."""
        convention = MaterialConvention()

        assert "wood" in convention.patterns
        assert "metal" in convention.patterns
        assert "glass" in convention.patterns

    def test_custom_convention(self):
        """Test custom material convention."""
        convention = MaterialConvention(
            patterns={
                "custom": "/Game/Materials/M_Custom",
            }
        )

        assert "custom" in convention.patterns

    def test_get_material_for_name(self):
        """Test getting material for a name."""
        convention = MaterialConvention()

        material = convention.get_material_for_name("SM_WoodTable")

        assert material is not None
        assert "wood" in material.lower() or "Wood" in material


class TestMaterialFunctions:
    """Tests for material functions."""

    @patch("src.macros.material_ops.unreal")
    def test_assign_material(self, mock_unreal):
        """Test assigning a material."""
        mock_mesh = MagicMock()
        mock_material = MagicMock()
        mock_unreal.EditorAssetLibrary.load_asset.side_effect = [
            mock_mesh,
            mock_material,
        ]

        result = assign_material(
            "/Game/Meshes/TestMesh",
            "/Game/Materials/M_Test",
        )

        assert result is True

    @patch("src.macros.material_ops.unreal")
    def test_assign_material_by_convention(self, mock_unreal):
        """Test assigning material by naming convention."""
        mock_mesh = MagicMock()
        mock_material = MagicMock()
        mock_unreal.EditorAssetLibrary.load_asset.side_effect = [
            mock_mesh,
            mock_material,
        ]

        result = assign_material_by_convention(
            "/Game/Meshes/SM_WoodTable",
        )

        assert result is True

    @patch("src.macros.material_ops.unreal")
    def test_create_material_instance(self, mock_unreal):
        """Test creating a material instance."""
        mock_parent = MagicMock()
        mock_instance = MagicMock()
        mock_unreal.EditorAssetLibrary.load_asset.return_value = mock_parent
        mock_unreal.AssetToolsHelpers.get_asset_tools.return_value.create_asset.return_value = mock_instance

        result = create_material_instance(
            "/Game/Materials/M_Parent",
            "/Game/Materials/MI_Child",
        )

        assert result is not None

    @patch("src.macros.material_ops.unreal")
    def test_batch_assign_materials(self, mock_unreal):
        """Test batch assigning materials."""
        mock_mesh = MagicMock()
        mock_material = MagicMock()
        mock_unreal.EditorAssetLibrary.load_asset.return_value = mock_mesh
        mock_unreal.EditorAssetLibrary.load_asset.return_value = mock_material

        assignments = {
            "/Game/Meshes/Mesh1": "/Game/Materials/M_1",
            "/Game/Meshes/Mesh2": "/Game/Materials/M_2",
        }

        results = batch_assign_materials(assignments)

        assert len(results) == 2
