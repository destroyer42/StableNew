"""Utility functions for WebUI API discovery"""

import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


def find_webui_api_port(base_url: str = "http://127.0.0.1", start_port: int = 7860, max_attempts: int = 5) -> Optional[str]:
    """
    Find the actual port where WebUI API is running.
    
    WebUI auto-increments ports when 7860 is busy, so this tries common ports.
    
    Args:
        base_url: Base URL without port
        start_port: Starting port to check (default: 7860)
        max_attempts: Maximum number of ports to try
        
    Returns:
        Full URL of working API or None if not found
    """
    for i in range(max_attempts):
        port = start_port + i
        test_url = f"{base_url}:{port}"
        
        try:
            # Quick health check
            response = requests.get(f"{test_url}/sdapi/v1/sd-models", timeout=5)
            if response.status_code == 200:
                logger.info(f"Found WebUI API at {test_url}")
                return test_url
        except Exception:
            continue
    
    logger.warning(f"Could not find WebUI API on ports {start_port}-{start_port + max_attempts - 1}")
    return None


def wait_for_webui_ready(api_url: str, max_wait_seconds: int = 60) -> bool:
    """
    Wait for WebUI to be ready and model loaded.
    
    Args:
        api_url: Full API URL
        max_wait_seconds: Maximum time to wait
        
    Returns:
        True if WebUI is ready, False if timeout
    """
    import time
    
    start_time = time.time()
    while time.time() - start_time < max_wait_seconds:
        try:
            # Check if API responds
            response = requests.get(f"{api_url}/sdapi/v1/options", timeout=5)
            if response.status_code == 200:
                options = response.json()
                
                # Check if model is loaded (has a current model)
                if options.get("sd_model_checkpoint"):
                    logger.info(f"WebUI ready with model: {options['sd_model_checkpoint']}")
                    return True
            
        except Exception as e:
            logger.debug(f"WebUI not ready yet: {e}")
        
        time.sleep(2)
    
    logger.error(f"WebUI did not become ready within {max_wait_seconds} seconds")
    return False