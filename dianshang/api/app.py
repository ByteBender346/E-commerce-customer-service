from contextlib import asynccontextmanager

from fastapi import FastAPI

from dianshang.api.dependencies import init_dialogue_engine
from dianshang.api.routers.chat_router import chat_router
from dianshang.infrastructure.database import close_db_engine, init_db_engine
from dianshang.infrastructure.http_client import close_http_client, init_http_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_http_client()
    init_db_engine()
    init_dialogue_engine()
    yield
    await close_db_engine()
    await close_http_client()


app = FastAPI(lifespan=lifespan)
app.include_router(chat_router)
