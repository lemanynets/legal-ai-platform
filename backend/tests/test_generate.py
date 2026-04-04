import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@patch('app.services.ai_generator.generate_legal_document_for_role')
def test_generate_document(mock_generate, client: TestClient) -> None:
    mock_generate.return_value = type('MockResult', (), {
        'text': 'Generated document content',
        'model': 'test-model',
        'tokens_used': 100
    })()

    response = client.post("/api/documents/generate", json={
        "prompt": "Test prompt",
        "doc_type": "contract",
        "style": "formal"
    })
    assert response.status_code == 200
    data = response.json()
    assert 'id' in data
    assert data['doc_type'] == 'contract'