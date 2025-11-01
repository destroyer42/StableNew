"""Logging utilities with structured JSON output"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import csv


class StructuredLogger:
    """Logger that creates JSON manifests and CSV summaries"""
    
    def __init__(self, output_dir: str = "output"):
        """
        Initialize structured logger.
        
        Args:
            output_dir: Base output directory
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Setup Python logging
        self.logger = logging.getLogger("StableNew")
        
    def create_run_directory(self, run_name: Optional[str] = None) -> Path:
        """
        Create a new run directory with improved architecture:
        single_date_time_folder/pack_name/combined_steps_folder/numbered_images.png
        
        Args:
            run_name: Optional name for the run
            
        Returns:
            Path to the run directory
        """
        if run_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_name = f"run_{timestamp}"
        
        run_dir = self.output_dir / run_name
        run_dir.mkdir(exist_ok=True, parents=True)
        
        # NOTE: Pack-specific subdirectories will be created as needed
        # Structure: run_dir / pack_name / steps_folder / images
        # No longer pre-creating generic subdirectories
        
        self.logger.info(f"Created run directory: {run_dir}")
        return run_dir
    
    def create_pack_directory(self, run_dir: Path, pack_name: str) -> Path:
        """
        Create directory structure for a specific pack with traditional pipeline folders.
        
        Args:
            run_dir: Main run directory
            pack_name: Name of the prompt pack (without .txt extension)
            
        Returns:
            Path to the pack directory
        """
        # Remove .txt extension if present and add _pack suffix
        clean_pack_name = pack_name.replace('.txt', '')
        if not clean_pack_name.endswith('_pack'):
            clean_pack_name += '_pack'
        
        pack_dir = run_dir / clean_pack_name
        pack_dir.mkdir(exist_ok=True, parents=True)
        
        # Create traditional pipeline subdirectories within pack
        (pack_dir / "txt2img").mkdir(exist_ok=True)
        (pack_dir / "img2img").mkdir(exist_ok=True)
        (pack_dir / "upscaled").mkdir(exist_ok=True)
        (pack_dir / "video").mkdir(exist_ok=True)
        (pack_dir / "manifests").mkdir(exist_ok=True)
        
        self.logger.info(f"Created pack directory with pipeline folders: {pack_dir}")
        return pack_dir
    
    def save_manifest(self, run_dir: Path, image_name: str, metadata: Dict[str, Any]) -> bool:
        """
        Save JSON manifest for an image.
        
        Args:
            run_dir: Run directory
            image_name: Name of the image
            metadata: Metadata to save
            
        Returns:
            True if saved successfully
        """
        manifest_path = run_dir / "manifests" / f"{image_name}.json"
        try:
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved manifest: {manifest_path.name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save manifest: {e}")
            return False
    
    def create_csv_summary(self, run_dir: Path, images_data: list) -> bool:
        """
        Create CSV rollup summary of all images.
        
        Args:
            run_dir: Run directory
            images_data: List of image metadata dictionaries
            
        Returns:
            True if created successfully
        """
        if not images_data:
            self.logger.warning("No image data to summarize")
            return True
        
        try:
            summary_file = run_dir / "summary.csv"
            
            # Define CSV headers
            headers = [
                'image_name', 'stage', 'timestamp', 'prompt', 'negative_prompt',
                'steps', 'sampler', 'cfg_scale', 'width', 'height', 'seed',
                'model', 'file_path', 'file_size'
            ]
            
            with open(summary_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                
                for img_data in images_data:
                    # Extract config data safely
                    config = img_data.get('config', {})
                    
                    # Get file size if file exists
                    file_size = ""
                    if 'path' in img_data:
                        try:
                            file_path = Path(img_data['path'])
                            if file_path.exists():
                                file_size = file_path.stat().st_size
                        except:
                            pass
                    
                    row = {
                        'image_name': img_data.get('name', ''),
                        'stage': img_data.get('stage', ''),
                        'timestamp': img_data.get('timestamp', ''),
                        'prompt': img_data.get('prompt', ''),
                        'negative_prompt': config.get('negative_prompt', ''),
                        'steps': config.get('steps', ''),
                        'sampler': config.get('sampler_name', ''),
                        'cfg_scale': config.get('cfg_scale', ''),
                        'width': config.get('width', ''),
                        'height': config.get('height', ''),
                        'seed': config.get('seed', ''),
                        'model': img_data.get('model', ''),
                        'file_path': img_data.get('path', ''),
                        'file_size': file_size
                    }
                    writer.writerow(row)
            
            self.logger.info(f"Created CSV summary: {summary_file}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create CSV summary: {e}")
            return False
    
    def create_pack_csv_summary(self, summary_path: Path, summary_data: List[Dict[str, Any]]) -> bool:
        """
        Create CSV summary for a specific pack.
        
        Args:
            summary_path: Path where to save the CSV
            summary_data: List of summary entries
            
        Returns:
            True if created successfully
        """
        try:
            with open(summary_path, 'w', newline='', encoding='utf-8') as csvfile:
                if not summary_data:
                    return False
                
                fieldnames = summary_data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(summary_data)
            
            self.logger.info(f"Created pack CSV summary: {summary_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create pack CSV summary: {e}")
            return False
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create CSV summary: {e}")
            return False
    
    def create_rollup_manifest(self, run_dir: Path) -> bool:
        """
        Create rollup manifest from all individual JSON manifests.
        
        Args:
            run_dir: Run directory
            
        Returns:
            True if created successfully
        """
        try:
            manifests_dir = run_dir / "manifests"
            if not manifests_dir.exists():
                self.logger.warning("No manifests directory found")
                return True
            
            # Collect all manifest files
            manifest_files = list(manifests_dir.glob("*.json"))
            if not manifest_files:
                self.logger.warning("No manifest files found")
                return True
            
            # Read all manifests
            all_images = []
            for manifest_file in manifest_files:
                try:
                    with open(manifest_file, 'r', encoding='utf-8') as f:
                        manifest_data = json.load(f)
                        all_images.append(manifest_data)
                except Exception as e:
                    self.logger.error(f"Failed to read manifest {manifest_file.name}: {e}")
            
            if not all_images:
                self.logger.warning("No valid manifest data found")
                return True
            
            # Create rollup manifest
            rollup_data = {
                'run_info': {
                    'run_directory': str(run_dir),
                    'timestamp': datetime.now().isoformat(),
                    'total_images': len(all_images)
                },
                'images': all_images
            }
            
            rollup_file = run_dir / "rollup_manifest.json"
            with open(rollup_file, 'w', encoding='utf-8') as f:
                json.dump(rollup_data, f, indent=2, ensure_ascii=False)
            
            # Create CSV summary
            self.create_csv_summary(run_dir, all_images)
            
            self.logger.info(f"Created rollup manifest with {len(all_images)} images")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create rollup manifest: {e}")
            return False


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """
    Setup logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
    """
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )
