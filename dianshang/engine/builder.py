from pathlib import Path

from dianshang.chitchat.handler import ChitChatHandler
from dianshang.chitchat.responder import ChitChatResponder
from dianshang.clarify.responder import ClarifyResponder
from dianshang.engine.dialogue_engine import DialogueEngine
from dianshang.knowledge.handler import KnowledgeHandler
from dianshang.knowledge.intents import KNOWLEDGE_INTENTS
from dianshang.knowledge.providers import FAQProvider, RAGProvider, OrderApiProvider, ProductApiProvider
from dianshang.knowledge.registry import KnowledgeProviderRegistry
from dianshang.knowledge.resposnder import KnowledgeResponder
from dianshang.plan.turn_planner import TurnPlanner
from dianshang.plan.validator import TurnPlanValidator
from dianshang.task.action.builder import build_action_runner
from dianshang.task.command.processor import CommandProcessor
from dianshang.task.flow.executor import FlowExecutor
from dianshang.task.flow.loader import FlowLoader
from dianshang.task.handler import TaskHandler

_PROJECT_ROOT = Path(__file__).parents[2]
_FLOW_CONFIG_DIR = _PROJECT_ROOT / "flow_config"
_FLOW_CONFIG_FILES = ("user_flows.yml", "system_flows.yml")


def build_dialogue_engine() -> DialogueEngine:
    """组装整个对话引擎：加载流程配置、注入所有 Handler 和 Provider。"""
    flow_paths = [_FLOW_CONFIG_DIR / f for f in _FLOW_CONFIG_FILES]
    flows = FlowLoader().load_many(flow_paths)
    return DialogueEngine(
        turn_planner=TurnPlanner(),
        task_handler=TaskHandler(
            flows=flows,
            command_processor=CommandProcessor(),
            flow_executor=FlowExecutor(),
            action_runner=build_action_runner(),
        ),
        knowledge_handler=KnowledgeHandler(
            knowledge_intents=KNOWLEDGE_INTENTS,
            knowledge_responder=KnowledgeResponder(),
            provider_registry=KnowledgeProviderRegistry([
                ProductApiProvider(),
                OrderApiProvider(),
                FAQProvider(),
                RAGProvider(),
            ]),
        ),
        chitchat_handler=ChitChatHandler(chitchat_responder=ChitChatResponder()),
        clarify_responder=ClarifyResponder(),
        turn_plan_validator=TurnPlanValidator(),
    )
