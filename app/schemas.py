from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 42,
                "rubrics": ["VK-1603736028819866", "VK-95883495386"],
                "text": "Конкурс на новый скин! Итоги 4 июня в 17:00 по МСК",
                "created_date": "2019-05-31T17:18:42",
            }
        },
    )

    id: int
    rubrics: list[str]
    text: str
    created_date: datetime


class ErrorResponse(BaseModel):
    detail: str
