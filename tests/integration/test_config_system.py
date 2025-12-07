"""Integration tests for configuration system."""

import pytest
import yaml

from claude_code_statusline.config.defaults import get_default_config
from claude_code_statusline.config.loader import (
    get_effective_widgets,
    load_config_file,
    save_config,
)
from claude_code_statusline.config.schema import (
    StatusLineConfigV2,
    WidgetOverride,
)


@pytest.fixture
def temp_config_dir(monkeypatch, tmp_path):
    """Create a temporary config directory."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return tmp_path


class TestConfigV2Loading:
    """Tests for v2 configuration loading."""

    def test_returns_empty_config_when_missing(self, temp_config_dir):
        """Test that empty config is returned when file doesn't exist."""
        config = load_config_file()

        assert isinstance(config, StatusLineConfigV2)
        assert config.version == 2
        assert config.widgets == {}
        assert config.order is None

    def test_loads_v2_config(self, temp_config_dir):
        """Test loading a v2 configuration file."""
        config_file = temp_config_dir / "claude-statusline" / "config.yaml"
        config_file.parent.mkdir(parents=True)

        config_data = {
            "version": 2,
            "widgets": {
                "model": {"color": "magenta"},
                "directory": {"enabled": False},
            },
        }
        config_file.write_text(yaml.dump(config_data))

        config = load_config_file()

        assert config.version == 2
        assert config.widgets["model"].color == "magenta"
        assert config.widgets["directory"].enabled is False

    def test_deletes_v1_config(self, temp_config_dir):
        """Test that v1 configs are deleted."""
        config_file = temp_config_dir / "claude-statusline" / "config.yaml"
        config_file.parent.mkdir(parents=True)

        v1_config = {
            "version": 1,
            "lines": [[{"type": "model"}, {"type": "directory"}]],
        }
        config_file.write_text(yaml.dump(v1_config))

        config = load_config_file()

        assert not config_file.exists()
        assert config.version == 2
        assert config.widgets == {}


class TestEffectiveWidgets:
    """Tests for get_effective_widgets()."""

    def test_returns_defaults_when_no_config(self, temp_config_dir):
        """Test that defaults are returned with no config."""
        widgets = get_effective_widgets()

        widget_types = [w.type for w in widgets if w.type != "separator"]

        assert "model" in widget_types
        assert "directory" in widget_types
        assert "subscription" in widget_types

    def test_applies_color_override(self, temp_config_dir):
        """Test that color overrides are applied."""
        config_file = temp_config_dir / "claude-statusline" / "config.yaml"
        config_file.parent.mkdir(parents=True)

        config_data = {
            "version": 2,
            "widgets": {"model": {"color": "red"}},
        }
        config_file.write_text(yaml.dump(config_data))

        widgets = get_effective_widgets()

        model_widget = next(w for w in widgets if w.type == "model")
        assert model_widget.color == "red"

    def test_hides_disabled_widgets(self, temp_config_dir):
        """Test that disabled widgets are hidden."""
        config_file = temp_config_dir / "claude-statusline" / "config.yaml"
        config_file.parent.mkdir(parents=True)

        config_data = {
            "version": 2,
            "widgets": {"subscription": {"enabled": False}},
        }
        config_file.write_text(yaml.dump(config_data))

        widgets = get_effective_widgets()

        widget_types = [w.type for w in widgets if w.type != "separator"]
        assert "subscription" not in widget_types
        assert "model" in widget_types

    def test_custom_order(self, temp_config_dir):
        """Test custom widget ordering."""
        config_file = temp_config_dir / "claude-statusline" / "config.yaml"
        config_file.parent.mkdir(parents=True)

        config_data = {
            "version": 2,
            "order": ["directory", "model"],
        }
        config_file.write_text(yaml.dump(config_data))

        widgets = get_effective_widgets()

        widget_types = [w.type for w in widgets if w.type != "separator"]
        assert widget_types == ["directory", "model"]

    def test_interleaves_separators(self, temp_config_dir):
        """Test that separators are properly interleaved."""
        widgets = get_effective_widgets()

        for i in range(len(widgets) - 1):
            if i % 2 == 0:
                assert widgets[i].type != "separator"
            else:
                assert widgets[i].type == "separator"


class TestDefaultConfig:
    """Tests for default configuration."""

    def test_default_config_structure(self):
        """Test that default config has expected structure."""
        config = get_default_config()

        assert config.version == 1
        assert len(config.lines) > 0
        assert len(config.lines[0]) > 0

    def test_subscription_at_end(self):
        """Test that subscription widget is at the end."""
        config = get_default_config()

        widget_types = [w.type for w in config.lines[0] if w.type != "separator"]

        assert widget_types[-1] == "subscription"


class TestConfigSaving:
    """Tests for configuration saving."""

    def test_saves_v2_config(self, temp_config_dir):
        """Test saving v2 configuration."""
        config = StatusLineConfigV2(widgets={"model": WidgetOverride(color="magenta")})

        save_config(config)

        config_file = temp_config_dir / "claude-statusline" / "config.yaml"
        assert config_file.exists()

        with open(config_file) as f:
            saved_data = yaml.safe_load(f)

        assert saved_data["version"] == 2
        assert saved_data["widgets"]["model"]["color"] == "magenta"
