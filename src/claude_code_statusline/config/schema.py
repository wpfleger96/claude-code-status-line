"""Configuration schema using Pydantic for validation."""

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class WidgetConfigModel(BaseModel):
    """Configuration for a single widget instance."""

    type: str
    id: str = Field(default_factory=lambda: str(uuid4()))
    color: str | None = None
    bold: bool = False
    priority: int | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class WidgetOverride(BaseModel):
    """Override settings for a single widget."""

    color: str | None = None
    bold: bool | None = None
    priority: int | None = None
    enabled: bool = True


class TerminalTitleConfig(BaseModel):
    """Configuration for terminal tab title emission."""

    enabled: bool = False


class StatusLineConfigV2(BaseModel):
    """Simplified override-only configuration (v2)."""

    version: Literal[2] = 2
    widgets: dict[str, WidgetOverride] = Field(default_factory=dict)
    order: list[str] | None = None
    terminal_title: TerminalTitleConfig = Field(default_factory=TerminalTitleConfig)

    model_config = {"extra": "forbid"}
