from typing import Any

from dianshang.domain.state import DialogueState
from dianshang.task.action.base import Action, ActionResult


class ActionCustom(Action):
    """自定义 Action 示例：作为扩展点参考，实际业务 Action 在此包下新增。"""
    name = "action_custom"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        return ActionResult()
