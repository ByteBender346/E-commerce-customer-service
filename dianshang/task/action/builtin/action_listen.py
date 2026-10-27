from typing import Any

from dianshang.domain.state import DialogueState
from dianshang.task.action.base import Action, ActionResult


class ActionListen(Action):
    """停止信号：流程等待用户下一轮输入，外层循环退出。"""
    name = "action_listen"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        return ActionResult()
