from collections.abc import Iterable

from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_bulk

from app.models import Document

# Встроенный русский анализатор приводит слова к основе,
# поэтому запрос «котики» найдёт и «котов», и «котик».
INDEX_MAPPINGS = {
    "properties": {
        "id": {"type": "integer"},
        "text": {"type": "text", "analyzer": "russian"},
    }
}


class SearchIndex:
    """Поисковый индекс документов в Elasticsearch.

    В индексе хранятся только id и text — всё остальное лежит в базе.
    """

    def __init__(self, client: AsyncElasticsearch, index_name: str) -> None:
        self._client = client
        self._index_name = index_name

    async def create_if_missing(self) -> None:
        if not await self._client.indices.exists(index=self._index_name):
            await self._client.indices.create(index=self._index_name, mappings=INDEX_MAPPINGS)

    async def recreate(self) -> None:
        await self._client.indices.delete(index=self._index_name, ignore_unavailable=True)
        await self._client.indices.create(index=self._index_name, mappings=INDEX_MAPPINGS)

    async def add_documents(self, documents: Iterable[Document]) -> None:
        actions = (
            {
                "_index": self._index_name,
                "_id": str(document.id),
                "id": document.id,
                "text": document.text,
            }
            for document in documents
        )
        await async_bulk(self._client, actions)

    async def find_document_ids(self, query: str, limit: int) -> list[int]:
        """Возвращает id самых релевантных запросу документов."""
        response = await self._client.search(
            index=self._index_name,
            query={"match": {"text": query}},
            size=limit,
            source=["id"],
        )
        return [hit["_source"]["id"] for hit in response["hits"]["hits"]]

    async def delete_document(self, document_id: int) -> None:
        try:
            await self._client.delete(index=self._index_name, id=str(document_id))
        except NotFoundError:
            # Документа в индексе уже нет — значит, удалять нечего.
            pass

    async def refresh(self) -> None:
        """Делает свежие изменения видимыми для поиска сразу, а не через секунду."""
        await self._client.indices.refresh(index=self._index_name)
