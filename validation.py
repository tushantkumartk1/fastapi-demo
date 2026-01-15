from pydantic import BaseModel
from typing import List, Optional


class Article(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    publishedAt: Optional[str] = None


class NewsResponse(BaseModel):
    status: str
    totalResults: int
    articles: List[Article]


def serialize_news(data: dict) -> dict:
    """
    Validates incoming data using Pydantic and returns clean JSON.
    Extra fields from NewsAPI are ignored automatically.
    """
    validated = NewsResponse(
        status=data.get("status", "error"),
        totalResults=data.get("totalResults", 0),
        articles=data.get("articles", []),
    )
    return validated.model_dump()
