"""
Tests for the setup_environment template module.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.templates.setup_environment import (
    EnvironmentPreset,
    EnvironmentResult,
    SetupEnvironmentTemplate,
)


class TestEnvironmentPreset:
    """Tests for the EnvironmentPreset class."""

    def test_preset_creation(self):
        """Test creating an environment preset."""
        preset = EnvironmentPreset(
            name="test_preset",
            sun_intensity=5.0,
            sun_color=(1.0, 0.9, 0.8),
            sky_intensity=1.0,
            fog_density=0.02,
        )

        assert preset.name == "test_preset"
        assert preset.sun_intensity == 5.0
        assert preset.fog_density == 0.02


class TestSetupEnvironmentTemplate:
    """Tests for the SetupEnvironmentTemplate class."""

    @pytest.fixture
    def template(self):
        """Create a SetupEnvironmentTemplate instance."""
        return SetupEnvironmentTemplate()

    def test_template_creation(self, template):
        """Test creating a template."""
        assert template is not None
        assert template.name == "Setup Environment"

    def test_get_available_presets(self, template):
        """Test getting available presets."""
        presets = template.get_available_presets()

        assert len(presets) > 0
        assert "outdoor_sunny" in presets
        assert "outdoor_sunset" in presets
        assert "indoor_office" in presets

    def test_get_preset_info(self, template):
        """Test getting preset information."""
        info = template.get_preset_info("outdoor_sunny")

        assert info is not None
        assert "sun_intensity" in info or "description" in info

    def test_get_default_config(self, template):
        """Test getting default configuration."""
        config = template.get_default_config()

        assert isinstance(config, EnvironmentPreset)

    @patch("src.templates.setup_environment.unreal")
    def test_execute_with_preset(self, mock_unreal, template):
        """Test executing with a preset."""
        mock_unreal.EditorLevelLibrary.spawn_actor_from_class.return_value = MagicMock()

        result = template.execute(preset_name="outdoor_sunny")

        assert isinstance(result, EnvironmentResult)
        assert result.success

    @patch("src.templates.setup_environment.unreal")
    def test_execute_with_custom_preset(self, mock_unreal, template):
        """Test executing with a custom preset."""
        mock_unreal.EditorLevelLibrary.spawn_actor_from_class.return_value = MagicMock()

        custom_preset = EnvironmentPreset(
            name="custom",
            sun_intensity=10.0,
            sun_color=(1.0, 1.0, 1.0),
            sky_intensity=2.0,
        )

        result = template.execute(preset=custom_preset)

        assert isinstance(result, EnvironmentResult)
        assert result.success

    def test_to_macro(self, template):
        """Test converting to macro."""
        macro = template.to_macro(preset_name="outdoor_sunny")

        assert macro is not None
        assert macro.name == "Setup Environment"
