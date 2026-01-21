from fastapi import FastAPI, Query, HTTPException
from datetime import date
import requests
import json
import hashlib
from redis import Redis
from redis.exceptions import RedisError

from validation import clean_news

app = FastAPI()

NEWS_API_KEY = "PASTE_YOUR_NEWSAPI_KEY_HERE"
NEWS_URL = "https://newsapi.org/v2/everything"
REDIS_URL = "redis://localhost:6379/0"
CACHE_TTL = 600

redis_client = Redis.from_url(REDIS_URL, decode_responses=True)


def make_key(prefix: str, params: dict):
    raw = json.dumps(params, sort_keys=True, default=str)
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{prefix}:{h}"


def cache_get(key: str):
    try:
        val = redis_client.get(key)
        return json.loads(val) if val else None
    except (RedisError, json.JSONDecodeError):
        return None


def cache_set(key: str, value, ttl: int = CACHE_TTL):
    try:
        redis_client.setex(key, ttl, json.dumps(value))
    except RedisError:
        pass


def get_news(params: dict):
    try:
        resp = requests.get(NEWS_URL, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/news/search")
def search_news(q: str = Query(..., min_length=1)):
    params = {"q": q, "apiKey": NEWS_API_KEY, "language": "en", "pageSize": 10}
    key = make_key("search", params)
    cached = cache_get(key)
    if cached:
        return {"source": "cache", "data": cached}
    raw = get_news(params)
    cleaned = clean_news(raw)
    cache_set(key, cleaned)
    return {"source": "api", "data": cleaned}


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
    key = make_key("range", params)
    cached = cache_get(key)
    if cached:
        return {"source": "cache", "data": cached}
    raw = get_news(params)
    cleaned = clean_news(raw)
    cache_set(key, cleaned)
    return {"source": "api", "data": cleaned}


@app.get("/news/location")
def search_by_location(location: str = Query(..., min_length=1)):
    params = {"q": location, "apiKey": NEWS_API_KEY, "language": "en", "pageSize": 10}
    key = make_key("location", params)
    cached = cache_get(key)
    if cached:
        return {"source": "cache", "data": cached}
    raw = get_news(params)
    cleaned = clean_news(raw)
    cache_set(key, cleaned)
    return {"source": "api", "data": cleaned}
