from typing import Any

from dianshang.domain.messages import BotMessage
from dianshang.task.action.base import Action, ActionResult
from dianshang.task.action.custom.shared import fetch_product
from dianshang.domain.state import DialogueState


class RecommendSimilarProductsAction(Action):
    """相似商品推荐（占位实现，后续接入推荐系统）。"""
    name = "action_recommend_similar_products"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        product_id = state.active_task.slots.get("product_id")
        label = product_id or "这件商品"

        payload = await fetch_product(product_id)
        if payload:
            label = str(payload.get("title") or "").strip() or label

        text = f"我已经收到你对\"{label}\"的相似商品推荐需求，推荐系统接入后即可为你展示同款好物。"
        return ActionResult(messages=[BotMessage(text=text)])
