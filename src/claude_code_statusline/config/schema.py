"""Configuration schema using Pydantic for validation."""

from typing import Optional
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
    """Complete status line configuration."""

    version: int = 1
    lines: list[list[WidgetConfigModel]] = Field(default_factory=list)

    model_config = {"extra": "forbid"}
