import uuid

from dianshang.api.schemas import ChatRequest, ChatResponse, ChatBotMessage
from dianshang.domain.messages import UserMessage, ProcessResult, MessageType, MessageObject
from dianshang.domain.state import DialogueState
from dianshang.engine.dialogue_engine import DialogueEngine
from dianshang.repository.dialogue_state_repository import DialogueStateRepository


class DialogueService:
    def __init__(self,
                 dialogue_state_repository: DialogueStateRepository,
                 dialogue_engine: DialogueEngine):
        self.dialogue_state_repository = dialogue_state_repository
        self.dialogue_engine = dialogue_engine

    async def process_message(self, user_message: UserMessage) -> ProcessResult:
        # 加载历史会话状态 -> 引擎处理 -> 持久化
        state: DialogueState = await self.dialogue_state_repository.load_state(user_message.sender_id)
        process_result: ProcessResult = await self.dialogue_engine.process_message(user_message, state)
        await self.dialogue_state_repository.save_state(state)
        return process_result

    def _build_user_message(self, chat_request: ChatRequest) -> UserMessage:
        return UserMessage(
            sender_id=chat_request.sender_id,
            message_id=chat_request.message_id or str(uuid.uuid4()),
            type=MessageType.TEXT if chat_request.text else MessageType.OBJECT,
            text=chat_request.text,
            object=MessageObject(
                type=chat_request.object.type if chat_request.object else None,
                id=chat_request.object.id,
                title=chat_request.object.title,
                attributes=chat_request.object.attributes,
            ) if chat_request.object else None
        )

    def _build_chat_response(self, process_result: ProcessResult) -> ChatResponse:
        return ChatResponse(
            sender_id=process_result.sender_id,
            message_id=process_result.message_id,
            messages=[
                ChatBotMessage(
                    text=message.text,
                    object=MessageObject(
                        type=message.object.type,
                        id=message.object.id,
                        title=message.object.title,
                        attributes=message.object.attributes,
                    ) if message.object else None
                ) for message in process_result.messages
            ]
        )
