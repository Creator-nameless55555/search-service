from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents import DocumentNotFoundError, delete_document, search_documents
from app.schemas import DocumentResponse, ErrorResponse
from app.search_index import SearchIndex
from app.storage import Storage

router = APIRouter(prefix="/documents", tags=["documents"])


def get_storage(request: Request) -> Storage:
    return request.app.state.storage


async def get_session(storage: Annotated[Storage, Depends(get_storage)]) -> AsyncIterator[AsyncSession]:
    async with storage.session_factory() as session:
        yield session


def get_search_index(storage: Annotated[Storage, Depends(get_storage)]) -> SearchIndex:
    return storage.search_index


Session = Annotated[AsyncSession, Depends(get_session)]
Index = Annotated[SearchIndex, Depends(get_search_index)]


@router.get(
    "/search",
    response_model=list[DocumentResponse],
    summary="Поиск документов по тексту",
    description=(
        "Ищет по тексту документов в Elasticsearch, берёт 20 самых релевантных "
        "и возвращает их со всеми полями из базы, отсортированными по дате создания "
        "(сначала новые)."
    ),
)
async def search(
    session: Session,
    search_index: Index,
    query: Annotated[str, Query(min_length=1, description="Произвольный текст запроса")],
) -> list[DocumentResponse]:
    documents = await search_documents(session, search_index, query)
    return [DocumentResponse.model_validate(document) for document in documents]


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление документа",
    description="Удаляет документ из базы и из поискового индекса.",
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Документ не найден"}},
)
async def delete(session: Session, search_index: Index, document_id: int) -> None:
    try:
        await delete_document(session, search_index, document_id)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
