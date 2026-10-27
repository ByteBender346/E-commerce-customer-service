import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

from dianshang.domain.contexts import (
    ResumedSystemContext,
    StartedSystemContext,
    CanceledSystemContext,
    InterruptedSystemContext,
    SystemContext,
    TaskContext,
)
from dianshang.domain.messages import BotMessage, MessageObject, UserMessage

SESSION_TTL_SECONDS = 60 * 60


@dataclass
class Session:
    session_id: str
    started_at: float = field(default_factory=time.time)
    last_activity_at: float = field(default_factory=time.time)
    turns: list = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "last_activity_at": self.last_activity_at,
            "turns": [turn.to_dict() for turn in self.turns],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        return cls(
            session_id=data["session_id"],
            started_at=data["started_at"],
            last_activity_at=data["last_activity_at"],
            turns=[Turn.from_dict(turn) for turn in data["turns"]],
        )


@dataclass
class Turn:
    turn_id: str
    started_at: float
    input_message: UserMessage
    assistant_messages: list[BotMessage] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "started_at": self.started_at,
            "input_message": self.input_message.to_dict(),
            "assistant_messages": [msg.to_dict() for msg in self.assistant_messages],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Turn":
        return cls(
            turn_id=data["turn_id"],
            started_at=data["started_at"],
            input_message=UserMessage.from_dict(data["input_message"]),
            assistant_messages=[BotMessage.from_dict(msg) for msg in data["assistant_messages"]],
        )


@dataclass
class FocusedObject:
    """当前用户聚焦的业务对象（订单卡片 / 商品卡片）。"""
    type: str
    id: str
    title: str | None = None
    attributes: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "id": self.id, "title": self.title, "attributes": self.attributes}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FocusedObject":
        return cls(type=data["type"], id=data["id"], title=data["title"], attributes=data["attributes"])


@dataclass
class DialogueState:
    sender_id: str
    # 活跃任务栈：正在执行的业务流程；paused_tasks 保存被打断的任务
    active_task: TaskContext | None = None
    paused_tasks: list[TaskContext] = field(default_factory=list)
    # 活跃系统流程：系统主动发起的交互（收集槽位、确认、纠错）
    active_system_flow: SystemContext | None = None
    # 当前聚焦的业务对象
    focused_object: FocusedObject | None = None
    # 会话与对话轮次
    sessions: list[Session] = field(default_factory=list)
    pending_turn: Turn | None = None

    # ---------- 序列化 ----------

    def to_dict(self) -> dict[str, Any]:
        return {
            "sender_id": self.sender_id,
            "active_task": self.active_task.to_dict() if self.active_task else None,
            "paused_tasks": [task.to_dict() for task in self.paused_tasks],
            "active_system_flow": self.active_system_flow.to_dict() if self.active_system_flow else None,
            "focused_object": self.focused_object.to_dict() if self.focused_object else None,
            "sessions": [session.to_dict() for session in self.sessions],
            "pending_turn": self.pending_turn.to_dict() if self.pending_turn else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DialogueState":
        return cls(
            sender_id=data["sender_id"],
            active_task=TaskContext.from_dict(data["active_task"]) if data["active_task"] else None,
            paused_tasks=[TaskContext.from_dict(task) for task in data["paused_tasks"]],
            active_system_flow=SystemContext.from_dict(data["active_system_flow"])
            if data["active_system_flow"] else None,
            focused_object=FocusedObject.from_dict(data["focused_object"]) if data["focused_object"] else None,
            sessions=[Session.from_dict(session) for session in data["sessions"]],
            pending_turn=Turn.from_dict(data["pending_turn"]) if data["pending_turn"] else None,
        )

    # ---------- 对象 ----------

    def set_focused_object(self, obj: FocusedObject) -> None:
        self.focused_object = obj

    # ---------- 任务栈 ----------

    def start_task(self, task: TaskContext) -> None:
        self.active_task = task

    def interrupt_activate_task(self) -> None:
        if self.active_task is None:
            return
        self.paused_tasks.append(self.active_task)
        self.active_task = None

    def resume_task(self, flow_id: str) -> None:
        for i, task in enumerate(self.paused_tasks):
            if task.flow_id == flow_id:
                self.active_task = task
                del self.paused_tasks[i]
                return

    def cancel_paused_task(self, flow_id: str) -> None:
        self.paused_tasks = [task for task in self.paused_tasks if task.flow_id != flow_id]

    def cancel_active_task(self) -> None:
        self.active_task = None

    # ---------- 系统流程 ----------

    def start_system_task(self, system_flow: SystemContext) -> None:
        self.active_system_flow = system_flow

    def end_system_task(self) -> None:
        self.active_system_flow = None

    # ---------- 槽位 ----------

    def set_slots(self, slots: dict) -> None:
        if self.active_task:
            self.active_task.slots.update(slots)

    def remove_slot(self, slot_name: str) -> None:
        if self.active_task and slot_name in self.active_task.slots:
            del self.active_task.slots[slot_name]

    # ---------- Session / Turn ----------

    def start_session(self) -> None:
        self.sessions.append(Session(session_id=str(time.time()), turns=[]))

    def current_session(self) -> Session | None:
        return self.sessions[-1] if self.sessions else None

    def close_current_session(self) -> None:
        self.sessions = self.sessions[:-1]

    def reset_runtime_state_for_new_session(self) -> None:
        self.active_task = None
        self.paused_tasks = []
        self.active_system_flow = None

    def begin_turn(self, user_message: UserMessage) -> None:
        self.pending_turn = Turn(
            turn_id=str(time.time()),
            started_at=time.time(),
            input_message=user_message,
        )

    def commit_pending_turn(self) -> None:
        if self.pending_turn:
            self.pending_turn.started_at = time.time()
            self.current_session().turns.append(self.pending_turn)
            self.pending_turn = None

    def current_task(self) -> TaskContext | SystemContext | None:
        return self.active_task or self.active_system_flow
