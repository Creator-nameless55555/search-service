from httpx import AsyncClient

from tests.conftest import AddDocuments, make_document


async def test_returns_matching_documents_with_all_fields(client: AsyncClient, add_documents: AddDocuments):
    [contest_post, _] = await add_documents(
        make_document("Конкурс на новый скин", "2019-05-31 17:18:42", ["VK-1", "VK-2"]),
        make_document("Обзор обновления игры"),
    )

    response = await client.get("/documents/search", params={"query": "конкурс"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": contest_post.id,
            "rubrics": ["VK-1", "VK-2"],
            "text": "Конкурс на новый скин",
            "created_date": "2019-05-31T17:18:42",
        }
    ]


async def test_results_are_sorted_from_newest_to_oldest(client: AsyncClient, add_documents: AddDocuments):
    await add_documents(
        make_document("Новости весны", "2019-04-01 10:00:00"),
        make_document("Новости зимы", "2019-01-15 10:00:00"),
        make_document("Новости осени", "2019-10-20 10:00:00"),
    )

    response = await client.get("/documents/search", params={"query": "новости"})

    texts = [document["text"] for document in response.json()]
    assert texts == ["Новости осени", "Новости весны", "Новости зимы"]


async def test_returns_at_most_20_documents(client: AsyncClient, add_documents: AddDocuments):
    await add_documents(*(make_document(f"Розыгрыш номер {number}") for number in range(25)))

    response = await client.get("/documents/search", params={"query": "розыгрыш"})

    assert len(response.json()) == 20


async def test_returns_empty_list_when_nothing_found(client: AsyncClient, add_documents: AddDocuments):
    await add_documents(make_document("Конкурс на новый скин"))

    response = await client.get("/documents/search", params={"query": "погода"})

    assert response.status_code == 200
    assert response.json() == []


async def test_empty_query_is_rejected(client: AsyncClient):
    response = await client.get("/documents/search", params={"query": ""})

    assert response.status_code == 422
