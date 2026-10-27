from dianshang.domain.state import DialogueState
from dianshang.knowledge.intents import KnowledgeIntent
from dianshang.plan.models import TurnPlan, TurnPlanValidationResult, ClarifyReason


class TurnPlanValidator:
    """校验 LLM 生成的 TurnPlan：轨道数量合法、命令/意图非空、焦点对象匹配。"""

    def validate(
            self,
            turn_plan: TurnPlan,
            state: DialogueState,
            knowledge_intents: dict[str, KnowledgeIntent],
    ) -> TurnPlanValidationResult:
        active_tracks = self._active_tracks(turn_plan)
        if len(active_tracks) == 0:
            return self._reject(ClarifyReason.MISSING_TRACK)
        if len(active_tracks) > 1:
            return self._reject(ClarifyReason.MULTIPLE_TRACKS)

        track = active_tracks[0]
        if track == "task":
            return self._validate_task(turn_plan)
        if track == "knowledge":
            return self._validate_knowledge(turn_plan, state, knowledge_intents)
        return TurnPlanValidationResult(valid=True)

    @staticmethod
    def _active_tracks(turn_plan: TurnPlan) -> list[str]:
        tracks = []
        if turn_plan.task is not None:
            tracks.append("task")
        if turn_plan.knowledge is not None:
            tracks.append("knowledge")
        if turn_plan.chitchat is not None:
            tracks.append("chitchat")
        return tracks

    @staticmethod
    def _reject(reason: ClarifyReason) -> TurnPlanValidationResult:
        return TurnPlanValidationResult(valid=False, reason=reason)

    def _validate_task(self, turn_plan: TurnPlan) -> TurnPlanValidationResult:
        if turn_plan.task is None or not turn_plan.task.commands:
            return self._reject(ClarifyReason.MISSING_TASK_COMMANDS)
        return TurnPlanValidationResult(valid=True)

    def _validate_knowledge(self, turn_plan: TurnPlan, state: DialogueState,
                            knowledge_intents: dict[str, KnowledgeIntent]) -> TurnPlanValidationResult:
        if turn_plan.knowledge is None or not turn_plan.knowledge.intents:
            return self._reject(ClarifyReason.MISSING_KNOWLEDGE_INTENT)

        # 校验需要焦点对象的意图（如商品信息必须先选中商品）
        focused_object = state.focused_object
        for intent_id in turn_plan.knowledge.intents:
            ki = knowledge_intents.get(intent_id)
            if ki and ki.requires_object:
                if focused_object is None or focused_object.type != ki.requires_object:
                    return self._reject(ClarifyReason.MISSING_FOCUSED_OBJECT)
        return TurnPlanValidationResult(valid=True)
