import json
from dataclasses import asdict
from typing import Any

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from dianshang.domain.state import DialogueState
from dianshang.infrastructure.llm import llm
from dianshang.knowledge.intents import KnowledgeIntent
from dianshang.plan.models import TurnPlan
from dianshang.prompts.history_builder import HistoryBuilder
from dianshang.prompts.prompt_load import load_prompt
from dianshang.task.flow.models import FlowsList, Flow


class TurnPlanner:
    """调用 LLM，根据对话上下文生成本轮 TurnPlan（task/knowledge/chitchat 三轨道）。"""

    async def predict(
            self,
            state: DialogueState,
            flows: FlowsList,
            knowledge_intents: dict[str, KnowledgeIntent],
    ) -> TurnPlan:
        prompt_inputs = self._build_prompt_inputs(state, flows, knowledge_intents)
        return await self._predict_from_prompt_inputs(prompt_inputs)

    def _build_prompt_inputs(self, state: DialogueState, flows: FlowsList,
                             knowledge_intents: dict[str, KnowledgeIntent]) -> dict[str, Any]:
        user_message = HistoryBuilder._render_user_message(state.pending_turn.input_message)
        current_conversation = HistoryBuilder.build(state.current_session().turns)
        active_task = state.active_task

        # 只暴露用户流程，过滤掉 system_ 开头的系统流程
        user_flows = [f for f in flows.flows if not f.id.startswith("system_")]

        return {
            "current_conversation": current_conversation,
            "user_message": user_message,
            "available_flows_json": json.dumps(
                {"flows": [{k: v for k, v in asdict(f).items() if k != "steps"} for f in user_flows]},
                ensure_ascii=False,
            ),
            "active_task_json": json.dumps(asdict(active_task) if active_task else None, ensure_ascii=False),
            "interrupted_tasks_json": json.dumps(
                [asdict(t) for t in state.paused_tasks], ensure_ascii=False,
            ),
            "focused_object_json": json.dumps(
                asdict(state.focused_object) if state.focused_object else None, ensure_ascii=False,
            ),
            "knowledge_intents_json": json.dumps(
                [{"id": i.id, "description": i.description} for i in knowledge_intents.values()],
                ensure_ascii=False,
            ),
        }

    async def _predict_from_prompt_inputs(self, prompt_inputs: dict[str, Any]) -> TurnPlan:
        prompt_text = load_prompt("turn_plan")
        prompt = PromptTemplate.from_template(prompt_text, template_format="jinja2")
        chain = prompt | llm | JsonOutputParser()
        response = await chain.ainvoke(prompt_inputs)
        return TurnPlan.from_dict(response)
