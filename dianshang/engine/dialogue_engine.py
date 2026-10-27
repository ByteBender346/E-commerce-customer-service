import time

from dianshang.chitchat.handler import ChitChatHandler
from dianshang.clarify.responder import ClarifyResponder
from dianshang.domain.contexts import CollectSystemContext
from dianshang.domain.messages import UserMessage, ProcessResult, MessageType, BotMessage
from dianshang.domain.state import DialogueState, FocusedObject
from dianshang.knowledge.handler import KnowledgeHandler
from dianshang.plan.models import TurnPlan, TurnPlanValidationResult, ClarifyReason
from dianshang.plan.turn_planner import TurnPlanner
from dianshang.plan.validator import TurnPlanValidator
from dianshang.task.command.models import Command, SetSlotsCommand
from dianshang.task.flow.models import FlowsList, Flow
from dianshang.task.flow.steps import FlowStep, CollectSlotStep
from dianshang.task.handler import TaskHandler

SESSION_TTL = 60 * 60


class DialogueEngine:
    """对话引擎总调度：准备会话 -> 开始轮次 -> 分发 Handler -> 提交轮次。"""

    def __init__(self,
                 task_handler: TaskHandler,
                 knowledge_handler: KnowledgeHandler,
                 chitchat_handler: ChitChatHandler,
                 turn_planner: TurnPlanner,
                 clarify_responder: ClarifyResponder,
                 turn_plan_validator: TurnPlanValidator):
        self.task_handler = task_handler
        self.knowledge_handler = knowledge_handler
        self.chitchat_handler = chitchat_handler
        self.turn_planner = turn_planner
        self.clarify_responder = clarify_responder
        self.turn_plan_validator = turn_plan_validator

    async def process_message(self, user_message: UserMessage, state: DialogueState) -> ProcessResult:
        self._prepare_session(state)
        self._begin_turn(user_message, state)

        if user_message.type is MessageType.TEXT:
            messages: list[BotMessage] = await self._handle_text_message(state)
        else:
            state.set_focused_object(FocusedObject.from_dict(user_message.object.to_dict()))
            messages: list[BotMessage] = await self._handle_object_message(state, user_message)

        state.pending_turn.assistant_messages.extend(messages)
        state.commit_pending_turn()
        return ProcessResult(
            sender_id=user_message.sender_id,
            message_id=user_message.message_id,
            messages=messages,
        )

    async def _handle_text_message(self, state: DialogueState) -> list[BotMessage]:
        # LLM 生成三轨道计划 -> 校验 -> 分发
        turn_plan: TurnPlan = await self.turn_planner.predict(
            state, self.task_handler.flows, self.knowledge_handler.knowledge_intents,
        )
        validation: TurnPlanValidationResult = self.turn_plan_validator.validate(
            turn_plan, state, self.knowledge_handler.knowledge_intents,
        )
        if not validation.valid:
            return await self.clarify_responder.respond(state, validation.reason)

        if turn_plan.task is not None:
            return await self.task_handler.handle(turn_plan.task.commands, state)

        if turn_plan.knowledge is not None:
            # 知识咨询时打断正在进行的业务任务
            if state.active_task is not None:
                state.interrupt_activate_task()
            return await self.knowledge_handler.handle(state, turn_plan.knowledge.intents)

        if turn_plan.chitchat is not None:
            return await self.chitchat_handler.handle(state)

        return []

    async def _handle_object_message(self, state: DialogueState, user_message: UserMessage) -> list[BotMessage]:
        # 用户点击订单/商品卡片时，自动填充对应槽位
        command = self._object_slot_command(state, user_message, self.task_handler.flows)
        if command is None:
            return await self.clarify_responder.respond(state, ClarifyReason.OBJECT_REQUIRES_INTENT)
        return await self.task_handler.handle([command], state)

    def _object_slot_command(self, state: DialogueState, user_message: UserMessage,
                             flows: FlowsList) -> Command | None:
        collect_slot_name = self._current_collect_slot_name(state, flows)
        object_type = user_message.object.type.strip().lower()

        if object_type == "order" and collect_slot_name == "order_number":
            return SetSlotsCommand(command="set_slots", slots={"order_number": user_message.object.id})
        if object_type == "product" and collect_slot_name == "product_id":
            return SetSlotsCommand(command="set_slots", slots={"product_id": user_message.object.id})
        return None

    def _current_collect_slot_name(self, state: DialogueState, flows: FlowsList) -> str | None:
        # 优先从系统收集流程取槽位名，其次从当前用户任务的 collect step 取
        if isinstance(state.active_system_flow, CollectSystemContext):
            return state.active_system_flow.slot_name or None
        active_task = state.active_task
        if active_task is None:
            return None
        flow: Flow = flows.get_flow_by_id(active_task.flow_id)
        step: FlowStep = flow.get_step_by_id(active_task.step_id)
        if isinstance(step, CollectSlotStep):
            return step.slot_name or None
        return None

    def _prepare_session(self, state: DialogueState):
        session = state.current_session()
        now = time.time()
        if session is None:
            state.start_session()
            return
        if now - session.last_activity_at > SESSION_TTL:
            state.close_current_session()
            state.reset_runtime_state_for_new_session()
            state.start_session()
        else:
            session.last_activity_at = now

    @staticmethod
    def _begin_turn(user_message: UserMessage, state: DialogueState):
        state.begin_turn(user_message)
