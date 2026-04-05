import asyncio

from backend.main import (
    _FORM_SCHEMA_CATALOG,
    _apply_rule_based_processual_repair,
    _find_processual_blockers,
    _sync_submission_with_adapter,
)


def test_form_schema_catalog_has_all_supported_types() -> None:
    expected = {
        "pozov_do_sudu",
        "pozov_trudovyi",
        "appeal_complaint",
        "dohovir_kupivli_prodazhu",
        "dohovir_orendi",
        "dohovir_nadannia_posluh",
        "pretenziya",
        "dovirennist",
    }
    assert expected.issubset(set(_FORM_SCHEMA_CATALOG.keys()))


def test_rule_based_processual_repair_adds_missing_sections() -> None:
    source = "Апеляційна скарга\nКороткий текст"
    repaired = _apply_rule_based_processual_repair("appeal_complaint", source)
    blockers = _find_processual_blockers("appeal_complaint", repaired)
    assert blockers == []


def test_sync_adapter_manual_provider_returns_reason() -> None:
    synced, reason = asyncio.run(_sync_submission_with_adapter({"provider": "manual", "tracking_url": None}))
    assert synced is False
    assert reason == "manual_provider_no_live_adapter"
