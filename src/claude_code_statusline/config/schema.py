"""Configuration schema using Pydantic for validation."""

from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class WidgetConfigModel(BaseModel):
    """Configuration for a single widget instance."""

    type: str
    id: str = Field(default_factory=lambda: str(uuid4()))
    color: Optional[str] = None
    bold: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)


class StatusLineConfig(BaseModel):
    """Complete status line configuration (v1 - deprecated)."""

    version: int = 1
    lines: list[list[WidgetConfigModel]] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class WidgetOverride(BaseModel):
    """Override settings for a single widget."""

    color: Optional[str] = None
    bold: Optional[bool] = None
    enabled: bool = True


class StatusLineConfigV2(BaseModel):
    """Simplified override-only configuration (v2)."""

    version: Literal[2] = 2
    widgets: dict[str, WidgetOverride] = Field(default_factory=dict)
    order: Optional[list[str]] = None

    model_config = {"extra": "forbid"}
