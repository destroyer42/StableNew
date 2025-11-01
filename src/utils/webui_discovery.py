"""Utility functions for WebUI API discovery"""

import logging
import requests
import subprocess
import time
# import psutil  # Optional dependency for process detection
from pathlib import Path
from typing import Optional, List

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


def launch_webui_safely(webui_path: Path, wait_time: int = 10) -> bool:
    """
    Launch WebUI with improved error handling and validation.
    
    Args:
        webui_path: Path to webui-user.bat
        wait_time: Time to wait for startup
        
    Returns:
        True if launch was successful
    """
    if not webui_path.exists():
        logger.error(f"WebUI not found at: {webui_path}")
        return False
    
    try:
        # Check if WebUI is already running
        existing_url = find_webui_api_port()
        if existing_url:
            logger.info(f"WebUI already running at {existing_url}")
            return True
        
        # Launch WebUI
        logger.info(f"Launching WebUI from: {webui_path}")
        process = subprocess.Popen(
            [str(webui_path), "--api"],
            cwd=webui_path.parent,
            creationflags=subprocess.CREATE_NEW_CONSOLE if subprocess.sys.platform == "win32" else 0
            # Remove stdout/stderr pipes to allow terminal output to be visible
        )
        
        # Wait for startup with periodic checks
        for attempt in range(wait_time):
            time.sleep(1)
            
            # Check if process crashed
            if process.poll() is not None:
                logger.error(f"WebUI process crashed during startup (exit code: {process.returncode})")
                return False
            
            # Check for API availability
            api_url = find_webui_api_port()
            if api_url:
                logger.info(f"WebUI successfully started at {api_url}")
                return True
            
            logger.debug(f"Waiting for WebUI startup... ({attempt + 1}/{wait_time})")
        
        logger.warning("WebUI startup timeout - process may still be initializing")
        return False
        
    except Exception as e:
        logger.error(f"Failed to launch WebUI: {e}")
        return False


def validate_webui_health(api_url: str) -> dict:
    """
    Perform comprehensive health check on WebUI API.
    
    Args:
        api_url: WebUI API URL
        
    Returns:
        Dictionary with health check results
    """
    health_status = {
        'url': api_url,
        'accessible': False,
        'models_loaded': False,
        'samplers_available': False,
        'errors': []
    }
    
    try:
        # Basic connectivity
        response = requests.get(f"{api_url}/sdapi/v1/sd-models", timeout=5)
        if response.status_code == 200:
            health_status['accessible'] = True
            models = response.json()
            health_status['models_loaded'] = len(models) > 0
            health_status['model_count'] = len(models)
        else:
            health_status['errors'].append(f"Models endpoint returned {response.status_code}")
    
    except requests.exceptions.ConnectionError:
        health_status['errors'].append("Connection refused - WebUI not running")
    except requests.exceptions.Timeout:
        health_status['errors'].append("Connection timeout - WebUI may be starting up")
    except Exception as e:
        health_status['errors'].append(f"Unexpected error: {e}")
    
    try:
        # Samplers check
        if health_status['accessible']:
            response = requests.get(f"{api_url}/sdapi/v1/samplers", timeout=5)
            if response.status_code == 200:
                samplers = response.json()
                health_status['samplers_available'] = len(samplers) > 0
                health_status['sampler_count'] = len(samplers)
    
    except Exception as e:
        health_status['errors'].append(f"Samplers check failed: {e}")
    
    return health_status