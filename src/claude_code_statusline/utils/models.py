"""Model information and context limit utilities."""

import json
import os
import tempfile
import threading
import time
import urllib.error
import urllib.request

from dataclasses import dataclass
from typing import Any, Optional, cast

from ..types import RenderContext


@dataclass
class ModelInfo:
    """Information about a specific model."""

    display_name: str
    context_limit: int


CACHE_FILE_NAME = "claude_code_model_data_cache.json"
CACHE_FILE = os.path.join(tempfile.gettempdir(), CACHE_FILE_NAME)
CACHE_TTL_SECONDS = 604800  # 1 week (7 days)

DEFAULT_SYSTEM_OVERHEAD_TOKENS = 21400

MODEL_INFO: dict[str, ModelInfo] = {
    "default": ModelInfo("Unknown Model", 200000),
    "claude": ModelInfo("Claude", 200000),
    "claude-sonnet-4": ModelInfo("Sonnet 4", 200000),
    "claude-sonnet-4-20250514": ModelInfo("Sonnet 4", 200000),
    "claude-sonnet-4-20250514[1m]": ModelInfo("Sonnet 4 (1M context)", 1000000),
    "claude-sonnet-4-5-20250929": ModelInfo("Sonnet 4.5", 200000),
    "claude-sonnet-4-5-20250929[1m]": ModelInfo("Sonnet 4.5 (1M context)", 1000000),
    "claude-opus-4": ModelInfo("Opus 4", 200000),
    "claude-opus-4.1": ModelInfo("Opus 4.1", 200000),
    "claude-opus-4-1": ModelInfo("Opus 4.1", 200000),
    "claude-opus-4-1-20250805": ModelInfo("Opus 4.1", 200000),
    "claude-opus-4.5": ModelInfo("Opus 4.5", 200000),
    "claude-opus-4-5": ModelInfo("Opus 4.5", 200000),
    "claude-opus-4-5-20251101": ModelInfo("Opus 4.5", 200000),
    "gemini": ModelInfo("Gemini", 1000000),
    "gpt-4": ModelInfo("GPT-4", 8192),
    "gpt-4-32k": ModelInfo("GPT-4 32K", 32768),
    "gpt-4-turbo": ModelInfo("GPT-4 Turbo", 128000),
    "gpt-4o": ModelInfo("GPT-4o", 128000),
    "gpt-4o-mini": ModelInfo("GPT-4o mini", 128000),
    "gpt-5": ModelInfo("GPT-5", 400000),
}


def extract_token_limit(model_info: dict[str, Any]) -> Optional[int]:
    """Extract token limit from model info dictionary."""
    limit = model_info.get("max_input_tokens") or model_info.get("max_tokens")
    return int(limit) if limit else None


def get_cached_or_fetch_data() -> Optional[dict[str, Any]]:
    """Get model data from cache or fetch from API if cache is expired or does not exist."""
    try:
        if os.path.exists(CACHE_FILE):
            cache_age = time.time() - os.path.getmtime(CACHE_FILE)
            if cache_age <= CACHE_TTL_SECONDS:
                with open(CACHE_FILE) as f:
                    return cast(dict[str, Any], json.load(f))
    except (OSError, json.JSONDecodeError):
        pass

    url = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            try:
                with open(CACHE_FILE, "w") as f:
                    json.dump(data, f)
            except OSError:
                pass
            return cast(dict[str, Any], data)
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        json.JSONDecodeError,
        TimeoutError,
    ):
        return None


def _is_cache_stale() -> bool:
    """Check if the model data cache is stale or missing."""
    try:
        if not os.path.exists(CACHE_FILE):
            return True
        cache_age = time.time() - os.path.getmtime(CACHE_FILE)
        return cache_age > CACHE_TTL_SECONDS
    except OSError:
        return True


def _maybe_refresh_cache_background() -> None:
    """Refresh model cache in background if stale (non-blocking)."""
    if _is_cache_stale():
        # Fire and forget - don't wait for result
        thread = threading.Thread(target=get_cached_or_fetch_data, daemon=True)
        thread.start()


# Module-level cache for prefetched model data
_prefetched_model_data = None
_prefetch_done = False


def prefetch_model_data() -> None:
    """Prefetch model data in background thread for parallel execution."""
    global _prefetched_model_data, _prefetch_done
    _prefetched_model_data = get_cached_or_fetch_data()
    _prefetch_done = True


def get_context_limit(model_id: str, model_name: str = "") -> int:
    """Get context limit for model, checking hardcoded limits first for speed.

    Args:
        model_id: Model identifier (e.g., "claude-sonnet-4-5-20250929")
        model_name: Optional display name

    Returns:
        Context limit in tokens
    """
    if not model_id:
        return MODEL_INFO["default"].context_limit

    # Fast path: check for 1M context markers
    if "[1m]" in model_id.lower():
        return 1000000

    if model_name and "1m" in model_name.lower():
        return 1000000

    # Fast path: check hardcoded MODEL_INFO first (instant for known models)
    model_lower = model_id.lower()

    if model_lower in MODEL_INFO:
        _maybe_refresh_cache_background()  # Non-blocking cache refresh
        return MODEL_INFO[model_lower].context_limit

    for key in sorted(MODEL_INFO.keys(), key=len, reverse=True):
        if key != "default" and (model_lower in key or key in model_lower):
            _maybe_refresh_cache_background()  # Non-blocking cache refresh
            return MODEL_INFO[key].context_limit

    # Unknown model - check API data
    # Use prefetched data if available, otherwise fetch (may block)
    global _prefetched_model_data, _prefetch_done
    if _prefetch_done:
        api_data = _prefetched_model_data
    else:
        api_data = get_cached_or_fetch_data()

    if api_data:
        if model_id in api_data:
            limit = extract_token_limit(api_data[model_id])
            if limit:
                return limit

        if model_lower in api_data:
            limit = extract_token_limit(api_data[model_lower])
            if limit:
                return limit

        for key in sorted(api_data.keys(), key=len, reverse=True):
            key_lower = key.lower()
            if model_lower in key_lower or key_lower in model_lower:
                limit = extract_token_limit(api_data[key])
                if limit:
                    return limit

    return MODEL_INFO["default"].context_limit


def get_context_limit_for_render(context: RenderContext) -> int:
    """Get context limit from render context's model data.

    Args:
        context: RenderContext with data containing model information

    Returns:
        Context limit for the model in the render context
    """
    model = context.data.get("model", {})
    model_id = model.get("id", "")
    model_name = model.get("display_name", "")
    return get_context_limit(model_id, model_name)
