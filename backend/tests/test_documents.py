import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_documents_history(client: TestClient) -> None:
    response = client.get("/api/documents/history")
    # Assuming auth is bypassed or mocked
    assert response.status_code in [200, 401]  # 401 if no auth