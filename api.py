from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import requests
import os
from validation import serialize_news

app = FastAPI()

# Templates & static
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

NEWS_API_KEY = "83df3cd2949c47a295ed4078bd8e8099"
BASE_URL = "https://newsapi.org/v2/everything"


def fetch_news(params: dict) -> dict:
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        data = response.json()
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Upstream News API request failed")

    if data.get("status") != "ok":
        raise HTTPException(status_code=502, detail=data.get("message", "News API error"))

    return serialize_news(data)


# ---------- STATIC PAGES ----------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


@app.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})


# ---------- RESULT PAGES ----------

@app.get("/results/search", response_class=HTMLResponse)
def search_news(request: Request, q: str):
    params = {"q": q, "apiKey": NEWS_API_KEY, "pageSize": 10}
    news = fetch_news(params)
    return templates.TemplateResponse(
        "results.html",
        {"request": request, "articles": news["articles"], "title": f"Search: {q}"}
    )


@app.get("/results/range", response_class=HTMLResponse)
def news_by_date(request: Request, q: str, from_date: str, to_date: str):
    params = {
        "q": q,
        "from": from_date,
        "to": to_date,
        "apiKey": NEWS_API_KEY,
        "pageSize": 10,
    }
    news = fetch_news(params)
    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "articles": news["articles"],
            "title": f"{q} ({from_date} → {to_date})",
        },
    )


@app.get("/results/location", response_class=HTMLResponse)
def news_by_location(request: Request, location: str):
    params = {"q": location, "apiKey": NEWS_API_KEY, "pageSize": 10}
    news = fetch_news(params)
    return templates.TemplateResponse(
        "results.html",
        {"request": request, "articles": news["articles"], "title": f"Location: {location}"}
    )
