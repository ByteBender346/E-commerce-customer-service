from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List

from dianshang.task.flow.links import FlowStepLink, StaticLink, ConditionalLink, FallbackLink


class FlowStepType(str, Enum):
    START = "start"
    ACTION = "action"
    COLLECT = "collect"
    END = "end"


@dataclass(slots=True)
class ResponseDefinition:
    mode: str = "static"
    text: str | None = None
    prompt: str | None = None


@dataclass(slots=True)
class SlotValidation:
    condition: str | None = None
    failure_response: ResponseDefinition | None = None


@dataclass(slots=True)
class FlowStep:
    id: str
    type: FlowStepType
    next: List[FlowStepLink] = field(default_factory=list)
    description: str = ""

    @classmethod
    def from_dict(cls, step_info: dict[str, Any]) -> "FlowStep":
        clz = STEP_TYPE_TO_CLASS[step_info["type"]]
        return clz.from_dict(step_info)

    @classmethod
    def base_fields(cls, step_info: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": step_info["id"],
            "type": FlowStepType(step_info["type"]),
            "next": FlowStep.build_links(step_info["next"]),
            "description": step_info.get("description", ""),
        }

    @classmethod
    def build_links(cls, next_data: str | list) -> list[FlowStepLink]:
        """next 可以是字符串（单分支）或列表（多条件分支）。"""
        if isinstance(next_data, str):
            return [StaticLink(target=next_data)]
        links = []
        for item in next_data:
            if "if" in item:
                links.append(ConditionalLink(target=item["then"], condition=item["if"]))
            else:
                links.append(FallbackLink(target=item["else"]))
        return links


@dataclass(slots=True)
class StartFlowStep(FlowStep):
    @classmethod
    def from_dict(cls, step_info: dict[str, Any]) -> "StartFlowStep":
        return cls(**FlowStep.base_fields(step_info))


@dataclass(slots=True)
class ActionFlowStep(FlowStep):
    action: str = ""
    args: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, step_info: dict[str, Any]) -> "ActionFlowStep":
        return cls(**FlowStep.base_fields(step_info),
                   action=step_info.get("action"),
                   args=step_info.get("args", {}))


@dataclass(slots=True)
class CollectSlotStep(FlowStep):
    slot_name: str = ""
    response: ResponseDefinition = field(default_factory=ResponseDefinition)
    validation: SlotValidation | None = None

    @classmethod
    def from_dict(cls, step_info: dict[str, Any]) -> "CollectSlotStep":
        return cls(**FlowStep.base_fields(step_info),
                   slot_name=step_info.get("slot_name"),
                   response=ResponseDefinition(**step_info.get("response", {})),
                   validation=SlotValidation(
                       condition=step_info.get("validation", {}).get("condition"),
                       failure_response=ResponseDefinition(
                           **step_info.get("validation", {}).get("failure_response", {}),
                       ),
                   ) if "validation" in step_info else None)


@dataclass(slots=True)
class EndFlowStep(FlowStep):
    @classmethod
    def from_dict(cls, step_info: dict[str, Any]) -> "EndFlowStep":
        return cls(**FlowStep.base_fields(step_info))


STEP_TYPE_TO_CLASS = {
    "start": StartFlowStep,
    "action": ActionFlowStep,
    "collect": CollectSlotStep,
    "end": EndFlowStep,
}
