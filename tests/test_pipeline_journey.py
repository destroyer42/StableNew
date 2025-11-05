#!/usr/bin/env python3
"""
Comprehensive journey tests for the StableNew pipeline.

Tests the complete pipeline flow with various configurations to ensure:
1. All stages work correctly (txt2img → img2img → upscale → video)
2. Config pass-through is preserved at each stage
3. Optional stages can be skipped (img2img, upscale)
4. Previous functionality remains intact
"""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.pipeline.executor import Pipeline
from src.utils import StructuredLogger


@pytest.fixture
def mock_client():
    """Create a mock SD WebUI client that returns valid responses"""
    client = Mock()

    # Mock txt2img response - returns a simple 1x1 pixel PNG as base64
    mock_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    # Create a side_effect function that returns the requested batch_size
    def txt2img_side_effect(payload):
        batch_size = payload.get("batch_size", 1)
        return {"images": [mock_image_b64] * batch_size, "parameters": {}}

    client.txt2img.side_effect = txt2img_side_effect

    client.img2img.return_value = {"images": [mock_image_b64], "parameters": {}}

    client.upscale.return_value = {"image": mock_image_b64}
    client.upscale_image.return_value = {"image": mock_image_b64}

    client.set_model = Mock()
    client.set_vae = Mock()

    return client


@pytest.fixture
def structured_logger(tmp_path):
    """Create a structured logger with temporary directory"""
    return StructuredLogger(output_dir=tmp_path)


@pytest.fixture
def pipeline(mock_client, structured_logger):
    """Create pipeline instance with mocked client"""
    return Pipeline(mock_client, structured_logger)


class TestFullPipelineJourney:
    """Test complete pipeline execution with all stages enabled"""

    def test_full_pipeline_all_stages(self, pipeline, mock_client, tmp_path):
        """Test complete pipeline: txt2img → img2img → upscale"""
        config = {
            "txt2img": {
                "steps": 20,
                "cfg_scale": 7.0,
                "width": 512,
                "height": 512,
                "sampler_name": "Euler a",
                "negative_prompt": "ugly",
            },
            "img2img": {
                "steps": 15,
                "cfg_scale": 7.0,
                "denoising_strength": 0.3,
                "sampler_name": "Euler a",
            },
            "upscale": {"upscaler": "R-ESRGAN 4x+", "upscaling_resize": 2.0},
            "pipeline": {"img2img_enabled": True, "upscale_enabled": True},
        }

        results = pipeline.run_full_pipeline(prompt="test prompt", config=config, batch_size=1)

        # Verify all stages executed
        assert len(results["txt2img"]) == 1
        assert len(results["img2img"]) == 1
        assert len(results["upscaled"]) == 1
        assert len(results["summary"]) == 1

        # Verify summary contains all paths
        summary = results["summary"][0]
        assert "txt2img_path" in summary
        assert "img2img_path" in summary
        assert "upscaled_path" in summary
        assert "final_image_path" in summary
        assert summary["stages_completed"] == ["txt2img", "img2img", "upscale"]

        # Verify API calls were made
        assert mock_client.txt2img.called
        assert mock_client.img2img.called
        assert mock_client.upscale.called

    def test_config_passthrough_txt2img(self, pipeline, mock_client, tmp_path):
        """Test that txt2img config is correctly passed to API"""
        config = {
            "txt2img": {
                "steps": 42,
                "cfg_scale": 12.5,
                "width": 1024,
                "height": 768,
                "sampler_name": "DPM++ 2M",
                "scheduler": "Karras",
                "clip_skip": 2,
                "seed": 12345,
                "negative_prompt": "bad quality",
            },
            "pipeline": {"img2img_enabled": False, "upscale_enabled": False},
        }

        results = pipeline.run_full_pipeline(prompt="config test", config=config, batch_size=1)

        # Get the actual call arguments
        call_args = mock_client.txt2img.call_args
        payload = call_args[0][0]  # First positional argument

        # Verify critical config values were passed through
        assert payload["steps"] == 42
        assert payload["cfg_scale"] == 12.5
        assert payload["width"] == 1024
        assert payload["height"] == 768
        assert payload["sampler_name"] == "DPM++ 2M"
        assert payload["scheduler"] == "Karras"
        assert payload["clip_skip"] == 2
        assert payload["seed"] == 12345
        # Note: negative_prompt will have global NSFW prevention added
        assert "bad quality" in payload["negative_prompt"]


