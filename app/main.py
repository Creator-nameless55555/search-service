from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router
from app.config import Settings
from app.storage import open_storage


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with open_storage(Settings()) as storage:
        await storage.create_if_missing()
        app.state.storage = storage
        yield


app = FastAPI(
    title="Document Search",
    description="Простой поисковик по текстам документов: PostgreSQL + Elasticsearch.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(router)
