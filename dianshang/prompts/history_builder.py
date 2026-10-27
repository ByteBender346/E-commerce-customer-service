from dianshang.domain.messages import UserMessage, BotMessage, MessageType, MessageObject
from dianshang.domain.state import Turn


class HistoryBuilder:
    """将对话历史渲染为 USER:/BOT: 交替的纯文本，供 Prompt 使用。"""

    @staticmethod
    def build(turns: list[Turn]) -> str:
        messages: list[str] = []
        for turn in turns:
            messages.append(f"USER:{HistoryBuilder._render_user_message(turn.input_message)}")
            for bot_msg in turn.assistant_messages:
                messages.append(f"BOT:{HistoryBuilder._render_bot_message(bot_msg)}")
        return "\n".join(messages)

    @staticmethod
    def _render_text(text: str) -> str:
        return text.strip()

    @staticmethod
    def _render_object(obj: MessageObject) -> str:
        label = "订单对象" if obj.type == "order" else "商品对象"
        attrs = ",".join(f"{k}={v}" for k, v in obj.attributes.items())
        return f"[{label},id={obj.id},title={obj.title},{attrs}]"

    @staticmethod
    def _render_user_message(user_message: UserMessage) -> str:
        if user_message.type == MessageType.TEXT:
            return HistoryBuilder._render_text(user_message.text)
        return HistoryBuilder._render_object(user_message.object)

    @staticmethod
    def _render_bot_message(bot_message: BotMessage) -> str:
        if bot_message.text:
            return HistoryBuilder._render_text(bot_message.text)
        return HistoryBuilder._render_object(bot_message.object)
