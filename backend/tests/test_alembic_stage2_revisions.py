from __future__ import annotations

from pathlib import Path


def test_stage2_revisions_exist() -> None:
    versions = Path("backend/alembic/versions")
    assert (versions / "20260405_000002_kep_auth_tables.py").exists()
    assert (versions / "20260405_000003_deadline_notifications.py").exists()
    assert (versions / "20260405_000004_registry_snapshots.py").exists()
    assert (versions / "20260405_000005_async_jobs_and_dead_letter.py").exists()
    assert (versions / "20260405_000006_legal_brain_sources.py").exists()


def test_stage2_revision_chain() -> None:
    rev2 = (Path("backend/alembic/versions") / "20260405_000002_kep_auth_tables.py").read_text(encoding="utf-8")
    rev3 = (Path("backend/alembic/versions") / "20260405_000003_deadline_notifications.py").read_text(encoding="utf-8")
    rev4 = (Path("backend/alembic/versions") / "20260405_000004_registry_snapshots.py").read_text(encoding="utf-8")
    rev5 = (Path("backend/alembic/versions") / "20260405_000005_async_jobs_and_dead_letter.py").read_text(encoding="utf-8")
    rev6 = (Path("backend/alembic/versions") / "20260405_000006_legal_brain_sources.py").read_text(encoding="utf-8")

    assert 'down_revision = "20260404_000001"' in rev2
    assert 'down_revision = "20260405_000002"' in rev3
    assert 'down_revision = "20260405_000003"' in rev4
    assert 'down_revision = "20260405_000004"' in rev5
    assert 'down_revision = "20260405_000005"' in rev6
