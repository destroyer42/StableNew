"""
Tests for ConfigPanel component.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import pytest

from src.gui.config_panel import ConfigPanel


class TestConfigPanelBasics:
    """Test basic ConfigPanel functionality."""

    @pytest.fixture(autouse=True)
    def _setup(self, tk_root):
        self.root = tk_root

    def test_panel_creation(self):
        """Test that ConfigPanel can be created."""
        panel = ConfigPanel(self.root)
        assert panel is not None
        assert isinstance(panel, ttk.Frame)

    def test_has_notebook(self):
        """Test that panel has a notebook widget."""
        panel = ConfigPanel(self.root)
        # Panel should create a notebook for tabs
        notebook = None
        for child in panel.winfo_children():
            if isinstance(child, ttk.Notebook):
                notebook = child
                break
        assert notebook is not None, "ConfigPanel should contain a Notebook widget"

    def test_has_txt2img_tab(self):
        """Test that panel has txt2img tab."""
        panel = ConfigPanel(self.root)
        # Find notebook
        notebook = None
        for child in panel.winfo_children():
            if isinstance(child, ttk.Notebook):
                notebook = child
                break

        assert notebook is not None
        # Check tabs exist
        assert notebook.index("end") >= 1, "Should have at least txt2img tab"


class TestConfigPanelAPI:
    """Test ConfigPanel public API methods."""

    @pytest.fixture(autouse=True)
    def _setup(self, tk_root):
        self.root = tk_root

    def test_get_config(self):
        """Test get_config returns a dictionary."""
        panel = ConfigPanel(self.root)
        config = panel.get_config()
        assert isinstance(config, dict)
        assert "txt2img" in config
        assert "img2img" in config
        assert "upscale" in config

    def test_set_config(self):
        """Test set_config updates panel state."""
        panel = ConfigPanel(self.root)

        test_config = {
            "txt2img": {
                "steps": 30,
                "cfg_scale": 8.5,
                "width": 768,
                "height": 768,
            },
            "img2img": {
                "steps": 20,
                "denoising_strength": 0.4,
            },
            "upscale": {
                "upscaler": "R-ESRGAN 4x+",
            },
        }

        panel.set_config(test_config)

        # Retrieve and verify
        retrieved = panel.get_config()
        assert retrieved["txt2img"]["steps"] == 30
        assert retrieved["txt2img"]["cfg_scale"] == 8.5
        assert retrieved["txt2img"]["width"] == 768

    def test_validate_returns_tuple(self):
        """Test validate returns (ok, messages) tuple."""
        panel = ConfigPanel(self.root)
        result = panel.validate()
        assert isinstance(result, tuple)
        assert len(result) == 2
        ok, messages = result
        assert isinstance(ok, bool)
        assert isinstance(messages, list)


class TestConfigPanelDimensionBounds:
    """Test dimension validation (≤2260)."""

    @pytest.fixture(autouse=True)
    def _setup(self, tk_root):
        self.root = tk_root

    def test_dimension_bounds_warning(self):
        """Test that dimensions >2260 trigger warnings."""
        panel = ConfigPanel(self.root)

        # Set valid config first
        panel.set_config(
            {
                "txt2img": {
                    "width": 1024,
                    "height": 1024,
                }
            }
        )
        ok, messages = panel.validate()
        assert ok is True

        # Now set invalid dimensions
        panel.set_config(
            {
                "txt2img": {
                    "width": 3000,  # Too large
                    "height": 1024,
                }
            }
        )
        ok, messages = panel.validate()
        assert ok is False
        assert any("width" in msg.lower() for msg in messages)
        assert any("2260" in msg for msg in messages)

    def test_max_valid_dimension(self):
        """Test that dimension of exactly 2260 is valid."""
        panel = ConfigPanel(self.root)
        panel.set_config(
            {
                "txt2img": {
                    "width": 2260,
                    "height": 2260,
                }
            }
        )
        ok, messages = panel.validate()
        assert ok is True
        assert len(messages) == 0


class TestConfigPanelHiresSteps:
    """Test hires_steps feature."""

    @pytest.fixture(autouse=True)
    def _setup(self, tk_root):
        self.root = tk_root

    def test_hires_steps_in_config(self):
        """Test that hires_steps can be set and retrieved."""
        panel = ConfigPanel(self.root)

        panel.set_config(
            {
                "txt2img": {
                    "hires_steps": 15,
                    "enable_hr": True,
                }
            }
        )

        config = panel.get_config()
        assert "hires_steps" in config["txt2img"]
        assert config["txt2img"]["hires_steps"] == 15

    def test_hires_steps_default(self):
        """Test default value for hires_steps."""
        panel = ConfigPanel(self.root)
        config = panel.get_config()
        # Should have a default value (usually 0 or same as steps)
        assert "hires_steps" in config["txt2img"]


class TestConfigPanelFaceRestoration:
    """Test face restoration toggle and visibility."""

    @pytest.fixture(autouse=True)
    def _setup(self, tk_root):
        self.root = tk_root

    def test_face_restoration_config(self):
        """Test face restoration can be enabled/disabled."""
        panel = ConfigPanel(self.root)

        # Enable face restoration
        panel.set_config(
            {
                "txt2img": {
                    "face_restoration_enabled": True,
                    "face_restoration_model": "GFPGAN",
                    "face_restoration_weight": 0.5,
                }
            }
        )

        config = panel.get_config()
        assert config["txt2img"]["face_restoration_enabled"] is True
        assert config["txt2img"]["face_restoration_model"] == "GFPGAN"

    def test_face_restoration_default_disabled(self):
        """Test face restoration is disabled by default."""
        panel = ConfigPanel(self.root)
        config = panel.get_config()
        # Face restoration should be off by default
        face_enabled = config["txt2img"].get("face_restoration_enabled", False)
        assert face_enabled is False


class TestConfigPanelRoundTrip:
    """Test configuration round-trip (set -> get -> set)."""

    @pytest.fixture(autouse=True)
    def _setup(self, tk_root):
        self.root = tk_root

    def test_config_round_trip(self):
        """Test that config can be set, retrieved, and set again."""
        panel = ConfigPanel(self.root)

        original_config = {
            "txt2img": {
                "steps": 25,
                "cfg_scale": 7.5,
                "width": 512,
                "height": 768,
                "sampler_name": "DPM++ 2M",
                "seed": 12345,
                "hires_steps": 10,
            },
            "img2img": {
                "steps": 15,
                "denoising_strength": 0.35,
            },
            "upscale": {
                "upscaler": "ESRGAN_4x",
                "scale": 2,
            },
        }

        # Set config
        panel.set_config(original_config)

        # Get config
        retrieved = panel.get_config()

        # Verify key values match
        assert retrieved["txt2img"]["steps"] == 25
        assert retrieved["txt2img"]["cfg_scale"] == 7.5
        assert retrieved["txt2img"]["width"] == 512
        assert retrieved["txt2img"]["height"] == 768
        assert retrieved["txt2img"]["hires_steps"] == 10
        assert retrieved["img2img"]["steps"] == 15

        # Set again
        panel.set_config(retrieved)

        # Get again and verify still matches
        final = panel.get_config()
        assert final["txt2img"]["steps"] == 25
        assert final["txt2img"]["cfg_scale"] == 7.5


class TestConfigPanelOptionSetters:
    """Test option setter methods (set_model_options, etc.)."""

    @pytest.fixture(autouse=True)
    def _setup(self, tk_root):
        self.root = tk_root

    def test_set_model_options_with_valid_widgets(self):
        """Test setting model options updates combobox values."""
        panel = ConfigPanel(self.root)
        models = ["model1.safetensors", "model2.ckpt", "model3.safetensors"]

        # Should not raise an exception
        panel.set_model_options(models)

    def test_set_vae_options_with_valid_widgets(self):
        """Test setting VAE options updates combobox values."""
        panel = ConfigPanel(self.root)
        vae_models = ["vae1.safetensors", "vae2.pt"]

        # Should not raise an exception
        panel.set_vae_options(vae_models)

    def test_set_upscaler_options_with_valid_widgets(self):
        """Test setting upscaler options updates combobox values."""
        panel = ConfigPanel(self.root)
        upscalers = ["R-ESRGAN 4x+", "ESRGAN_4x", "Lanczos"]

        # Should not raise an exception
        panel.set_upscaler_options(upscalers)

    def test_set_scheduler_options_with_valid_widgets(self):
        """Test setting scheduler options updates combobox values."""
        panel = ConfigPanel(self.root)
        schedulers = ["DPM++ 2M", "Euler a", "DDIM"]

        # Should not raise an exception
        panel.set_scheduler_options(schedulers)

    def test_set_combobox_values_with_none_widget(self):
        """Test that _set_combobox_values handles None widget gracefully."""
        panel = ConfigPanel(self.root)

        # Should not raise an exception when widget is None
        panel._set_combobox_values(None, ["option1", "option2"])

    def test_set_combobox_values_with_invalid_widget(self, caplog):
        """Test that _set_combobox_values logs warning for invalid widget."""
        import logging

        panel = ConfigPanel(self.root)

        # Create a widget that doesn't support 'values' attribute
        invalid_widget = tk.Label(self.root, text="Not a combobox")

        with caplog.at_level(logging.WARNING):
            panel._set_combobox_values(invalid_widget, ["option1", "option2"])

        # Should have logged a warning
        assert any("Failed to set combobox values" in record.message for record in caplog.records)
