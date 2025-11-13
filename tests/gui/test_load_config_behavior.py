"""Tests for Load Pack Config and Load Preset functionality."""
import json
from unittest.mock import Mock

import pytest

from src.gui.main_window import StableNewGUI
from src.services.config_service import ConfigService


@pytest.fixture
def mock_config_service(tmp_path):
    """Create a mock config service with test data."""
    service = ConfigService(
        packs_dir=tmp_path / "packs",
        presets_dir=tmp_path / "presets",
        lists_dir=tmp_path / "lists"
    )

    # Create test pack config
    pack_config = {
        "txt2img": {
            "steps": 25,
            "sampler_name": "Euler",
            "cfg_scale": 7.0,
            "width": 512,
            "height": 512
        }
    }
    pack_path = service.packs_dir / "test_pack.json"
    pack_path.parent.mkdir(parents=True, exist_ok=True)
    with open(pack_path, "w") as f:
        json.dump(pack_config, f)

    # Create test preset
    preset_config = {
        "txt2img": {
            "steps": 30,
            "sampler_name": "DPM++ 2M",
            "cfg_scale": 8.0,
            "width": 1024,
            "height": 1024
        }
    }
    preset_path = service.presets_dir / "test_preset.json"
    preset_path.parent.mkdir(parents=True, exist_ok=True)
    with open(preset_path, "w") as f:
        json.dump(preset_config, f)

    return service


@pytest.fixture
def minimal_app(tk_root, mock_config_service):
    """Create a minimal app instance for testing."""
    app = StableNewGUI(tk_root)
    app.config_service = mock_config_service

    # Mock the components we need
    app.config_panel = Mock()
    app.config_panel.set_config = Mock()

    # Initialize required attributes
    app.current_selected_packs = []
    app.preset_combobox = Mock()
    app.preset_combobox.get.return_value = "test_preset"

    return app


def test_pack_selection_does_not_change_editor(minimal_app):
    """Test that selecting packs does not auto-load config into editor."""
    # Initially, config_panel.set_config should not have been called
    minimal_app.config_panel.set_config.assert_not_called()

    # Simulate pack selection
    minimal_app._on_pack_selection_changed_mediator(["test_pack"])

    # config_panel.set_config should still not have been called
    minimal_app.config_panel.set_config.assert_not_called()

    # But the selected packs should be updated
    assert minimal_app.selected_packs == ["test_pack"]
    assert minimal_app.current_selected_packs == ["test_pack"]


def test_load_pack_config_updates_editor_and_banner(minimal_app):
    """Test that Load Pack Config updates the editor and banner."""
    # Set up pack selection
    minimal_app.current_selected_packs = ["test_pack"]

    # Call load pack config
    minimal_app._ui_load_pack_config()

    # Should have called config_panel.set_config with the pack config
    minimal_app.config_panel.set_config.assert_called_once()
    called_config = minimal_app.config_panel.set_config.call_args[0][0]

    # Verify the config contains expected values
    assert called_config["txt2img"]["steps"] == 25
    assert called_config["txt2img"]["sampler_name"] == "Euler"

    # Banner should be updated
    assert minimal_app.config_source_banner.cget("text") == "Using: Pack Config (view)"


def test_load_preset_updates_editor_and_banner(minimal_app):
    """Test that Load Preset updates the editor and banner."""
    # Call load preset
    minimal_app._ui_load_preset()

    # Should have called config_panel.set_config with the preset config
    minimal_app.config_panel.set_config.assert_called_once()
    called_config = minimal_app.config_panel.set_config.call_args[0][0]

    # Verify the config contains expected values
    assert called_config["txt2img"]["steps"] == 30
    assert called_config["txt2img"]["sampler_name"] == "DPM++ 2M"

    # Banner should be updated
    assert minimal_app.config_source_banner.cget("text") == "Using: Preset: test_preset"


def test_load_pack_config_requires_selection(minimal_app):
    """Test that Load Pack Config does nothing when no pack is selected."""
    # No pack selected
    minimal_app.current_selected_packs = []

    # Call load pack config
    minimal_app._ui_load_pack_config()

    # Should not have called config_panel.set_config
    minimal_app.config_panel.set_config.assert_not_called()

    # Banner should remain unchanged
    assert minimal_app.config_source_banner.cget("text") == "Using: Pack Config"


def test_load_preset_requires_selection(minimal_app):
    """Test that Load Preset does nothing when no preset is selected."""
    # No preset selected
    minimal_app.preset_combobox.get.return_value = ""

    # Call load preset
    minimal_app._ui_load_preset()

    # Should not have called config_panel.set_config
    minimal_app.config_panel.set_config.assert_not_called()

    # Banner should remain unchanged
    assert minimal_app.config_source_banner.cget("text") == "Using: Pack Config"


def test_initial_banner_is_pack_config(minimal_app):
    """Test that the initial banner shows 'Using: Pack Config'."""
    # The banner should be set during initialization
    assert minimal_app.config_source_banner.cget("text") == "Using: Pack Config"
