from fastapi import FastAPI, Query, HTTPException
from datetime import date
import requests

from validation import clean_news

app = FastAPI()

NEWS_API_KEY = "PASTE_YOUR_NEWSAPI_KEY_HERE"
NEWS_URL = "https://newsapi.org/v2/everything"


def get_news(params: dict):
    try:
        response = requests.get(NEWS_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/news/search")
def search_news(q: str = Query(..., min_length=1)):
    params = {
        "q": q,
        "apiKey": NEWS_API_KEY,
        "language": "en",
        "pageSize": 10,
    }
    raw = get_news(params)
    return {"data": clean_news(raw)}


@app.get("/news/range")
def search_by_date(
    q: str = Query(..., min_length=1),
    from_date: date = Query(...),
    to_date: date = Query(...),
):
    if from_date > to_date:
        raise HTTPException(status_code=400, detail="invalid date range")

    params = {
        "q": q,
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
        "apiKey": NEWS_API_KEY,
        "language": "en",
        "pageSize": 10,
    }
    raw = get_news(params)
    return {"data": clean_news(raw)}


@app.get("/news/location")
def search_by_location(location: str = Query(..., min_length=1)):
    params = {
        "q": location,
        "apiKey": NEWS_API_KEY,
        "language": "en",
        "pageSize": 10,
    }
    raw = get_news(params)
    return {"data": clean_news(raw)}
