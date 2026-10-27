from dataclasses import asdict, dataclass, field
from typing import Any, Dict


@dataclass
class TaskContext:
    """业务任务执行快照（用户发起的对话流程）。"""
    flow_id: str
    step_id: str | None = None
    slots: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"flow_id": self.flow_id, "step_id": self.step_id, "slots": self.slots}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskContext":
        return cls(flow_id=data["flow_id"], step_id=data["step_id"], slots=data["slots"])


@dataclass
class SystemContext:
    """系统流程执行快照（系统主动发起的交互，如收集信息、确认、纠错）。"""
    flow_id: str
    step_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SystemContext":
        clz = FLOW_ID_TO_CONTEXT_CLASS[data["flow_id"]]
        return clz(**data)


@dataclass
class StartedSystemContext(SystemContext):
    started_flow_id: str = ""
    started_flow_name: str = ""


@dataclass
class InterruptedSystemContext(SystemContext):
    interrupted_flow_id: str = ""
    interrupted_flow_name: str = ""
    started_flow_id: str = ""
    started_flow_name: str = ""


@dataclass
class CanceledSystemContext(SystemContext):
    canceled_flow_id: str = ""
    canceled_flow_name: str = ""


@dataclass
class ResumedSystemContext(SystemContext):
    resumed_flow_id: str = ""
    resumed_flow_name: str = ""


@dataclass
class CollectSystemContext(SystemContext):
    slot_name: str = ""
    response: dict[str, Any] = field(default_factory=dict)


FLOW_ID_TO_CONTEXT_CLASS = {
    "system_task_started": StartedSystemContext,
    "system_task_interrupted": InterruptedSystemContext,
    "system_task_canceled": CanceledSystemContext,
    "system_task_resumed": ResumedSystemContext,
    "system_collect_information": CollectSystemContext,
}
