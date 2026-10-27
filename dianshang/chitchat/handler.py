from dianshang.chitchat.responder import ChitChatResponder
from dianshang.domain.messages import BotMessage
from dianshang.domain.state import DialogueState


class ChitChatHandler:
    """闲聊处理入口。"""

    def __init__(self, chitchat_responder: ChitChatResponder) -> None:
        self.chitchat_responder = chitchat_responder

    async def handle(self, state: DialogueState) -> list[BotMessage]:
        return await self.chitchat_responder.respond(
            user_message=state.pending_turn.input_message,
            recent_turns=state.current_session().turns,
        )
