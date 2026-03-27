"""
GDPR compliance analyzer for Ukrainian legal documents.

Detects personal data (PII) categories common in Ukrainian legal texts,
evaluates GDPR compliance risks, and provides actionable recommendations.
"""

import re
from dataclasses import dataclass, field


@dataclass
class PiiMatch:
    type: str
    value: str
    start: int
    end: int


@dataclass
class PiiCategory:
    type: str
    count: int
    examples: list[str] = field(default_factory=list)


@dataclass
class GdprAnalysisResult:
    compliant: bool
    issues: list[str]
    personal_data_found: list[PiiCategory]
    recommendations: list[str]
    report: str


# ---------------------------------------------------------------------------
# PII detection patterns for Ukrainian legal documents
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[str, re.Pattern[str], int]] = [
    # Ukrainian tax ID (РНОКПП / ІПН) — 10 digits
    ("tax_id", re.compile(r"\b\d{10}\b"), 3),
    # Ukrainian passport old format: 2 Cyrillic + 6 digits
    ("passport", re.compile(r"\b[А-ЯІЇЄҐ]{2}\s?\d{6}\b"), 3),
    # Ukrainian ID-card: 9 digits
    ("id_card", re.compile(r"\b\d{9}\b"), 2),
    # Phone numbers: Ukrainian +380 or 0-prefix
    ("phone", re.compile(r"(?:\+380|0)\s?\(?\d{2}\)?\s?\d{3}[\s-]?\d{2}[\s-]?\d{2}"), 3),
    # Email addresses
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), 2),
    # IBAN — UA + 27 digits
    ("iban", re.compile(r"\bUA\d{27}\b"), 3),
    # Date of birth patterns: DD.MM.YYYY
    ("date_of_birth", re.compile(
        r"\b(?:дата народження|дата нар\.|д\.н\.)\s*[:\-–]?\s*\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4}\b",
        re.IGNORECASE,
    ), 2),
    # Address with Ukrainian keywords
    ("address", re.compile(
        r"(?:проживає|зареєстрован(?:ий|а)|адреса|місце проживання)\s*[:\-–]?\s*[А-ЯІЇЄҐа-яіїєґ0-9.,\s\-/]{10,80}",
        re.IGNORECASE,
    ), 2),
    # Full name patterns (ПІБ) — three Cyrillic capitalized words in a row
    ("full_name", re.compile(
        r"\b[А-ЯІЇЄҐ][а-яіїєґ']+\s+[А-ЯІЇЄҐ][а-яіїєґ']+\s+[А-ЯІЇЄҐ][а-яіїєґ']+\b"
    ), 1),
]

# Compliance check keywords
_CONSENT_KEYWORDS = re.compile(
    r"згод[аиу]?\s+на\s+обробку|consent\s+to\s+process|обробк[аиу]\s+персональних",
    re.IGNORECASE,
)
_RETENTION_KEYWORDS = re.compile(
    r"строк\s+зберігання|термін\s+обробки|retention\s+period|data\s+retention",
    re.IGNORECASE,
)
_DPO_KEYWORDS = re.compile(
    r"відповідальн\w+\s+за\s+захист|data\s+protection\s+officer|DPO",
    re.IGNORECASE,
)
_PURPOSE_KEYWORDS = re.compile(
    r"мета\s+обробки|purpose\s+of\s+processing|цілі\s+обробки",
    re.IGNORECASE,
)


def _detect_pii(text: str) -> list[PiiMatch]:
    """Find all PII matches in text."""
    matches: list[PiiMatch] = []
    for pii_type, pattern, _ in _PATTERNS:
        for m in pattern.finditer(text):
            matches.append(PiiMatch(
                type=pii_type,
                value=m.group(),
                start=m.start(),
                end=m.end(),
            ))
    return matches


def _group_pii(matches: list[PiiMatch], max_examples: int = 3) -> list[PiiCategory]:
    """Group PII matches by type with counts and truncated examples."""
    groups: dict[str, list[str]] = {}
    for m in matches:
        groups.setdefault(m.type, []).append(m.value)
    return [
        PiiCategory(
            type=pii_type,
            count=len(values),
            examples=[_mask(v) for v in values[:max_examples]],
        )
        for pii_type, values in groups.items()
    ]


