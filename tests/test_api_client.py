"""Test API client functionality"""

import pytest
import requests_mock
from pathlib import Path
from src.api.client import SDWebUIClient


class TestSDWebUIClient:
    
    def test_init(self):
        """Test client initialization"""
        client = SDWebUIClient()
        assert client.base_url == "http://127.0.0.1:7860"
        assert client.timeout == 300
        
        custom_client = SDWebUIClient("http://localhost:8080", timeout=600)
        assert custom_client.base_url == "http://localhost:8080"
        assert custom_client.timeout == 600
    
    def test_check_api_ready_success(self):
        """Test successful API readiness check"""
        with requests_mock.Mocker() as m:
            m.get("http://127.0.0.1:7860/sdapi/v1/sd-models", 
                  json=[{"model_name": "test_model"}])
            
            client = SDWebUIClient()
            assert client.check_api_ready(max_retries=1) is True
    
    def test_check_api_ready_failure(self):
        """Test failed API readiness check"""
        with requests_mock.Mocker() as m:
            m.get("http://127.0.0.1:7860/sdapi/v1/sd-models", 
                  exc=requests_mock.exceptions.ConnectTimeout)
            
            client = SDWebUIClient()
            assert client.check_api_ready(max_retries=1, retry_delay=0.1) is False
    
    def test_txt2img_success(self):
        """Test successful txt2img request"""
        with requests_mock.Mocker() as m:
            mock_response = {
                "images": ["base64_image_data_here"],
                "info": "generation_info"
            }
            m.post("http://127.0.0.1:7860/sdapi/v1/txt2img", json=mock_response)
            
            client = SDWebUIClient()
            payload = {
                "prompt": "test prompt",
                "steps": 20,
                "width": 512,
                "height": 512
            }
            
            result = client.txt2img(payload)
            assert result is not None
            assert "images" in result
            assert len(result["images"]) == 1
    
    def test_txt2img_failure(self):
        """Test failed txt2img request"""
        with requests_mock.Mocker() as m:
            m.post("http://127.0.0.1:7860/sdapi/v1/txt2img", 
                   status_code=500, text="Internal Server Error")
            
            client = SDWebUIClient()
            payload = {"prompt": "test"}
            
            result = client.txt2img(payload)
            assert result is None
    
    def test_img2img_success(self):
        """Test successful img2img request"""
        with requests_mock.Mocker() as m:
            mock_response = {"images": ["refined_image_data"]}
            m.post("http://127.0.0.1:7860/sdapi/v1/img2img", json=mock_response)
            
            client = SDWebUIClient()
            payload = {
                "init_images": ["input_image_base64"],
                "prompt": "refine this image",
                "denoising_strength": 0.3
            }
            
            result = client.img2img(payload)
            assert result is not None
            assert "images" in result
    
    def test_upscale_success(self):
        """Test successful upscale request"""
        with requests_mock.Mocker() as m:
            mock_response = {"image": "upscaled_image_data"}
            m.post("http://127.0.0.1:7860/sdapi/v1/extra-single-image", 
                   json=mock_response)
            
            client = SDWebUIClient()
            payload = {
                "image": "input_image_base64",
                "upscaler_1": "R-ESRGAN 4x+",
                "upscaling_resize": 2.0
            }
            
            result = client.upscale(payload)
            assert result is not None
            assert "image" in result
    
    def test_get_models_success(self):
        """Test getting available models"""
        with requests_mock.Mocker() as m:
            models_response = [
                {"model_name": "model1.safetensors", "title": "Model 1"},
                {"model_name": "model2.ckpt", "title": "Model 2"}
            ]
            m.get("http://127.0.0.1:7860/sdapi/v1/sd-models", json=models_response)
            
            client = SDWebUIClient()
            models = client.get_models()
            
            assert models is not None
            assert len(models) == 2
            assert models[0]["model_name"] == "model1.safetensors"
    
    def test_get_current_model_success(self):
        """Test getting current model"""
        with requests_mock.Mocker() as m:
            options_response = {
                "sd_model_checkpoint": "current_model.safetensors",
                "sd_vae": "vae_model.pt"
            }
            m.get("http://127.0.0.1:7860/sdapi/v1/options", json=options_response)
            
            client = SDWebUIClient()
            current_model = client.get_current_model()
            
            assert current_model == "current_model.safetensors"