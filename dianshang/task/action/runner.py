from dataclasses import dataclass, field
from typing import Any

from dianshang.domain.state import DialogueState
from dianshang.task.action.base import Action, ActionResult
from dianshang.task.action.registry import ActionRegistry


@dataclass
class ActionCall:
    action_name: str
    action_kwargs: dict[str, Any] = field(default_factory=dict)


class ActionRunner:
    """根据 ActionCall 从注册中心查找对应 Action 并执行。"""

    def __init__(self, registry: ActionRegistry):
        self.registry = registry

    async def run(self, action_call: ActionCall, state: DialogueState) -> ActionResult:
        action = self.registry.get(action_call.action_name)
        return await action.run(state, action_call.action_kwargs)
