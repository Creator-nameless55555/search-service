from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.documents import save_documents
from app.main import app
from app.models import Document
from app.storage import Storage, open_storage

settings = Settings()

# Тесты перед каждым запуском стирают все документы — не даём им случайно
# добраться до рабочей базы.
database_name = settings.database_url.rsplit("/", 1)[-1]
if "test" not in database_name or "test" not in settings.elasticsearch_index:
    pytest.exit(
        "Тесты запускаются только на тестовой базе и тестовом индексе: "
        "в DATABASE_URL и ELASTICSEARCH_INDEX должно быть слово 'test'.",
        returncode=1,
    )


AddDocuments = Callable[..., Awaitable[list[Document]]]


def make_document(text: str, created_date: str = "2019-01-01 12:00:00", rubrics: list[str] | None = None) -> Document:
    return Document(
        text=text,
        created_date=datetime.fromisoformat(created_date),
        rubrics=rubrics if rubrics is not None else ["VK-1"],
    )


@pytest.fixture
async def storage() -> AsyncIterator[Storage]:
    async with open_storage(settings) as storage:
        await storage.reset()
        yield storage


@pytest.fixture
async def client(storage: Storage) -> AsyncIterator[AsyncClient]:
    async with (
        LifespanManager(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client


@pytest.fixture
def add_documents(storage: Storage) -> AddDocuments:
    async def add(*documents: Document) -> list[Document]:
        async with storage.session_factory() as session:
            await save_documents(session, storage.search_index, documents)
        await storage.search_index.refresh()
        return list(documents)

    return add
