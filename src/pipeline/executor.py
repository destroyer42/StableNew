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
        
    def _parse_sampler_config(self, config: Dict[str, Any]) -> Dict[str, str]:
        """
        Parse sampler configuration and extract scheduler if present.
        
        Args:
            config: Configuration dict that may contain sampler_name and scheduler
            
        Returns:
            Dict with 'sampler_name' and optional 'scheduler'
        """
        sampler_name = config.get("sampler_name", "Euler a")
        
        # If scheduler is already specified separately, use it
        if "scheduler" in config:
            return {
                "sampler_name": sampler_name,
                "scheduler": config["scheduler"]
            }
        
        # Common scheduler mappings for legacy format
        scheduler_mappings = {
            "Karras": "Karras",
            "Exponential": "Exponential", 
            "Polyexponential": "Polyexponential",
            "SGM Uniform": "SGM Uniform"
        }
        
        # Check if sampler name contains a scheduler
        for scheduler_keyword, scheduler_value in scheduler_mappings.items():
            if scheduler_keyword in sampler_name:
                # Split and clean the sampler name
                clean_sampler = sampler_name.replace(scheduler_keyword, "").strip()
                return {
                    "sampler_name": clean_sampler,
                    "scheduler": scheduler_value
                }
        
        # No scheduler found, return sampler with automatic scheduler
        return {
            "sampler_name": sampler_name,
            "scheduler": "Automatic"
        }
        
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
        
        # Parse sampler configuration
        sampler_config = self._parse_sampler_config(config)
        
        payload = {
            "prompt": prompt,
            "negative_prompt": enhanced_negative,
            "steps": config.get("steps", 20),
            "cfg_scale": config.get("cfg_scale", 7.0),
            "width": config.get("width", 512),
            "height": config.get("height", 512),
            "batch_size": batch_size,
            "n_iter": 1
        }
        
        # Add sampler configuration
        payload.update(sampler_config)
        
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
        
        # Parse sampler configuration
        sampler_config = self._parse_sampler_config(config)
        
        payload = {
            "init_images": [input_base64],
            "prompt": prompt,
            "negative_prompt": enhanced_negative,
            "steps": config.get("steps", 15),
            "cfg_scale": config.get("cfg_scale", 7.0),
            "denoising_strength": config.get("denoising_strength", 0.3),
            "width": config.get("width", 512),
            "height": config.get("height", 512)
        }
        
        # Add sampler configuration
        payload.update(sampler_config)
        
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
    
    def run_pack_pipeline(self, pack_name: str, prompt: str, config: Dict[str, Any], 
                         run_dir: Path, prompt_index: int = 0, batch_size: int = 1) -> Dict[str, Any]:
        """
        Run pipeline for a single prompt from a pack with new directory structure.
        
        Args:
            pack_name: Name of the prompt pack (without .txt)
            prompt: Text prompt to process
            config: Configuration dictionary
            run_dir: Main session run directory
            prompt_index: Index of prompt within pack
            batch_size: Number of images to generate
            
        Returns:
            Pipeline results for this prompt
        """
        logger.info(f"🎨 Processing prompt {prompt_index + 1} from pack '{pack_name}'")
        
        # Create pack-specific directory structure
        pack_dir = self.logger.create_pack_directory(run_dir, pack_name)
        
        # Save config for this pack run
        config_path = pack_dir / "config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            import json
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        results = {
            "pack_name": pack_name,
            "pack_dir": str(pack_dir),
            "prompt": prompt,
            "txt2img": [],
            "img2img": [],
            "upscaled": [],
            "summary": []
        }
        
        # Generate images with numbered naming
        for batch_idx in range(batch_size):
            # Calculate global image number for this pack
            image_number = (prompt_index * batch_size) + batch_idx + 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_name = f"{image_number:03d}_{timestamp}"
            
            # Step 1: txt2img
            txt2img_dir = pack_dir / "txt2img"
            txt2img_meta = self.run_txt2img_stage(
                prompt,
                config.get("txt2img", {}).get("negative_prompt", ""),
                config,
                txt2img_dir,
                image_name
            )
            
            if txt2img_meta:
                results["txt2img"].append(txt2img_meta)
                
                # Step 2: img2img cleanup (if enabled)
                if config.get("pipeline", {}).get("img2img_enabled", True):
                    img2img_dir = pack_dir / "img2img"
                    img2img_meta = self.run_img2img_stage(
                        Path(txt2img_meta["path"]),
                        prompt,
                        config.get("img2img", {}),
                        img2img_dir,
                        image_name  # Use same base name
                    )
                    if img2img_meta:
                        results["img2img"].append(img2img_meta)
                        last_image_path = img2img_meta["path"]
                    else:
                        last_image_path = txt2img_meta["path"]
                else:
                    last_image_path = txt2img_meta["path"]
                
                # Step 3: Upscale (if enabled)
                if config.get("pipeline", {}).get("upscale_enabled", True):
                    upscale_dir = pack_dir / "upscaled"
                    upscaled_meta = self.run_upscale_stage(
                        Path(last_image_path),
                        config.get("upscale", {}),
                        upscale_dir,
                        image_name  # Use same base name
                    )
                    if upscaled_meta:
                        results["upscaled"].append(upscaled_meta)
                        final_image_path = upscaled_meta["path"]
                    else:
                        final_image_path = last_image_path
                else:
                    final_image_path = last_image_path
                
                # Add to summary
                summary_entry = {
                    "pack": pack_name,
                    "prompt_index": prompt_index,
                    "batch_index": batch_idx,
                    "image_number": image_number,
                    "prompt": prompt,
                    "final_image": final_image_path,
                    "steps_completed": []
                }
                
                if txt2img_meta:
                    summary_entry["steps_completed"].append("txt2img")
                if results["img2img"] and len(results["img2img"]) > batch_idx:
                    summary_entry["steps_completed"].append("img2img")
                if results["upscaled"] and len(results["upscaled"]) > batch_idx:
                    summary_entry["steps_completed"].append("upscaled")
                
                results["summary"].append(summary_entry)
        
        # Create CSV summary for this pack
        if results["summary"]:
            summary_path = pack_dir / "summary.csv"
            self.logger.create_pack_csv_summary(summary_path, results["summary"])
        
        logger.info(f"✅ Completed pack '{pack_name}' prompt {prompt_index + 1}: {len(results['summary'])} images")
        return results
    
    def run_txt2img_stage(self, prompt: str, negative_prompt: str, 
                         config: Dict[str, Any], output_dir: Path, 
                         image_name: str) -> Optional[Dict[str, Any]]:
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
            
            # Save image with provided name
            image_path = output_dir / f"{image_name}.png"
            
            if save_image_from_base64(response['images'][0], image_path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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
                
                # Save manifest to manifests directory
                # Get the pack directory (parent of parent of output_dir)
                pack_dir = output_dir.parent
                manifest_dir = pack_dir / "manifests"
                manifest_path = manifest_dir / f"{image_name}.json"
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                return metadata
            else:
                logger.error("Failed to save generated image")
                return None
                
        except Exception as e:
            logger.error(f"txt2img stage failed: {str(e)}")
            return None
    
    def run_img2img_stage(self, input_image_path: Path, prompt: str, 
                         config: Dict[str, Any], output_dir: Path,
                         image_name: str) -> Optional[Dict[str, Any]]:
        """
        Run img2img stage for image cleanup/refinement.
        
        Args:
            input_image_path: Path to input image
            prompt: Text prompt
            config: img2img configuration
            output_dir: Output directory
            image_name: Base name for output image
            
        Returns:
            Generated image metadata or None if failed
        """
        try:
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Load input image as base64
            input_image_b64 = load_image_to_base64(input_image_path)
            if not input_image_b64:
                logger.error(f"Failed to load input image: {input_image_path}")
                return None
            
            # Build img2img payload
            payload = {
                "init_images": [input_image_b64],
                "prompt": prompt,
                "negative_prompt": config.get("negative_prompt", ""),
                "steps": config.get("steps", 15),
                "cfg_scale": config.get("cfg_scale", 7.0),
                "denoising_strength": config.get("denoising_strength", 0.3),
                "width": config.get("width", 512),
                "height": config.get("height", 512),
                "sampler_name": config.get("sampler_name", "Euler a"),
                "batch_size": 1,
                "n_iter": 1
            }
            
            # Execute img2img
            response = self.client.img2img(payload)
            if not response or 'images' not in response or not response['images']:
                logger.error("img2img request failed or returned no images")
                return None
            
            # Save image
            image_path = output_dir / f"{image_name}.png"
            
            if save_image_from_base64(response['images'][0], image_path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                metadata = {
                    "name": image_name,
                    "stage": "img2img",
                    "timestamp": timestamp,
                    "prompt": prompt,
                    "input_image": str(input_image_path),
                    "config": payload,
                    "path": str(image_path)
                }
                
                # Save manifest to manifests directory
                pack_dir = output_dir.parent
                manifest_dir = pack_dir / "manifests"
                manifest_path = manifest_dir / f"{image_name}.json"
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                logger.info(f"✅ img2img completed: {image_path.name}")
                return metadata
            else:
                logger.error(f"Failed to save img2img image: {image_path}")
                return None
                
        except Exception as e:
            logger.error(f"img2img stage failed: {e}")
            return None
    
    def run_upscale_stage(self, input_image_path: Path, config: Dict[str, Any],
                         output_dir: Path, image_name: str) -> Optional[Dict[str, Any]]:
        """
        Run upscale stage for image enhancement.
        
        Args:
            input_image_path: Path to input image
            config: Upscale configuration
            output_dir: Output directory
            image_name: Base name for output image
            
        Returns:
            Generated image metadata or None if failed
        """
        try:
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Load input image as base64
            input_image_b64 = load_image_to_base64(input_image_path)
            if not input_image_b64:
                logger.error(f"Failed to load input image: {input_image_path}")
                return None
            
            # Build upscale payload
            payload = {
                "image": input_image_b64,
                "upscaling_resize": config.get("upscaling_resize", 2.0),
                "upscaler_1": config.get("upscaler_1", "R-ESRGAN 4x+"),
                "upscaler_2": config.get("upscaler_2", "None"),
                "extras_upscaler_2_visibility": config.get("extras_upscaler_2_visibility", 0)
            }
            
            # Execute upscale
            response = self.client.upscale(payload)
            if not response or 'image' not in response:
                logger.error("Upscale request failed or returned no image")
                return None
            
            # Save image
            image_path = output_dir / f"{image_name}.png"
            
            if save_image_from_base64(response['image'], image_path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                metadata = {
                    "name": image_name,
                    "stage": "upscale",
                    "timestamp": timestamp,
                    "input_image": str(input_image_path),
                    "config": payload,
                    "path": str(image_path)
                }
                
                # Save manifest to manifests directory
                pack_dir = output_dir.parent
                manifest_dir = pack_dir / "manifests"
                manifest_path = manifest_dir / f"{image_name}.json"
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                logger.info(f"✅ Upscale completed: {image_path.name}")
                return metadata
            else:
                logger.error(f"Failed to save upscaled image: {image_path}")
                return None
                
        except Exception as e:
            logger.error(f"Upscale stage failed: {e}")
            return None
