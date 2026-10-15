from httpx import AsyncClient

from app.models import Document
from app.storage import Storage
from tests.conftest import AddDocuments, make_document


async def test_deleted_document_disappears_from_db_and_index(
    client: AsyncClient,
    storage: Storage,
    add_documents: AddDocuments,
):
    [document_to_delete, document_to_keep] = await add_documents(
        make_document("Конкурс первый"),
        make_document("Конкурс второй"),
    )

    response = await client.delete(f"/documents/{document_to_delete.id}")
    await storage.search_index.refresh()

    assert response.status_code == 204
    async with storage.session_factory() as session:
        assert await session.get(Document, document_to_delete.id) is None
    assert await storage.search_index.find_document_ids("конкурс", limit=20) == [document_to_keep.id]


async def test_deleting_unknown_document_returns_404(client: AsyncClient):
    response = await client.delete("/documents/100500")

    assert response.status_code == 404
    assert response.json() == {"detail": "Документ с id=100500 не найден"}


async def test_document_cannot_be_deleted_twice(client: AsyncClient, add_documents: AddDocuments):
    [document] = await add_documents(make_document("Конкурс"))

    first_response = await client.delete(f"/documents/{document.id}")
    second_response = await client.delete(f"/documents/{document.id}")

    assert first_response.status_code == 204
    assert second_response.status_code == 404
