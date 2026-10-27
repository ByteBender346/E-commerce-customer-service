from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from dianshang.domain.messages import BotMessage
from dianshang.domain.state import DialogueState


@dataclass
class ActionResult:
    messages: list[BotMessage] = field(default_factory=list)
    slot_updates: dict[str, Any] = field(default_factory=dict)


class Action(ABC):
    """流程动作基类：每个动作有唯一 name，由 ActionRegistry 注册查找。"""
    name: str

    @abstractmethod
    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        pass
