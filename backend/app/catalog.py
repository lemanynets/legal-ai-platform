from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentType:
    doc_type: str
    title: str
    category: str
    procedure: str


DOCUMENT_TYPES: tuple[DocumentType, ...] = (
    DocumentType(
        doc_type="lawsuit_debt_loan",
        title="Позов: стягнення боргу (договір позики, розписка)",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="lawsuit_debt_sale",
        title="Позов: стягнення боргу (договір купівлі-продажу)",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="appeal_complaint",
        title="Апеляційна скарга",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="motion_appeal_deadline_renewal",
        title="Заява про поновлення строку апеляційного оскарження",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="motion_claim_security",
        title="Заява про забезпечення позову (арешт майна)",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="motion_evidence_request",
        title="Клопотання про витребування доказів",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="motion_expertise",
        title="Клопотання про призначення експертизи",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="motion_court_fee_deferral",
        title="Клопотання про відстрочку/розстрочку судового збору",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="lawsuit_alimony",
        title="Позов: стягнення аліментів",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="lawsuit_property_division",
        title="Позов: поділ майна подружжя",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="lawsuit_damages",
        title="Позов: відшкодування шкоди",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="cassation_complaint",
        title="Касаційна скарга",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="objection_response",
        title="Заперечення на відзив",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="complaint_executor_actions",
        title="Скарга на дії/бездіяльність виконавця",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="statement_enforcement_opening",
        title="Заява про відкриття виконавчого провадження",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="statement_enforcement_asset_search",
        title="Заява про розшук майна боржника",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="complaint_state_inaction",
        title="Скарга на бездіяльність держоргану (КАС)",
        category="judicial",
        procedure="administrative",
    ),
    DocumentType(
        doc_type="notarial_sale_real_estate",
        title="Нотаріальний договір купівлі-продажу нерухомості",
        category="notarial",
        procedure="notarial",
    ),
    DocumentType(
        doc_type="pretension_debt_return",
        title="Претензія про повернення боргу",
        category="pretension",
        procedure="pretrial",
    ),
    DocumentType(
        doc_type="contract_services",
        title="Договір надання послуг",
        category="contract",
        procedure="contract",
    ),
    DocumentType(
        doc_type="lawsuit_invalidate_executive_inscription",
        title="Позов: визнання виконавчого напису недійсним",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="lawsuit_writ_issuance",
        title="Заява про видачу виконавчого листа",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="civil_claim",
        title="Позовна заява (цивільна справа)",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="divorce_claim",
        title="Позов: розірвання шлюбу",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="motion_injunction",
        title="Заява про забезпечення позову",
        category="judicial",
        procedure="civil",
    ),
    DocumentType(
        doc_type="evidence_request",
        title="Клопотання про витребування доказів (generic)",
        category="judicial",
        procedure="civil",
    ),
)


DEBT_LAWSUIT_FORM_SCHEMA: tuple[dict[str, object], ...] = (
    {"key": "court_mode", "type": "select", "required": True, "options": ["auto", "manual"]},
    {"key": "court_name", "type": "string", "required": False},
    {"key": "plaintiff_name", "type": "string", "required": True},
    {"key": "plaintiff_tax_id", "type": "string", "required": True},
    {"key": "plaintiff_address", "type": "string", "required": True},
    {"key": "defendant_name", "type": "string", "required": True},
    {"key": "defendant_tax_id", "type": "string", "required": True},
    {"key": "defendant_address", "type": "string", "required": True},
    {"key": "debt_basis", "type": "select", "required": True, "options": ["loan", "receipt", "other"]},
    {"key": "debt_start_date", "type": "date", "required": True},
    {"key": "principal_debt_uah", "type": "number", "required": True},
    {"key": "accrued_interest_uah", "type": "number", "required": False},
    {"key": "claim_requests", "type": "array", "required": True},
)


GENERIC_FORM_SCHEMA: tuple[dict[str, object], ...] = (
    {"key": "party_a", "type": "string", "required": True},
    {"key": "party_b", "type": "string", "required": True},
    {"key": "fact_summary", "type": "string", "required": True},
    {"key": "request_summary", "type": "string", "required": True},
)

MOTION_FORM_SCHEMA: tuple[dict[str, object], ...] = (
    {"key": "court_name", "type": "string", "required": True},
    {"key": "case_number", "type": "string", "required": False},
    {"key": "plaintiff_name", "type": "string", "required": True},
    {"key": "defendant_name", "type": "string", "required": False},
    {"key": "fact_summary", "type": "string", "required": True},
    {"key": "request_summary", "type": "string", "required": True},
    {"key": "legal_basis", "type": "array", "required": False},
    {"key": "attachments", "type": "array", "required": False},
)

