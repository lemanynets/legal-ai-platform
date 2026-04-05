from backend.main import (
    _build_citations,
    _chunk_text,
    _grounding_quality_metrics,
    _text_to_embedding,
)


def test_chunk_text_splits_long_text() -> None:
    text = "A" * 1600
    chunks = _chunk_text(text, chunk_size=700, overlap=100)
    assert len(chunks) >= 2


def test_embedding_is_deterministic() -> None:
    vec1 = _text_to_embedding("стаття 627 ЦКУ")
    vec2 = _text_to_embedding("стаття 627 ЦКУ")
    assert vec1 == vec2


def test_build_citations_and_metrics() -> None:
    citations = _build_citations(
        [
            {
                "code": "ЦКУ",
                "title": "Цивільний кодекс України",
                "article": "ст. 627",
                "source_url": "https://zakon.rada.gov.ua",
                "content": "Свобода договору гарантується...",
                "chunk_index": 1,
                "score": 0.99,
            }
        ]
    )
    assert citations[0]["citation_id"] == "CIT-1"
    metrics = _grounding_quality_metrics("Посилання: ст. 627 Цивільний кодекс України", citations)
    assert metrics["citations_count"] == 1
    assert metrics["citation_coverage"] >= 1.0
