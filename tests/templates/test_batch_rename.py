"""
Tests for the batch_rename template module.
"""

from unittest.mock import patch

import pytest

from src.templates.batch_rename import (
    BatchRenameTemplate,
    RenameConfig,
    RenameResult,
    smart_rename,
)


class TestRenameConfig:
    """Tests for the RenameConfig class."""

    def test_default_config(self):
        """Test default rename configuration."""
        config = RenameConfig()

        assert config.prefix == ""
        assert config.suffix == ""
        assert config.search == ""
        assert config.replace == ""
        assert config.use_regex is False
        assert config.start_number == 1

    def test_custom_config(self):
        """Test custom rename configuration."""
        config = RenameConfig(
            prefix="SM_",
            suffix="_LOD0",
            search="old",
            replace="new",
            use_regex=True,
        )

        assert config.prefix == "SM_"
        assert config.suffix == "_LOD0"
        assert config.search == "old"
        assert config.replace == "new"
        assert config.use_regex is True


class TestSmartRename:
    """Tests for the smart_rename function."""

    def test_add_prefix(self):
        """Test adding prefix."""
        result = smart_rename("Mesh", prefix="SM_")

        assert result == "SM_Mesh"

    def test_add_suffix(self):
        """Test adding suffix."""
        result = smart_rename("Mesh", suffix="_LOD0")

        assert result == "Mesh_LOD0"

    def test_search_replace(self):
        """Test search and replace."""
        result = smart_rename("OldMesh", search="Old", replace="New")

        assert result == "NewMesh"

    def test_regex_replace(self):
        """Test regex replacement."""
        result = smart_rename(
            "Mesh_001",
            search=r"_\d+",
            replace="_LOD0",
            use_regex=True,
        )

        assert result == "Mesh_LOD0"

    def test_sequential_numbering(self):
        """Test sequential numbering."""
        result = smart_rename("Mesh", number=5, number_padding=3)

        assert "005" in result

    def test_case_transform_upper(self):
        """Test uppercase transformation."""
        result = smart_rename("mesh", case_transform="upper")

        assert result == "MESH"

    def test_case_transform_lower(self):
        """Test lowercase transformation."""
        result = smart_rename("MESH", case_transform="lower")

        assert result == "mesh"

    def test_remove_spaces(self):
        """Test removing spaces."""
        result = smart_rename("My Mesh Name", remove_spaces=True)

        assert " " not in result


class TestBatchRenameTemplate:
    """Tests for the BatchRenameTemplate class."""

    @pytest.fixture
    def template(self):
        """Create a BatchRenameTemplate instance."""
        return BatchRenameTemplate()

    def test_template_creation(self, template):
        """Test creating a template."""
        assert template is not None
        assert template.name == "Batch Rename"

    def test_get_default_config(self, template):
        """Test getting default configuration."""
        config = template.get_default_config()

        assert isinstance(config, RenameConfig)

    def test_preview(self, template):
        """Test preview functionality."""
        config = RenameConfig(prefix="SM_")
        targets = ["Mesh1", "Mesh2", "Mesh3"]

        preview = template.preview(targets, config)

        assert len(preview) == 3
        assert all(name.startswith("SM_") for name in preview.values())

    @patch("src.templates.batch_rename.unreal")
    def test_execute(self, mock_unreal, template):
        """Test executing the template."""
        mock_unreal.EditorAssetLibrary.rename_asset.return_value = True

        config = RenameConfig(prefix="SM_")

        result = template.execute(
            targets=["/Game/Meshes/Mesh1"],
            config=config,
        )

        assert isinstance(result, RenameResult)
        assert result.success

    def test_to_macro(self, template):
        """Test converting to macro."""
        config = RenameConfig(prefix="SM_")

        macro = template.to_macro(
            targets=["/Game/Meshes/Mesh1"],
            config=config,
        )

        assert macro is not None
        assert macro.name == "Batch Rename"
