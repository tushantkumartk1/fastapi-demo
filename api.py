from fastapi import FastAPI, HTTPException
import requests
from validation import serialize_news

app = FastAPI()

NEWS_API_KEY = "83df3cd2949c47a295ed4078bd8e8099"
BASE_URL = "https://newsapi.org/v2/everything"


def fetch_news(params: dict) -> dict:
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        data = response.json()
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Upstream News API request failed")

    # If NewsAPI returns error, forward it cleanly
    if data.get("status") != "ok":
        raise HTTPException(status_code=502, detail=data.get("message", "News API error"))

    return serialize_news(data)


@app.get("/news/search")
def search_news(q: str):
    params = {"q": q, "apiKey": NEWS_API_KEY, "pageSize": 10}
    return fetch_news(params)


@app.get("/news/range")
def news_by_date(q: str, from_date: str, to_date: str):
    params = {
        "q": q,
        "from": from_date,
        "to": to_date,
        "apiKey": NEWS_API_KEY,
        "pageSize": 10,
    }
    return fetch_news(params)


@app.get("/news/location")
def news_by_location(location: str):
    params = {"q": location, "apiKey": NEWS_API_KEY, "pageSize": 10}
    return fetch_news(params)
