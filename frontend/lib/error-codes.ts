/**
 * Machine-readable error codes shared between backend and frontend.
 *
 * Backend MUST return one of these codes in the 422/400 response body:
 *   { "detail": { "error_code": "<CODE>", "message": "...", ...fields } }
 *
 * Frontend reads `error_code` and maps it to a Ukrainian user message.
 * Never display raw backend English strings to users.
 */

// ---------------------------------------------------------------------------
// All failure taxonomy codes (Wave 0 → Wave 5)
// ---------------------------------------------------------------------------

export const ErrorCode = {
  // Wave 0 — input gates
  INPUT_MISSING_REQUIRED_FIELDS: "INPUT_MISSING_REQUIRED_FIELDS",
  // Wave 0 — processual gates
  PROC_BLOCKER:                  "PROC_BLOCKER",
  // Wave 0 — export/filing gate
  LAYOUT_COMPLIANCE_FAIL:        "LAYOUT_COMPLIANCE_FAIL",
  MISSING_COURT:                 "MISSING_COURT",
  MISSING_PARTIES:               "MISSING_PARTIES",
  MISSING_TITLE:                 "MISSING_TITLE",
  MISSING_CLAIMS:                "MISSING_CLAIMS",
  MISSING_SIGNATURE_BLOCK:       "MISSING_SIGNATURE_BLOCK",
  MISSING_ATTACHMENTS:           "MISSING_ATTACHMENTS",
  // Wave 1 — IR pipeline
  IR_PARSE_FAIL:                 "IR_PARSE_FAIL",
  IR_VALIDATION_FAIL:            "IR_VALIDATION_FAIL",
  // Wave 2 — sectional generation
  SECTION_INCONSISTENCY:         "SECTION_INCONSISTENCY",
  // Wave 3 — citation grounding
  CITATION_GROUNDING_FAIL:       "CITATION_GROUNDING_FAIL",
  RETRIEVAL_TIMEOUT:             "RETRIEVAL_TIMEOUT",
  // Wave 4 — rendering
  RENDER_FAIL:                   "RENDER_FAIL",
} as const;

export type ErrorCodeValue = (typeof ErrorCode)[keyof typeof ErrorCode];

// ---------------------------------------------------------------------------
// Ukrainian user-facing messages per code
// ---------------------------------------------------------------------------

export const ERROR_MESSAGES: Record<ErrorCodeValue, string> = {
  INPUT_MISSING_REQUIRED_FIELDS: "Не заповнені обов'язкові поля документа.",
  PROC_BLOCKER:                  "Процесуальний блокер: документ не може бути згенерований у поточному стані.",
  LAYOUT_COMPLIANCE_FAIL:        "Документ не відповідає формальним вимогам для подання.",
  MISSING_COURT:                 "Не зазначено суд.",
  MISSING_PARTIES:               "Не зазначені сторони (позивач / відповідач).",
  MISSING_TITLE:                 "Не зазначена назва документа.",
  MISSING_CLAIMS:                "Прохальна частина відсутня або порожня.",
  MISSING_SIGNATURE_BLOCK:       "Відсутній блок підпису.",
  MISSING_ATTACHMENTS:           "Відсутні обов'язкові додатки.",
  IR_PARSE_FAIL:                 "Сервер повернув некоректну структуру документа. Спробуй ще раз.",
  IR_VALIDATION_FAIL:            "Структура згенерованого документа не пройшла валідацію.",
  SECTION_INCONSISTENCY:         "Секції документа суперечать одна одній (сторони, дати або суми не збігаються).",
  CITATION_GROUNDING_FAIL:       "Правова теза не підкріплена джерелом. Документ не може бути фіналізований.",
  RETRIEVAL_TIMEOUT:             "Пошук судової практики перевищив ліміт часу. Спробуй без digest або пізніше.",
  RENDER_FAIL:                   "Помилка формування фінального документа (DOCX/PDF). Зверніться до підтримки.",
};

// ---------------------------------------------------------------------------
// Structured 422 response payload (what backend MUST return)
// ---------------------------------------------------------------------------

export type BlockerItem = {
  code: string;
  message: string;
  severity?: "critical" | "warning" | "info";
};

export type StructuredApiError = {
  error_code: ErrorCodeValue | string;
  message?: string;
  /** For INPUT_MISSING_REQUIRED_FIELDS */
  missing_fields?: string[];
  /** For PROC_BLOCKER, LAYOUT_COMPLIANCE_FAIL */
  blockers?: BlockerItem[];
  doc_type?: string;
};

// ---------------------------------------------------------------------------
// Helper: resolve user-facing message from error code
// ---------------------------------------------------------------------------

export function resolveErrorMessage(
  code: string | undefined,
  fallback: string
): string {
  if (!code) return fallback;
  return ERROR_MESSAGES[code as ErrorCodeValue] ?? fallback;
}
