"""Test API client functionality"""

import pytest
import requests
import requests_mock
from src.api.client import SDWebUIClient

API_BASE_URL = "http://127.0.0.1:7860"


class TestSDWebUIClient:
    """Test suite for the SD WebUI API client"""

    def setup_method(self):
        """Setup for each test"""
        self.client = SDWebUIClient()

    def test_init(self):
        """Test client initialization"""
        assert self.client.base_url == API_BASE_URL

    def test_check_api_ready_success(self):
        """Test successful API readiness check"""
        with requests_mock.Mocker() as m:
            m.get(f"{API_BASE_URL}/sdapi/v1/sd-models", json=[{"title": "model1.safetensors"}])
            assert self.client.check_api_ready() is True

    def test_check_api_ready_failure(self):
        """Test failed API readiness check"""
        with requests_mock.Mocker() as m:
            m.get(f"{API_BASE_URL}/sdapi/v1/sd-models",
                  exc=requests.exceptions.ConnectTimeout)
            assert self.client.check_api_ready() is False

    def test_txt2img_success(self):
        """Test successful txt2img call"""
        with requests_mock.Mocker() as m:
            m.post(f"{API_BASE_URL}/sdapi/v1/txt2img", json={'images': ['test_image_base64']})
            response = self.client.txt2img({})
            assert response is not None
            assert 'images' in response

    def test_txt2img_failure(self):
        """Test failed txt2img call"""
        with requests_mock.Mocker() as m:
            m.post(f"{API_BASE_URL}/sdapi/v1/txt2img", status_code=500)
            response = self.client.txt2img({})
            assert response is None

    def test_img2img_success(self):
        """Test successful img2img call"""
        with requests_mock.Mocker() as m:
            m.post(f"{API_BASE_URL}/sdapi/v1/img2img", json={'images': ['test_image_base64']})
            response = self.client.img2img({})
            assert response is not None
            assert 'images' in response

    def test_upscale_success(self):
        """Test successful upscale call"""
        with requests_mock.Mocker() as m:
            m.post(f"{API_BASE_URL}/sdapi/v1/extra-single-image", json={'image': 'upscaled_image_base64'})
            response = self.client.upscale_image("dummy_base64", "R-ESRGAN 4x+", 2.0)
            assert response is not None
            assert 'image' in response

    def test_get_models_success(self):
        """Test successful get_models call"""
        with requests_mock.Mocker() as m:
            m.get(f"{API_BASE_URL}/sdapi/v1/sd-models", json=[{'title': 'model1'}, {'title': 'model2'}])
            models = self.client.get_models()
            assert [m['title'] for m in models] == ['model1', 'model2']

    def test_get_current_model_success(self):
        """Test successful get_current_model call"""
        with requests_mock.Mocker() as m:
            m.get(f"{API_BASE_URL}/sdapi/v1/options", json={'sd_model_checkpoint': 'current_model'})
            model = self.client.get_current_model()
            assert model == 'current_model'