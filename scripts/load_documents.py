"""Загружает документы из CSV в базу и в поисковый индекс.

Запуск:
    python -m scripts.load_documents data/posts.csv

Скрипт начинает с чистого листа: старые документы удаляются.
"""

import argparse
import ast
import asyncio
import csv
from datetime import datetime
from pathlib import Path

from app.config import Settings
from app.documents import save_documents
from app.models import Document
from app.storage import open_storage


def read_documents_from_csv(csv_path: Path) -> list[Document]:
    with csv_path.open(encoding="utf-8", newline="") as csv_file:
        return [
            Document(
                text=row["text"],
                created_date=datetime.fromisoformat(row["created_date"]),
                # В CSV рубрики записаны как питоновский список: "['VK-1', 'VK-2']"
                rubrics=ast.literal_eval(row["rubrics"]),
            )
            for row in csv.DictReader(csv_file)
        ]


async def load_documents(csv_path: Path) -> int:
    documents = read_documents_from_csv(csv_path)
    async with open_storage(Settings()) as storage:
        await storage.reset()
        async with storage.session_factory() as session:
            await save_documents(session, storage.search_index, documents)
    return len(documents)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_path", type=Path, nargs="?", default=Path("data/posts.csv"))
    args = parser.parse_args()

    loaded_count = asyncio.run(load_documents(args.csv_path))
    print(f"Загружено документов: {loaded_count}")


if __name__ == "__main__":
    main()
