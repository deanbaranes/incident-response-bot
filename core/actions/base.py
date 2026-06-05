from abc import ABC, abstractmethod
from typing import Dict, Any
from core.context import IncidentContext


class ActionHandler(ABC):
    @abstractmethod
    async def execute(
        self, action: Dict[str, Any], context: IncidentContext, alert: Dict[str, Any]
    ):
        """Execute the action and modify the context accordingly."""
        pass