class TestOptionalStages:
    """Test pipeline with optional stages disabled"""

    def test_skip_img2img(self, pipeline, mock_client, tmp_path):
        """Test pipeline with img2img disabled: txt2img → upscale"""
        config = {
            "txt2img": {"steps": 20, "cfg_scale": 7.0},
            "upscale": {"upscaler": "R-ESRGAN 4x+"},
            "pipeline": {"img2img_enabled": False, "upscale_enabled": True},
        }

        results = pipeline.run_full_pipeline(
            prompt="skip img2img test", config=config, batch_size=1
        )

        # Verify stages
        assert len(results["txt2img"]) == 1
        assert len(results["img2img"]) == 0  # Should be empty
        assert len(results["upscaled"]) == 1

        # Verify summary
        summary = results["summary"][0]
        assert "txt2img_path" in summary
        assert "img2img_path" not in summary
        assert "upscaled_path" in summary
        assert summary["stages_completed"] == ["txt2img", "upscale"]

        # Verify API calls
        assert mock_client.txt2img.called
        assert not mock_client.img2img.called  # Should NOT be called
        assert mock_client.upscale.called

    def test_skip_upscale(self, pipeline, mock_client, tmp_path):
        """Test pipeline with upscale disabled: txt2img → img2img"""
        config = {
            "txt2img": {"steps": 20},
            "img2img": {"steps": 15},
            "pipeline": {"img2img_enabled": True, "upscale_enabled": False},
        }

        results = pipeline.run_full_pipeline(
            prompt="skip upscale test", config=config, batch_size=1
        )

        # Verify stages
        assert len(results["txt2img"]) == 1
        assert len(results["img2img"]) == 1
        assert len(results["upscaled"]) == 0  # Should be empty

        # Verify summary
        summary = results["summary"][0]
        assert "txt2img_path" in summary
        assert "img2img_path" in summary
        assert "upscaled_path" not in summary
        assert summary["stages_completed"] == ["txt2img", "img2img"]

        # Verify API calls
        assert mock_client.txt2img.called
        assert mock_client.img2img.called
        assert not mock_client.upscale.called  # Should NOT be called

    def test_skip_both_img2img_and_upscale(self, pipeline, mock_client, tmp_path):
        """Test pipeline with both img2img and upscale disabled: txt2img only"""
        config = {
            "txt2img": {"steps": 20, "cfg_scale": 7.0},
            "pipeline": {"img2img_enabled": False, "upscale_enabled": False},
        }

        results = pipeline.run_full_pipeline(
            prompt="txt2img only test", config=config, batch_size=1
        )

        # Verify only txt2img executed
        assert len(results["txt2img"]) == 1
        assert len(results["img2img"]) == 0
        assert len(results["upscaled"]) == 0

        # Verify summary
        summary = results["summary"][0]
        assert "txt2img_path" in summary
        assert "img2img_path" not in summary
        assert "upscaled_path" not in summary
        assert summary["stages_completed"] == ["txt2img"]
        assert summary["final_image_path"] == summary["txt2img_path"]

        # Verify only txt2img was called
        assert mock_client.txt2img.called
        assert not mock_client.img2img.called
        assert not mock_client.upscale.called


class TestBatchProcessing:
    """Test batch processing capabilities"""

    def test_multiple_images_full_pipeline(self, pipeline, mock_client, tmp_path):
        """Test batch generation with all stages"""
        config = {
            "txt2img": {"steps": 20},
            "img2img": {"steps": 15},
            "upscale": {"upscaler": "R-ESRGAN 4x+"},
            "pipeline": {"img2img_enabled": True, "upscale_enabled": True},
        }

        results = pipeline.run_full_pipeline(prompt="batch test", config=config, batch_size=3)

        # Should process 3 images through all stages
        assert len(results["txt2img"]) == 3
        assert len(results["img2img"]) == 3
        assert len(results["upscaled"]) == 3
        assert len(results["summary"]) == 3

        # Verify each summary has all stages
        for summary in results["summary"]:
            assert summary["stages_completed"] == ["txt2img", "img2img", "upscale"]

    def test_multiple_images_skip_img2img(self, pipeline, mock_client, tmp_path):
        """Test batch generation skipping img2img"""
        config = {
            "txt2img": {"steps": 20},
            "upscale": {"upscaler": "R-ESRGAN 4x+"},
            "pipeline": {"img2img_enabled": False, "upscale_enabled": True},
        }

        results = pipeline.run_full_pipeline(
            prompt="batch skip img2img", config=config, batch_size=2
        )

        # Should process 2 images, skipping img2img
        assert len(results["txt2img"]) == 2
        assert len(results["img2img"]) == 0
        assert len(results["upscaled"]) == 2
        assert len(results["summary"]) == 2

        # Verify each summary skipped img2img
        for summary in results["summary"]:
            assert summary["stages_completed"] == ["txt2img", "upscale"]
            assert "img2img_path" not in summary


