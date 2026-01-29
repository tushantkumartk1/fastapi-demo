import os
import json
import hashlib
from datetime import date

import requests
from fastapi import (
    FastAPI,
    Query,
    HTTPException,
    Request,
    Form,
    Depends,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_303_SEE_OTHER
from passlib.context import CryptContext

from validation import clean_news
from db import Base, engine, get_db
from models import User


app = FastAPI()

# --------------------
# SESSIONS
# --------------------

app.add_middleware(
    SessionMiddleware,
    secret_key="very-secret-key",
)

# --------------------
# STARTUP (DB INIT)
# --------------------

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

# --------------------
# TEMPLATES & STATIC
# --------------------

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --------------------
# NEWS API
# --------------------

NEWS_API_KEY = "83df3cd2949c47a295ed4078bd8e8099"
NEWS_URL = "https://newsapi.org/v2/everything"

# --------------------
# REDIS
# --------------------

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = 600
redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

# --------------------
# PASSWORD HASHING
# --------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# --------------------
# CACHE HELPERS
# --------------------

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


# --------------------
# NEWS FETCHING
# --------------------

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


# --------------------
# HOME
# --------------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    logged_in = "user_id" in request.session
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "title": "News Hub",
            "logged_in": logged_in,
        },
    )


# --------------------
# AUTH
# --------------------

@app.post("/register")
def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=email,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    request.session["user_id"] = str(user.id)
    return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)


@app.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not pwd_context.verify(password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    request.session["user_id"] = str(user.id)
    return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)


# --------------------
# PUBLIC PAGES
# --------------------

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


# --------------------
# NEWS (LOGIN REQUIRED)
# --------------------

@app.get("/results/search", response_class=HTMLResponse)
def results_search(request: Request, q: str = Query(..., min_length=1)):
    if "user_id" not in request.session:
        return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)

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
    if "user_id" not in request.session:
        return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)

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
            "title": f"Results for '{q}' ({from_date} to {to_date})",
            "articles": data.get("articles", []),
        },
    )


@app.get("/results/location", response_class=HTMLResponse)
def results_location(request: Request, location: str = Query(..., min_length=1)):
    if "user_id" not in request.session:
        return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)

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
