import os
import json
import hashlib
from datetime import date

import requests
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from redis import Redis
from redis.exceptions import RedisError

from validation import clean_news

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

NEWS_API_KEY = "83df3cd2949c47a295ed4078bd8e8099"
NEWS_URL = "https://newsapi.org/v2/everything"

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = 600

redis_client = Redis.from_url(REDIS_URL, decode_responses=True)


def make_key(prefix: str, params: dict):
    raw = json.dumps(params, sort_keys=True, default=str)
    return f"{prefix}:{hashlib.sha256(raw.encode()).hexdigest()}"


def cache_get(key: str):
    try:
        val = redis_client.get(key)
        return json.loads(val) if val else None
    except (RedisError, json.JSONDecodeError):
        return None


def cache_set(key: str, value):
    try:
        redis_client.setex(key, CACHE_TTL, json.dumps(value))
    except RedisError:
        pass


def get_news(params: dict):
    try:
        r = requests.get(NEWS_URL, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))


def cached_call(prefix: str, params: dict):
    key = make_key(prefix, params)
    cached = cache_get(key)
    if cached:
        return cached
    raw = get_news(params)
    cleaned = clean_news(raw)
    cache_set(key, cleaned)
    return cleaned


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "title": "News Hub"},
    )


@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return templates.TemplateResponse(
        "about.html",
        {"request": request, "title": "About"},
    )


@app.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    return templates.TemplateResponse(
        "contact.html",
        {"request": request, "title": "Contact"},
    )


@app.get("/results/search", response_class=HTMLResponse)
def results_search(request: Request, q: str = Query(..., min_length=1)):
    params = {"q": q, "apiKey": NEWS_API_KEY, "language": "en", "pageSize": 10}
    data = cached_call("ui:search", params)

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "title": f"Results for '{q}'",
            "articles": data.get("articles", []),
        },
    )


@app.get("/results/range", response_class=HTMLResponse)
def results_range(
    request: Request,
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

    data = cached_call("ui:range", params)

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "title": f"Results for '{q}' ({from_date} → {to_date})",
            "articles": data.get("articles", []),
        },
    )


@app.get("/results/location", response_class=HTMLResponse)
def results_location(request: Request, location: str = Query(..., min_length=1)):
    params = {"q": location, "apiKey": NEWS_API_KEY, "language": "en", "pageSize": 10}
    data = cached_call("ui:location", params)

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "title": f"News from '{location}'",
            "articles": data.get("articles", []),
        },
    )