class TestConfigurationPreservation:
    """Test that configuration is preserved through all pipeline stages"""

    def test_hires_fix_config_passthrough(self, pipeline, mock_client, tmp_path):
        """Test high-res fix configuration is passed through correctly"""
        config = {
            "txt2img": {
                "steps": 20,
                "enable_hr": True,
                "hr_scale": 2.0,
                "hr_upscaler": "Latent",
                "hr_second_pass_steps": 15,
                "denoising_strength": 0.6,
            },
            "pipeline": {"img2img_enabled": False, "upscale_enabled": False},
        }

        pipeline.run_full_pipeline("hires test", config, batch_size=1)

        # Verify hires.fix config was passed
        call_args = mock_client.txt2img.call_args[0][0]
        assert call_args["enable_hr"] == True
        assert call_args["hr_scale"] == 2.0
        assert call_args["hr_upscaler"] == "Latent"
        assert call_args["hr_second_pass_steps"] == 15
        assert call_args["denoising_strength"] == 0.6

    def test_model_and_vae_config(self, pipeline, mock_client, tmp_path):
        """Test model and VAE configuration is applied"""
        config = {
            "txt2img": {
                "steps": 20,
                "model": "sd_xl_base_1.0.safetensors",
                "vae": "sdxl_vae.safetensors",
            },
            "pipeline": {"img2img_enabled": False, "upscale_enabled": False},
        }

        pipeline.run_full_pipeline("model test", config, batch_size=1)

        # Verify model and VAE were set
        mock_client.set_model.assert_called_once_with("sd_xl_base_1.0.safetensors")
        mock_client.set_vae.assert_called_once_with("sdxl_vae.safetensors")

    def test_negative_prompt_enhancement(self, pipeline, mock_client, tmp_path):
        """Test that negative prompts get global NSFW prevention"""
        config = {
            "txt2img": {"steps": 20, "negative_prompt": "bad quality, blurry"},
            "pipeline": {"img2img_enabled": False, "upscale_enabled": False},
        }

        pipeline.run_full_pipeline("negative test", config, batch_size=1)

        # Verify negative prompt was enhanced (should contain original + global_neg)
        call_args = mock_client.txt2img.call_args[0][0]
        enhanced_negative = call_args["negative_prompt"]

        # Should contain the original negative prompt
        assert "bad quality" in enhanced_negative
        assert "blurry" in enhanced_negative

        # Should be longer than original (global_neg added)
        assert len(enhanced_negative) > len("bad quality, blurry")


class TestErrorHandling:
    """Test pipeline behavior with errors"""

    def test_txt2img_failure(self, pipeline, mock_client, tmp_path):
        """Test pipeline handles txt2img failure gracefully"""
        # Override the side_effect for this test only
        mock_client.txt2img.side_effect = None
        mock_client.txt2img.return_value = None  # Simulate failure

        config = {
            "txt2img": {"steps": 20},
            "pipeline": {"img2img_enabled": True, "upscale_enabled": True},
        }

        results = pipeline.run_full_pipeline("fail test", config, batch_size=1)

        # Should fail early with no results
        assert len(results["txt2img"]) == 0
        assert len(results["img2img"]) == 0
        assert len(results["upscaled"]) == 0
        assert len(results["summary"]) == 0

    def test_img2img_failure_continues(self, pipeline, mock_client, tmp_path):
        """Test pipeline continues to upscale when img2img fails"""
        # txt2img succeeds, img2img fails
        mock_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        mock_client.txt2img.return_value = {"images": [mock_image_b64]}
        mock_client.img2img.return_value = None  # img2img fails
        mock_client.upscale.return_value = {"image": mock_image_b64}

        config = {
            "txt2img": {"steps": 20},
            "img2img": {"steps": 15},
            "upscale": {"upscaler": "R-ESRGAN 4x+"},
            "pipeline": {"img2img_enabled": True, "upscale_enabled": True},
        }

        results = pipeline.run_full_pipeline("partial fail", config, batch_size=1)

        # txt2img should succeed
        assert len(results["txt2img"]) == 1

        # img2img fails, so upscale should use txt2img output
        assert len(results["img2img"]) == 0
        assert len(results["upscaled"]) == 1

        # Summary should show partial completion
        assert len(results["summary"]) == 1
        summary = results["summary"][0]
        assert "txt2img" in summary["stages_completed"]
        assert "img2img" not in summary["stages_completed"]
        assert "upscale" in summary["stages_completed"]


class TestDirectoryStructure:
    """Test that output directory structure is created correctly"""

    def test_run_directory_creation(self, pipeline, mock_client, tmp_path):
        """Test that run directories are created properly"""
        config = {
            "txt2img": {"steps": 20},
            "pipeline": {"img2img_enabled": True, "upscale_enabled": True},
        }

        results = pipeline.run_full_pipeline("dir test", config, batch_size=1)

        run_dir = Path(results["run_dir"])

        # Verify run directory exists
        assert run_dir.exists()
        assert run_dir.is_dir()

        # Verify subdirectories for each stage
        assert (run_dir / "txt2img").exists()
        assert (run_dir / "img2img").exists()
        assert (run_dir / "upscaled").exists()
        assert (run_dir / "manifests").exists()

    def test_manifest_creation(self, pipeline, mock_client, tmp_path):
        """Test that manifests are created for each image"""
        config = {
            "txt2img": {"steps": 20},
            "pipeline": {"img2img_enabled": False, "upscale_enabled": False},
        }

        results = pipeline.run_full_pipeline("manifest test", config, batch_size=1)

        run_dir = Path(results["run_dir"])
        manifest_dir = run_dir / "manifests"

        # Should have at least one manifest file
        manifests = list(manifest_dir.glob("*.json"))
        assert len(manifests) > 0

        # Verify manifest content
        with open(manifests[0], encoding="utf-8") as f:
            manifest = json.load(f)
            assert "stage" in manifest
            assert "timestamp" in manifest
            assert "prompt" in manifest


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
