"""Configuration management utilities"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

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
        
    def load_preset(self, name: str) -> Optional[Dict[str, Any]]:
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
            with open(preset_path, 'r', encoding='utf-8') as f:
                preset = json.load(f)
            logger.info(f"Loaded preset: {name}")
            return preset
        except Exception as e:
            logger.error(f"Failed to load preset '{name}': {e}")
            return None
    
    def save_preset(self, name: str, config: Dict[str, Any]) -> bool:
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
            with open(preset_path, 'w', encoding='utf-8') as f:
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
    
    def get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration.
        
        Returns:
            Default configuration dictionary
        """
        return {
            "txt2img": {
                "steps": 20,
                "sampler_name": "Euler a",
                "cfg_scale": 7.0,
                "width": 512,
                "height": 512,
                "negative_prompt": "blurry, bad quality, distorted"
            },
            "img2img": {
                "steps": 15,
                "sampler_name": "Euler a",
                "cfg_scale": 7.0,
                "denoising_strength": 0.3
            },
            "upscale": {
                "upscaler": "R-ESRGAN 4x+",
                "upscaling_resize": 2.0
            },
            "video": {
                "fps": 24,
                "codec": "libx264",
                "quality": "medium"
            },
            "api": {
                "base_url": "http://127.0.0.1:7862",
                "timeout": 300
            }
        }
    
    def resolve_config(self, preset_name: str = None, pack_overrides: Dict[str, Any] = None, 
                      runtime_params: Dict[str, Any] = None) -> Dict[str, Any]:
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
    
    def _merge_configs(self, base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
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
    
    def get_pack_overrides(self, pack_name: str) -> Dict[str, Any]:
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
            with open(overrides_file, 'r', encoding='utf-8') as f:
                all_overrides = json.load(f)
            
            return all_overrides.get(pack_name, {})
        except Exception as e:
            logger.error(f"Failed to load pack overrides: {e}")
            return {}
    
    def save_pack_overrides(self, pack_name: str, overrides: Dict[str, Any]) -> bool:
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
                with open(overrides_file, 'r', encoding='utf-8') as f:
                    all_overrides = json.load(f)
            
            # Update with new overrides
            all_overrides[pack_name] = overrides
            
            # Save back
            with open(overrides_file, 'w', encoding='utf-8') as f:
                json.dump(all_overrides, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved pack overrides for: {pack_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save pack overrides: {e}")
            return False
    
    def add_global_negative(self, negative_prompt: str) -> str:
        """
        Add global NSFW prevention to negative prompt.
        
        Args:
            negative_prompt: Existing negative prompt
            
        Returns:
            Enhanced negative prompt with safety additions
        """
        global_neg = ("nsfw, nude, naked, explicit, sexual content, adult content, "
                     "inappropriate, offensive, disturbing, violent, graphic")
        
        if negative_prompt:
            return f"{negative_prompt}, {global_neg}"
        return global_neg
