from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from elasticsearch import AsyncElasticsearch
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings
from app.models import Base
from app.search_index import SearchIndex


@dataclass
class Storage:
    """База и поисковый индекс вместе: документы всегда живут в обоих местах."""

    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    search_index: SearchIndex

    async def create_if_missing(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await self.search_index.create_if_missing()

    async def reset(self) -> None:
        """Удаляет все документы: пересоздаёт таблицы и индекс с нуля."""
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
        await self.search_index.recreate()


@asynccontextmanager
async def open_storage(settings: Settings) -> AsyncIterator[Storage]:
    engine = create_async_engine(settings.database_url)
    elasticsearch = AsyncElasticsearch(settings.elasticsearch_url)
    try:
        yield Storage(
            engine=engine,
            session_factory=async_sessionmaker(engine, expire_on_commit=False),
            search_index=SearchIndex(elasticsearch, settings.elasticsearch_index),
        )
    finally:
        await elasticsearch.close()
        await engine.dispose()
