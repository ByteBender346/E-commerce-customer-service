from typing import Any

from jinja2 import Template
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from dianshang.domain.messages import BotMessage
from dianshang.domain.state import DialogueState
from dianshang.infrastructure.llm import llm
from dianshang.prompts.history_builder import HistoryBuilder
from dianshang.task.action.base import Action, ActionResult


class ActionResponse(Action):
    """
    回复动作，支持三种模式：
    - static：直接渲染 Jinja2 模板文本
    - rephrase：先渲染模板，再让 LLM 改写为更自然的表达
    - generate：完全由 LLM 根据 prompt 生成回复
    """
    name = "action_response"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        mode = action_kwargs.get("mode", "static")

        if mode == "static":
            text = action_kwargs.get("text")
            rendered = self._render_text(text, state)
            return ActionResult(messages=[BotMessage(text=rendered)])

        elif mode == "rephrase":
            text = action_kwargs.get("text")
            rendered = self._render_text(text, state)
            message = await self._call_llm(action_kwargs.get("prompt"), state, rendered)
            return ActionResult(messages=[BotMessage(text=message)])

        else:  # generate
            message = await self._call_llm(action_kwargs.get("prompt"), state)
            return ActionResult(messages=[BotMessage(text=message)])

    @staticmethod
    async def _call_llm(prompt_text: str, state: DialogueState, rendered_text: str = "") -> str:
        prompt = PromptTemplate.from_template(prompt_text, template_format="jinja2")
        chain = prompt | llm | StrOutputParser()
        return await chain.ainvoke({
            "history": HistoryBuilder.build(state.current_session().turns),
            "user_message": HistoryBuilder._render_user_message(state.pending_turn.input_message),
            "current_response": rendered_text,
        })

    @staticmethod
    def _render_text(text: str, state: DialogueState) -> str:
        """用槽位数据和系统上下文渲染 Jinja2 模板文本。"""
        template = Template(text)
        return template.render(
            slots=state.active_task.slots if state.active_task else {},
            context=state.active_system_flow or state.active_task,
        )
