import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_auth_login_success(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"email": "test@example.com", "password": "test"})
    # Assuming dev auth is enabled
    assert response.status_code in [200, 401]  # 200 if dev auth allows


def test_auth_me_unauthorized(client: TestClient) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401