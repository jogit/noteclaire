import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def protected(settings: Settings) -> TestClient:
    return TestClient(create_app(settings.model_copy(update={"app_password": "secret"})))


def test_open_access_without_password(client: TestClient) -> None:
    assert client.get("/api/auth/status").json() == {
        "auth_required": False,
        "authenticated": True,
    }
    assert client.get("/api/subjects").status_code == 200


def test_password_protects_api(protected: TestClient) -> None:
    with protected as client:
        assert client.get("/api/health").status_code == 200
        response = client.get("/api/subjects")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "auth_required"
        assert client.get("/api/auth/status").json()["authenticated"] is False


def test_wrong_password(protected: TestClient) -> None:
    with protected as client:
        response = client.post("/api/auth/login", json={"password": "nope"})
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "auth_invalid"


def test_login_then_logout(protected: TestClient) -> None:
    with protected as client:
        response = client.post("/api/auth/login", json={"password": "secret"})
        assert response.status_code == 204
        assert "httponly" in response.headers["set-cookie"].lower()
        assert client.get("/api/subjects").status_code == 200

        client.post("/api/auth/logout")
        assert client.get("/api/subjects").status_code == 401


def test_token_expires_and_is_bound_to_password() -> None:
    from app.auth import SESSION_LIFETIME_SECONDS, is_valid_token, session_token

    token = session_token("secret", now=1000)
    assert is_valid_token("secret", token, now=1000 + SESSION_LIFETIME_SECONDS - 1)
    assert not is_valid_token("secret", token, now=1000 + SESSION_LIFETIME_SECONDS)
    assert not is_valid_token("autre", token, now=1000)
    forged = f"{int(token.split('.')[0]) + 999999}.{token.split('.')[1]}"
    assert not is_valid_token("secret", forged, now=1000)
    assert not is_valid_token("secret", "n'importe quoi", now=1000)
    assert not is_valid_token("secret", None, now=1000)


def test_login_is_blocked_after_repeated_failures(protected: TestClient) -> None:
    with protected as client:
        client.app.state.login_throttle.max_failures = 2  # type: ignore[attr-defined]
        for _ in range(2):
            assert client.post("/api/auth/login", json={"password": "x"}).status_code == 401
        blocked = client.post("/api/auth/login", json={"password": "secret"})
        assert blocked.status_code == 429
        assert blocked.json()["error"]["code"] == "auth_throttled"
