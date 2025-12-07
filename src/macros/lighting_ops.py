"""
Lighting Operations Macros for UE5 Macro Automation.

Provides functions for building lighting, configuring quality settings,
and setting up basic lighting scenarios.

Example Usage:
    >>> build_lighting(quality="production")
    >>> set_lighting_quality("high")
    >>> setup_basic_lighting("/Game/Levels/Main")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

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


class LightingQuality(Enum):
    """Lighting build quality levels."""
    PREVIEW = auto()
    MEDIUM = auto()
    HIGH = auto()
    PRODUCTION = auto()


@dataclass
class LightingResult:
    """
    Result of a lighting operation.

    Attributes:
        success: Whether operation was successful
        build_time: Time taken for lighting build
        error: Error message if failed
        details: Additional operation details
    """
    success: bool
    build_time: float = 0.0
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class LightSetup:
    """
    Configuration for a light.

    Attributes:
        light_type: Type of light (point, spot, directional, rect, sky)
        location: World location
        rotation: Rotation (pitch, yaw, roll)
        intensity: Light intensity
        color: Light color (RGB)
        attenuation_radius: Attenuation radius for point/spot lights
        source_radius: Source radius for soft shadows
        cast_shadows: Whether to cast shadows
    """
    light_type: str = "point"
    location: tuple[float, float, float] = (0, 0, 300)
    rotation: tuple[float, float, float] = (0, 0, 0)
    intensity: float = 5000.0
    color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    attenuation_radius: float = 1000.0
    source_radius: float = 0.0
    cast_shadows: bool = True


@profile_function
def build_lighting(
    quality: str = "production",
    maps: list[str] | None = None
) -> LightingResult:
    """
    Build lighting for the current level or specified maps.

    Args:
        quality: Build quality ("preview", "medium", "high", "production")
        maps: List of map paths to build (if None, builds current level)

    Returns:
        LightingResult with build details

    Example:
        >>> result = build_lighting(quality="production")
        >>> print(f"Build completed in {result.build_time:.2f}s")
    """
    quality_map = {
        "preview": LightingQuality.PREVIEW,
        "medium": LightingQuality.MEDIUM,
        "high": LightingQuality.HIGH,
        "production": LightingQuality.PRODUCTION,
    }

    quality_enum = quality_map.get(quality.lower(), LightingQuality.PRODUCTION)

    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Build lighting: quality={quality}")
        return LightingResult(
            success=True,
            build_time=0.0,
            details={"quality": quality}
        )

    import time

    import unreal  # noqa: F401

    try:
        start_time = time.time()

        quality_settings = {
            LightingQuality.PREVIEW: unreal.LightingBuildQuality.QUALITY_PREVIEW,
            LightingQuality.MEDIUM: unreal.LightingBuildQuality.QUALITY_MEDIUM,
            LightingQuality.HIGH: unreal.LightingBuildQuality.QUALITY_HIGH,
            LightingQuality.PRODUCTION: unreal.LightingBuildQuality.QUALITY_PRODUCTION,
        }

        quality_settings.get(
            quality_enum,
            unreal.LightingBuildQuality.QUALITY_PRODUCTION
        )

        if maps:
            for map_path in maps:
                unreal.EditorLoadingAndSavingUtils.load_map(map_path)
                unreal.EditorLevelLibrary.build_lighting_only()
        else:
            unreal.EditorLevelLibrary.build_lighting_only()

        build_time = time.time() - start_time

        logger.info(f"Lighting build completed in {build_time:.2f}s")
        return LightingResult(
            success=True,
            build_time=build_time,
            details={"quality": quality}
        )

    except Exception as e:
        logger.error(f"Lighting build failed: {e}")
        return LightingResult(
            success=False,
            error=str(e)
        )


@profile_function
def set_lighting_quality(quality: str = "high") -> LightingResult:
    """
    Set the lighting quality settings for the project.

    Args:
        quality: Quality level ("low", "medium", "high", "epic", "cinematic")

    Returns:
        LightingResult with operation details

    Example:
        >>> result = set_lighting_quality("epic")
    """
    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Set lighting quality: {quality}")
        return LightingResult(
            success=True,
            details={"quality": quality}
        )

    import unreal  # noqa: F401

    try:
        quality_settings = {
            "low": 0,
            "medium": 1,
            "high": 2,
            "epic": 3,
            "cinematic": 4,
        }

        quality_level = quality_settings.get(quality.lower(), 2)

        unreal.GameUserSettings.get_game_user_settings().set_shadow_quality(quality_level)
        unreal.GameUserSettings.get_game_user_settings().set_global_illumination_quality(quality_level)

        logger.info(f"Set lighting quality to: {quality}")
        return LightingResult(
            success=True,
            details={"quality": quality, "level": quality_level}
        )

    except Exception as e:
        logger.error(f"Failed to set lighting quality: {e}")
        return LightingResult(
            success=False,
            error=str(e)
        )


@profile_function
def setup_basic_lighting(
    lighting_type: str = "outdoor",
    time_of_day: str = "noon"
) -> LightingResult:
    """
    Set up basic lighting for a level.

    Args:
        lighting_type: Type of lighting setup ("outdoor", "indoor", "studio")
        time_of_day: Time of day for outdoor ("dawn", "noon", "sunset", "night")

    Returns:
        LightingResult with created light actors

    Example:
        >>> result = setup_basic_lighting("outdoor", "sunset")
    """
    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Setup basic lighting: {lighting_type}, {time_of_day}")
        return LightingResult(
            success=True,
            details={
                "lighting_type": lighting_type,
                "time_of_day": time_of_day,
                "lights_created": ["DirectionalLight", "SkyLight", "SkyAtmosphere"]
            }
        )

    import unreal  # noqa: F401

    try:
        created_lights = []

        if lighting_type == "outdoor":
            sun_settings = _get_sun_settings(time_of_day)

            directional_light = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.DirectionalLight,
                unreal.Vector(0, 0, 0),
                unreal.Rotator(sun_settings["pitch"], sun_settings["yaw"], 0)
            )
            directional_light.set_actor_label("Sun")

            light_component = directional_light.get_component_by_class(
                unreal.DirectionalLightComponent
            )
            if light_component:
                light_component.set_intensity(sun_settings["intensity"])
                light_component.set_light_color(
                    unreal.LinearColor(
                        sun_settings["color"][0],
                        sun_settings["color"][1],
                        sun_settings["color"][2],
                        1.0
                    )
                )

            created_lights.append("DirectionalLight (Sun)")

            sky_light = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.SkyLight,
                unreal.Vector(0, 0, 500)
            )
            sky_light.set_actor_label("SkyLight")
            created_lights.append("SkyLight")

            sky_atmosphere = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.SkyAtmosphere,
                unreal.Vector(0, 0, 0)
            )
            sky_atmosphere.set_actor_label("SkyAtmosphere")
            created_lights.append("SkyAtmosphere")

            fog = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.ExponentialHeightFog,
                unreal.Vector(0, 0, 0)
            )
            fog.set_actor_label("HeightFog")
            created_lights.append("ExponentialHeightFog")

        elif lighting_type == "indoor":
            point_light = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.PointLight,
                unreal.Vector(0, 0, 300)
            )
            point_light.set_actor_label("MainLight")

            light_component = point_light.get_component_by_class(
                unreal.PointLightComponent
            )
            if light_component:
                light_component.set_intensity(5000)
                light_component.set_attenuation_radius(1000)

            created_lights.append("PointLight (MainLight)")

            fill_light = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.PointLight,
                unreal.Vector(500, 500, 200)
            )
            fill_light.set_actor_label("FillLight")

            fill_component = fill_light.get_component_by_class(
                unreal.PointLightComponent
            )
            if fill_component:
                fill_component.set_intensity(2000)
                fill_component.set_attenuation_radius(800)

            created_lights.append("PointLight (FillLight)")

        elif lighting_type == "studio":
            key_light = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.RectLight,
                unreal.Vector(-500, -500, 400),
                unreal.Rotator(-45, 45, 0)
            )
            key_light.set_actor_label("KeyLight")
            created_lights.append("RectLight (KeyLight)")

            fill_light = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.RectLight,
                unreal.Vector(500, -300, 300),
                unreal.Rotator(-30, -45, 0)
            )
            fill_light.set_actor_label("FillLight")
            created_lights.append("RectLight (FillLight)")

            rim_light = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.SpotLight,
                unreal.Vector(0, 500, 500),
                unreal.Rotator(-45, 180, 0)
            )
            rim_light.set_actor_label("RimLight")
            created_lights.append("SpotLight (RimLight)")

        logger.info(f"Created {len(created_lights)} lights for {lighting_type} setup")
        return LightingResult(
            success=True,
            details={
                "lighting_type": lighting_type,
                "time_of_day": time_of_day,
                "lights_created": created_lights
            }
        )

    except Exception as e:
        logger.error(f"Lighting setup failed: {e}")
        return LightingResult(
            success=False,
            error=str(e)
        )


def _get_sun_settings(time_of_day: str) -> dict[str, Any]:
    """Get sun settings for a time of day."""
    settings = {
        "dawn": {
            "pitch": -10,
            "yaw": 90,
            "intensity": 3.0,
            "color": (1.0, 0.8, 0.6),
        },
        "noon": {
            "pitch": -75,
            "yaw": 0,
            "intensity": 10.0,
            "color": (1.0, 1.0, 0.95),
        },
        "sunset": {
            "pitch": -15,
            "yaw": 270,
            "intensity": 4.0,
            "color": (1.0, 0.6, 0.3),
        },
        "night": {
            "pitch": -30,
            "yaw": 180,
            "intensity": 0.1,
            "color": (0.5, 0.5, 0.7),
        },
    }

    return settings.get(time_of_day.lower(), settings["noon"])


@profile_function
def spawn_light(
    setup: LightSetup,
    name: str | None = None
) -> Any | None:
    """
    Spawn a light actor with the given setup.

    Args:
        setup: Light configuration
        name: Optional name for the light

    Returns:
        The spawned light actor or None

    Example:
        >>> setup = LightSetup(
        ...     light_type="spot",
        ...     location=(0, 0, 500),
        ...     intensity=10000,
        ...     color=(1.0, 0.9, 0.8)
        ... )
        >>> light = spawn_light(setup, "MainSpotlight")
    """
    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Spawn light: {setup.light_type} at {setup.location}")
        return None

    import unreal  # noqa: F401

    try:
        light_classes = {
            "point": unreal.PointLight,
            "spot": unreal.SpotLight,
            "directional": unreal.DirectionalLight,
            "rect": unreal.RectLight,
            "sky": unreal.SkyLight,
        }

        light_class = light_classes.get(setup.light_type.lower())
        if not light_class:
            logger.error(f"Unknown light type: {setup.light_type}")
            return None

        light = unreal.EditorLevelLibrary.spawn_actor_from_class(
            light_class,
            unreal.Vector(*setup.location),
            unreal.Rotator(*setup.rotation)
        )

        if name:
            light.set_actor_label(name)

        component_classes = {
            "point": unreal.PointLightComponent,
            "spot": unreal.SpotLightComponent,
            "directional": unreal.DirectionalLightComponent,
            "rect": unreal.RectLightComponent,
            "sky": unreal.SkyLightComponent,
        }

        component_class = component_classes.get(setup.light_type.lower())
        if component_class:
            light_component = light.get_component_by_class(component_class)
            if light_component:
                light_component.set_intensity(setup.intensity)
                light_component.set_light_color(
                    unreal.LinearColor(
                        setup.color[0],
                        setup.color[1],
                        setup.color[2],
                        1.0
                    )
                )

                if hasattr(light_component, "set_attenuation_radius"):
                    light_component.set_attenuation_radius(setup.attenuation_radius)

                if hasattr(light_component, "set_source_radius"):
                    light_component.set_source_radius(setup.source_radius)

                light_component.set_cast_shadows(setup.cast_shadows)

        logger.info(f"Spawned {setup.light_type} light at {setup.location}")
        return light

    except Exception as e:
        logger.error(f"Failed to spawn light: {e}")
        return None


def get_all_lights() -> list[Any]:
    """
    Get all light actors in the current level.

    Returns:
        List of light actors

    Example:
        >>> lights = get_all_lights()
        >>> for light in lights:
        ...     print(light.get_name())
    """
    if not UNREAL_AVAILABLE:
        return []

    import unreal  # noqa: F401

    light_classes = [
        "PointLight",
        "SpotLight",
        "DirectionalLight",
        "RectLight",
        "SkyLight",
    ]

    all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
    lights = []

    for actor in all_actors:
        if actor.get_class().get_name() in light_classes:
            lights.append(actor)

    return lights


def configure_post_process(
    exposure: float = 1.0,
    bloom_intensity: float = 0.675,
    ambient_occlusion: float = 0.5,
    auto_exposure: bool = True
) -> LightingResult:
    """
    Configure post-process settings for the level.

    Args:
        exposure: Exposure compensation
        bloom_intensity: Bloom intensity
        ambient_occlusion: Ambient occlusion intensity
        auto_exposure: Enable auto exposure

    Returns:
        LightingResult with operation details

    Example:
        >>> result = configure_post_process(
        ...     exposure=1.2,
        ...     bloom_intensity=0.5,
        ...     auto_exposure=True
        ... )
    """
    if not UNREAL_AVAILABLE:
        logger.info(f"[MOCK] Configure post-process: exposure={exposure}")
        return LightingResult(
            success=True,
            details={
                "exposure": exposure,
                "bloom_intensity": bloom_intensity,
                "ambient_occlusion": ambient_occlusion,
                "auto_exposure": auto_exposure
            }
        )

    import unreal  # noqa: F401

    try:
        pp_volume = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.PostProcessVolume,
            unreal.Vector(0, 0, 0)
        )
        pp_volume.set_actor_label("PostProcessVolume")

        pp_volume.set_editor_property("unbound", True)

        settings = pp_volume.get_editor_property("settings")

        settings.set_editor_property("bloom_intensity", bloom_intensity)
        settings.set_editor_property("auto_exposure_bias", exposure)
        settings.set_editor_property("ambient_occlusion_intensity", ambient_occlusion)

        if auto_exposure:
            settings.set_editor_property(
                "auto_exposure_method",
                unreal.AutoExposureMethod.AEM_HISTOGRAM
            )
        else:
            settings.set_editor_property(
                "auto_exposure_method",
                unreal.AutoExposureMethod.AEM_MANUAL
            )

        logger.info("Configured post-process settings")
        return LightingResult(
            success=True,
            details={
                "exposure": exposure,
                "bloom_intensity": bloom_intensity,
                "ambient_occlusion": ambient_occlusion,
                "auto_exposure": auto_exposure
            }
        )

    except Exception as e:
        logger.error(f"Post-process configuration failed: {e}")
        return LightingResult(
            success=False,
            error=str(e)
        )
