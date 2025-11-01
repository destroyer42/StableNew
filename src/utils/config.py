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
                "base_url": "http://127.0.0.1:7860",
                "timeout": 300
            }
        }
