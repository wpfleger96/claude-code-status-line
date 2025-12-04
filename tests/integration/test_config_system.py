"""Integration tests for configuration system."""

import pytest
import yaml

from pydantic import ValidationError

from claude_code_statusline.config.defaults import get_default_config
from claude_code_statusline.config.loader import load_config, save_config
from claude_code_statusline.config.schema import (
    StatusLineConfig,
    WidgetConfigModel,
)


@pytest.fixture
def temp_config_dir(monkeypatch, tmp_path):
    """Create a temporary config directory."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    return tmp_path


@pytest.fixture
def sample_config():
    """Create a sample configuration."""
    return StatusLineConfig(
        version=1,
        lines=[
            [
                WidgetConfigModel(type="model", color="cyan"),
                WidgetConfigModel(type="separator"),
                WidgetConfigModel(type="directory", color="blue"),
            ]
        ],
    )


class TestConfigLoading:
    """Tests for configuration loading."""

    def test_creates_default_config_when_missing(self, temp_config_dir):
        """Test that default config is created when file doesn't exist."""
        config = load_config()

        assert isinstance(config, StatusLineConfig)
        assert config.version == 1
        assert len(config.lines) > 0
        assert len(config.lines[0]) > 0

        config_file = temp_config_dir / "claude-statusline" / "config.yaml"
        assert config_file.exists()

    def test_loads_existing_config(self, temp_config_dir, sample_config):
        """Test loading an existing configuration file."""

        save_config(sample_config)

        loaded_config = load_config()

        assert loaded_config.version == sample_config.version
        assert len(loaded_config.lines) == len(sample_config.lines)
        assert loaded_config.lines[0][0].type == "model"
        assert loaded_config.lines[0][0].color == "cyan"

    def test_handles_invalid_yaml(self, temp_config_dir):
        """Test that invalid YAML falls back to defaults."""

        config_dir = temp_config_dir / "claude-statusline"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("invalid: yaml: content: [[[")

        config = load_config()
        assert isinstance(config, StatusLineConfig)
        assert config.version == 1

    def test_handles_invalid_schema(self, temp_config_dir):
        """Test that invalid schema falls back to defaults."""

        config_dir = temp_config_dir / "claude-statusline"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.yaml"

        invalid_config = {"version": "not-a-number", "lines": "not-a-list"}
        with open(config_file, "w") as f:
            yaml.dump(invalid_config, f)

        config = load_config()
        assert isinstance(config, StatusLineConfig)
        assert isinstance(config.version, int)


class TestConfigSaving:
    """Tests for configuration saving."""

    def test_saves_config_to_yaml(self, temp_config_dir, sample_config):
        """Test saving configuration to YAML file."""

        save_config(sample_config)

        config_file = temp_config_dir / "claude-statusline" / "config.yaml"
        assert config_file.exists()

        with open(config_file) as f:
            yaml_data = yaml.safe_load(f)

        assert yaml_data["version"] == 1
        assert len(yaml_data["lines"]) == 1
        assert len(yaml_data["lines"][0]) == 3
        assert yaml_data["lines"][0][0]["type"] == "model"

    def test_creates_config_directory(self, temp_config_dir, sample_config):
        """Test that config directory is created if it doesn't exist."""

        config_dir = temp_config_dir / "claude-statusline"
        if config_dir.exists():
            import shutil

            shutil.rmtree(config_dir)

        save_config(sample_config)

        assert config_dir.exists()
        assert (config_dir / "config.yaml").exists()

    def test_overwrites_existing_config(self, temp_config_dir, sample_config):
        """Test that saving overwrites existing configuration."""

        save_config(sample_config)

        sample_config.lines[0].append(WidgetConfigModel(type="cost", color="green"))
        save_config(sample_config)

        loaded = load_config()
        assert len(loaded.lines[0]) == 4
        assert loaded.lines[0][3].type == "cost"


class TestDefaultConfig:
    """Tests for default configuration generation."""

    def test_default_config_structure(self):
        """Test that default config has expected structure."""
        config = get_default_config()

        assert config.version == 1
        assert len(config.lines) > 0
        assert len(config.lines[0]) > 0

    def test_default_config_has_essential_widgets(self):
        """Test that default config includes essential widgets."""
        config = get_default_config()

        widget_types = [w.type for w in config.lines[0]]

        assert "model" in widget_types
        assert "directory" in widget_types
        assert "context-percentage" in widget_types or "context-tokens" in widget_types


class TestConfigSchema:
    """Tests for configuration schema validation."""

    def test_allows_empty_lines(self):
        """Test that empty lines are allowed."""
        config = StatusLineConfig(version=1, lines=[[]])

        assert len(config.lines) == 1
        assert len(config.lines[0]) == 0

    def test_forbids_extra_fields(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError):
            StatusLineConfig(
                version=1,
                lines=[[]],
                extra_field="not allowed",  # type: ignore[call-arg]
            )
