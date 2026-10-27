from dianshang.domain.state import DialogueState
from dianshang.knowledge.providers import KnowledgeProvider


class KnowledgeProviderRegistry:
    """Provider 注册中心：provider_id -> KnowledgeProvider。"""

    def __init__(self, providers: list[KnowledgeProvider]) -> None:
        self._providers_by_id = {p.provider_id: p for p in providers}

    def get(self, provider_id: str) -> KnowledgeProvider:
        return self._providers_by_id[provider_id]
