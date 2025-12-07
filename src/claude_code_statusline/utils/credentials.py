"""Utilities for reading Claude credentials and subscription info."""

import json
import os

from pathlib import Path

from ..types import SubscriptionInfo

__all__ = ["SubscriptionInfo", "get_credentials_path", "read_subscription_info"]


def get_credentials_path() -> Path:
    """Get path to Claude credentials file."""
    return Path.home() / ".claude" / ".credentials.json"


def read_subscription_info() -> SubscriptionInfo:
    """Read subscription info from Claude credentials.

    Returns:
        SubscriptionInfo with subscription details, or defaults if unavailable
    """
    # Check ANTHROPIC_API_KEY for console API key (not OAuth token)
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if api_key.startswith("sk-ant-api"):
        return SubscriptionInfo(is_subscription=False)

    # OAuth tokens (sk-ant-oat) or no env var: check credentials file
    credentials_path = get_credentials_path()

    if not credentials_path.exists():
        return SubscriptionInfo()

    try:
        with open(credentials_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return SubscriptionInfo()

    oauth_data = data.get("claudeAiOauth")
    if oauth_data and isinstance(oauth_data, dict):
        return SubscriptionInfo(
            is_subscription=True,
            subscription_type=oauth_data.get("subscriptionType"),
            rate_limit_tier=oauth_data.get("rateLimitTier"),
        )

    return SubscriptionInfo(is_subscription=False)
