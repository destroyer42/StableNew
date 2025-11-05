import pytest
from unittest.mock import patch, Mock
from pathlib import Path
from src.pipeline.executor import Pipeline
from src.utils import StructuredLogger

@pytest.fixture
def mock_client():
    client = Mock()
    mock_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    client.txt2img.return_value = {"images": [mock_image_b64]}
    client.set_model = Mock()
    client.set_vae = Mock()
    return client

@pytest.fixture
def structured_logger(tmp_path):
    return StructuredLogger(output_dir=tmp_path)

@pytest.fixture
def pipeline(mock_client, structured_logger):
    return Pipeline(mock_client, structured_logger)

def test_run_txt2img_stage_basic(pipeline, tmp_path):
    prompt = "castle on a hill"
    negative_prompt = "low quality"
    config = {"txt2img": {"steps": 5, "width": 256, "height": 256}}
    image_name = "castle_test"
    output_dir = tmp_path / "txt2img_stage"
    output_dir.mkdir(exist_ok=True)
    with patch("src.pipeline.executor.save_image_from_base64", return_value=True):
        result = pipeline.run_txt2img_stage(
            prompt,
            negative_prompt,
            config,
            output_dir,
            image_name,
        )
    assert result is not None
    assert result["name"] == image_name
    assert result["stage"] == "txt2img"
    assert "path" in result
