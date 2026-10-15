"""Сохраняет OpenAPI-схему сервиса в docs.json.

Запуск:
    python -m scripts.export_openapi
"""

import json
from pathlib import Path

from app.main import app

DOCS_PATH = Path(__file__).resolve().parent.parent / "docs.json"


def main() -> None:
    DOCS_PATH.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Схема сохранена в {DOCS_PATH}")


if __name__ == "__main__":
    main()
