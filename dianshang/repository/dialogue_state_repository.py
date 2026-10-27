import asyncio
import json

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from dianshang.domain.contexts import TaskContext
from dianshang.domain.state import DialogueState
from dianshang.infrastructure.database import init_db_engine, close_db_engine
from dianshang.models.dialogue_state import DialogueStateRecord


class DialogueStateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def load_state(self, sender_id: str) -> DialogueState:
        """从 dialogue_states 表读取指定用户的状态 JSON，反序列化为 DialogueState。"""
        result = await self.session.execute(
            select(DialogueStateRecord).where(DialogueStateRecord.sender_id == sender_id)
        )
        record = result.scalar_one_or_none()
        if record:
            return DialogueState.from_dict(json.loads(record.state_json))
        return DialogueState(sender_id=sender_id)

    async def save_state(self, state: DialogueState):
        """将 DialogueState 序列化为 JSON，按主键 upsert 写入。"""
        state_json = json.dumps(state.to_dict(), ensure_ascii=False)
        insert_stmt = insert(DialogueStateRecord).values(
            sender_id=state.sender_id,
            state_json=state_json,
        )
        update_stmt = insert_stmt.on_duplicate_key_update(
            state_json=insert_stmt.inserted.state_json,
        )
        await self.session.execute(update_stmt)
        await self.session.commit()


if __name__ == '__main__':
    async def test():
        init_db_engine()
        from dianshang.infrastructure.database import session_factory
        async with session_factory() as session:
            rep = DialogueStateRepository(session)
            await rep.save_state(
                DialogueState(
                    sender_id="user001",
                    active_task=TaskContext(flow_id="refund_request", step_id="ask_order_number"),
                )
            )
            result = await rep.load_state("user001")
            print(result)
        await close_db_engine()

    asyncio.run(test())
