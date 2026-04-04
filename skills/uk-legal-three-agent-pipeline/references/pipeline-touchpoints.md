# Pipeline Touchpoints

Use this file as the map of the existing three-stage pipeline in this repository.

## Backend entrypoints

- `backend/app/routers/strategy.py`
  - `POST /api/analyze/intake`
  - `POST /api/analyze/{intake_id}/precedent-map`
  - `POST /api/strategy/blueprint`
  - downstream consumers:
    - `POST /api/generate-with-strategy`
    - `GET /api/documents/{document_id}/strategy-audit`

## Core backend services

- `backend/app/services/file_text_extractor.py`
  - file parsing for uploads that seed stage 1
- `backend/app/services/legal_strategy.py`
  - stage 1: `classify_document_intake`, `create_document_analysis_intake`
  - stage 2: `build_precedent_groups_for_intake`, `list_precedent_groups`
  - stage 3: `build_strategy_blueprint`, `get_strategy_blueprint`
  - downstream audit binding: `bind_strategy_to_document`, `create_document_generation_audit`

## Persistence layer

- `backend/app/models/legal_strategy.py`
  - `DocumentAnalysisIntake`
  - `CaseLawPrecedentGroup`
  - `LegalStrategyBlueprint`
  - `DocumentGenerationAudit`
- `backend/migrations/versions/20260306_0013_legal_strategy_core.py`
  - baseline migration for all three stages and audit linkage

## API contracts

- `backend/app/schemas.py`
  - `DocumentIntakeResponse`
  - `PrecedentMapResponse`
  - `StrategyBlueprintResponse`
  - `GenerateWithStrategyResponse`
  - `StrategyAuditResponse`

## Frontend flow

- `frontend/app/dashboard/strategy-studio/page.tsx`
  - user-visible step order:
    1. Intake
    2. Precedent map
    3. Blueprint
    4. Generation
    5. Audit
- `frontend/app/dashboard/strategy-studio/page.test.tsx`
  - best place to catch UI regressions when stage contracts change
- `frontend/lib/api.ts`
  - client contracts for each stage

## Artifact examples already in the repo

These root docs show the intended shape of the staged reasoning:

- `SPRAVA_711_FASE_1_CLASSIFIER.md`
- `SPRAVA_711_FASE_2_PRECEDENT_MAP.md`
- `SPRAVA_711_FASE_3_STRATEGY_BLUEPRINT.md`

Use them as examples of stage outputs and reasoning granularity.

`SPRAVA_711_FASE_4_DOCUMENTS.md` is downstream document generation, not part of the core three-agent pipeline.

## Prompt-level expectations

- `AI_GENERATION_PROMPTS_CATALOG.md`
  - contains sequential pipeline expectations, confidence thresholds, and final pipeline status examples

## Current repo assumptions to watch for

- Stage 1 defaults are Ukrainian-first
- Stage 2 currently searches the case-law cache using intake-derived text and Ukrainian assumptions
- Stage 3 strategy defaults are also Ukrainian-first in language, deadlines, and legal framing
- Strategy Studio presents the sequence as a strict ordered flow

## Useful searches

```powershell
rg -n "analyze/intake|precedent-map|strategy_blueprint|generate-with-strategy" backend frontend
rg -n "classify_document_intake|build_precedent_groups_for_intake|build_strategy_blueprint" backend/app/services
rg -n "DocumentAnalysisIntake|CaseLawPrecedentGroup|LegalStrategyBlueprint" backend/app
```
