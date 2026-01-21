from fastapi.testclient import TestClient
import api

client = TestClient(api.app)


def fake_news():
    return {
        "totalResults": 1,
        "articles": [
            {
                "source": {"name": "Example"},
                "title": "Test title",
                "description": "Test description",
                "url": "https://example.com",
                "publishedAt": "2026-01-01",
            }
        ],
    }


def test_health():
    r = client.get("/health")
    assert r.status_code == 200


def test_search_news(mocker):
    mock = mocker.patch("api.requests.get")
    mock.return_value.status_code = 200
    mock.return_value.json.return_value = fake_news()
    mock.return_value.raise_for_status.return_value = None

    r = client.get("/news/search?q=Modi")
    assert r.status_code == 200
    assert r.json()["data"]["total"] == 1


def test_search_by_date_invalid():
    r = client.get(
        "/news/range?q=test&from_date=2026-01-10&to_date=2026-01-01"
    )
    assert r.status_code == 400


def test_search_by_date_valid(mocker):
    mock = mocker.patch("api.requests.get")
    mock.return_value.status_code = 200
    mock.return_value.json.return_value = fake_news()
    mock.return_value.raise_for_status.return_value = None

    r = client.get(
        "/news/range?q=test&from_date=2026-01-01&to_date=2026-01-10"
    )
    assert r.status_code == 200


def test_search_by_location(mocker):
    mock = mocker.patch("api.requests.get")
    mock.return_value.status_code = 200
    mock.return_value.json.return_value = fake_news()
    mock.return_value.raise_for_status.return_value = None

    r = client.get("/news/location?location=Delhi")
    assert r.status_code == 200


def test_clean_news_bad_input():
    from validation import clean_news

    result = clean_news("bad")
    assert result["total"] == 0
