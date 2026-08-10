from abc import ABC, abstractmethod
from typing import Any

from core.context import IncidentContext


class ActionHandler(ABC):
    @abstractmethod
    async def execute(
        self, action: dict[str, Any], context: IncidentContext, alert: dict[str, Any]
    ):
        """Execute the action and modify the context accordingly."""
        pass
