from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document
from app.search_index import SearchIndex

SEARCH_RESULTS_LIMIT = 20


class DocumentNotFoundError(Exception):
    def __init__(self, document_id: int) -> None:
        super().__init__(f"Документ с id={document_id} не найден")
        self.document_id = document_id


async def search_documents(
    session: AsyncSession,
    search_index: SearchIndex,
    query: str,
) -> list[Document]:
    """Находит 20 самых релевантных документов и отдаёт их от новых к старым."""
    found_ids = await search_index.find_document_ids(query, limit=SEARCH_RESULTS_LIMIT)
    if not found_ids:
        return []

    newest_first = (
        select(Document)
        .where(Document.id.in_(found_ids))
        .order_by(Document.created_date.desc(), Document.id.desc())
    )
    return list(await session.scalars(newest_first))


async def save_documents(
    session: AsyncSession,
    search_index: SearchIndex,
    documents: Sequence[Document],
) -> None:
    session.add_all(documents)
    await session.flush()  # чтобы база выдала документам id до записи в индекс
    await search_index.add_documents(documents)
    await session.commit()


async def delete_document(
    session: AsyncSession,
    search_index: SearchIndex,
    document_id: int,
) -> None:
    document = await session.get(Document, document_id)
    if document is None:
        raise DocumentNotFoundError(document_id)

    await session.delete(document)
    await session.flush()
    # Транзакция ещё не закоммичена: если индекс ответит ошибкой,
    # документ останется и в базе, и в индексе, а не в одном из них.
    await search_index.delete_document(document_id)
    await session.commit()
