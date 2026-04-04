# Stage Contracts

Use these contracts when changing the pipeline. The main failure mode here is letting one stage drift without updating its consumers.

## Stage 1: Intake classifier

Input:
- uploaded file bytes
- extracted source text

Primary output:
- persisted `DocumentAnalysisIntake`
- serialized `DocumentIntakeResponse`

Fields that matter downstream:
- `classified_type`
- `jurisdiction`
- `primary_party_role`
- `identified_parties`
- `subject_matter`
- `financial_exposure_*`
- `document_date`
- `deadline_from_document`
- `urgency_level`
- `risk_level_*`
- `detected_issues`
- `classifier_confidence`
- `classifier_model`
- `raw_text_preview`

Rules:
- Stage 1 should not pretend uncertainty does not exist. If confidence or extraction quality is weak, expose that clearly.
- If the matter is UK-specific, encode that at stage 1 so later stages do not fall back to UA assumptions.
- If you add new fields, wire model, migration, schema, serializer, and frontend together.

## Stage 2: Precedent-map agent

Input:
- `DocumentAnalysisIntake`

Primary output:
- persisted `CaseLawPrecedentGroup` rows
- serialized `PrecedentMapResponse`

Responsibilities:
- build a search query from intake data
- retrieve candidate authorities
- bucket them into usable patterns
- attach relevance scores and pattern strengths

Rules:
- Use real precedent references, not invented citations.
- Keep grouping reproducible enough for tests.
- If jurisdiction affects precedent source selection, make that dependency explicit.
- If no precedents are found, return a degraded but coherent result instead of fabricating strength.

## Stage 3: Strategy agent

Input:
- `DocumentAnalysisIntake`
- precedent groups, either existing or refreshed

Primary output:
- persisted `LegalStrategyBlueprint`
- serialized `StrategyBlueprintResponse`

Responsibilities:
- convert intake and precedent patterns into:
  - immediate actions
  - procedural roadmap
  - evidence strategy
  - negotiation playbook
  - risk heat map
  - critical deadlines
  - confidence score and rationale

Rules:
- Stage 3 should consume structured signals from stages 1 and 2, not rebuild the whole case from scratch.
- Confidence must reflect the quality of the earlier stages and the strength of precedent support.
- If stage 2 is weak or jurisdiction coverage is limited, surface that in strategy confidence or rationale.

## Optional stage 4: Document generation

This stage is downstream. Touch it only when the task explicitly includes strategy-based drafting.

Input:
- strategy blueprint
- document type
- form data
- precedent refs

Consumers:
- `generate_with_strategy`
- `DocumentGenerationAudit`
- Strategy Studio generation and audit steps

Rule:
- If stage 3 output changes shape, confirm prompt assembly and strategy audit still work.

## Cross-stage invariants

- The pipeline is sequential. Each stage should accept the prior stage's persisted output as canonical input.
- Confidence thresholds should have behavior, not just numbers.
- Jurisdiction must survive all handoffs.
- Risk and deadline data must not disappear between stages.
- Frontend step labels and expected response shapes must stay aligned with backend responses.

## Review thresholds

The prompt catalog in this repo suggests these practical thresholds:

- if classification confidence is below `0.5`, prefer clarification or human review
- if strategy confidence is below `0.6`, flag the case for review
- if precedent support is weak, say so explicitly rather than overstating certainty

If you change those thresholds, update code and tests that depend on them.

## Tests to update when contracts move

- backend extraction/intake tests
- backend strategy and case-law integration tests
- frontend Strategy Studio tests

The minimal acceptable verification is one end-to-end sequence that reaches stage 3 successfully and proves the stage outputs still connect.
