"""Subscription status widget."""

from typing import Optional

from ...config.schema import WidgetConfigModel
from ...types import RenderContext
from ..base import Widget
from ..registry import register_widget


@register_widget(
    "subscription",
    display_name="Subscription",
    default_color="cyan",
    description="Claude subscription type (Pro/Max) or API usage indicator",
    fallback_text="Unknown",
)
class SubscriptionWidget(Widget):
    """Display subscription type or API usage."""

    def render(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Render subscription status."""
        if not context.subscription_info:
            return None

        info = context.subscription_info

        if not info.is_subscription:
            return "API usage"

        if info.subscription_type:
            return info.subscription_type.capitalize()

        return "Subscription"
