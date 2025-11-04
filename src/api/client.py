"""API client for Stable Diffusion WebUI"""

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)


class SDWebUIClient:
    """Client for interacting with Stable Diffusion WebUI API"""

    def __init__(self, base_url: str = "http://127.0.0.1:7860", timeout: int = 300):
        """
        Initialize the SD WebUI API client.

        Args:
            base_url: Base URL of the SD WebUI API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def check_api_ready(self, max_retries: int = 5, retry_delay: int = 2) -> bool:
        """
        Check if the API is ready to accept requests.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds

        Returns:
            True if API is ready, False otherwise
        """
        for attempt in range(max_retries):
            try:
                response = requests.get(f"{self.base_url}/sdapi/v1/sd-models", timeout=10)
                if response.status_code == 200:
                    logger.info("SD WebUI API is ready")
                    return True
            except Exception as e:
                logger.warning(f"API check attempt {attempt + 1}/{max_retries} failed: {e}")

            if attempt < max_retries - 1:
                time.sleep(retry_delay)

        logger.error("SD WebUI API is not ready after max retries")
        return False

    def txt2img(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """
        Generate image from text prompt.

        Args:
            payload: Request payload with generation parameters

        Returns:
            Response data including base64 encoded images
        """
        try:
            response = requests.post(
                f"{self.base_url}/sdapi/v1/txt2img", json=payload, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            logger.info(
                f"txt2img completed successfully, generated {len(data.get('images', []))} images"
            )
            return data
        except Exception as e:
            logger.error(f"txt2img request failed: {e}")
            return None

    def img2img(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """
        Refine image using img2img.

        Args:
            payload: Request payload with generation parameters and init image

        Returns:
            Response data including base64 encoded images
        """
        try:
            response = requests.post(
                f"{self.base_url}/sdapi/v1/img2img", json=payload, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            logger.info("img2img completed successfully")
            return data
        except Exception as e:
            logger.error(f"img2img request failed: {e}")
            return None

    def upscale(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """
        Upscale image using extra-single-image endpoint.

        Args:
            payload: Request payload with image and upscaling parameters

        Returns:
            Response data including base64 encoded upscaled image
        """
        try:
            response = requests.post(
                f"{self.base_url}/sdapi/v1/extra-single-image", json=payload, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            logger.info("Upscaling completed successfully")
            return data
        except Exception as e:
            logger.error(f"Upscale request failed: {e}")
            return None

    def get_models(self) -> list[dict[str, Any]] | None:
        """
        Get list of available models.

        Returns:
            List of model information
        """
        try:
            response = requests.get(f"{self.base_url}/sdapi/v1/sd-models", timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Retrieved {len(data)} models")
            return data
        except Exception as e:
            logger.error(f"img2img request failed: {e}")
            return None

    def upscale_image(
        self,
        image_base64: str,
        upscaler: str,
        upscaling_resize: float,
        gfpgan_visibility: float = 0.0,
        codeformer_visibility: float = 0.0,
        codeformer_weight: float = 0.5,
    ) -> dict[str, Any] | None:
        """
        Upscale image using extra upscalers with optional face restoration.

        Args:
            image_base64: Base64 encoded image
            upscaler: Name of the upscaler to use
            upscaling_resize: Scale factor
            gfpgan_visibility: GFPGAN strength (0.0-1.0)
            codeformer_visibility: CodeFormer strength (0.0-1.0)
            codeformer_weight: CodeFormer fidelity (0.0-1.0)

        Returns:
            Response data with upscaled image
        """
        try:
            payload = {
                "resize_mode": 0,
                "upscaling_resize": upscaling_resize,
                "upscaler_1": upscaler,
                "image": image_base64,
                "gfpgan_visibility": gfpgan_visibility,
                "codeformer_visibility": codeformer_visibility,
                "codeformer_weight": codeformer_weight,
            }
            response = requests.post(
                f"{self.base_url}/sdapi/v1/extra-single-image", json=payload, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            # Log face restoration usage
            face_restoration_used = []
            if gfpgan_visibility > 0:
                face_restoration_used.append(f"GFPGAN({gfpgan_visibility})")
            if codeformer_visibility > 0:
                face_restoration_used.append(f"CodeFormer({codeformer_visibility})")

            restoration_info = (
                f" + {', '.join(face_restoration_used)}" if face_restoration_used else ""
            )
            logger.info(f"Upscale completed successfully with {upscaler}{restoration_info}")
            return data
        except Exception as e:
            logger.error(f"Upscale request failed: {e}")
            return None

    def get_models(self) -> list[dict[str, Any]]:
        """
        Get list of available SD models.

        Returns:
            List of model information
        """
        try:
            response = requests.get(f"{self.base_url}/sdapi/v1/sd-models", timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Retrieved {len(data)} models")
            return data
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            return []

    def get_vae_models(self) -> list[dict[str, Any]]:
        """
        Get list of available VAE models.

        Returns:
            List of VAE model information
        """
        try:
            response = requests.get(f"{self.base_url}/sdapi/v1/sd-vae", timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Retrieved {len(data)} VAE models")
            return data
        except Exception as e:
            logger.error(f"Failed to get VAE models: {e}")
            return []

    def get_samplers(self) -> list[dict[str, Any]]:
        """
        Get list of available samplers.

        Returns:
            List of sampler information
        """
        try:
            response = requests.get(f"{self.base_url}/sdapi/v1/samplers", timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Retrieved {len(data)} samplers")
            return data
        except Exception as e:
            logger.error(f"Failed to get samplers: {e}")
            return []

    def get_upscalers(self) -> list[dict[str, Any]]:
        """
        Get list of available upscalers.

        Returns:
            List of upscaler information
        """
        try:
            response = requests.get(f"{self.base_url}/sdapi/v1/upscalers", timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Retrieved {len(data)} upscalers")
            return data
        except Exception as e:
            logger.error(f"Failed to get upscalers: {e}")
            return []

    def get_schedulers(self) -> list[str]:
        """
        Get list of available schedulers.

        Returns:
            List of scheduler names
        """
        try:
            response = requests.get(f"{self.base_url}/sdapi/v1/schedulers", timeout=10)
            response.raise_for_status()
            data = response.json()
            schedulers = [
                scheduler.get("name", scheduler.get("label", "")) for scheduler in data if scheduler
            ]
            logger.info(f"Retrieved {len(schedulers)} schedulers")
            return schedulers
        except Exception as e:
            logger.warning(f"Failed to get schedulers from API: {e}")
            # Fallback to common schedulers with proper capitalization
            return [
                "Normal",
                "Karras",
                "Exponential",
                "SGM Uniform",
                "Simple",
                "DDIM Uniform",
                "Beta",
                "Linear",
                "Cosine",
            ]

    def set_model(self, model_name: str) -> bool:
        """
        Set the current SD model.

        Args:
            model_name: Name of the model to set

        Returns:
            True if successful
        """
        try:
            payload = {"sd_model_checkpoint": model_name}
            response = requests.post(
                f"{self.base_url}/sdapi/v1/options",
                json=payload,
                timeout=30,  # Model switching can take time
            )
            response.raise_for_status()
            logger.info(f"Set model to: {model_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to set model: {e}")
            return False

    def set_vae(self, vae_name: str) -> bool:
        """
        Set the current VAE model.

        Args:
            vae_name: Name of the VAE to set

        Returns:
            True if successful
        """
        try:
            payload = {"sd_vae": vae_name}
            response = requests.post(f"{self.base_url}/sdapi/v1/options", json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Set VAE to: {vae_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to set VAE: {e}")
            return False

    def get_models_old(self) -> list[dict[str, Any]]:
        """
        Get list of available models.

        Returns:
            List of available models
        """
        try:
            response = requests.get(f"{self.base_url}/sdapi/v1/sd-models", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            return []

    def get_samplers(self) -> list[dict[str, Any]]:
        """
        Get list of available samplers.

        Returns:
            List of available samplers
        """
        try:
            response = requests.get(f"{self.base_url}/sdapi/v1/samplers", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get samplers: {e}")
            return []

    def get_current_model(self) -> str | None:
        """
        Get the currently loaded model.

        Returns:
            Current model name
        """
        try:
            response = requests.get(f"{self.base_url}/sdapi/v1/options", timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("sd_model_checkpoint")
        except Exception as e:
            logger.error(f"Failed to get current model: {e}")
            return None
