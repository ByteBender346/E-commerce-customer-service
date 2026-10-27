from dianshang.domain.messages import BotMessage
from dianshang.domain.state import DialogueState
from dianshang.knowledge.intents import KnowledgeIntent
from dianshang.knowledge.providers import KnowledgeChunk
from dianshang.knowledge.registry import KnowledgeProviderRegistry
from dianshang.knowledge.resposnder import KnowledgeResponder


class KnowledgeHandler:
    """知识咨询入口：根据意图找到 Provider，检索知识片段，交给 Responder 生成回复。"""

    def __init__(self,
                 knowledge_intents: dict[str, KnowledgeIntent],
                 provider_registry: KnowledgeProviderRegistry,
                 knowledge_responder: KnowledgeResponder):
        self.knowledge_intents = knowledge_intents
        self.provider_registry = provider_registry
        self.knowledge_responder = knowledge_responder

    async def handle(self, state: DialogueState, intents: list[str]) -> list[BotMessage]:
        provider_ids = self._get_provider_ids(intents)
        chunks: list[KnowledgeChunk] = []
        for pid in provider_ids:
            result = await self.provider_registry.get(pid).retrieve(state)
            chunks.extend(result)

        return await self.knowledge_responder.respond(
            user_message=state.pending_turn.input_message,
            recent_turns=state.current_session().turns,
            chunks=chunks,
        )

    def _get_provider_ids(self, intents: list[str]) -> list[str]:
        ids = []
        for intent_id in intents:
            ids.extend(self.knowledge_intents[intent_id].provider_ids)
        return list(set(ids))
