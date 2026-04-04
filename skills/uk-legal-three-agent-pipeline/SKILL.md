---
name: uk-legal-three-agent-pipeline
description: Design, implement, refactor, or validate a three-stage UK legal reasoning pipeline in legal-ai-platform where stage 1 classifies uploaded case materials, stage 2 builds a precedent map, and stage 3 produces a strategy blueprint, with optional downstream document generation. Use when Codex needs to change sequential agent orchestration, stage contracts, persistence, confidence gating, UK-specific legal reasoning, or Strategy Studio behavior across `/api/analyze/intake`, `/api/analyze/{intake_id}/precedent-map`, and `/api/strategy/blueprint`.
---

# UK Legal Three-Agent Pipeline

Use this skill when the work spans the full reasoning chain, not just a single classifier rule or document template.

In this repository, the real pipeline already exists in code as:

1. intake classification
2. precedent mapping
3. strategy blueprint

Document generation is downstream stage 4. Treat it as a consumer of the three-agent pipeline, not part of the core pipeline unless the task explicitly includes it.

## Start Here

1. Read [references/pipeline-touchpoints.md](references/pipeline-touchpoints.md) to locate the router, services, models, schema, UI, and tests.
2. Read [references/stage-contracts.md](references/stage-contracts.md) before changing outputs, confidence logic, or cross-stage dependencies.
3. Inspect the current implementation before adding abstractions. The repo already has persistence and API contracts for all three stages.

## Core Workflow

1. Keep stage boundaries explicit:
   - Stage 1 produces intake classification data.
   - Stage 2 consumes intake and produces grouped precedent signals.
   - Stage 3 consumes intake plus precedent groups and produces litigation strategy.
2. Preserve sequential execution. Do not let stage 3 silently recompute incompatible stage 1 or stage 2 outputs unless the endpoint contract already allows it.
3. Propagate jurisdiction and risk signals across stages. If stage 1 identifies a UK matter, stage 2 and stage 3 must stop assuming Ukrainian precedent and procedural defaults.
4. Keep stored entities aligned with stage outputs. If a stage output changes shape, update persistence, API serialization, and frontend rendering together.
5. Add or update tests for both backend stage logic and the Strategy Studio flow when contracts change.

## Implementation Rules

- Prefer extending existing functions and models over introducing a parallel orchestration layer.
- Keep deterministic logic first. AI enrichment is allowed, but pipeline state must remain explainable and testable without relying on opaque model behavior.
- Treat confidence as data, not decoration. If you add or revise confidence values, define what consumes them and how review thresholds work.
- Keep the handoff payloads small and structured. Do not pass large free-form blobs between stages when structured fields already exist.
- If you introduce UK-specific precedent search or strategy logic, thread the jurisdiction from stage 1 through stage 2 and stage 3 explicitly.
- Do not leave the frontend on stale assumptions. Strategy Studio currently exposes the pipeline as ordered user-visible steps.

## Typical Changes

### Stage 1: Intake agent

- Work in `backend/app/services/file_text_extractor.py`, `backend/app/services/legal_strategy.py`, and `backend/app/routers/strategy.py`.
- Extend file parsing, classification, deadlines, risk extraction, and intake persistence.
- Keep `DocumentAnalysisIntake` and `DocumentIntakeResponse` aligned.

### Stage 2: Precedent-map agent

- Work primarily in `backend/app/services/legal_strategy.py` and related case-law lookup services.
- Change query construction, grouping rules, pattern bucketing, reference scoring, and jurisdiction-aware source selection.
- Keep the stage 2 output grounded in real citations and stable IDs.

### Stage 3: Strategy agent

- Work in `backend/app/services/legal_strategy.py` and `backend/app/routers/strategy.py`.
- Refine immediate actions, roadmap, evidence strategy, negotiation playbook, risk heat map, and confidence rationale.
- Ensure stage 3 uses stage 1 and stage 2 outputs rather than re-inventing them from raw text.

### Optional downstream stage 4

- Only include `generate-with-strategy` and strategy audit changes when the task explicitly crosses into document generation.
- If stage 3 output shape changes, verify downstream consumers still render prompts and audits correctly.

## Validation

- Run targeted backend tests for extraction, intake, precedent map, and strategy.
- Run Strategy Studio tests if any API shape, sequence, or labels change.
- Verify the sequential flow end to end:
  1. upload
  2. intake created
  3. precedent map created
  4. strategy blueprint created
- If the task includes UK support, verify the pipeline does not revert to UA-specific precedent or appellate assumptions after stage 1.

## Deliverable Standard

- Leave stage outputs coherent and version-safe across backend and frontend.
- Keep stage responsibilities obvious in code.
- Add tests that prove the pipeline works for the intended UK scenario, not only for existing UA fixtures.
