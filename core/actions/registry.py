import logging
from typing import Dict
from core.actions.base import ActionHandler

logger = logging.getLogger(__name__)


class ActionRegistry:
    _handlers: Dict[str, ActionHandler] = {}

    @classmethod
    def register(cls, action_type: str, handler: ActionHandler):
        cls._handlers[action_type] = handler

    @classmethod
    def get_handler(cls, action_type: str) -> ActionHandler | None:
        return cls._handlers.get(action_type)
