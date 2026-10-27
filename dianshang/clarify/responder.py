import json

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from dianshang.domain.messages import BotMessage
from dianshang.domain.state import DialogueState
from dianshang.infrastructure.llm import llm
from dianshang.plan.models import ClarifyReason
from dianshang.prompts.history_builder import HistoryBuilder
from dianshang.prompts.prompt_load import load_prompt


class ClarifyResponder:
    """校验失败时，根据澄清原因生成自然语言的追问回复。"""

    async def respond(self, state: DialogueState, reason: ClarifyReason) -> list[BotMessage]:
        user_message = HistoryBuilder._render_user_message(state.pending_turn.input_message)
        history = HistoryBuilder.build(state.current_session().turns)
        focused_object = json.dumps(state.focused_object.to_dict(), ensure_ascii=False)
        clarify_message = self._build_clarify_message(reason, state)

        prompt_text = load_prompt("clarify_respond")
        prompt = PromptTemplate.from_template(prompt_text, template_format="jinja2")
        chain = prompt | llm | StrOutputParser()
        response = await chain.ainvoke({
            "reason": reason.value,
            "clarify_message": clarify_message,
            "focused_object": focused_object,
            "history": history,
            "user_message": user_message,
        })
        return [BotMessage(text=response)]

    @staticmethod
    def _build_clarify_message(reason: ClarifyReason, state: DialogueState) -> str:
        messages = {
            ClarifyReason.MULTIPLE_TRACKS: "你这次同时提到了多个方向。我们先处理一个，你想先办业务还是先咨询信息呢？",
            ClarifyReason.MISSING_FOCUSED_OBJECT: "请先发送你想咨询的商品或订单，我再继续帮你看。",
            ClarifyReason.MISSING_KNOWLEDGE_INTENT: "你是想了解商品信息、订单信息，还是售后配送规则呢？",
            ClarifyReason.MISSING_TRACK: "你是想先处理业务问题，还是先咨询信息呢？",
            ClarifyReason.MISSING_TASK_COMMANDS: "你这次是想办理什么业务呢？比如查订单、查物流，或者申请退款。",
        }
        if reason in messages:
            return messages[reason]

        if reason is ClarifyReason.OBJECT_REQUIRES_INTENT:
            fo = state.focused_object
            if fo and fo.type == "order":
                return "我已经收到这个订单了。你想查订单状态、查物流，还是申请退款呢？"
            if fo and fo.type == "product":
                return "我已经收到这个商品了。你想了解它的商品信息、发货情况，还是售后相关问题呢？"

        return "我还需要再确认一下你的意思，你可以换个更具体的说法告诉我。"
