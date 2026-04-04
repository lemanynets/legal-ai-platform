import base64
import asyncio
import json

from backend.main import KepVerifyRequest, _decode_signed_payload, _verify_kep_with_provider


def _b64(data: dict) -> str:
    raw = json.dumps(data).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def test_decode_signed_payload_accepts_urlsafe_base64() -> None:
    payload = {"nonce": "abc", "challenge_id": "id-1"}
    decoded = _decode_signed_payload(_b64(payload))
    assert decoded["nonce"] == "abc"
    assert decoded["challenge_id"] == "id-1"


def test_verify_kep_rejects_wrong_origin() -> None:
    payload = {
        "nonce": "n1",
        "challenge_id": "c1",
        "origin": "https://wrong.example",
        "ua_hash": "h1",
        "purpose": "login",
        "issued_at": "2026-01-01T00:00:00Z",
    }
    body = KepVerifyRequest(
        challenge_id="c1",
        signature="sig",
        signed_payload=_b64(payload),
        certificate="cert",
        provider="local_key",
    )
    ok, data = asyncio.run(
        _verify_kep_with_provider(
            body=body,
            nonce="n1",
            challenge_id="c1",
            expected_origin="https://app.example",
            expected_ua_hash="h1",
            expected_purpose="login",
        )
    )
    assert ok is False
    assert data["reason"] == "payload_origin_mismatch"
