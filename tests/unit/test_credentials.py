"""Unit tests for credentials utility."""

import json

from claude_code_statusline.utils.credentials import (
    read_subscription_info,
)


class TestReadSubscriptionInfo:
    """Tests for read_subscription_info function."""

    def test_reads_pro_subscription(self, tmp_path, monkeypatch):
        credentials = {
            "claudeAiOauth": {
                "subscriptionType": "pro",
                "rateLimitTier": "default_claude_ai",
            }
        }
        creds_file = tmp_path / ".claude" / ".credentials.json"
        creds_file.parent.mkdir(parents=True)
        creds_file.write_text(json.dumps(credentials))

        monkeypatch.setattr(
            "claude_code_statusline.utils.credentials.get_credentials_path",
            lambda: creds_file,
        )
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        result = read_subscription_info()
        assert result.is_subscription is True
        assert result.subscription_type == "pro"
        assert result.rate_limit_tier == "default_claude_ai"

    def test_reads_max_subscription(self, tmp_path, monkeypatch):
        credentials = {
            "claudeAiOauth": {
                "subscriptionType": "max",
                "rateLimitTier": "default_claude_ai",
            }
        }
        creds_file = tmp_path / ".claude" / ".credentials.json"
        creds_file.parent.mkdir(parents=True)
        creds_file.write_text(json.dumps(credentials))

        monkeypatch.setattr(
            "claude_code_statusline.utils.credentials.get_credentials_path",
            lambda: creds_file,
        )
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        result = read_subscription_info()
        assert result.is_subscription is True
        assert result.subscription_type == "max"

    def test_returns_api_usage_when_no_oauth(self, tmp_path, monkeypatch):
        credentials = {"someOtherKey": "value"}
        creds_file = tmp_path / ".claude" / ".credentials.json"
        creds_file.parent.mkdir(parents=True)
        creds_file.write_text(json.dumps(credentials))

        monkeypatch.setattr(
            "claude_code_statusline.utils.credentials.get_credentials_path",
            lambda: creds_file,
        )
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        result = read_subscription_info()
        assert result.is_subscription is False
        assert result.subscription_type is None

    def test_returns_default_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "claude_code_statusline.utils.credentials.get_credentials_path",
            lambda: tmp_path / "nonexistent.json",
        )
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        result = read_subscription_info()
        assert result.is_subscription is False

    def test_handles_malformed_json(self, tmp_path, monkeypatch):
        creds_file = tmp_path / ".credentials.json"
        creds_file.write_text("not valid json")

        monkeypatch.setattr(
            "claude_code_statusline.utils.credentials.get_credentials_path",
            lambda: creds_file,
        )
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        result = read_subscription_info()
        assert result.is_subscription is False

    def test_handles_oauth_data_not_dict(self, tmp_path, monkeypatch):
        credentials = {"claudeAiOauth": "not a dict"}
        creds_file = tmp_path / ".claude" / ".credentials.json"
        creds_file.parent.mkdir(parents=True)
        creds_file.write_text(json.dumps(credentials))

        monkeypatch.setattr(
            "claude_code_statusline.utils.credentials.get_credentials_path",
            lambda: creds_file,
        )
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        result = read_subscription_info()
        assert result.is_subscription is False

    def test_returns_api_usage_when_console_api_key_set(self, tmp_path, monkeypatch):
        """Test that console API key (sk-ant-api) returns API usage."""
        credentials = {
            "claudeAiOauth": {
                "subscriptionType": "pro",
                "rateLimitTier": "default_claude_ai",
            }
        }
        creds_file = tmp_path / ".claude" / ".credentials.json"
        creds_file.parent.mkdir(parents=True)
        creds_file.write_text(json.dumps(credentials))

        monkeypatch.setattr(
            "claude_code_statusline.utils.credentials.get_credentials_path",
            lambda: creds_file,
        )
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-abcdef123456")

        result = read_subscription_info()
        assert result.is_subscription is False
        assert result.subscription_type is None

    def test_falls_through_when_oauth_token_set(self, tmp_path, monkeypatch):
        """Test that OAuth token (sk-ant-oat) falls through to credentials check."""
        credentials = {
            "claudeAiOauth": {
                "subscriptionType": "max",
                "rateLimitTier": "default_claude_ai",
            }
        }
        creds_file = tmp_path / ".claude" / ".credentials.json"
        creds_file.parent.mkdir(parents=True)
        creds_file.write_text(json.dumps(credentials))

        monkeypatch.setattr(
            "claude_code_statusline.utils.credentials.get_credentials_path",
            lambda: creds_file,
        )
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-oat01-xyz789")

        result = read_subscription_info()
        assert result.is_subscription is True
        assert result.subscription_type == "max"