EXECUTIVE_INSCRIPTION_FORM_SCHEMA: tuple[dict[str, object], ...] = (
    {"key": "court_name", "type": "string", "required": True},
    {"key": "court_address", "type": "string", "required": False},
    {"key": "plaintiff_name", "type": "string", "required": True},
    {"key": "plaintiff_email", "type": "string", "required": False},
    {"key": "plaintiff_phone", "type": "string", "required": True},
    {"key": "plaintiff_address", "type": "string", "required": True},
    {"key": "plaintiff_tax_id", "type": "string", "required": True},
    {"key": "representative_name", "type": "string", "required": False},
    {"key": "representative_phone", "type": "string", "required": False},
    {"key": "representative_address", "type": "string", "required": False},
    {"key": "representative_tax_id", "type": "string", "required": False},
    {"key": "defendant_1_name", "type": "string", "required": True},
    {"key": "defendant_1_phone", "type": "string", "required": False},
    {"key": "defendant_1_address", "type": "string", "required": True},
    {"key": "defendant_1_tax_id", "type": "string", "required": False},
    {"key": "defendant_2_name", "type": "string", "required": False},
    {"key": "defendant_2_role", "type": "string", "required": False},
    {"key": "defendant_2_address", "type": "string", "required": False},
    {"key": "third_party_name", "type": "string", "required": False},
    {"key": "third_party_role", "type": "string", "required": False},
    {"key": "third_party_address", "type": "string", "required": False},
    {"key": "inscription_number", "type": "string", "required": True},
    {"key": "inscription_date", "type": "date", "required": True},
    {"key": "notary_name", "type": "string", "required": True},
    {"key": "total_claimed_amount_uah", "type": "number", "required": True},
    {"key": "actual_debt_amount_uah", "type": "number", "required": False},
    {"key": "contract_date", "type": "date", "required": True},
    {"key": "contract_subject", "type": "string", "required": True},
    {"key": "factual_circumstances", "type": "string", "required": True},
    {"key": "violations_description", "type": "string", "required": True},
    {"key": "demands", "type": "array", "required": True},
    {"key": "fee_petition", "type": "select", "required": False, "options": ["full_exemption", "reduction", "deferral", "none"]},
    {"key": "fee_petition_grounds", "type": "string", "required": False},
    {"key": "attachments", "type": "array", "required": False},
)


TARIFFS: tuple[dict[str, object], ...] = (
    {"code": "FREE", "price_usd": 0, "limits": "1 аналіз + 1 документ", "analyses_limit": 1, "docs_limit": 1},
    {"code": "START", "price_usd": 15, "limits": "10 аналізів + 20 документів", "analyses_limit": 10, "docs_limit": 20},
    {"code": "PRO", "price_usd": 35, "limits": "необмежено + всі типи документів", "analyses_limit": None, "docs_limit": None},
    {"code": "PRO_PLUS", "price_usd": 60, "limits": "PRO + Електронний суд + моніторинг", "analyses_limit": None, "docs_limit": None},
    {"code": "TEAM", "price_usd": 120, "limits": "до 5 юристів + API", "analyses_limit": None, "docs_limit": None},
)


def get_document_type(doc_type: str) -> DocumentType | None:
    for item in DOCUMENT_TYPES:
        if item.doc_type == doc_type:
            return item
    return None


def get_form_schema(doc_type: str) -> tuple[dict[str, object], ...]:
    if doc_type == "lawsuit_debt_loan":
        return DEBT_LAWSUIT_FORM_SCHEMA
    if doc_type in {
        "lawsuit_invalidate_executive_inscription",
        "lawsuit_writ_issuance",
    }:
        return EXECUTIVE_INSCRIPTION_FORM_SCHEMA
    if doc_type in {
        "motion_claim_security",
        "motion_injunction",
        "motion_evidence_request",
        "evidence_request",
        "motion_expertise",
        "motion_court_fee_deferral",
        "motion_appeal_deadline_renewal",
        "objection_response",
        "complaint_executor_actions",
        "statement_enforcement_opening",
        "statement_enforcement_asset_search",
        "complaint_state_inaction",
    }:
        return MOTION_FORM_SCHEMA
    return GENERIC_FORM_SCHEMA


def get_tariff(code: str) -> dict[str, object] | None:
    wanted = code.strip().upper()
    for item in TARIFFS:
        if str(item["code"]).upper() == wanted:
            return item
    return None
