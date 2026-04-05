from backend.main import _extract_pdf_links_from_case_payload


def test_extract_pdf_links_from_case_payload_returns_unique_links() -> None:
    payload = {
        "history": [
            {"doc_url": "https://example.com/a.pdf"},
            {"nested": {"file": "https://example.com/b.pdf"}},
            {"dup": "https://example.com/a.pdf"},
        ],
        "other": "https://example.com/not-pdf",
    }
    links = _extract_pdf_links_from_case_payload(payload)
    assert links == ["https://example.com/a.pdf", "https://example.com/b.pdf"]
