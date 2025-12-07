"""
Setup Environment Template for UE5 Macro Automation.

A pre-built macro template for setting up environment lighting, post-processing,
and atmospheric effects.

Example Usage:
    >>> from src.templates.setup_environment import SetupEnvironmentTemplate
    >>> template = SetupEnvironmentTemplate()
    >>> result = template.execute(preset="outdoor_sunny")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from src.core.macro_recorder import ActionType, Macro, RecordedAction
from src.macros.lighting_ops import (
    configure_post_process,
    setup_basic_lighting,
)
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
class EnvironmentPreset:
    """
    Preset configuration for environment setup.

    Attributes:
        name: Preset name
        description: Preset description
        lighting_type: Type of lighting (outdoor, indoor, studio)
        time_of_day: Time of day for outdoor lighting
        sun_intensity: Sun/main light intensity
        sun_color: Sun/main light color (RGB)
        sky_light_intensity: Sky light intensity
        fog_density: Fog density
        fog_height: Fog height falloff
        exposure: Exposure compensation
        bloom_intensity: Bloom intensity
        ambient_occlusion: Ambient occlusion intensity
    """
    name: str
    description: str = ""
    lighting_type: str = "outdoor"
    time_of_day: str = "noon"
    sun_intensity: float = 10.0
    sun_color: tuple[float, float, float] = (1.0, 1.0, 0.95)
    sky_light_intensity: float = 1.0
    fog_density: float = 0.02
    fog_height: float = 0.2
    exposure: float = 1.0
    bloom_intensity: float = 0.675
    ambient_occlusion: float = 0.5


PRESETS: dict[str, EnvironmentPreset] = {
    "outdoor_sunny": EnvironmentPreset(
        name="Outdoor Sunny",
        description="Bright outdoor environment with clear sky",
        lighting_type="outdoor",
        time_of_day="noon",
        sun_intensity=10.0,
        sun_color=(1.0, 1.0, 0.95),
        sky_light_intensity=1.0,
        fog_density=0.01,
        fog_height=0.1,
        exposure=1.0,
        bloom_intensity=0.5,
        ambient_occlusion=0.3,
    ),
    "outdoor_sunset": EnvironmentPreset(
        name="Outdoor Sunset",
        description="Warm sunset environment with orange tones",
        lighting_type="outdoor",
        time_of_day="sunset",
        sun_intensity=4.0,
        sun_color=(1.0, 0.6, 0.3),
        sky_light_intensity=0.5,
        fog_density=0.03,
        fog_height=0.3,
        exposure=1.2,
        bloom_intensity=0.8,
        ambient_occlusion=0.4,
    ),
    "outdoor_overcast": EnvironmentPreset(
        name="Outdoor Overcast",
        description="Cloudy outdoor environment with soft lighting",
        lighting_type="outdoor",
        time_of_day="noon",
        sun_intensity=3.0,
        sun_color=(0.9, 0.9, 1.0),
        sky_light_intensity=1.5,
        fog_density=0.05,
        fog_height=0.5,
        exposure=0.8,
        bloom_intensity=0.3,
        ambient_occlusion=0.5,
    ),
    "indoor_office": EnvironmentPreset(
        name="Indoor Office",
        description="Standard office interior lighting",
        lighting_type="indoor",
        time_of_day="noon",
        sun_intensity=5000.0,
        sun_color=(1.0, 0.98, 0.95),
        sky_light_intensity=0.3,
        fog_density=0.0,
        fog_height=0.0,
        exposure=1.0,
        bloom_intensity=0.2,
        ambient_occlusion=0.6,
    ),
    "indoor_dramatic": EnvironmentPreset(
        name="Indoor Dramatic",
        description="High contrast interior with dramatic shadows",
        lighting_type="indoor",
        time_of_day="noon",
        sun_intensity=8000.0,
        sun_color=(1.0, 0.95, 0.9),
        sky_light_intensity=0.1,
        fog_density=0.0,
        fog_height=0.0,
        exposure=1.2,
        bloom_intensity=0.4,
        ambient_occlusion=0.8,
    ),
    "studio_product": EnvironmentPreset(
        name="Studio Product",
        description="Clean studio lighting for product visualization",
        lighting_type="studio",
        time_of_day="noon",
        sun_intensity=5000.0,
        sun_color=(1.0, 1.0, 1.0),
        sky_light_intensity=0.5,
        fog_density=0.0,
        fog_height=0.0,
        exposure=1.0,
        bloom_intensity=0.1,
        ambient_occlusion=0.3,
    ),
    "night_moonlit": EnvironmentPreset(
        name="Night Moonlit",
        description="Nighttime environment with moonlight",
        lighting_type="outdoor",
        time_of_day="night",
        sun_intensity=0.1,
        sun_color=(0.5, 0.5, 0.7),
        sky_light_intensity=0.05,
        fog_density=0.08,
        fog_height=0.4,
        exposure=2.0,
        bloom_intensity=0.3,
        ambient_occlusion=0.7,
    ),
}


@dataclass
class EnvironmentResult:
    """
    Result of environment setup.

    Attributes:
        success: Whether setup was successful
        preset_used: Name of preset used
        lights_created: List of created light names
        post_process_configured: Whether post-process was configured
        fog_configured: Whether fog was configured
        total_time: Total execution time
    """
    success: bool
    preset_used: str = ""
    lights_created: list[str] = field(default_factory=list)
    post_process_configured: bool = False
    fog_configured: bool = False
    total_time: float = 0.0


class SetupEnvironmentTemplate:
    """
    Template for setting up environment lighting and effects.

    This template performs:
    1. Place directional/sun light
    2. Configure sky light
    3. Set up atmospheric fog
    4. Configure post-process volume
    5. Apply preset settings

    Example:
        >>> template = SetupEnvironmentTemplate()
        >>> result = template.execute(preset="outdoor_sunny")
        >>> print(f"Created {len(result.lights_created)} lights")
    """

    NAME = "Setup Environment"
    DESCRIPTION = "Set up environment lighting, fog, and post-processing"
    CATEGORY = "lighting"

    def __init__(self) -> None:
        """Initialize the template."""
        self._preset: EnvironmentPreset | None = None

    def execute(
        self,
        preset: str = "outdoor_sunny",
        **kwargs: Any
    ) -> EnvironmentResult:
        """
        Execute the environment setup template.

        Args:
            preset: Name of preset to use
            **kwargs: Override preset values

        Returns:
            EnvironmentResult with setup details
        """
        import time
        start_time = time.time()

        if preset in PRESETS:
            self._preset = PRESETS[preset]
        else:
            logger.warning(f"Unknown preset: {preset}, using outdoor_sunny")
            self._preset = PRESETS["outdoor_sunny"]

        for key, value in kwargs.items():
            if hasattr(self._preset, key):
                setattr(self._preset, key, value)

        result = EnvironmentResult(success=True, preset_used=preset)

        logger.info(f"Setting up environment with preset: {preset}")

        with ProgressTracker("Setting Up Environment", total=4) as tracker:
            tracker.update(0, "Creating lights...")
            lights = self._create_lights()
            result.lights_created = lights

            tracker.update(1, "Configuring fog...")
            result.fog_configured = self._configure_fog()

            tracker.update(1, "Setting up post-process...")
            result.post_process_configured = self._configure_post_process()

            tracker.update(1, "Finalizing...")
            self._finalize_setup()

            tracker.update(1, "Complete")

        result.total_time = time.time() - start_time

        logger.info(
            f"Environment setup complete: {len(result.lights_created)} lights created"
        )

        return result

    def _create_lights(self) -> list[str]:
        """Create lights based on preset."""
        if not self._preset:
            return []

        created = []

        lighting_result = setup_basic_lighting(
            lighting_type=self._preset.lighting_type,
            time_of_day=self._preset.time_of_day
        )

        if lighting_result.success:
            created.extend(lighting_result.details.get("lights_created", []))

        return created

    def _configure_fog(self) -> bool:
        """Configure atmospheric fog."""
        if not self._preset:
            return False

        if self._preset.fog_density <= 0:
            return True

        if not UNREAL_AVAILABLE:
            logger.info(f"[MOCK] Configure fog: density={self._preset.fog_density}")
            return True

        import unreal  # noqa: F401

        try:
            fog = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.ExponentialHeightFog,
                unreal.Vector(0, 0, 0)
            )
            fog.set_actor_label("EnvironmentFog")

            fog_component = fog.get_component_by_class(
                unreal.ExponentialHeightFogComponent
            )
            if fog_component:
                fog_component.set_fog_density(self._preset.fog_density)
                fog_component.set_fog_height_falloff(self._preset.fog_height)

            return True

        except Exception as e:
            logger.error(f"Fog configuration failed: {e}")
            return False

    def _configure_post_process(self) -> bool:
        """Configure post-process volume."""
        if not self._preset:
            return False

        result = configure_post_process(
            exposure=self._preset.exposure,
            bloom_intensity=self._preset.bloom_intensity,
            ambient_occlusion=self._preset.ambient_occlusion,
            auto_exposure=True
        )

        return result.success

    def _finalize_setup(self) -> None:
        """Finalize the environment setup."""
        logger.info("Finalizing environment setup")

    def to_macro(self) -> Macro:
        """Convert the template to a Macro object."""
        actions = [
            RecordedAction(
                action_type=ActionType.CUSTOM,
                parameters={
                    "template": "SetupEnvironmentTemplate",
                    "config": {"preset": self._preset.name if self._preset else "outdoor_sunny"}
                },
                description="Execute Setup Environment template"
            )
        ]

        return Macro(
            name=self.NAME,
            actions=actions,
            description=self.DESCRIPTION,
            metadata={"category": self.CATEGORY, "template": True}
        )

    @classmethod
    def get_available_presets(cls) -> list[str]:
        """Get list of available preset names."""
        return list(PRESETS.keys())

    @classmethod
    def get_preset_info(cls, preset_name: str) -> dict[str, Any] | None:
        """Get information about a preset."""
        if preset_name not in PRESETS:
            return None

        preset = PRESETS[preset_name]
        return {
            "name": preset.name,
            "description": preset.description,
            "lighting_type": preset.lighting_type,
            "time_of_day": preset.time_of_day,
        }

    @classmethod
    def get_default_config(cls) -> dict[str, Any]:
        """Get the default configuration for this template."""
        return {
            "preset": "outdoor_sunny",
        }
