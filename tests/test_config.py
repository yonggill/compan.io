"""Tests for configuration schema, defaults, and loading."""

import json
from pathlib import Path

import pytest

from companio.config.schema import Config, TelegramConfig, ProviderConfig


class TestConfigDefaults:
    """Verify Config can be instantiated with sane defaults."""

    def test_default_instantiation(self):
        config = Config()
        assert config.agents.defaults.provider == "auto"
        assert config.agents.defaults.model == "anthropic/claude-opus-4-5"
        assert config.agents.defaults.max_tokens == 8192
        assert config.agents.defaults.temperature == 1.0
        assert config.agents.defaults.max_tool_iterations == 40
        assert config.agents.defaults.memory_window == 200
        assert config.agents.defaults.reasoning_effort == "medium"
        assert config.tools.restrict_to_workspace is True

    def test_telegram_config_defaults(self):
        tc = TelegramConfig()
        assert tc.enabled is False
        assert tc.token == ""
        assert tc.allow_from == []
        assert tc.proxy is None
        assert tc.reply_to_message is False

    def test_provider_config_defaults(self):
        pc = ProviderConfig()
        assert pc.api_key == ""
        assert pc.api_base is None
        assert pc.extra_headers is None

    def test_env_prefix(self):
        config = Config()
        assert config.model_config.get("env_prefix") == "COMPANIO_"

    def test_workspace_path_uses_companio(self):
        config = Config()
        assert ".companio" in config.agents.defaults.workspace
        assert ".nanobot" not in config.agents.defaults.workspace

    def test_gateway_defaults(self):
        config = Config()
        assert config.gateway.host == "0.0.0.0"
        assert config.gateway.port == 18790
        assert config.gateway.heartbeat.enabled is True
        assert config.gateway.heartbeat.interval_s == 600

    def test_channels_defaults(self):
        config = Config()
        assert config.channels.send_progress is True
        assert config.channels.send_tool_hints is False


class TestConfigExampleConsistency:
    """Verify config.example.json matches schema defaults."""

    @pytest.fixture()
    def example_config(self) -> dict:
        path = Path(__file__).resolve().parent.parent / "companio" / "templates" / "config.example.json"
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def test_example_validates_against_schema(self, example_config):
        """config.example.json must be loadable by the schema without errors."""
        config = Config.model_validate(example_config)
        assert config.agents.defaults.provider == "auto"

    def test_example_matches_defaults(self, example_config):
        """Key values in config.example.json should equal schema defaults."""
        default = Config()
        loaded = Config.model_validate(example_config)
        assert loaded.agents.defaults.model == default.agents.defaults.model
        assert loaded.agents.defaults.max_tokens == default.agents.defaults.max_tokens
        assert loaded.tools.restrict_to_workspace == default.tools.restrict_to_workspace
        assert loaded.gateway.heartbeat.interval_s == default.gateway.heartbeat.interval_s


class TestConfigLoader:
    """Verify loader helpers."""

    def test_load_dotenv_does_not_crash_on_missing(self, tmp_path):
        from companio.config.loader import load_dotenv_if_exists

        # Should silently do nothing when .env is absent
        load_dotenv_if_exists(tmp_path)

    def test_load_config_from_nonexistent_path(self, tmp_path):
        from companio.config.loader import load_config

        config = load_config(tmp_path / "does_not_exist.json")
        assert config.agents.defaults.provider == "auto"
