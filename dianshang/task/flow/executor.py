from dataclasses import asdict

from dianshang.domain.contexts import CollectSystemContext
from dianshang.domain.messages import BotMessage
from dianshang.domain.state import DialogueState
from dianshang.task.action.base import ActionResult
from dianshang.task.action.runner import ActionCall, ActionRunner
# noqa: F401  (ActionResult used as type annotation)
from dianshang.task.flow.links import StaticLink, ConditionalLink, FallbackLink
from dianshang.task.flow.models import FlowsList, Flow
from dianshang.task.flow.steps import (
    FlowStep, StartFlowStep, CollectSlotStep, EndFlowStep, ActionFlowStep,
)


class FlowExecutor:
    """
    流程推进器：双层循环。
    - 外层：不断取出 ActionCall 并执行，直到遇到 action_listen（等待用户输入）。
    - 内层：在流程节点间导航，跳过 start/end，处理 collect 槽位收集，直到遇到 action 节点。
    """

    async def run_task(self, state: DialogueState, action_runner: ActionRunner,
                       flows: FlowsList) -> list[BotMessage]:
        messages: list[BotMessage] = []
        while True:
            action_call = self._advance_until_action(state, flows)
            if action_call.action_name == "action_listen":
                break
            action_result = await action_runner.run(action_call, state)
            state.set_slots(action_result.slot_updates)
            messages.extend(action_result.messages)
        return messages

    def _advance_until_action(self, state: DialogueState, flows: FlowsList) -> ActionCall:
        """在内层循环中推进流程节点，直到返回一个 ActionCall。"""
        while True:
            current_task = state.current_task()
            if current_task is None:
                return ActionCall(action_name="action_listen")

            flow = flows.get_flow_by_id(current_task.flow_id)
            step = flow.get_step_by_id(current_task.step_id)
            action_call = self._run_step(state, step, flows)
            if action_call is not None:
                return action_call

    def _run_step(self, state: DialogueState, step: FlowStep, flows: FlowsList) -> ActionCall | None:
        if isinstance(step, StartFlowStep):
            self._advance_to_next_step(step, state)
            return None
        if isinstance(step, EndFlowStep):
            self._run_end_step(state)
            return None
        if isinstance(step, CollectSlotStep):
            return self._run_collect_step(step, state, flows)
        if isinstance(step, ActionFlowStep):
            return self._run_action_step(step, state)
        return None

    def _advance_to_next_step(self, step: FlowStep, state: DialogueState):
        next_step_id = self._select_next_step(step, state)
        state.current_task().step_id = next_step_id

    def _select_next_step(self, step: FlowStep, state: DialogueState) -> str | None:
        for link in step.next:
            if isinstance(link, StaticLink):
                return link.target
            if isinstance(link, ConditionalLink):
                # 条件表达式在 YAML 中以 Python 表达式编写，如 slots.get('refund_reason')
                data = {"slots": state.active_task.slots if state.active_task else {},
                        "context": asdict(state.current_task())}
                if eval(link.condition, {}, data):
                    return link.target
            if isinstance(link, FallbackLink):
                return link.target
        return None

    def _run_end_step(self, state: DialogueState):
        if state.active_system_flow:
            state.end_system_task()
        elif state.active_task:
            state.end_active_task()

    def _run_collect_step(self, step: CollectSlotStep, state: DialogueState,
                          flows: FlowsList) -> ActionCall | None:
        # 先尝试从焦点对象自动填充槽位
        self._try_fill_slot_from_focused_object(step, state)

        if state.active_task.slots.get(step.slot_name):
            # 槽位已有值，执行校验
            if step.validation:
                if self._eval_condition(step.validation.condition, state):
                    self._advance_to_next_step(step, state)
                    return None
                else:
                    state.remove_slot(step.slot_name)
                    if step.validation.failure_response:
                        return ActionCall(
                            action_name="action_response",
                            action_kwargs=asdict(step.validation.failure_response),
                        )
                    return None
            self._advance_to_next_step(step, state)
            return None

        # 槽位缺失：激活系统收集流程，等待用户输入
        state.start_system_task(CollectSystemContext(
            flow_id="system_collect_information",
            step_id=flows.get_flow_by_id("system_collect_information").start_step().id,
            slot_name=step.slot_name,
            response=asdict(step.response),
        ))
        return None

    @staticmethod
    def _eval_condition(condition: str, state: DialogueState) -> bool:
        data = {"slots": state.active_task.slots if state.active_task else {},
                "context": asdict(state.current_task())}
        return eval(condition, {}, data)

    def _run_action_step(self, step: ActionFlowStep, state: DialogueState) -> ActionCall:
        self._advance_to_next_step(step, state)
        return self._build_action_call(step, state)

    @staticmethod
    def _build_action_call(step: ActionFlowStep, state: DialogueState) -> ActionCall:
        args = step.args
        # 系统流程中 args 可能是字符串引用，如 context.response
        if isinstance(args, str):
            args = asdict(state.current_task())[args.split(".")[1]]
        return ActionCall(action_name=step.action, action_kwargs=args)

    @staticmethod
    def _try_fill_slot_from_focused_object(step: CollectSlotStep, state: DialogueState):
        """用户点击订单/商品卡片时，自动填充对应槽位值。"""
        fo = state.focused_object
        if fo is None:
            return
        if (fo.type == "order" and step.slot_name == "order_number") or \
           (fo.type == "product" and step.slot_name == "product_id"):
            state.set_slots({step.slot_name: fo.id})


if __name__ == '__main__':
    print("条件表达式求值示例：", eval("a < b", {}, {"a": 1, "b": 2}))
