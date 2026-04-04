# Repo Touchpoints

Use this file as the map for UK PDF intake changes in this repository.

## Core intake path

- `backend/app/services/file_text_extractor.py`
  - Entry point: `extract_text_from_file`
  - PDF stack: `pypdf`, `pdfminer`, external `pdftotext`, then OCR
  - Current OCR language order: `ukr+eng`, `ukr`, `eng`
  - Current quality scoring favors Cyrillic-heavy text and repairs mojibake
- `backend/app/services/legal_strategy.py`
  - Entry point: `classify_document_intake`
  - Contains most heuristics for dates, money, language, type, jurisdiction, party roles, issues, and deadlines
  - Current defaults are Ukrainian-first, including `jurisdiction="UA"` and Ukrainian precedent assumptions
- `backend/app/routers/strategy.py`
  - Upload endpoint: `POST /api/analyze/intake`
  - Reads upload bytes, extracts text, checks quota, stores `DocumentAnalysisIntake`, returns `DocumentIntakeResponse`

## Data model and API surface

- `backend/app/models/legal_strategy.py`
  - `DocumentAnalysisIntake` stores classified type, jurisdiction, parties, deadlines, risks, preview text, and full source text
- `backend/app/schemas.py`
  - `DocumentIntakeResponse` exposes the intake contract returned to the frontend
- `backend/migrations/versions/20260306_0013_legal_strategy_core.py`
  - Baseline migration for intake, precedent groups, strategy blueprint, and generation audit

## Existing product flows that rely on intake or uploads

- `README.md`
  - Documents the implemented upload flows and `/api/analyze/intake`
- `frontend/app/dashboard/strategy-studio/page.tsx`
  - Strategy intake UI that uploads files for intake classification
- `frontend/lib/api.ts`
  - Frontend helpers for `analyze/intake`, precedent map, and strategy generation
- `backend/app/routers/auto_process.py`
  - Other upload flows reuse file extraction and may need alignment if PDF handling changes

## Existing tests worth extending

- `backend/tests/test_file_text_extractor.py`
  - Best place for extraction and OCR-fallback behavior
- `backend/tests/test_decision_analysis.py`
  - Useful when upload parsing changes affect document analysis flows
- `backend/tests/test_documents_case_law_integration.py`
  - Relevant if downstream document export or strategy integration changes

## Current limitations to assume until proven otherwise

- Jurisdiction detection mostly returns `UA`, `EU`, or `OTHER`
- Deadline inference is based on Ukrainian appellate timing settings
- Party-role and document-type detection are primarily Ukrainian with a few English markers
- Precedent grouping and strategy guidance are Ukrainian court-practice oriented

## Search patterns

Use these repository searches before editing:

```powershell
rg -n "analyze/intake|classify_document_intake|extract_text_from_file|deadline_from_document|jurisdiction" backend frontend
rg -n "ukr\\+eng|pdftotext|PdfReader|pdfminer" backend/app/services
rg -n "DocumentIntakeResponse|DocumentAnalysisIntake" backend/app
```