def _mask(value: str) -> str:
    """Partially mask a PII value for safe display."""
    if len(value) <= 4:
        return "***"
    return value[:2] + "***" + value[-2:]


def _check_compliance(text: str, pii_found: bool) -> tuple[list[str], list[str]]:
    """Check for GDPR compliance issues and produce recommendations."""
    issues: list[str] = []
    recommendations: list[str] = []

    if pii_found and not _CONSENT_KEYWORDS.search(text):
        issues.append("no_consent_clause")
        recommendations.append(
            "Додати клаузулу про згоду на обробку персональних даних відповідно до ст. 6 GDPR."
        )

    if pii_found and not _RETENTION_KEYWORDS.search(text):
        issues.append("no_data_retention_policy")
        recommendations.append(
            "Визначити строк зберігання персональних даних (ст. 5(1)(e) GDPR)."
        )

    if pii_found and not _PURPOSE_KEYWORDS.search(text):
        issues.append("no_processing_purpose")
        recommendations.append(
            "Чітко вказати мету обробки персональних даних (ст. 5(1)(b) GDPR)."
        )

    if pii_found and not _DPO_KEYWORDS.search(text):
        issues.append("no_dpo_reference")
        recommendations.append(
            "Розглянути призначення відповідальної особи за захист даних (ст. 37 GDPR)."
        )

    if pii_found:
        issues.append("pii_exposed")
        recommendations.append(
            "Замаскувати або видалити персональні дані, які не є необхідними для цілей документа."
        )

    return issues, recommendations


def _build_report(
    categories: list[PiiCategory],
    issues: list[str],
    recommendations: list[str],
    compliant: bool,
) -> str:
    """Build a human-readable Ukrainian report string."""
    lines: list[str] = []

    if compliant:
        lines.append("✅ Документ не містить очевидних порушень GDPR.")
        lines.append("")
        lines.append("Персональних даних не виявлено або всі необхідні клаузули присутні.")
        return "\n".join(lines)

    lines.append("⚠️ Виявлено потенційні GDPR-ризики.")
    lines.append("")

    if categories:
        lines.append(f"Знайдено {len(categories)} категорій персональних даних:")
        for cat in categories:
            masked = ", ".join(cat.examples) if cat.examples else "—"
            lines.append(f"  • {cat.type}: {cat.count} випадків (приклади: {masked})")
        lines.append("")

    if issues:
        lines.append(f"Проблеми ({len(issues)}):")
        issue_labels = {
            "pii_exposed": "Персональні дані відкрито присутні в тексті",
            "no_consent_clause": "Відсутня клаузула про згоду на обробку ПД",
            "no_data_retention_policy": "Не визначено строк зберігання даних",
            "no_processing_purpose": "Не вказано мету обробки даних",
            "no_dpo_reference": "Відсутнє посилання на відповідальну особу за захист даних",
        }
        for issue in issues:
            lines.append(f"  ❌ {issue_labels.get(issue, issue)}")
        lines.append("")

    if recommendations:
        lines.append("Рекомендації:")
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"  {i}. {rec}")

    return "\n".join(lines)


def analyze_gdpr_compliance(text: str) -> GdprAnalysisResult:
    """
    Main entry point: analyze text for GDPR compliance.

    Returns a structured result with PII categories, issues,
    recommendations, and a human-readable report.
    """
    if not text or not text.strip():
        return GdprAnalysisResult(
            compliant=True,
            issues=[],
            personal_data_found=[],
            recommendations=[],
            report="Порожній текст — аналіз неможливий.",
        )

    matches = _detect_pii(text)
    categories = _group_pii(matches)
    pii_found = len(matches) > 0

    issues, recommendations = _check_compliance(text, pii_found)

    compliant = len(issues) == 0

    report = _build_report(categories, issues, recommendations, compliant)

    return GdprAnalysisResult(
        compliant=compliant,
        issues=issues,
        personal_data_found=categories,
        recommendations=recommendations,
        report=report,
    )
