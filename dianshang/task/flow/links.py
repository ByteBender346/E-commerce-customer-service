from dataclasses import dataclass


@dataclass(slots=True)
class FlowStepLink:
    target: str


@dataclass(slots=True)
class StaticLink(FlowStepLink):
    """无条件跳转到目标节点。"""


@dataclass(slots=True)
class ConditionalLink(FlowStepLink):
    """条件跳转：condition 为 Python 表达式，由 FlowExecutor 用 eval 求值。"""
    condition: str


@dataclass(slots=True)
class FallbackLink(FlowStepLink):
    """所有条件都不满足时的兜底跳转。"""
