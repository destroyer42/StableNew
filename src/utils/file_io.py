"""File I/O utilities with UTF-8 support"""

import base64
import logging
from pathlib import Path
from typing import Optional
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)


def save_image_from_base64(base64_str: str, output_path: Path) -> bool:
    """
    Save base64 encoded image to file.
    
    Args:
        base64_str: Base64 encoded image string
        output_path: Path to save the image
        
    Returns:
        True if saved successfully
    """
    try:
        # Remove data URL prefix if present
        if ',' in base64_str:
            base64_str = base64_str.split(',', 1)[1]
        
        image_data = base64.b64decode(base64_str)
        image = Image.open(BytesIO(image_data))
        
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        image.save(output_path)
        logger.info(f"Saved image: {output_path.name}")
        return True
    except Exception as e:
        logger.error(f"Failed to save image: {e}")
        return False


def load_image_to_base64(image_path: Path) -> Optional[str]:
    """
    Load image and convert to base64.
    
    Args:
        image_path: Path to the image
        
    Returns:
        Base64 encoded image string
    """
    try:
        with Image.open(image_path) as img:
            buffered = BytesIO()
            img.save(buffered, format=img.format or "PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        logger.info(f"Loaded image to base64: {image_path.name}")
        return img_str
    except Exception as e:
        logger.error(f"Failed to load image: {e}")
        return None


def read_text_file(file_path: Path) -> Optional[str]:
    """
    Read text file with UTF-8 encoding.
    
    Args:
        file_path: Path to the text file
        
    Returns:
        File contents as string
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"Read text file: {file_path.name}")
        return content
    except Exception as e:
        logger.error(f"Failed to read text file: {e}")
        return None


def write_text_file(file_path: Path, content: str) -> bool:
    """
    Write text file with UTF-8 encoding.
    
    Args:
        file_path: Path to save the file
        content: Content to write
        
    Returns:
        True if saved successfully
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Wrote text file: {file_path.name}")
        return True
    except Exception as e:
        logger.error(f"Failed to write text file: {e}")
        return False
