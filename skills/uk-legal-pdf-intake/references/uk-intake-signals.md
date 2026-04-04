# UK Intake Signals

Use these signals when extending heuristics. Treat them as starting points, not an exhaustive ontology.

## Jurisdiction cues

- England and Wales: `England and Wales`, `E&W`, `EWCA`, `EWHC`, `UKSC`, `County Court`, `High Court of Justice`, `Business and Property Courts`
- UK-wide: `United Kingdom`, `UK`, `HMCTS`, `Companies House`, `Employment Tribunal`, `Upper Tribunal`
- Keep the stored code explicit if the source text allows it. `UK` is a better fallback than `OTHER`.

## Common UK legal PDF types

- Claim form
- Particulars of claim
- Defence
- Witness statement
- Consent order
- Draft order
- Judgment
- Order
- Letter before claim
- Statutory demand
- N1, N244, EX160, and other HMCTS form references

## Party and role cues

- `Claimant`, `Defendant`, `Applicant`, `Respondent`, `Appellant`, `Appellee`, `Petitioner`, `Interested Party`
- Company markers: `Ltd`, `Limited`, `LLP`, `PLC`
- Representative markers: `Solicitor`, `Counsel`, `Firm`, `Instructed by`

## Date and money cues

- Dates may appear as `31/01/2026`, `31 January 2026`, `1 Jan 2026`, or ISO
- Money may appear as `GBP`, `£`, `pounds sterling`, or comma-grouped English numerals such as `£125,000.50`
- Do not reuse Ukrainian money parsing unchanged; UK thousands and decimal separators differ

## Deadline cues

- Do not hardcode CPR deadlines unless the task explicitly requires them and the code has a clear source of truth
- Infer deadlines only when the document text states one or the repo has configuration and tests for that rule
- If introducing UK procedural deadlines, make them configuration-backed and test exact trigger phrases

## OCR and extraction guidance

- English OCR must remain available for scanned UK PDFs
- Mixed-language documents are possible, especially bilingual evidence bundles
- Poor PDF text extraction often fails on headers, claim numbers, party blocks, and signature/footer zones; add tests for those fragments

## Acceptance examples

Add or update tests for examples close to these shapes:

1. A text PDF judgment mentioning `IN THE HIGH COURT OF JUSTICE` and `Claimant/Defendant`, producing a UK or England-and-Wales jurisdiction and a court-document type.
2. A scanned letter before claim where OCR extracts enough English text to avoid a 422 error from `/api/analyze/intake`.
3. An HMCTS form snippet with an `N244` reference and `Application notice`, classified as a procedural or court filing rather than `other`.
4. A damages claim with `£125,000.50`, parsed into amount, GBP currency, and a sensible exposure type.
5. A mixed UK/Ukrainian PDF that still preserves the best extraction candidate and does not regress current Ukrainian behavior.

## Non-goals unless the task asks for them

- Full CPR rule engine
- Full UK precedent retrieval pipeline
- Full tribunal-specific taxonomy
- Production-grade OCR tuning for every scan profile
