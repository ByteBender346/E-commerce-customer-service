import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import dianshang.infrastructure.http_client
from dianshang.conf.config import settings
from dianshang.domain.state import DialogueState


@dataclass
class KnowledgeChunk:
    """检索到的知识片段。"""
    content: str


class KnowledgeProvider(ABC):
    """知识来源基类，子类通过 provider_id 标识自己。"""
    provider_id = ""

    @abstractmethod
    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        pass


class ProductApiProvider(KnowledgeProvider):
    """根据焦点商品 ID 调用商品 API 获取信息。"""
    provider_id = "api.product"

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        product_id = state.focused_object.id
        data = await self._fetch_product(product_id)
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=text)]

    @staticmethod
    async def _fetch_product(product_id: str) -> dict[str, Any]:
        url = f"{settings.commerce_api_base_url}/products/{product_id}"
        result = await dianshang.infrastructure.http_client.http_client.get(url)
        return result.json()["data"]


class OrderApiProvider(KnowledgeProvider):
    """根据焦点订单 ID 并发获取订单详情和物流信息。"""
    provider_id = "api.order"

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        order_number = state.focused_object.id
        order_payload, logistics_payload = await asyncio.gather(
            self._fetch_order(order_number),
            self._fetch_logistics(order_number),
        )
        return [KnowledgeChunk(content="订单与物流信息：\n" + json.dumps(
            {"order_number": order_number, "order": order_payload, "logistics": logistics_payload},
            ensure_ascii=False, indent=2,
        ))]

    @staticmethod
    async def _fetch_order(order_number: str) -> dict[str, Any]:
        url = f"{settings.commerce_api_base_url}/orders/{order_number}"
        resp = await dianshang.infrastructure.http_client.http_client.get(url)
        return resp.json()["data"]

    @staticmethod
    async def _fetch_logistics(order_number: str) -> dict[str, Any]:
        url = f"{settings.commerce_api_base_url}/orders/{order_number}/logistics"
        resp = await dianshang.infrastructure.http_client.http_client.get(url)
        return resp.json().get("data", {})


class FAQProvider(KnowledgeProvider):
    """FAQ 问答库（占位实现）。"""
    provider_id = "faq.default"

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        return [KnowledgeChunk(content="未检索到相关问题。")]


class RAGProvider(KnowledgeProvider):
    """RAG 知识库检索（对接掌柜智库 API 的扩展点）。"""
    provider_id = "rag.default"

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        # TODO: 对接掌柜智库 RAG API，根据用户输入检索知识片段
        user_text = state.pending_turn.input_message.text
        return [KnowledgeChunk(content="未检索到相关信息。")]
