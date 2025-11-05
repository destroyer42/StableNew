"""Configuration management utilities"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration and presets"""

    def __init__(self, presets_dir: str = "presets"):
        """
        Initialize configuration manager.

        Args:
            presets_dir: Directory containing preset files
        """
        self.presets_dir = Path(presets_dir)
        self.presets_dir.mkdir(exist_ok=True)

    def load_preset(self, name: str) -> dict[str, Any] | None:
        """
        Load a preset configuration.

        Args:
            name: Name of the preset

        Returns:
            Preset configuration dictionary
        """
        preset_path = self.presets_dir / f"{name}.json"
        if not preset_path.exists():
            logger.warning(f"Preset '{name}' not found at {preset_path}")
            return None

        try:
            with open(preset_path, encoding="utf-8") as f:
                preset = json.load(f)
            logger.info(f"Loaded preset: {name}")
            return preset
        except Exception as e:
            logger.error(f"Failed to load preset '{name}': {e}")
            return None

    def save_preset(self, name: str, config: dict[str, Any]) -> bool:
        """
        Save a preset configuration.

        Args:
            name: Name of the preset
            config: Configuration dictionary

        Returns:
            True if saved successfully
        """
        preset_path = self.presets_dir / f"{name}.json"
        try:
            with open(preset_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved preset: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save preset '{name}': {e}")
            return False

    def list_presets(self) -> list:
        """
        List all available presets.

        Returns:
            List of preset names
        """
        presets = [p.stem for p in self.presets_dir.glob("*.json")]
        logger.info(f"Found {len(presets)} presets")
        return sorted(presets)

    def get_default_config(self) -> dict[str, Any]:
        """
        Get the default configuration for all pipeline stages.

        IMPORTANT: When adding new parameters to this configuration,
        run the validation test to ensure proper parameter pass-through:

        python tests/test_config_passthrough.py

        See CONFIGURATION_TESTING_GUIDE.md for detailed maintenance instructions.

        Returns:
            Dictionary containing default configuration for all stages
        """
        """
        Get default configuration.
        
        Returns:
            Default configuration dictionary
        """
        return {
            "txt2img": {
                "steps": 20,
                "sampler_name": "Euler a",
                "scheduler": "Normal",
                "cfg_scale": 7.0,
                "width": 512,
                "height": 512,
                "negative_prompt": "blurry, bad quality, distorted",
                "seed": -1,  # -1 for random
                "seed_resize_from_h": -1,
                "seed_resize_from_w": -1,
                "enable_hr": False,  # High-res fix / hires.fix
                "hr_scale": 2.0,  # Hires.fix upscale factor
                "hr_upscaler": "Latent",  # Hires.fix upscaler
                "hr_second_pass_steps": 0,  # 0 = use same as steps
                "hr_resize_x": 0,  # 0 = automatic based on hr_scale
                "hr_resize_y": 0,  # 0 = automatic based on hr_scale
                "denoising_strength": 0.7,  # For hires.fix second pass
                "clip_skip": 2,  # CLIP layers to skip
                "model": "",  # SD model checkpoint (empty = use current)
                "vae": "",  # VAE model (empty = use model default)
                "styles": [],  # Style names to apply
            },
            "img2img": {
                "steps": 15,
                "sampler_name": "Euler a",
                "scheduler": "Normal",
                "cfg_scale": 7.0,
                "denoising_strength": 0.3,
                "seed": -1,  # -1 for random
                "clip_skip": 2,
                "model": "",  # SD model checkpoint (empty = use current)
                "vae": "",  # VAE model (empty = use model default)
            },
            "upscale": {
                "upscaler": "R-ESRGAN 4x+",
                "upscaling_resize": 2.0,
                "mode": "extras",  # "extras" (direct) or "img2img" (more control)
                "denoising_strength": 0.35,  # For img2img-based upscaling
                "gfpgan_visibility": 0.0,  # Face restoration strength
                "codeformer_visibility": 0.0,  # Face restoration alternative
                "codeformer_weight": 0.5,  # CodeFormer fidelity
            },
            "video": {"fps": 24, "codec": "libx264", "quality": "medium"},
            "api": {"base_url": "http://127.0.0.1:7860", "timeout": 300},
        }

    def resolve_config(
        self,
        preset_name: str = None,
        pack_overrides: dict[str, Any] = None,
        runtime_params: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """
        Resolve configuration with hierarchy: Default → Preset → Pack overrides → Runtime params.

        Args:
            preset_name: Name of preset to load
            pack_overrides: Pack-specific configuration overrides
            runtime_params: Runtime parameter overrides

        Returns:
            Resolved configuration dictionary
        """
        # Start with default config
        config = self.get_default_config()

        # Apply preset overrides
        if preset_name:
            preset_config = self.load_preset(preset_name)
            if preset_config:
                config = self._merge_configs(config, preset_config)

        # Apply pack-specific overrides
        if pack_overrides:
            config = self._merge_configs(config, pack_overrides)

        # Apply runtime parameters
        if runtime_params:
            config = self._merge_configs(config, runtime_params)

        return config

    def _merge_configs(
        self, base_config: dict[str, Any], override_config: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Deep merge two configuration dictionaries.

        Args:
            base_config: Base configuration
            override_config: Override configuration

        Returns:
            Merged configuration
        """
        import copy

        merged = copy.deepcopy(base_config)

        for key, value in override_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value

        return merged

    def get_pack_overrides(self, pack_name: str) -> dict[str, Any]:
        """
        Get pack-specific configuration overrides.

        Args:
            pack_name: Name of the prompt pack

        Returns:
            Pack override configuration
        """
        overrides_file = self.presets_dir / "pack_overrides.json"
        if not overrides_file.exists():
            return {}

        try:
            with open(overrides_file, encoding="utf-8") as f:
                all_overrides = json.load(f)

            return all_overrides.get(pack_name, {})
        except Exception as e:
            logger.error(f"Failed to load pack overrides: {e}")
            return {}

    def save_pack_overrides(self, pack_name: str, overrides: dict[str, Any]) -> bool:
        """
        Save pack-specific configuration overrides.

        Args:
            pack_name: Name of the prompt pack
            overrides: Override configuration

        Returns:
            True if saved successfully
        """
        overrides_file = self.presets_dir / "pack_overrides.json"

        try:
            # Load existing overrides
            all_overrides = {}
            if overrides_file.exists():
                with open(overrides_file, encoding="utf-8") as f:
                    all_overrides = json.load(f)

            # Update with new overrides
            all_overrides[pack_name] = overrides

            # Save back
            with open(overrides_file, "w", encoding="utf-8") as f:
                json.dump(all_overrides, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved pack overrides for: {pack_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save pack overrides: {e}")
            return False

    def get_pack_config(self, pack_name: str) -> dict[str, Any]:
        """
        Get individual pack configuration from its .json file.

        Args:
            pack_name: Name of the prompt pack (e.g., "heroes.txt")

        Returns:
            Pack configuration or empty dict if not found
        """
        from pathlib import Path

        # Convert pack_name to config filename (heroes.txt -> heroes.json)
        pack_stem = Path(pack_name).stem
        config_path = Path("packs") / f"{pack_stem}.json"

        if not config_path.exists():
            return {}

        try:
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
            logger.debug(f"Loaded pack config: {pack_name}")
            return config
        except Exception as e:
            logger.error(f"Failed to load pack config '{pack_name}': {e}")
            return {}

    def save_pack_config(self, pack_name: str, config: dict[str, Any]) -> bool:
        """
        Save individual pack configuration to its .json file.

        Args:
            pack_name: Name of the prompt pack (e.g., "heroes.txt")
            config: Configuration to save

        Returns:
            True if successful
        """
        from pathlib import Path

        try:
            # Convert pack_name to config filename (heroes.txt -> heroes.json)
            pack_stem = Path(pack_name).stem
            config_path = Path("packs") / f"{pack_stem}.json"

            # Ensure packs directory exists
            config_path.parent.mkdir(exist_ok=True)

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved pack config: {pack_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save pack config '{pack_name}': {e}")
            return False

    def ensure_pack_config(self, pack_name: str, preset_name: str = "default") -> dict[str, Any]:
        """
        Ensure pack has a configuration file, creating one with preset defaults if needed.

        Args:
            pack_name: Name of the prompt pack
            preset_name: Preset to use as base for new pack config

        Returns:
            Pack configuration
        """
        config = self.get_pack_config(pack_name)

        if not config:
            # Create pack config from preset defaults
            preset_config = self.load_preset(preset_name)
            if preset_config:
                self.save_pack_config(pack_name, preset_config)
                logger.info(
                    f"Created pack config for '{pack_name}' based on preset '{preset_name}'"
                )
                return preset_config
            else:
                logger.warning(f"Failed to create pack config - preset '{preset_name}' not found")

        return config

    def add_global_negative(self, negative_prompt: str) -> str:
        """
        Add global NSFW prevention to negative prompt.

        Args:
            negative_prompt: Existing negative prompt

        Returns:
            Enhanced negative prompt with safety additions
        """
        global_neg = (
            "nsfw, nude, naked, explicit, sexual content, adult content, "
            "inappropriate, offensive, disturbing, violent, graphic"
        )

        if negative_prompt:
            return f"{negative_prompt}, {global_neg}"
        return global_neg
