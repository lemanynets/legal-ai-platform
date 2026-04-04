---
name: uk-legal-pdf-intake
description: Extend the legal-ai-platform document intake pipeline for UK legal PDFs, including extraction, OCR fallback, classification, party/deadline detection, and regression tests. Use when Codex needs to add or refine support for England and Wales or broader UK court and pre-action PDFs, scanned legal files, HMCTS-style forms/orders/judgments, or UK-specific intake behavior in `/api/analyze/intake`, strategy intake, or related upload flows.
---

# UK Legal PDF Intake

Use this skill to implement or refine UK-specific PDF intake in this repository.

Start from the existing intake stack instead of creating a parallel pipeline. The repo already has file upload, PDF extraction, intake persistence, and strategy endpoints; most work should be additive and test-backed.

## Workflow

1. Read [references/repo-touchpoints.md](references/repo-touchpoints.md) to locate the current extractor, classifier, schema, migration, API, and test surfaces.
2. Read [references/uk-intake-signals.md](references/uk-intake-signals.md) before changing heuristics, enums, regexes, or OCR behavior.
3. Inspect current code before editing. The present implementation is Ukrainian-first and hardcodes several UA-oriented assumptions in `backend/app/services/legal_strategy.py`.
4. Extend existing functions before adding new modules unless the change clearly deserves separation.
5. Preserve backward compatibility for current UA flows. UK support should broaden the intake pipeline, not replace it.
6. Add or update tests for every heuristic or parsing branch you introduce.

## Implementation Rules

- Keep intake centered on `extract_text_from_file`, `classify_document_intake`, and `POST /api/analyze/intake`.
- Prefer deterministic heuristics first, then optional AI enrichment. Do not make UK intake depend entirely on model output.
- Normalize for UK date and currency formats before deriving deadlines or exposure.
- Treat scanned PDFs as first-class input. If OCR language or fallback order changes, keep English as a supported OCR path and avoid regressing Ukrainian extraction.
- Reuse existing persisted fields when possible. If UK support needs new structured data, update the SQLAlchemy model, Alembic migration, Pydantic schema, and serializer together.
- Keep jurisdiction values explicit. Avoid collapsing UK documents into `OTHER` when the text makes `UK`, `EW`, `E&W`, or another concrete code viable.
- Do not stop at classifier heuristics if downstream queries or document generation still assume Ukrainian case law or terminology.

## Typical Changes

### Extend extraction

- Adjust PDF/OCR logic in `backend/app/services/file_text_extractor.py`.
- Improve quality scoring if English-heavy legal PDFs lose to noisy Cyrillic or mojibake candidates.
- Add tests for text PDFs, scanned PDFs, and mixed-layout PDFs.

### Extend classification

- Update `backend/app/services/legal_strategy.py` for:
  - document type detection
  - jurisdiction detection
  - party-role extraction
  - subject-matter mapping
  - money parsing
  - date extraction
  - deadline inference
  - issue/risk detection
- Prefer small helper functions or constant tables when UK logic would otherwise sprawl through one function.

### Extend data contracts

- Update `backend/app/models/legal_strategy.py`, `backend/app/schemas.py`, and an Alembic migration if fields or defaults change.
- Keep API serialization aligned with stored values in `backend/app/routers/strategy.py`.

### Extend downstream behavior

- Check whether precedent-map or strategy generation should branch on UK jurisdictions instead of defaulting to Ukrainian case-law assumptions.
- If UK intake is intentionally limited to classification only, state that explicitly in code comments or tests so later work does not assume end-to-end UK support already exists.

## Validation

- Run targeted backend tests first, especially file-extraction, decision-analysis, and strategy/intake tests.
- Add focused fixtures that exercise UK claim forms, orders, judgments, letters before claim, and scanned-image PDFs.
- Verify at least one real upload path end to end through `POST /api/analyze/intake`.
- If migrations are added, run Alembic upgrade tests or at minimum confirm the migration applies cleanly.

## Deliverable Standard

- Leave the repo with concrete UK-triggering test coverage.
- Keep heuristic additions readable and localize UK-specific constants.
- Document any intentionally unsupported UK document classes in tests or code comments, not in separate ad hoc docs.
