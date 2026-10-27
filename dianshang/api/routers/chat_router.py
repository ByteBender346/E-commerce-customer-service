from fastapi import APIRouter, Depends

from dianshang.api.dependencies import get_dialogue_service
from dianshang.api.schemas import ChatRequest, ChatResponse, HistoryMessage, HistoryResponse
from dianshang.domain.messages import ProcessResult, UserMessage
from dianshang.service.dialogue_service import DialogueService

chat_router = APIRouter()


@chat_router.post("/api/chat")
async def chat(
        chat_request: ChatRequest,
        dialogue_service: DialogueService = Depends(get_dialogue_service),
) -> ChatResponse:
    user_message: UserMessage = dialogue_service._build_user_message(chat_request)
    process_result: ProcessResult = await dialogue_service.process_message(user_message)
    return dialogue_service._build_chat_response(process_result)


@chat_router.get("/api/chat/history")
def history(sender_id: str) -> HistoryResponse:
    return HistoryResponse(
        sender_id=sender_id,
        messages=[
            HistoryMessage(role="user", text="你好"),
            HistoryMessage(role="bot", text="你好，我是电商客服助手，有什么可以帮您？"),
        ],
    )
