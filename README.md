# Поисковик по текстам документов

Небольшой сервис: принимает текстовый запрос, ищет по документам в Elasticsearch и отдаёт
найденное со всеми полями из PostgreSQL. Ещё умеет удалять документ — сразу из базы и из индекса.

**Стек:** Python 3.12, FastAPI, SQLAlchemy (async) + asyncpg, Elasticsearch 8, pytest, Docker Compose.
Все обращения к базе и к Elasticsearch асинхронные.

## Быстрый старт (Docker)

Нужны Docker и Docker Compose.

```bash
# 1. Поднять сервис, PostgreSQL и Elasticsearch
docker compose up -d --build

# 2. Загрузить тестовые данные из data/posts.csv (1500 документов)
docker compose run --rm app python -m scripts.load_documents data/posts.csv
```

Сервис доступен на http://localhost:8000, интерактивная документация — http://localhost:8000/docs.

> Elasticsearch стартует секунд 20–40. Compose ждёт, пока он станет здоровым,
> так что `up` в первый раз может немного подумать — это нормально.

Повторный запуск загрузки начинает с чистого листа: таблица и индекс пересоздаются.

## API

### Поиск

```
GET /documents/search?query=<текст>
```

Возвращает до 20 документов, отсортированных по дате создания — сначала новые.

```bash
curl -G http://localhost:8000/documents/search --data-urlencode "query=конкурс на скин"
```

```json
[
  {
    "id": 2,
    "rubrics": ["VK-1603736028819866", "VK-95883495386", "VK-55347043459"],
    "text": "🎁 Конкурс на НОВЫЙ СКИН ‼️ ...",
    "created_date": "2019-05-31T17:18:42"
  }
]
```

Пустой `query` → `422`.

### Удаление

```
DELETE /documents/{id}
```

```bash
curl -X DELETE http://localhost:8000/documents/2
```

`204` — удалено, `404` — такого документа нет.

Полная схема — в [`docs.json`](docs.json) (OpenAPI 3.1). Если API меняется, её нужно обновить:

```bash
python -m scripts.export_openapi
```

## Тесты

Тесты функциональные: ходят в API и работают с настоящими PostgreSQL и Elasticsearch.
Для них используются отдельная база `search_test` и индекс `documents_test`,
так что рабочие данные не пострадают.

```bash
docker compose run --rm tests
```

На всякий случай `conftest.py` откажется запускаться, если в названии базы или индекса нет слова `test`:
тесты перед каждым прогоном стирают все документы.

## Запуск без Docker

Понадобятся запущенные PostgreSQL 16 и Elasticsearch 8.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # и поправить адреса, если нужно
python -m scripts.load_documents data/posts.csv
uvicorn app.main:app --reload
```

Тесты локально (базу `search_test` нужно создать заранее):

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/search_test \
ELASTICSEARCH_INDEX=documents_test \
pytest
```

## Как это устроено

```
app/
  main.py          — приложение FastAPI, подключение к базе и индексу при старте
  api.py           — HTTP-ручки
  documents.py     — логика поиска и удаления
  search_index.py  — работа с Elasticsearch
  storage.py       — база + индекс вместе: подключение, создание, сброс
  models.py        — таблица documents
  schemas.py       — формат ответов API
  config.py        — настройки из переменных окружения
scripts/
  load_documents.py  — загрузка CSV в базу и индекс
  export_openapi.py  — генерация docs.json
tests/               — функциональные тесты
```

**База** — таблица `documents`: `id`, `rubrics` (массив строк), `text`, `created_date`.
**Индекс** — `id` и `text`, как в задании. Для `text` включён русский анализатор, поэтому
поиск понимает словоформы: по запросу «конкурсы» найдётся и «конкурс».

Пояснения некоторых решений:

- **Какие 20 документов возвращаются.** Elasticsearch находит 20 самых релевантных,
  а уже их сервис сортирует по дате (новые сверху). Если сортировать по дате *все*
  совпадения, то на запрос из нескольких слов наверх попадут свежие, но почти
  не относящиеся к делу документы, где совпало одно слово. Если нужен обратный порядок
  дат — это одна строка в `app/documents.py`.
- **Удаление без рассинхрона.** Документ сначала удаляется из базы внутри транзакции,
  потом из индекса, и только после этого транзакция коммитится. Если Elasticsearch
  ответит ошибкой, документ останется на месте в обоих хранилищах.
