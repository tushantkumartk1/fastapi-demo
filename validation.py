def clean_news(data):
    if not isinstance(data, dict):
        return {"total": 0, "articles": []}

    articles = data.get("articles") or []
    cleaned = []

    for item in articles:
        source = item.get("source") or {}
        cleaned.append(
            {
                "source": source.get("name"),
                "title": item.get("title"),
                "description": item.get("description"),
                "url": item.get("url"),
                "published": item.get("publishedAt"),
            }
        )

    return {
        "total": data.get("totalResults", len(cleaned)),
        "articles": cleaned,
    }
