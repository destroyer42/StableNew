"""Pipeline execution module"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..api import SDWebUIClient
from ..utils import (
    save_image_from_base64,
    load_image_to_base64,
    StructuredLogger,
    ConfigManager
)

logger = logging.getLogger(__name__)


class Pipeline:
    """Main pipeline orchestrator for txt2img → img2img → upscale → video"""
    
    def __init__(self, client: SDWebUIClient, structured_logger: StructuredLogger):
        """
        Initialize pipeline.
        
        Args:
            client: SD WebUI API client
            structured_logger: Structured logger instance
        """
        self.client = client
        self.logger = structured_logger
        self.config_manager = ConfigManager()  # For global negative prompt handling
        
    def run_txt2img(self, prompt: str, config: Dict[str, Any], 
                    run_dir: Path, batch_size: int = 1) -> List[Dict[str, Any]]:
        """
        Run txt2img generation.
        
        Args:
            prompt: Text prompt
            config: Configuration for txt2img
            run_dir: Run directory
            batch_size: Number of images to generate
            
        Returns:
            List of generated image metadata
        """
        logger.info(f"Starting txt2img with prompt: {prompt[:50]}...")
        
        # Apply global NSFW prevention to negative prompt
        base_negative = config.get("negative_prompt", "")
        enhanced_negative = self.config_manager.add_global_negative(base_negative)
        logger.info(f"🛡️ Applied global NSFW prevention - Original: '{base_negative}' → Enhanced: '{enhanced_negative[:100]}...'")
        
        payload = {
            "prompt": prompt,
            "negative_prompt": enhanced_negative,
            "steps": config.get("steps", 20),
            "sampler_name": config.get("sampler_name", "Euler a"),
            "cfg_scale": config.get("cfg_scale", 7.0),
            "width": config.get("width", 512),
            "height": config.get("height", 512),
            "batch_size": batch_size,
            "n_iter": 1
        }
        
        response = self.client.txt2img(payload)
        if not response or 'images' not in response:
            logger.error("txt2img failed")
            return []
        
        results = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for idx, img_base64 in enumerate(response['images']):
            image_name = f"txt2img_{timestamp}_{idx:03d}"
            image_path = run_dir / "txt2img" / f"{image_name}.png"
            
            if save_image_from_base64(img_base64, image_path):
                metadata = {
                    "name": image_name,
                    "stage": "txt2img",
                    "timestamp": timestamp,
                    "prompt": prompt,
                    "config": payload,
                    "path": str(image_path)
                }
                
                self.logger.save_manifest(run_dir, image_name, metadata)
                results.append(metadata)
        
        logger.info(f"txt2img completed: {len(results)} images generated")
        return results
    
    def run_img2img(self, input_image_path: Path, prompt: str, 
                    config: Dict[str, Any], run_dir: Path) -> Optional[Dict[str, Any]]:
        """
        Run img2img cleanup/refinement.
        
        Args:
            input_image_path: Path to input image
            prompt: Text prompt
            config: Configuration for img2img
            run_dir: Run directory
            
        Returns:
            Generated image metadata
        """
        logger.info(f"Starting img2img cleanup for: {input_image_path.name}")
        
        # Load input image
        input_base64 = load_image_to_base64(input_image_path)
        if not input_base64:
            logger.error("Failed to load input image for img2img")
            return None
        
        # Apply global NSFW prevention to negative prompt
        base_negative = config.get("negative_prompt", "")
        enhanced_negative = self.config_manager.add_global_negative(base_negative)
        logger.info(f"🛡️ Applied global NSFW prevention (img2img) - Enhanced: '{enhanced_negative[:100]}...'")
        
        payload = {
            "init_images": [input_base64],
            "prompt": prompt,
            "negative_prompt": enhanced_negative,
            "steps": config.get("steps", 15),
            "sampler_name": config.get("sampler_name", "Euler a"),
            "cfg_scale": config.get("cfg_scale", 7.0),
            "denoising_strength": config.get("denoising_strength", 0.3),
            "width": config.get("width", 512),
            "height": config.get("height", 512)
        }
        
        response = self.client.img2img(payload)
        if not response or 'images' not in response:
            logger.error("img2img failed")
            return None
        
        # Save cleaned image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_name = f"img2img_{timestamp}"
        image_path = run_dir / "img2img" / f"{image_name}.png"
        
        if save_image_from_base64(response['images'][0], image_path):
            metadata = {
                "name": image_name,
                "stage": "img2img",
                "timestamp": timestamp,
                "prompt": prompt,
                "input_image": str(input_image_path),
                "config": payload,
                "path": str(image_path)
            }
            
            self.logger.save_manifest(run_dir, image_name, metadata)
            logger.info(f"img2img completed: {image_name}")
            return metadata
        
        return None
    

    
    def run_upscale(self, input_image_path: Path, config: Dict[str, Any], 
                    run_dir: Path) -> Optional[Dict[str, Any]]:
        """
        Run upscaling.
        
        Args:
            input_image_path: Path to input image
            config: Configuration for upscaling
            run_dir: Run directory
            
        Returns:
            Upscaled image metadata
        """
        logger.info(f"Starting upscale for: {input_image_path.name}")
        
        init_image = load_image_to_base64(input_image_path)
        if not init_image:
            logger.error("Failed to load input image")
            return None
        
        response = self.client.upscale_image(
            init_image,
            upscaler=config.get("upscaler", "R-ESRGAN 4x+"),
            upscaling_resize=config.get("upscaling_resize", 2.0),
            gfpgan_visibility=config.get("gfpgan_visibility", 0.0),
            codeformer_visibility=config.get("codeformer_visibility", 0.0),
            codeformer_weight=config.get("codeformer_weight", 0.5)
        )
        
        if not response or 'image' not in response:
            logger.error("Upscale failed")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_name = f"upscaled_{input_image_path.stem}_{timestamp}"
        image_path = run_dir / "upscaled" / f"{image_name}.png"
        
        if save_image_from_base64(response['image'], image_path):
            metadata = {
                "name": image_name,
                "stage": "upscale",
                "timestamp": timestamp,
                "input_image": str(input_image_path),
                "config": config,
                "path": str(image_path)
            }
            
            self.logger.save_manifest(run_dir, image_name, metadata)
            logger.info("Upscale completed successfully")
            return metadata
        
        return None
    
    def run_full_pipeline(self, prompt: str, config: Dict[str, Any], 
                         run_name: Optional[str] = None,
                         batch_size: int = 1) -> Dict[str, Any]:
        """
        Run complete pipeline: txt2img → img2img → upscale.
        
        Args:
            prompt: Text prompt
            config: Full pipeline configuration
            run_name: Optional run name
            batch_size: Number of images to generate
            
        Returns:
            Pipeline results summary
        """
        logger.info("=" * 60)
        logger.info("Starting full pipeline execution")
        logger.info("=" * 60)
        
        # Create run directory
        run_dir = self.logger.create_run_directory(run_name)
        
        results = {
            "run_dir": str(run_dir),
            "prompt": prompt,
            "txt2img": [],
            "img2img": [],
            "upscaled": [],
            "summary": []
        }
        
        # Step 1: txt2img
        txt2img_results = self.run_txt2img(
            prompt,
            config.get("txt2img", {}),
            run_dir,
            batch_size
        )
        results["txt2img"] = txt2img_results
        
        if not txt2img_results:
            logger.error("Pipeline failed at txt2img stage")
            return results
        
        # Step 2: img2img cleanup (for each generated image)
        for txt2img_meta in txt2img_results:
            img2img_meta = self.run_img2img(
                Path(txt2img_meta["path"]),
                prompt,
                config.get("img2img", {}),
                run_dir
            )
            if img2img_meta:
                results["img2img"].append(img2img_meta)
                
                # Step 3: Upscale
                upscaled_meta = self.run_upscale(
                    Path(img2img_meta["path"]),
                    config.get("upscale", {}),
                    run_dir
                )
                if upscaled_meta:
                    results["upscaled"].append(upscaled_meta)
                    
                    # Add to summary
                    summary_entry = {
                        "prompt": prompt,
                        "txt2img_path": txt2img_meta["path"],
                        "img2img_path": img2img_meta["path"],
                        "upscaled_path": upscaled_meta["path"],
                        "timestamp": upscaled_meta["timestamp"]
                    }
                    results["summary"].append(summary_entry)
        
        # Create CSV summary
        if results["summary"]:
            self.logger.create_csv_summary(run_dir, results["summary"])
        
        logger.info("=" * 60)
        logger.info(f"Pipeline completed: {len(results['summary'])} images processed")
        logger.info(f"Output directory: {run_dir}")
        logger.info("=" * 60)
        
        return results
    
    def run_txt2img_stage(self, prompt: str, negative_prompt: str, 
                         config: Dict[str, Any], output_dir: Path, 
                         image_index: int = 0) -> Optional[Dict[str, Any]]:
        """
        Run single txt2img stage for individual prompt.
        
        Args:
            prompt: Text prompt
            negative_prompt: Negative prompt
            config: Configuration dictionary
            output_dir: Output directory
            image_index: Index for naming
            
        Returns:
            Generated image metadata or None if failed
        """
        try:
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Build txt2img payload
            txt2img_config = config.get("txt2img", {})
            
            # Apply global NSFW prevention to negative prompt
            enhanced_negative = self.config_manager.add_global_negative(negative_prompt)
            logger.info(f"🛡️ Applied global NSFW prevention (stage) - Enhanced: '{enhanced_negative[:100]}...'")
            
            payload = {
                "prompt": prompt,
                "negative_prompt": enhanced_negative,
                "steps": txt2img_config.get("steps", 20),
                "sampler_name": txt2img_config.get("sampler_name", "Euler a"),
                "cfg_scale": txt2img_config.get("cfg_scale", 7.0),
                "width": txt2img_config.get("width", 512),
                "height": txt2img_config.get("height", 512),
                "batch_size": 1,
                "n_iter": 1
            }
            
            # Generate image
            response = self.client.txt2img(payload)
            if not response or 'images' not in response or not response['images']:
                logger.error("txt2img failed - no images returned")
                return None
            
            # Save image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_name = f"txt2img_{timestamp}_{image_index:03d}"
            image_path = output_dir / f"{image_name}.png"
            
            if save_image_from_base64(response['images'][0], image_path):
                metadata = {
                    "name": image_name,
                    "stage": "txt2img", 
                    "timestamp": timestamp,
                    "prompt": prompt,
                    "negative_prompt": enhanced_negative,  # Log the enhanced negative prompt
                    "original_negative_prompt": negative_prompt,  # Also keep original
                    "config": payload,
                    "output_path": str(image_path),
                    "path": str(image_path)
                }
                
                # Save manifest
                manifest_dir = output_dir.parent / "manifests"
                self.logger.save_manifest(manifest_dir, image_name, metadata)
                
                return metadata
            else:
                logger.error("Failed to save generated image")
                return None
                
        except Exception as e:
            logger.error(f"txt2img stage failed: {str(e)}")
            return None
