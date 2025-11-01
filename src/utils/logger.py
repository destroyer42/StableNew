"""Logging utilities with structured JSON output"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
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
        Create a new run directory.
        
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
        
        # Create subdirectories
        (run_dir / "txt2img").mkdir(exist_ok=True)
        (run_dir / "img2img").mkdir(exist_ok=True)
        (run_dir / "upscaled").mkdir(exist_ok=True)
        (run_dir / "video").mkdir(exist_ok=True)
        (run_dir / "manifests").mkdir(exist_ok=True)
        
        self.logger.info(f"Created run directory: {run_dir}")
        return run_dir
    
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
            True if saved successfully
        """
        csv_path = run_dir / "summary.csv"
        try:
            if not images_data:
                self.logger.warning("No images data to write to CSV")
                return False
                
            # Determine all unique keys
            all_keys = set()
            for data in images_data:
                all_keys.update(data.keys())
            
            fieldnames = sorted(all_keys)
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(images_data)
            
            self.logger.info(f"Created CSV summary with {len(images_data)} entries")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create CSV summary: {e}")
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
