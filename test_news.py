import json
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


def login_session(client: TestClient):
    """
    Helper to simulate a logged-in user session.
    """
    with client.session_transaction() as session:
        session["user_id"] = "test-user-id"


def test_home_page():
    r = client.get("/")
    assert r.status_code == 200


def test_search_results_authenticated(mocker):
    login_session(client)

    mock_req = mocker.patch("api.requests.get")
    mock_req.return_value.status_code = 200
    mock_req.return_value.json.return_value = fake_news()
    mock_req.return_value.raise_for_status.return_value = None

    r = client.get("/results/search?q=Modi")

    assert r.status_code == 200
    assert "Modi" in r.text


def test_search_results_unauthenticated_redirect():
    r = client.get("/results/search?q=Modi")
    assert r.status_code == 303


def test_range_invalid_dates_authenticated():
    login_session(client)

    r = client.get(
        "/results/range?q=test&from_date=2026-01-10&to_date=2026-01-01"
    )
    assert r.status_code == 400


def test_range_valid_dates_authenticated(mocker):
    login_session(client)

    mock_req = mocker.patch("api.requests.get")
    mock_req.return_value.status_code = 200
    mock_req.return_value.json.return_value = fake_news()
    mock_req.return_value.raise_for_status.return_value = None

    r = client.get(
        "/results/range?q=test&from_date=2026-01-01&to_date=2026-01-10"
    )

    assert r.status_code == 200
    assert "test" in r.text


def test_location_results_authenticated(mocker):
    login_session(client)

    mock_req = mocker.patch("api.requests.get")
    mock_req.return_value.status_code = 200
    mock_req.return_value.json.return_value = fake_news()
    mock_req.return_value.raise_for_status.return_value = None

    r = client.get("/results/location?location=Delhi")

    assert r.status_code == 200
    assert "Delhi" in r.text


def test_clean_news_bad_input():
    from validation import clean_news

    result = clean_news("bad")
    assert result["total"] == 0


def test_cache_miss_calls_api_authenticated(mocker):
    login_session(client)

    mock_redis = mocker.patch("api.redis_client")
    mock_redis.get.return_value = None

    mock_req = mocker.patch("api.requests.get")
    mock_req.return_value.status_code = 200
    mock_req.return_value.json.return_value = fake_news()
    mock_req.return_value.raise_for_status.return_value = None

    r = client.get("/results/search?q=India")

    assert r.status_code == 200
    mock_req.assert_called_once()
    mock_redis.setex.assert_called_once()


def test_cache_hit_skips_api_authenticated(mocker):
    login_session(client)

    cached_data = {
        "total": 1,
        "articles": fake_news()["articles"]
    }

    mock_redis = mocker.patch("api.redis_client")
    mock_redis.get.return_value = json.dumps(cached_data)

    mock_req = mocker.patch("api.requests.get")

    r = client.get("/results/search?q=India")

    assert r.status_code == 200
    mock_req.assert_not_called()
