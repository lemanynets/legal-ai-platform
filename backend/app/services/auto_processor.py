from __future__ import annotations

from datetime import date, datetime
import json
import re
from typing import Any

from app.catalog import DOCUMENT_TYPES
from app.config import settings
from app.services.ai_generator import generate_legal_document
from app.services.calculators import (
    calculate_court_fee,
    calculate_deadline,
    calculate_limitation_deadline,
    calculate_penalty,
)


DOC_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "lawsuit_debt_loan": (
        "debt",
        "loan",
        "\u0431\u043e\u0440\u0433",
        "\u043f\u043e\u0437\u0438\u043a",
        "\u0440\u043e\u0437\u043f\u0438\u0441\u043a",
        "\u0441\u0442\u044f\u0433\u043d\u0435\u043d\u043d",
    ),
    "lawsuit_debt_sale": (
        "debt",
        "sale",
        "\u0431\u043e\u0440\u0433",
        "\u043a\u0443\u043f\u0456\u0432\u043b",
        "\u043f\u0440\u043e\u0434\u0430\u0436",
        "\u043f\u043e\u0441\u0442\u0430\u0432\u043a",
        "\u043e\u043f\u043b\u0430\u0442",
    ),
    "appeal_complaint": (
        "appeal",
        "complaint",
        "\u0430\u043f\u0435\u043b\u044f\u0446",
        "\u043e\u0441\u043a\u0430\u0440\u0436",
        "\u0441\u043a\u0430\u0440\u0433",
    ),
    "motion_claim_security": (
        "security of claim",
        "asset arrest",
        "\u0437\u0430\u0431\u0435\u0437\u043f\u0435\u0447\u0435\u043d\u043d\u044f \u043f\u043e\u0437\u043e\u0432\u0443",
        "\u0430\u0440\u0435\u0448\u0442 \u043c\u0430\u0439\u043d\u0430",
        "\u0440\u0438\u0437\u0438\u043a \u043d\u0435\u0432\u0438\u043a\u043e\u043d\u0430\u043d\u043d\u044f",
    ),
    "motion_evidence_request": (
        "request evidence",
        "evidence request",
        "\u0432\u0438\u0442\u0440\u0435\u0431\u0443\u0432\u0430\u043d\u043d\u044f \u0434\u043e\u043a\u0430\u0437\u0456\u0432",
        "\u0432\u0438\u0442\u0440\u0435\u0431\u0443\u0432\u0430",
        "\u0434\u043e\u043a\u0430\u0437",
        "\u0434\u043e\u043a\u0430\u0437\u0438 \u0443 \u0432\u043e\u043b\u043e\u0434\u0456\u043d\u043d\u0456",
        "\u043d\u0435\u043c\u043e\u0436\u043b\u0438\u0432\u043e \u0441\u0430\u043c\u043e\u0441\u0442\u0456\u0439\u043d\u043e \u043e\u0442\u0440\u0438\u043c\u0430\u0442\u0438",
    ),
    "motion_expertise": (
        "expert examination",
        "forensic examination",
        "\u043f\u0440\u0438\u0437\u043d\u0430\u0447\u0435\u043d\u043d\u044f \u0435\u043a\u0441\u043f\u0435\u0440\u0442\u0438\u0437\u0438",
        "\u043f\u0438\u0442\u0430\u043d\u043d\u044f \u0435\u043a\u0441\u043f\u0435\u0440\u0442\u0443",
        "\u0441\u043f\u0435\u0446\u0456\u0430\u043b\u044c\u043d\u0456 \u0437\u043d\u0430\u043d\u043d\u044f",
    ),
    "motion_court_fee_deferral": (
        "court fee deferral",
        "court fee installment",
        "\u0432\u0456\u0434\u0441\u0442\u0440\u043e\u0447\u043a\u0430 \u0441\u0443\u0434\u043e\u0432\u043e\u0433\u043e \u0437\u0431\u043e\u0440\u0443",
        "\u0440\u043e\u0437\u0441\u0442\u0440\u043e\u0447\u043a\u0430 \u0441\u0443\u0434\u043e\u0432\u043e\u0433\u043e \u0437\u0431\u043e\u0440\u0443",
        "\u043c\u0430\u0439\u043d\u043e\u0432\u0438\u0439 \u0441\u0442\u0430\u043d",
    ),
    "motion_appeal_deadline_renewal": (
        "renew appeal deadline",
        "restore appeal deadline",
        "\u043f\u043e\u043d\u043e\u0432\u043b\u0435\u043d\u043d\u044f \u0441\u0442\u0440\u043e\u043a\u0443 \u0430\u043f\u0435\u043b\u044f\u0446\u0456\u0439\u043d\u043e\u0433\u043e \u043e\u0441\u043a\u0430\u0440\u0436\u0435\u043d\u043d\u044f",
        "\u043f\u043e\u043d\u043e\u0432\u0438\u0442\u0438 \u0441\u0442\u0440\u043e\u043a \u043d\u0430 \u0430\u043f\u0435\u043b\u044f\u0446\u0456\u0439\u043d\u0443 \u0441\u043a\u0430\u0440\u0433\u0443",
        "\u043f\u0440\u043e\u043f\u0443\u0449\u0435\u043d\u043e \u0441\u0442\u0440\u043e\u043a \u0430\u043f\u0435\u043b\u044f\u0446\u0456\u0457",
    ),
    "lawsuit_alimony": (
        "alimony",
        "\u0430\u043b\u0456\u043c\u0435\u043d\u0442",
        "\u0443\u0442\u0440\u0438\u043c\u0430\u043d\u043d\u044f \u0434\u0438\u0442\u0438\u043d\u0438",
        "\u0441\u0456\u043c\u0435\u0439\u043d\u0438\u0439 \u043a\u043e\u0434\u0435\u043a\u0441",
    ),
    "lawsuit_property_division": (
        "property division",
        "\u043f\u043e\u0434\u0456\u043b \u043c\u0430\u0439\u043d\u0430",
        "\u0441\u043f\u0456\u043b\u044c\u043d\u0435 \u043c\u0430\u0439\u043d\u043e \u043f\u043e\u0434\u0440\u0443\u0436\u0436\u044f",
        "\u0448\u043b\u044e\u0431",
    ),
    "lawsuit_damages": (
        "damages",
        "compensation",
        "\u0432\u0456\u0434\u0448\u043a\u043e\u0434\u0443\u0432\u0430\u043d\u043d\u044f \u0448\u043a\u043e\u0434\u0438",
        "\u043c\u043e\u0440\u0430\u043b\u044c\u043d\u0430 \u0448\u043a\u043e\u0434\u0430",
    ),
    "cassation_complaint": (
        "cassation",
        "\u043a\u0430\u0441\u0430\u0446\u0456\u0439",
        "\u0432\u0435\u0440\u0445\u043e\u0432\u043d\u0438\u0439 \u0441\u0443\u0434",
        "\u0441\u0443\u0434 \u043a\u0430\u0441\u0430\u0446\u0456\u0439\u043d\u043e\u0457 \u0456\u043d\u0441\u0442\u0430\u043d\u0446\u0456\u0457",
    ),
    "objection_response": (
        "objection to response",
        "\u0437\u0430\u043f\u0435\u0440\u0435\u0447\u0435\u043d\u043d\u044f \u043d\u0430 \u0432\u0456\u0434\u0437\u0438\u0432",
        "\u0441\u043f\u0440\u043e\u0441\u0442\u0443\u0432\u0430\u043d\u043d\u044f \u0434\u043e\u0432\u043e\u0434\u0456\u0432",
    ),
    "complaint_executor_actions": (
        "executor complaint",
        "\u0441\u043a\u0430\u0440\u0433\u0430 \u043d\u0430 \u0434\u0456\u0457 \u0432\u0438\u043a\u043e\u043d\u0430\u0432\u0446\u044f",
        "\u0431\u0435\u0437\u0434\u0456\u044f\u043b\u044c\u043d\u0456\u0441\u0442\u044c \u0432\u0438\u043a\u043e\u043d\u0430\u0432\u0446\u044f",
        "\u0432\u0438\u043a\u043e\u043d\u0430\u0432\u0447\u0435 \u043f\u0440\u043e\u0432\u0430\u0434\u0436\u0435\u043d\u043d\u044f",
    ),
    "statement_enforcement_opening": (
        "open enforcement proceeding",
        "\u0432\u0456\u0434\u043a\u0440\u0438\u0442\u0442\u044f \u0432\u0438\u043a\u043e\u043d\u0430\u0432\u0447\u043e\u0433\u043e \u043f\u0440\u043e\u0432\u0430\u0434\u0436\u0435\u043d\u043d\u044f",
        "\u0432\u0438\u043a\u043e\u043d\u0430\u0432\u0447\u0438\u0439 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442",
    ),
    "statement_enforcement_asset_search": (
        "asset search debtor",
        "\u0440\u043e\u0437\u0448\u0443\u043a \u043c\u0430\u0439\u043d\u0430 \u0431\u043e\u0440\u0436\u043d\u0438\u043a\u0430",
        "\u0432\u0438\u044f\u0432\u043b\u0435\u043d\u043d\u044f \u0430\u043a\u0442\u0438\u0432\u0456\u0432",
    ),
    "complaint_state_inaction": (
        "state authority inaction",
        "\u0431\u0435\u0437\u0434\u0456\u044f\u043b\u044c\u043d\u0456\u0441\u0442\u044c \u0434\u0435\u0440\u0436\u043e\u0440\u0433\u0430\u043d\u0443",
        "\u0430\u0434\u043c\u0456\u043d\u0456\u0441\u0442\u0440\u0430\u0442\u0438\u0432\u043d\u0438\u0439 \u043f\u043e\u0437\u043e\u0432",
        "\u043a\u0430\u0441 \u0443\u043a\u0440\u0430\u0457\u043d\u0438",
    ),
    "pretension_debt_return": (
        "pretension",
        "demand letter",
        "\u043f\u0440\u0435\u0442\u0435\u043d\u0437",
        "\u0434\u043e\u0441\u0443\u0434",
        "\u0432\u0438\u043c\u043e\u0433",
    ),
    "contract_services": (
        "services agreement",
        "service contract",
        "\u043f\u043e\u0441\u043b\u0443\u0433",
        "\u0434\u043e\u0433\u043e\u0432\u0456\u0440",
        "\u0432\u0438\u043a\u043e\u043d\u0430\u0432\u0435\u0446\u044c",
        "\u0437\u0430\u043c\u043e\u0432\u043d\u0438\u043a",
    ),
}

PARTY_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        "plaintiff_name",
        r"(?:\u043f\u043e\u0437\u0438\u0432\u0430\u0447|\u0437\u0430\u044f\u0432\u043d\u0438\u043a|plaintiff)\s*[:\-]\s*([^\n\r]+)",
    ),
    (
        "defendant_name",
        r"(?:\u0432\u0456\u0434\u043f\u043e\u0432\u0456\u0434\u0430\u0447|\u0431\u043e\u0440\u0436\u043d\u0438\u043a|defendant)\s*[:\-]\s*([^\n\r]+)",
    ),
    (
        "party_a",
        r"(?:\u0441\u0442\u043e\u0440\u043e\u043d\u0430\s*1|\u0441\u0442\u043e\u0440\u043e\u043d\u0430\s*\u0430|party\s*a)\s*[:\-]\s*([^\n\r]+)",
    ),
    (
        "party_b",
        r"(?:\u0441\u0442\u043e\u0440\u043e\u043d\u0430\s*2|\u0441\u0442\u043e\u0440\u043e\u043d\u0430\s*\u0431|party\s*b)\s*[:\-]\s*([^\n\r]+)",
    ),
)

KNOWN_DOCUMENT_TYPES = {item.doc_type for item in DOCUMENT_TYPES}
PROCESSUAL_DOCUMENT_TYPES: tuple[str, ...] = (
    "lawsuit_debt_loan",
    "lawsuit_debt_sale",
    "appeal_complaint",
    "motion_claim_security",
    "motion_evidence_request",
    "motion_expertise",
    "motion_court_fee_deferral",
    "motion_appeal_deadline_renewal",
    "lawsuit_alimony",
    "lawsuit_property_division",
    "lawsuit_damages",
    "cassation_complaint",
    "objection_response",
    "complaint_executor_actions",
    "statement_enforcement_opening",
    "statement_enforcement_asset_search",
    "complaint_state_inaction",
)

APPELLATE_DOC_TYPES: set[str] = {"appeal_complaint", "cassation_complaint"}
CRITICAL_APPELLATE_DEADLINE_CODES: set[str] = {"appeal_deadline", "cassation_deadline"}

DOC_TYPE_LAW_REFERENCES: dict[str, tuple[str, ...]] = {
    "lawsuit_debt_loan": ("Civil Code of Ukraine: arts. 1046, 1049, 625", "Civil Procedure Code of Ukraine"),
    "lawsuit_debt_sale": ("Civil Code of Ukraine: contract and obligations provisions", "Civil Procedure Code of Ukraine"),
    "appeal_complaint": ("Relevant procedural code: appeal chapter and filing deadlines",),
    "motion_claim_security": ("Civil Procedure Code of Ukraine: arts. 149-151 (security for claim)",),
    "motion_evidence_request": ("Civil Procedure Code of Ukraine: art. 84 (requesting evidence), art. 95",),
    "motion_expertise": ("Civil Procedure Code of Ukraine: arts. 103-104 (court expertise)",),
    "motion_court_fee_deferral": (
        "Civil Procedure Code of Ukraine: art. 136 (deferral/installment of court fee)",
        "Law of Ukraine On Court Fee: art. 8",
    ),
    "motion_appeal_deadline_renewal": (
        "Civil Procedure Code of Ukraine: arts. 127, 354 (renewal of procedural term and appeal timing)",
    ),
    "lawsuit_alimony": ("Family Code of Ukraine: arts. 180-183, 191", "Civil Procedure Code of Ukraine"),
    "lawsuit_property_division": (
        "Family Code of Ukraine: arts. 60, 69-71 (division of marital property)",
        "Civil Procedure Code of Ukraine",
    ),
    "lawsuit_damages": ("Civil Code of Ukraine: arts. 22, 23, 1166, 1167", "Civil Procedure Code of Ukraine"),
    "cassation_complaint": ("Civil Procedure Code of Ukraine: arts. 389-392, 400",),
    "objection_response": ("Civil Procedure Code of Ukraine: art. 178 (objections to response)",),
    "complaint_executor_actions": ("Civil Procedure Code of Ukraine: arts. 447-451", "Law On Enforcement Proceedings"),
    "statement_enforcement_opening": ("Law On Enforcement Proceedings: art. 26",),
    "statement_enforcement_asset_search": ("Law On Enforcement Proceedings: search of debtor assets",),
    "complaint_state_inaction": ("Code of Administrative Procedure of Ukraine: arts. 2, 5, 160, 161",),
    "pretension_debt_return": ("Civil Code of Ukraine: obligations and pre-trial demand practice",),
    "contract_services": ("Civil Code of Ukraine: services contract provisions",),
}

DOC_TYPE_REQUIRED_MARKERS = {
    "lawsuit_debt_loan": ("\u041f\u041e\u0417\u041e\u0412\u041d\u0410 \u0417\u0410\u042f\u0412\u0410", "\u041f\u0420\u041e\u0428\u0423 \u0421\u0423\u0414", "\u0441\u0442. 175", "\u0441\u0442. 177"),
    "lawsuit_debt_sale": ("\u041f\u041e\u0417\u041e\u0412\u041d\u0410 \u0417\u0410\u042f\u0412\u0410", "\u041f\u0420\u041e\u0428\u0423 \u0421\u0423\u0414", "\u0441\u0442. 175", "\u0441\u0442. 177"),
    "appeal_complaint": ("\u0410\u041f\u0415\u041b\u042f\u0426\u0406\u0419\u041d\u0410 \u0421\u041a\u0410\u0420\u0413\u0410", "\u041f\u0420\u041e\u0428\u0423 \u0421\u0423\u0414", "\u0441\u0442. 352", "\u0441\u0442. 356"),
    "motion_claim_security": ("\u0417\u0410\u042f\u0412\u0410 \u041f\u0420\u041e \u0417\u0410\u0411\u0415\u0417\u041f\u0415\u0427\u0415\u041d\u041d\u042f \u041f\u041e\u0417\u041e\u0412\u0423", "\u041f\u0420\u041e\u0428\u0423 \u0421\u0423\u0414", "\u0441\u0442. 149", "\u0441\u0442. 150"),
    "motion_evidence_request": ("\u041a\u041b\u041e\u041f\u041e\u0422\u0410\u041d\u041d\u042f \u041f\u0420\u041e \u0412\u0418\u0422\u0420\u0415\u0411\u0423\u0412\u0410\u041d\u041d\u042f \u0414\u041e\u041a\u0410\u0417\u0406\u0412", "\u041f\u0420\u041e\u0428\u0423 \u0421\u0423\u0414", "\u0441\u0442. 84"),
    "motion_expertise": ("\u041a\u041b\u041e\u041f\u041e\u0422\u0410\u041d\u041d\u042f \u041f\u0420\u041e \u041f\u0420\u0418\u0417\u041d\u0410\u0427\u0415\u041d\u041d\u042f \u0415\u041a\u0421\u041f\u0415\u0420\u0422\u0418\u0417\u0418", "\u041f\u0420\u041e\u0428\u0423 \u0421\u0423\u0414", "\u0441\u0442. 103"),
    "motion_court_fee_deferral": (
        "\u041a\u041b\u041e\u041f\u041e\u0422\u0410\u041d\u041d\u042f \u041f\u0420\u041e \u0412\u0406\u0414\u0421\u0422\u0420\u041e\u0427\u0415\u041d\u041d\u042f/\u0420\u041e\u0417\u0421\u0422\u0420\u041e\u0427\u0415\u041d\u041d\u042f \u0421\u041f\u041b\u0410\u0422\u0418 \u0421\u0423\u0414\u041e\u0412\u041e\u0413\u041e \u0417\u0411\u041e\u0420\u0423",
        "\u041f\u0420\u041e\u0428\u0423 \u0421\u0423\u0414",
        "\u0441\u0442. 136",
    ),
    "motion_appeal_deadline_renewal": (
        "\u0417\u0410\u042f\u0412\u0410 \u041f\u0420\u041e \u041f\u041e\u041d\u041e\u0412\u041b\u0415\u041d\u041d\u042f \u0421\u0422\u0420\u041e\u041a\u0423 \u0410\u041f\u0415\u041b\u042f\u0426\u0406\u0419\u041d\u041e\u0413\u041e \u041e\u0421\u041a\u0410\u0420\u0416\u0415\u041d\u041d\u042f",
        "\u041f\u0420\u041e\u0428\u0423 \u0421\u0423\u0414",
        "\u0441\u0442. 127",
        "\u0441\u0442. 354",
    ),
    "lawsuit_alimony": (
        "\u041f\u041e\u0417\u041e\u0412\u041d\u0410 \u0417\u0410\u042f\u0412\u0410",
        "\u041f\u0420\u041e\u0428\u0423 \u0421\u0423\u0414",
        "\u0441\u0442. 175",
        "\u0441\u0442. 177",
    ),
    "lawsuit_property_division": (
        "\u041f\u041e\u0417\u041e\u0412\u041d\u0410 \u0417\u0410\u042f\u0412\u0410",
        "\u041f\u0420\u041e\u0428\u0423 \u0421\u0423\u0414",
        "\u0441\u0442. 175",
        "\u0441\u0442. 177",
    ),
    "lawsuit_damages": (
        "\u041f\u041e\u0417\u041e\u0412\u041d\u0410 \u0417\u0410\u042f\u0412\u0410",
        "\u041f\u0420\u041e\u0428\u0423 \u0421\u0423\u0414",
        "\u0441\u0442. 175",
        "\u0441\u0442. 177",
    ),
    "cassation_complaint": (
        "\u041a\u0410\u0421\u0410\u0426\u0406\u0419\u041d\u0410 \u0421\u041a\u0410\u0420\u0413\u0410",
        "\u041f\u0420\u041e\u0428\u0423 \u0421\u0423\u0414",
        "\u0441\u0442. 389",
    ),
    "objection_response": (
        "\u0417\u0410\u041f\u0415\u0420\u0415\u0427\u0415\u041d\u041d\u042f \u041d\u0410 \u0412\u0406\u0414\u0417\u0418\u0412",
        "\u041f\u0420\u041e\u0428\u0423",
    ),
    "complaint_executor_actions": (
        "\u0421\u041a\u0410\u0420\u0413\u0410 \u041d\u0410 \u0414\u0406\u0407/\u0411\u0415\u0417\u0414\u0406\u042f\u041b\u042c\u041d\u0406\u0421\u0422\u042c \u0412\u0418\u041a\u041e\u041d\u0410\u0412\u0426\u042f",
        "\u041f\u0420\u041e\u0428\u0423",
    ),
    "statement_enforcement_opening": (
        "\u0417\u0410\u042f\u0412\u0410 \u041f\u0420\u041e \u0412\u0406\u0414\u041a\u0420\u0418\u0422\u0422\u042f \u0412\u0418\u041a\u041e\u041d\u0410\u0412\u0427\u041e\u0413\u041e \u041f\u0420\u041e\u0412\u0410\u0414\u0416\u0415\u041d\u041d\u042f",
        "\u041f\u0420\u041e\u0428\u0423",
    ),
    "statement_enforcement_asset_search": (
        "\u0417\u0410\u042f\u0412\u0410 \u041f\u0420\u041e \u0420\u041e\u0417\u0428\u0423\u041a \u041c\u0410\u0419\u041d\u0410 \u0411\u041e\u0420\u0416\u041d\u0418\u041a\u0410",
        "\u041f\u0420\u041e\u0428\u0423",
    ),
    "complaint_state_inaction": (
        "\u0421\u041a\u0410\u0420\u0413\u0410 \u041d\u0410 \u0411\u0415\u0417\u0414\u0406\u042f\u041b\u042c\u041d\u0406\u0421\u0422\u042c \u0414\u0415\u0420\u0416\u041e\u0420\u0413\u0410\u041d\u0423 (\u041a\u0410\u0421)",
        "\u041f\u0420\u041e\u0428\u0423",
    ),
}

EVIDENCE_HINT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("contract", r"(?:\u0434\u043e\u0433\u043e\u0432\u0456\u0440|contract)"),
    ("receipt", r"(?:\u0440\u043e\u0437\u043f\u0438\u0441\u043a|receipt)"),
    ("bank_statement", r"(?:\u0432\u0438\u043f\u0438\u0441\u043a|\u0431\u0430\u043d\u043a|iban|\u0440\u0430\u0445\u0443\u043d\u043e\u043a|bank statement)"),
    ("correspondence", r"(?:\u043b\u0438\u0441\u0442\u0443\u0432\u0430\u043d|email|e-mail|\u043f\u0435\u0440\u0435\u043f\u0438\u0441\u043a|messenger|viber|telegram)"),
    ("act_or_invoice", r"(?:\u0430\u043a\u0442|\u043d\u0430\u043a\u043b\u0430\u0434\u043d|\u0456\u043d\u0432\u043e\u0439\u0441|invoice)"),
)


def _normalized(text: str) -> str:
    return _repair_mojibake_text(text or "").lower().strip()


def _extract_amount_uah(text: str) -> float | None:
    matches = re.findall(
        r"(\d[\d\s]{2,}(?:[.,]\d{1,2})?)\s*(?:\u0433\u0440\u043d|uah|\u20b4)",
        text or "",
        flags=re.IGNORECASE,
    )
    if not matches:
        return None
    cleaned = matches[0].replace(" ", "").replace(",", ".")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if value <= 0:
        return None
    return round(value, 2)


def _extract_dates(text: str) -> list[date]:
    values: list[date] = []
    seen: set[date] = set()
    for raw in re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", text or ""):
        try:
            parsed = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            continue
        if parsed not in seen:
            seen.add(parsed)
            values.append(parsed)
    for raw in re.findall(r"\b(\d{2}\.\d{2}\.\d{4})\b", text or ""):
        try:
            parsed = datetime.strptime(raw, "%d.%m.%Y").date()
        except ValueError:
            continue
        if parsed not in seen:
            seen.add(parsed)
            values.append(parsed)
    return sorted(values)


def _text_quality_score(value: str) -> float:
    text = str(value or "")
    if not text:
        return float("-inf")
    cyrillic_count = len(re.findall(r"[А-Яа-яІіЇїЄєҐґ]", text))
    latin_count = len(re.findall(r"[A-Za-z]", text))
    marker_count = sum(text.count(marker) for marker in _MOJIBAKE_MARKERS)
    return float(cyrillic_count * 3 + latin_count - marker_count * 5)


def _repair_mojibake_text(value: str) -> str:
    text = str(value or "")
    if not text or not _looks_mojibake(text):
        return text

    candidates = [text]
    for source_encoding in ("cp1250", "latin1", "cp1252"):
        try:
            repaired = text.encode(source_encoding, errors="ignore").decode("utf-8", errors="ignore")
        except Exception:
            continue
        repaired = repaired.strip()
        if repaired:
            candidates.append(repaired)
    return max(candidates, key=_text_quality_score)


def _extract_legal_basis_refs(source_text: str, *, limit: int = 8) -> list[str]:
    text = _repair_mojibake_text(source_text or "")
    matches: list[str] = []
    patterns = (
        r"(?:ст\.?\s*\d{1,4}(?:[-–]\d{1,4})?(?:\s*,\s*\d{1,4})?\s*(?:ЦК|ЦПК|ГК|ГПК|КК|КПК|КАС)\s*України)",
        r"(?:п\.?\s*\d+\s*Перехідних положень\s*(?:ЦК|ЦПК)\s*України)",
        r"(?:ст\.?\s*\d{1,4}(?:[-–]\d{1,4})?\s*Закону України\s+[\"«][^\"»]{3,120}[\"»])",
    )
    seen: set[str] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            candidate = re.sub(r"\s+", " ", (match.group(0) or "").strip(" ,.;:"))
            if not candidate:
                continue
            key = candidate.lower()
            if key in seen:
                continue
            seen.add(key)
            matches.append(candidate)
            if len(matches) >= limit:
                return matches
    return matches


def _parse_json_array(raw_text: str) -> list[str]:
    text = (raw_text or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except Exception:
        pass

    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except Exception:
            pass
    return []


def _parse_json_object(raw_text: str) -> dict[str, Any]:
    text = (raw_text or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {}


def _as_str_list(value: Any, *, max_items: int = 10) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = str(item).strip()
        if not text:
            continue
        result.append(text)
        if len(result) >= max_items:
            break
    return result


def _as_known_doc_type_list(value: Any, *, max_items: int) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        key = str(item).strip()
        if key in KNOWN_DOCUMENT_TYPES and key not in result:
            result.append(key)
        if len(result) >= max_items:
            break
    return result


def _filter_doc_types(
    doc_types: list[str],
    *,
    processual_only: bool,
    limit: int,
) -> list[str]:
    allowed = set(PROCESSUAL_DOCUMENT_TYPES) if processual_only else KNOWN_DOCUMENT_TYPES
    filtered: list[str] = []
    for doc_type in doc_types:
        if doc_type in allowed and doc_type not in filtered:
            filtered.append(doc_type)
        if len(filtered) >= limit:
            break
    return filtered


def suggest_document_types(source_text: str, *, max_documents: int = 3, processual_only: bool = False) -> list[str]:
    safe_limit = max(1, min(max_documents, 5))
    text = _normalized(source_text)
    scores: list[tuple[str, int]] = []

    for doc_type, keywords in DOC_TYPE_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score > 0:
            scores.append((doc_type, score))

    if not scores:
        fallback_candidates = ["lawsuit_debt_loan"]
        if "appeal" in text or "\u0430\u043f\u0435\u043b\u044f\u0446" in text:
            fallback_candidates = ["appeal_complaint", "lawsuit_debt_loan"]
        elif "pretension" in text or "\u043f\u0440\u0435\u0442\u0435\u043d\u0437" in text:
            fallback_candidates = ["pretension_debt_return", "lawsuit_debt_loan"]
        elif "contract" in text or "\u0434\u043e\u0433\u043e\u0432" in text:
            fallback_candidates = ["contract_services", "lawsuit_debt_loan"]
        filtered_fallback = _filter_doc_types(
            fallback_candidates,
            processual_only=processual_only,
            limit=safe_limit,
        )
        return filtered_fallback or ["lawsuit_debt_loan"]

    scores.sort(key=lambda item: item[1], reverse=True)
    recommended_candidates: list[str] = []
    for doc_type, _ in scores:
        if doc_type in KNOWN_DOCUMENT_TYPES and doc_type not in recommended_candidates:
            recommended_candidates.append(doc_type)
        if len(recommended_candidates) >= safe_limit:
            break
    recommended = _filter_doc_types(
        recommended_candidates,
        processual_only=processual_only,
        limit=safe_limit,
    )
    return recommended or ["lawsuit_debt_loan"]


def _normalize_court_name(value: str) -> str:
    candidate = re.sub(r"\s+", " ", str(value or "")).strip(" ,.;:")
    candidate = re.split(
        r"(?i)\b(?:розглянув|розглянула|розглянуто|ухвалив|ухвалила|ухвалено|"
        r"постановив|постановила|постановлено|у\s+складі|у\s+справі|справа\s*№)\b",
        candidate,
        maxsplit=1,
    )[0].strip(" ,.;:")
    candidate = re.split(r"[,;]", candidate, maxsplit=1)[0].strip(" ,.;:")
    return candidate


def _is_plausible_court_name(value: str) -> bool:
    candidate = _normalize_court_name(value)
    if len(candidate) < 8:
        return False

    lowered = candidate.lower()
    if "суд" not in lowered:
        return False

    if lowered.startswith(("чи ", "коли ", "як ", "який ", "яка ", "яке ", "що ", "де ", "чому ")):
        return False
    if any(
        marker in lowered
        for marker in (
            "ключові юридичні питання",
            "контекст для генерації",
            "рекомендована сторона",
            "підсумковий висновок",
        )
    ):
        return False

    explicit_markers = (
        "верхов",
        "апеляц",
        "район",
        "міськ",
        "міськрайон",
        "окруж",
        "господар",
        "адміністратив",
        "касац",
        "місцев",
    )
    if any(marker in lowered for marker in explicit_markers):
        return True
    return bool(re.search(r"(област[іи]|район[уі]|міст[аі]|м\.)", lowered))


def _extract_court_name(raw_text: str) -> str:
    text = str(raw_text or "")
    patterns = (
        r"([А-ЯІЇЄҐA-Z][^\n\r]{3,120}?суд[^\n\r]{0,80})",
        r"((?:верховний|касаційний|апеляційний|окружний|районний|міський|міськрайонний|"
        r"господарський|адміністративний|місцевий)[^\n\r]{0,90}?суд[^\n\r]{0,90})",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            candidate = _normalize_court_name(match.group(1) or "")
            if _is_plausible_court_name(candidate):
                return candidate
    return ""


def extract_parties_and_facts(source_text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    raw_text = _repair_mojibake_text(source_text or "")
    for key, pattern in PARTY_PATTERNS:
        match = re.search(pattern, raw_text, flags=re.IGNORECASE)
        if not match:
            continue
        value = (match.group(1) or "").strip()
        if value:
            result[key] = value

    # Typical court style: "за позовом ... до ... про ..."
    if not result.get("plaintiff_name") or not result.get("defendant_name"):
        claim_match = re.search(
            r"за\s+позовом\s+(.{3,160}?)\s+до\s+(.{3,160}?)(?:\s+про|\s*,|\.)",
            raw_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if claim_match:
            plaintiff = re.sub(r"\s+", " ", claim_match.group(1)).strip(" ,.;:")
            defendant = re.sub(r"\s+", " ", claim_match.group(2)).strip(" ,.;:")
            if plaintiff and not result.get("plaintiff_name"):
                result["plaintiff_name"] = plaintiff
            if defendant and not result.get("defendant_name"):
                result["defendant_name"] = defendant

    # Alternative court wording: "<Party> подало/звернулося з позовом до <Party> ..."
    if not result.get("plaintiff_name") or not result.get("defendant_name"):
        filed_match = re.search(
            r"([А-ЯІЇЄҐA-Z][^.\n]{3,160}?)\s+(?:звернул[ао][ссья]+|подал[аио]?|пред[’']?явив(?:ла)?)\s+"
            r"(?:до\s+суду\s+)?(?:позов|заяву)\s+до\s+(.{3,160}?)(?:\s+про|\s*,|\.)",
            raw_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if filed_match:
            plaintiff = re.sub(r"\s+", " ", filed_match.group(1)).strip(" ,.;:")
            defendant = re.sub(r"\s+", " ", filed_match.group(2)).strip(" ,.;:")
            if plaintiff and not result.get("plaintiff_name"):
                result["plaintiff_name"] = plaintiff
            if defendant and not result.get("defendant_name"):
                result["defendant_name"] = defendant

    case_number = _extract_case_number(raw_text)
    if case_number:
        result["case_number"] = case_number

    court_name = _extract_court_name(raw_text)
    if court_name:
        result["court_name"] = court_name

    compact = " ".join(raw_text.split())
    sentences = [
        re.sub(r"\s+", " ", item).strip(" -–—")
        for item in re.split(r"(?<=[\.\!\?;])\s+", compact)
        if str(item).strip()
    ]
    fact_keywords = (
        "догов",
        "борг",
        "заборгован",
        "простроч",
        "рішення",
        "постан",
        "ухвал",
        "виконав",
        "кредит",
        "позик",
        "стяг",
        "відмов",
        "апеляц",
        "касац",
        "порук",
        "625",
    )
    request_keywords = (
        "просить",
        "просив",
        "просять",
        "прошу",
        "прохає",
        "вимага",
        "заявляє",
        "стягнути",
        "скасувати",
        "визнати",
        "зобов",
        "залишити",
    )

    fact_parts: list[str] = []
    for sentence in sentences:
        lowered = sentence.lower()
        if len(sentence) < 30:
            continue
        if any(keyword in lowered for keyword in fact_keywords):
            fact_parts.append(sentence)
        if len(fact_parts) >= 8:
            break
    if not fact_parts:
        fact_parts = [item for item in sentences if len(item) >= 30][:5]
    fact_summary = " ".join(fact_parts).strip()
    if not fact_summary:
        fact_summary = compact[:1000]
    result["fact_summary"] = fact_summary[:1800]
    if _is_missing_string(result.get("issue_summary")):
        result["issue_summary"] = " ".join(fact_parts[:2]).strip()[:900]

    request_parts: list[str] = []
    for sentence in sentences:
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in request_keywords):
            request_parts.append(sentence)
        if len(request_parts) >= 3:
            break
    request_summary = " ".join(request_parts).strip()
    if not request_summary:
        request_summary = (
            "Просимо суд задовольнити заявлені вимоги на підставі встановлених обставин "
            "та норм матеріального і процесуального права України."
        )
    result["request_summary"] = request_summary[:900]

    chronology_parts: list[str] = []
    chronology_keywords = ("подано", "ухвал", "постан", "рішен", "відкрито", "виконано", "стягнуто")
    for sentence in sentences:
        lowered = sentence.lower()
        has_date_marker = bool(
            re.search(r"\b\d{2}\.\d{2}\.\d{4}\b|\b\d{4}-\d{2}-\d{2}\b", sentence)
        )
        if has_date_marker or any(keyword in lowered for keyword in chronology_keywords):
            chronology_parts.append(sentence)
        if len(chronology_parts) >= 6:
            break
    if not chronology_parts:
        chronology_parts = fact_parts[:3]
    chronology_summary = " ".join(chronology_parts).strip()
    if chronology_summary:
        result["chronology_summary"] = chronology_summary[:1400]

    legal_refs = _extract_legal_basis_refs(raw_text, limit=8)
    if legal_refs:
        result["legal_basis_summary"] = "; ".join(legal_refs)

    risk_sentence = next(
        (
            sentence
            for sentence in sentences
            if any(keyword in sentence.lower() for keyword in ("ризик", "відчуж", "прихов", "невиконан", "арешт"))
        ),
        "",
    )
    if risk_sentence:
        result["risk_of_non_execution_summary"] = risk_sentence[:650]

    evidence_sentence = next(
        (
            sentence
            for sentence in sentences
            if any(keyword in sentence.lower() for keyword in ("доказ", "документ", "виписк", "акт", "листуван"))
        ),
        "",
    )
    if evidence_sentence:
        result["evidence_description"] = evidence_sentence[:700]

    inability_sentence = next(
        (
            sentence
            for sentence in sentences
            if any(keyword in sentence.lower() for keyword in ("неможлив", "не може", "відсутн", "не має доступ"))
        ),
        "",
    )
    if inability_sentence:
        result["inability_reason"] = inability_sentence[:700]

    holder_match = re.search(
        r"(?:витребуват[иьи].{0,80}?у|доказ[аиів]{0,2}\s+у)\s+([^,.;:\n]{3,120})",
        compact,
        flags=re.IGNORECASE,
    )
    if holder_match:
        holder = re.sub(r"\s+", " ", holder_match.group(1)).strip(" ,.;:")
        if holder:
            result["holder_of_evidence"] = holder[:200]

    return result


def _split_text_into_sentences(text: str, *, min_len: int = 24, max_items: int = 50) -> list[str]:
    compact = " ".join(str(text or "").split())
    raw_items = re.split(r"(?<=[\.\!\?;:])\s+", compact)
    rows: list[str] = []
    seen: set[str] = set()
    for raw in raw_items:
        sentence = re.sub(r"\s+", " ", str(raw or "").strip(" -–—"))
        if len(sentence) < min_len:
            continue
        normalized_key = sentence.lower()
        if normalized_key in seen:
            continue
        seen.add(normalized_key)
        rows.append(sentence[:420])
        if len(rows) >= max_items:
            break
    return rows


def _summary_to_points(summary: str, *, max_items: int = 6) -> list[str]:
    points = _split_text_into_sentences(summary, min_len=18, max_items=max_items * 2)
    if points:
        return points[:max_items]
    cleaned = re.sub(r"\s+", " ", str(summary or "").strip())
    if cleaned:
        return [cleaned[:420]]
    return []


def build_document_fact_pack(source_text: str, *, max_items: int = 6) -> dict[str, Any]:
    safe_limit = max(3, min(max_items, 10))
    raw_text = _repair_mojibake_text(source_text or "")
    base = extract_parties_and_facts(raw_text)
    sentences = _split_text_into_sentences(raw_text, min_len=22, max_items=80)

    fact_keywords = (
        "догов",
        "борг",
        "заборгован",
        "простроч",
        "рішення",
        "постан",
        "ухвал",
        "виконав",
        "стяг",
        "порук",
        "апеляц",
        "касац",
        "кредит",
        "позик",
        "розписк",
    )
    chronology_keywords = ("подано", "ухвал", "постан", "рішен", "відкрито", "виконано", "стягнуто", "оскаржен")
    evidence_keywords = ("доказ", "документ", "виписк", "акт", "листуван", "догов", "розписк", "квитанц")
    request_keywords = ("просить", "просив", "прошу", "вимага", "заявляє", "стягнути", "скасувати", "визнати", "зобов")

    factual_points: list[str] = []
    chronology_points: list[str] = []
    evidence_points: list[str] = []
    request_points: list[str] = []

    for sentence in sentences:
        lowered = sentence.lower()
        has_date_marker = bool(re.search(r"\b\d{2}\.\d{2}\.\d{4}\b|\b\d{4}-\d{2}-\d{2}\b", sentence))
        if any(keyword in lowered for keyword in fact_keywords) and sentence not in factual_points:
            factual_points.append(sentence)
        if (has_date_marker or any(keyword in lowered for keyword in chronology_keywords)) and sentence not in chronology_points:
            chronology_points.append(sentence)
        if any(keyword in lowered for keyword in evidence_keywords) and sentence not in evidence_points:
            evidence_points.append(sentence)
        if any(keyword in lowered for keyword in request_keywords) and sentence not in request_points:
            request_points.append(sentence)

    if not factual_points:
        factual_points = _summary_to_points(str(base.get("fact_summary") or ""), max_items=safe_limit)
    if not chronology_points:
        chronology_points = _summary_to_points(str(base.get("chronology_summary") or ""), max_items=safe_limit)
    if not evidence_points:
        evidence_points = _summary_to_points(str(base.get("evidence_description") or ""), max_items=safe_limit)
    if not request_points:
        request_points = _summary_to_points(str(base.get("request_summary") or ""), max_items=3)

    legal_basis_refs = [item.strip() for item in str(base.get("legal_basis_summary") or "").split(";") if item.strip()][:8]

    return {
        "factual_points": factual_points[:safe_limit],
        "chronology_points": chronology_points[:safe_limit],
        "evidence_points": evidence_points[:safe_limit],
        "request_points": request_points[:3],
        "legal_basis_refs": legal_basis_refs,
        "court_name": str(base.get("court_name") or "").strip(),
        "case_number": str(base.get("case_number") or "").strip(),
    }


def _enrich_form_data_with_fact_pack(
    payload: dict[str, Any],
    fact_pack: dict[str, Any],
    *,
    doc_type: str | None = None,
) -> dict[str, Any]:
    merged = dict(payload)
    current_doc_type = str(doc_type or "").strip()
    factual_points = [str(item).strip() for item in (fact_pack.get("factual_points") or []) if str(item).strip()]
    chronology_points = [str(item).strip() for item in (fact_pack.get("chronology_points") or []) if str(item).strip()]
    evidence_points = [str(item).strip() for item in (fact_pack.get("evidence_points") or []) if str(item).strip()]
    request_points = [str(item).strip() for item in (fact_pack.get("request_points") or []) if str(item).strip()]
    legal_basis_refs = [str(item).strip() for item in (fact_pack.get("legal_basis_refs") or []) if str(item).strip()]

    if factual_points:
        merged["factual_points"] = factual_points[:6]
    if chronology_points:
        merged["chronology_points"] = chronology_points[:6]
    if evidence_points:
        merged["evidence_points"] = evidence_points[:6]
    if request_points:
        merged["request_points"] = request_points[:3]

    compact_facts = [*factual_points[:3], *chronology_points[:2]]
    if compact_facts:
        merged["facts_context_digest"] = " ".join(compact_facts)[:1600]

    fact_summary = str(merged.get("fact_summary") or "").strip()
    if _is_missing_string(fact_summary) or len(fact_summary) < 80:
        if compact_facts:
            merged["fact_summary"] = " ".join(compact_facts)[:1800]

    request_summary = str(merged.get("request_summary") or "").strip()
    if _is_missing_string(request_summary) and request_points:
        merged["request_summary"] = " ".join(request_points[:2])[:900]

    existing_claim_requests = (
        [str(item).strip() for item in (merged.get("claim_requests") or []) if str(item).strip()]
        if isinstance(merged.get("claim_requests"), list)
        else []
    )
    if not existing_claim_requests:
        if request_points:
            merged["claim_requests"] = request_points[:3]
        elif request_summary and not _is_missing_string(request_summary):
            merged["claim_requests"] = [request_summary]

    legal_basis_current = merged.get("legal_basis")
    if legal_basis_refs:
        if isinstance(legal_basis_current, list):
            cleaned_basis = [str(item).strip() for item in legal_basis_current if str(item).strip() and not _is_missing_string(str(item))]
            if not cleaned_basis:
                merged["legal_basis"] = legal_basis_refs[:8]
        elif _is_missing_string(legal_basis_current):
            merged["legal_basis"] = legal_basis_refs[:8]

    if current_doc_type in {"appeal_complaint", "cassation_complaint"}:
        case_number = str(fact_pack.get("case_number") or "").strip()
        court_name = str(fact_pack.get("court_name") or "").strip()
        if case_number and _is_missing_string(merged.get("case_number")):
            merged["case_number"] = case_number
        if court_name and _is_missing_string(merged.get("court_name")):
            merged["court_name"] = court_name

    if current_doc_type == "motion_evidence_request":
        if _is_missing_string(merged.get("evidence_description")) and evidence_points:
            merged["evidence_description"] = "; ".join(evidence_points[:3])[:700]

    issue_summary = str(merged.get("issue_summary") or "").strip()
    if _is_missing_string(issue_summary) and factual_points:
        merged["issue_summary"] = factual_points[0][:900]

    return merged


_MOJIBAKE_MARKERS: tuple[str, ...] = ("Đ", "Ń", "Â", "Ã", "Ð", "Ñ", "�")


def _looks_mojibake(value: str) -> bool:
    text = str(value or "")
    return any(marker in text for marker in _MOJIBAKE_MARKERS)


def _sanitize_mojibake_string(*, field: str, value: str, amount: float) -> str:
    text = str(value or "").strip()
    if not text or not _looks_mojibake(text):
        return text
    placeholder_map = {
        "plaintiff_name": "[потрібно уточнити позивача]",
        "plaintiff_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ позивача]",
        "plaintiff_address": "[потрібно уточнити адресу позивача]",
        "defendant_name": "[потрібно уточнити відповідача]",
        "defendant_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ відповідача]",
        "defendant_address": "[потрібно уточнити адресу відповідача]",
        "party_a": "[потрібно уточнити сторону 1]",
        "party_b": "[потрібно уточнити сторону 2]",
        "court_name": "[потрібно уточнити суд]",
        "case_number": "[потрібно уточнити номер справи/провадження]",
        "goods_description": "[потрібно уточнити предмет договору]",
    }
    if field in placeholder_map:
        return placeholder_map[field]
    if field == "request_summary":
        return (
            f"Просимо задовольнити заявлені вимоги та, за наявності підстав, "
            f"стягнути заборгованість у розмірі {amount:.2f} грн."
        )
    if field == "fact_summary":
        return "Обставини справи потребують уточнення та деталізації."
    return "[потрібно уточнити дані]"


def _sanitize_form_data_payload(payload: dict[str, Any], *, amount: float) -> dict[str, Any]:
    claim_request_fallbacks = [
        "Стягнути з відповідача суму основного боргу.",
        "Стягнути передбачені законом проценти/інфляційні втрати (за наявності підстав).",
        "Стягнути судові витрати.",
    ]
    cleaned: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            cleaned[key] = _sanitize_mojibake_string(field=key, value=value, amount=amount)
            continue
        if isinstance(value, list):
            normalized_items: list[Any] = []
            for item in value:
                if isinstance(item, str):
                    fixed = _sanitize_mojibake_string(field=key, value=item, amount=amount)
                    if fixed == "[потрібно уточнити дані]" and key == "claim_requests":
                        fallback = claim_request_fallbacks[len(normalized_items) % len(claim_request_fallbacks)]
                        normalized_items.append(fallback)
                    elif fixed:
                        normalized_items.append(fixed)
                else:
                    normalized_items.append(item)
            cleaned[key] = normalized_items
            continue
        cleaned[key] = value
    return cleaned


def _is_missing_string(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip().lower()
    if not text:
        return True
    if _looks_mojibake(text):
        return True
    return text.startswith("[потрібно уточнити")


def _merge_extracted_defaults(
    payload: dict[str, Any],
    base: dict[str, str],
    *,
    doc_type: str | None = None,
) -> dict[str, Any]:
    merged = dict(payload)
    current_doc_type = str(doc_type or "").strip()

    for field in ("fact_summary", "request_summary", "case_number", "court_name", "issue_summary"):
        current = merged.get(field)
        candidate = str(base.get(field) or "").strip()
        if candidate and _is_missing_string(current):
            merged[field] = candidate

    if _is_missing_string(merged.get("issue_summary")):
        candidate_fact = str(base.get("fact_summary") or "").strip()
        if candidate_fact:
            merged["issue_summary"] = candidate_fact[:900]

    chronology_summary = str(base.get("chronology_summary") or "").strip()
    if chronology_summary:
        if _is_missing_string(merged.get("fact_summary")):
            merged["fact_summary"] = chronology_summary[:1800]
        if _is_missing_string(merged.get("issue_summary")):
            merged["issue_summary"] = chronology_summary[:900]

    risk_summary = str(base.get("risk_of_non_execution_summary") or "").strip()
    if risk_summary and _is_missing_string(merged.get("risk_of_non_execution_summary")):
        merged["risk_of_non_execution_summary"] = risk_summary[:700]

    evidence_description = str(base.get("evidence_description") or "").strip()
    if evidence_description and _is_missing_string(merged.get("evidence_description")):
        merged["evidence_description"] = evidence_description[:700]

    holder_of_evidence = str(base.get("holder_of_evidence") or "").strip()
    if holder_of_evidence and _is_missing_string(merged.get("holder_of_evidence")):
        merged["holder_of_evidence"] = holder_of_evidence[:220]

    inability_reason = str(base.get("inability_reason") or "").strip()
    if inability_reason and _is_missing_string(merged.get("inability_reason")):
        merged["inability_reason"] = inability_reason[:700]

    legal_basis_summary = str(base.get("legal_basis_summary") or "").strip()
    if legal_basis_summary:
        legal_basis_refs = [item.strip() for item in legal_basis_summary.split(";") if item.strip()]
        if isinstance(merged.get("legal_basis"), list):
            raw_existing = [str(item).strip() for item in merged.get("legal_basis") or [] if str(item).strip()]
            existing = [item for item in raw_existing if not _is_missing_string(item)]
            if not existing:
                merged["legal_basis"] = legal_basis_refs[:8]
        elif _is_missing_string(merged.get("legal_basis")):
            merged["legal_basis"] = legal_basis_refs[:8]

    claim_requests = merged.get("claim_requests")
    candidate_request = str(base.get("request_summary") or "").strip()
    if isinstance(claim_requests, list):
        normalized_claims = [
            str(item).strip()
            for item in claim_requests
            if str(item).strip() and not _is_missing_string(str(item))
        ]
        if not normalized_claims and candidate_request:
            normalized_claims.append(candidate_request)
        if normalized_claims:
            merged["claim_requests"] = normalized_claims[:6]

    if current_doc_type in {"appeal_complaint", "cassation_complaint"}:
        base_court = str(base.get("court_name") or "").strip()
        if base_court and _is_missing_string(merged.get("first_instance_court")):
            merged["first_instance_court"] = base_court

    if current_doc_type == "cassation_complaint":
        base_court = str(base.get("court_name") or "").strip()
        if base_court and _is_missing_string(merged.get("appeal_court")):
            merged["appeal_court"] = base_court

    if current_doc_type == "motion_appeal_deadline_renewal":
        base_court = str(base.get("court_name") or "").strip()
        if base_court and _is_missing_string(merged.get("first_instance_court")):
            merged["first_instance_court"] = base_court

    if current_doc_type == "motion_claim_security" and _is_missing_string(merged.get("risk_of_non_execution_summary")):
        fact_candidate = str(base.get("fact_summary") or "").strip()
        if fact_candidate:
            merged["risk_of_non_execution_summary"] = (
                f"Наявні обставини, що свідчать про ризик утруднення виконання рішення: {fact_candidate[:500]}"
            )

    if current_doc_type == "motion_evidence_request":
        fact_candidate = str(base.get("fact_summary") or "").strip()
        if _is_missing_string(merged.get("evidence_description")) and fact_candidate:
            merged["evidence_description"] = (
                "Документи та відомості, що підтверджують ключові факти спору, "
                f"зокрема: {fact_candidate[:450]}"
            )
        if _is_missing_string(merged.get("inability_reason")):
            merged["inability_reason"] = (
                "Заявник не має процесуальної або фактичної можливості самостійно отримати ці докази, "
                "оскільки вони перебувають у володінні іншої сторони або третьої особи."
            )

    return merged


def _build_form_data_for_doc_type_raw(doc_type: str, source_text: str) -> dict[str, Any]:
    base = extract_parties_and_facts(source_text)
    amount = _extract_amount_uah(source_text) or 10000.0
    extracted_dates = _extract_dates(source_text)
    debt_start_date = extracted_dates[0].isoformat() if extracted_dates else "2025-01-01"
    debt_due_date = extracted_dates[1].isoformat() if len(extracted_dates) > 1 else ""
    total_claim = round(amount, 2)
    court_fee = calculate_court_fee(claim_amount_uah=total_claim)

    if doc_type == "lawsuit_debt_loan":
        return {
            "court_mode": "auto",
            "court_name": "",
            "plaintiff_name": base.get("plaintiff_name") or base.get("party_a") or "[потрібно уточнити позивача]",
            "plaintiff_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "plaintiff_address": "[потрібно уточнити адресу позивача]",
            "defendant_name": base.get("defendant_name") or base.get("party_b") or "[потрібно уточнити відповідача]",
            "defendant_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "defendant_address": "[потрібно уточнити адресу відповідача]",
            "debt_basis": "loan",
            "debt_start_date": debt_start_date,
            "debt_due_date": debt_due_date,
            "principal_debt_uah": amount,
            "accrued_interest_uah": 0,
            "penalty_uah": 0,
            "court_fee_uah": court_fee,
            "total_claim_uah": round(total_claim + float(court_fee), 2),
            "claim_requests": [
                "Стягнути з Відповідача суму основного боргу.",
                "Стягнути 3% річних та інфляційні втрати відповідно до ст. 625 ЦК України.",
                "Стягнути з Відповідача судовий збір та інші судові витрати.",
            ],
            "fact_summary": base.get("fact_summary", ""),
        }

    if doc_type == "lawsuit_debt_sale":
        return {
            "court_mode": "auto",
            "court_name": "",
            "plaintiff_name": base.get("plaintiff_name") or base.get("party_a") or "[потрібно уточнити позивача]",
            "plaintiff_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "plaintiff_address": "[потрібно уточнити адресу позивача]",
            "defendant_name": base.get("defendant_name") or base.get("party_b") or "[потрібно уточнити відповідача]",
            "defendant_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "defendant_address": "[потрібно уточнити адресу відповідача]",
            "contract_date": debt_start_date,
            "debt_start_date": debt_start_date,
            "debt_due_date": debt_due_date,
            "goods_description": "[потрібно уточнити предмет договору купівлі-продажу]",
            "principal_debt_uah": amount,
            "accrued_interest_uah": 0,
            "penalty_uah": 0,
            "court_fee_uah": court_fee,
            "total_claim_uah": round(total_claim + float(court_fee), 2),
            "claim_requests": [
                "Стягнути з Відповідача заборгованість за договором купівлі-продажу.",
                "Стягнути 3% річних, інфляційні втрати та/або неустойку.",
                "Стягнути з Відповідача судовий збір та інші судові витрати.",
            ],
            "fact_summary": base.get("fact_summary", ""),
        }

    if doc_type == "appeal_complaint":
        return {
            "plaintiff_name": base.get("plaintiff_name") or base.get("party_a") or "[потрібно уточнити апелянта]",
            "plaintiff_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "plaintiff_address": "[потрібно уточнити адресу апелянта]",
            "defendant_name": base.get("defendant_name") or base.get("party_b") or "[потрібно уточнити іншу сторону]",
            "defendant_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "defendant_address": "[потрібно уточнити адресу іншої сторони]",
            "court_name": "[потрібно уточнити апеляційний суд]",
            "first_instance_court": "[потрібно уточнити суд першої інстанції]",
            "case_number": "[потрібно уточнити номер справи]",
            "decision_date": debt_start_date,
            "fact_summary": base.get("fact_summary", ""),
            "request_summary": "Скасувати рішення суду першої інстанції та ухвалити нове рішення по суті спору.",
        }

    if doc_type == "motion_claim_security":
        return {
            "court_name": "[потрібно уточнити суд]",
            "case_number": "[потрібно уточнити номер справи]",
            "plaintiff_name": base.get("plaintiff_name") or base.get("party_a") or "[потрібно уточнити заявника]",
            "plaintiff_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "plaintiff_address": "[потрібно уточнити адресу заявника]",
            "defendant_name": base.get("defendant_name") or base.get("party_b") or "[потрібно уточнити іншу сторону]",
            "defendant_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "defendant_address": "[потрібно уточнити адресу іншої сторони]",
            "fact_summary": base.get("fact_summary", ""),
            "risk_of_non_execution_summary": "[потрібно уточнити ризик відчуження/приховування майна або інших дій, що унеможливлюють виконання рішення]",
            "request_summary": "Вжити заходів забезпечення позову шляхом накладення арешту на майно/кошти відповідача в межах ціни позову.",
            "legal_basis": ["ст. 149-151 ЦПК України"],
            "attachments": [
                "Докази на підтвердження ризику невиконання рішення",
                "Копії документів для інших учасників",
            ],
        }

    if doc_type == "motion_evidence_request":
        return {
            "court_name": "[потрібно уточнити суд]",
            "case_number": "[потрібно уточнити номер справи]",
            "plaintiff_name": base.get("plaintiff_name") or base.get("party_a") or "[потрібно уточнити заявника]",
            "plaintiff_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "plaintiff_address": "[потрібно уточнити адресу заявника]",
            "defendant_name": base.get("defendant_name") or base.get("party_b") or "[потрібно уточнити іншу сторону]",
            "defendant_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "defendant_address": "[потрібно уточнити адресу іншої сторони]",
            "fact_summary": base.get("fact_summary", ""),
            "evidence_description": "[потрібно уточнити, які саме докази потрібно витребувати]",
            "holder_of_evidence": "[потрібно уточнити, у кого знаходяться докази]",
            "inability_reason": "[потрібно уточнити, чому неможливо самостійно отримати докази]",
            "request_summary": "Витребувати у відповідної особи докази, що мають значення для правильного вирішення спору.",
            "legal_basis": ["ст. 84, 95 ЦПК України"],
            "attachments": [
                "Копії запитів про надання доказів (за наявності)",
                "Копії документів для інших учасників",
            ],
        }

    if doc_type == "motion_expertise":
        return {
            "court_name": "[потрібно уточнити суд]",
            "case_number": "[потрібно уточнити номер справи]",
            "plaintiff_name": base.get("plaintiff_name") or base.get("party_a") or "[потрібно уточнити заявника]",
            "plaintiff_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "plaintiff_address": "[потрібно уточнити адресу заявника]",
            "defendant_name": base.get("defendant_name") or base.get("party_b") or "[потрібно уточнити іншу сторону]",
            "defendant_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "defendant_address": "[потрібно уточнити адресу іншої сторони]",
            "fact_summary": base.get("fact_summary", ""),
            "expertise_type": "судова експертиза",
            "expert_questions": [
                "Які обставини справи підтверджуються матеріалами, наданими на дослідження?",
                "Чи є причинно-наслідковий зв'язок між встановленими обставинами та заявленими вимогами?",
            ],
            "request_summary": "Призначити експертизу та поставити експерту питання, наведені у клопотанні.",
            "legal_basis": ["ст. 103, 104 ЦПК України"],
            "attachments": [
                "Матеріали для дослідження експертом",
                "Копії документів для інших учасників",
            ],
        }

    if doc_type == "motion_court_fee_deferral":
        return {
            "court_name": "[потрібно уточнити суд]",
            "case_number": "[потрібно уточнити номер справи]",
            "plaintiff_name": base.get("plaintiff_name") or base.get("party_a") or "[потрібно уточнити заявника]",
            "plaintiff_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "plaintiff_address": "[потрібно уточнити адресу заявника]",
            "defendant_name": base.get("defendant_name") or base.get("party_b") or "[потрібно уточнити іншу сторону]",
            "defendant_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "defendant_address": "[потрібно уточнити адресу іншої сторони]",
            "fact_summary": base.get("fact_summary", ""),
            "financial_hardship_summary": "[потрібно уточнити обставини, що підтверджують неможливість одноразової сплати судового збору]",
            "court_fee_uah": court_fee,
            "request_summary": "Відстрочити/розстрочити сплату судового збору з урахуванням майнового стану заявника.",
            "legal_basis": ["ст. 136 ЦПК України", "ст. 8 Закону України \"Про судовий збір\""],
            "attachments": [
                "Довідки про доходи та майновий стан",
                "Документи, що підтверджують фінансові труднощі",
            ],
        }

    if doc_type == "motion_appeal_deadline_renewal":
        return {
            "court_name": "[потрібно уточнити апеляційний суд]",
            "case_number": base.get("case_number") or "[потрібно уточнити номер справи]",
            "first_instance_court": base.get("court_name") or "[потрібно уточнити суд першої інстанції]",
            "plaintiff_name": base.get("plaintiff_name") or base.get("party_a") or "[потрібно уточнити заявника]",
            "plaintiff_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "plaintiff_address": "[потрібно уточнити адресу заявника]",
            "defendant_name": base.get("defendant_name") or base.get("party_b") or "[потрібно уточнити іншу сторону]",
            "defendant_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "defendant_address": "[потрібно уточнити адресу іншої сторони]",
            "decision_date": debt_start_date,
            "service_date": debt_start_date,
            "fact_summary": base.get("fact_summary", ""),
            "delay_reason": (
                "Строк апеляційного оскарження пропущено з поважних причин, "
                "які підтверджуються доданими доказами."
            ),
            "request_summary": (
                "Поновити строк апеляційного оскарження та прийняти апеляційну скаргу до розгляду."
            ),
            "legal_basis": ["ст. 127, 354 ЦПК України"],
            "attachments": [
                "Копія апеляційної скарги з додатками",
                "Докази поважності причин пропуску строку",
                "Копія оскаржуваного рішення (за наявності)",
            ],
        }

    if doc_type == "lawsuit_alimony":
        return {
            "court_mode": "auto",
            "court_name": "",
            "plaintiff_name": base.get("plaintiff_name") or base.get("party_a") or "[потрібно уточнити позивача]",
            "plaintiff_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "plaintiff_address": "[потрібно уточнити адресу позивача]",
            "defendant_name": base.get("defendant_name") or base.get("party_b") or "[потрібно уточнити відповідача]",
            "defendant_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "defendant_address": "[потрібно уточнити адресу відповідача]",
            "debt_start_date": debt_start_date,
            "court_fee_uah": court_fee,
            "total_claim_uah": round(total_claim + float(court_fee), 2),
            "fact_summary": base.get("fact_summary", ""),
            "request_summary": "Стягнути аліменти на утримання дитини у розмірі, визначеному судом.",
            "claim_requests": [
                "Стягнути з Відповідача аліменти на утримання дитини у розмірі, визначеному судом.",
                "Визначити початок нарахування аліментів з дня подання позову.",
                "Стягнути з Відповідача судові витрати Позивача.",
            ],
        }

    if doc_type == "lawsuit_property_division":
        return {
            "court_mode": "auto",
            "court_name": "",
            "plaintiff_name": base.get("plaintiff_name") or base.get("party_a") or "[потрібно уточнити позивача]",
            "plaintiff_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "plaintiff_address": "[потрібно уточнити адресу позивача]",
            "defendant_name": base.get("defendant_name") or base.get("party_b") or "[потрібно уточнити відповідача]",
            "defendant_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "defendant_address": "[потрібно уточнити адресу відповідача]",
            "debt_start_date": debt_start_date,
            "court_fee_uah": court_fee,
            "total_claim_uah": round(total_claim + float(court_fee), 2),
            "fact_summary": base.get("fact_summary", ""),
            "request_summary": "Поділити спільне майно подружжя у порядку, визначеному судом.",
            "claim_requests": [
                "Визнати за Позивачем право власності на частку у спільному майні подружжя.",
                "Поділити спільне майно подружжя у спосіб, визначений судом.",
                "Стягнути з Відповідача судові витрати Позивача.",
            ],
        }

    if doc_type == "lawsuit_damages":
        return {
            "court_mode": "auto",
            "court_name": "",
            "plaintiff_name": base.get("plaintiff_name") or base.get("party_a") or "[потрібно уточнити позивача]",
            "plaintiff_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "plaintiff_address": "[потрібно уточнити адресу позивача]",
            "defendant_name": base.get("defendant_name") or base.get("party_b") or "[потрібно уточнити відповідача]",
            "defendant_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "defendant_address": "[потрібно уточнити адресу відповідача]",
            "debt_start_date": debt_start_date,
            "court_fee_uah": court_fee,
            "total_claim_uah": round(total_claim + float(court_fee), 2),
            "fact_summary": base.get("fact_summary", ""),
            "request_summary": "Стягнути з Відповідача майнову та/або моральну шкоду.",
            "claim_requests": [
                "Стягнути з Відповідача майнову шкоду у визначеному судом розмірі.",
                "Стягнути з Відповідача моральну шкоду (за наявності підстав).",
                "Стягнути з Відповідача судові витрати Позивача.",
            ],
        }

    if doc_type == "cassation_complaint":
        return {
            "plaintiff_name": base.get("plaintiff_name") or base.get("party_a") or "[потрібно уточнити скаржника]",
            "plaintiff_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "plaintiff_address": "[потрібно уточнити адресу скаржника]",
            "defendant_name": base.get("defendant_name") or base.get("party_b") or "[потрібно уточнити іншу сторону]",
            "defendant_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "defendant_address": "[потрібно уточнити адресу іншої сторони]",
            "court_name": "[потрібно уточнити суд касаційної інстанції]",
            "first_instance_court": "[потрібно уточнити суд першої інстанції]",
            "appeal_court": "[потрібно уточнити апеляційний суд]",
            "case_number": "[потрібно уточнити номер справи]",
            "decision_date": debt_start_date,
            "fact_summary": base.get("fact_summary", ""),
            "request_summary": "Скасувати оскаржувані судові рішення та ухвалити нове рішення/направити справу на новий розгляд.",
            "cassation_deadline_note": "Касаційну скаргу подано у межах процесуального строку.",
            "attachments": [
                "Копії касаційної скарги для інших учасників справи",
                "Документ про сплату судового збору",
                "Копії оскаржуваних судових рішень",
            ],
        }

    if doc_type == "objection_response":
        return {
            "court_name": "[потрібно уточнити суд]",
            "case_number": "[потрібно уточнити номер справи]",
            "plaintiff_name": base.get("plaintiff_name") or base.get("party_a") or "[потрібно уточнити заявника]",
            "plaintiff_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "plaintiff_address": "[потрібно уточнити адресу заявника]",
            "defendant_name": base.get("defendant_name") or base.get("party_b") or "[потрібно уточнити іншу сторону]",
            "defendant_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "defendant_address": "[потрібно уточнити адресу іншої сторони]",
            "fact_summary": base.get("fact_summary", ""),
            "issue_summary": "Доводи відзиву не відповідають фактичним обставинам справи.",
            "request_summary": "Відхилити доводи відзиву та врахувати заперечення при вирішенні спору.",
            "attachments": ["Докази на спростування доводів відзиву"],
        }

    if doc_type == "complaint_executor_actions":
        return {
            "court_name": "[потрібно уточнити суд]",
            "case_number": "[потрібно уточнити номер виконавчого провадження]",
            "plaintiff_name": base.get("plaintiff_name") or base.get("party_a") or "[потрібно уточнити заявника]",
            "plaintiff_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "plaintiff_address": "[потрібно уточнити адресу заявника]",
            "defendant_name": base.get("defendant_name") or "[потрібно уточнити виконавця]",
            "defendant_tax_id": "[потрібно уточнити службові реквізити]",
            "defendant_address": "[потрібно уточнити адресу/орган виконавця]",
            "fact_summary": base.get("fact_summary", ""),
            "issue_summary": "Виконавець не вчиняє передбачені законом виконавчі дії/вчинив неправомірні дії.",
            "request_summary": "Визнати дії/бездіяльність виконавця протиправними та зобов'язати усунути порушення.",
            "attachments": ["Копії постанов/документів виконавчого провадження"],
        }

    if doc_type == "statement_enforcement_opening":
        return {
            "court_name": "[потрібно уточнити орган ДВС/приватного виконавця]",
            "case_number": "[потрібно уточнити реквізити виконавчого документа]",
            "plaintiff_name": base.get("plaintiff_name") or base.get("party_a") or "[потрібно уточнити стягувача]",
            "plaintiff_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "plaintiff_address": "[потрібно уточнити адресу стягувача]",
            "defendant_name": base.get("defendant_name") or base.get("party_b") or "[потрібно уточнити боржника]",
            "defendant_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ боржника]",
            "defendant_address": "[потрібно уточнити адресу боржника]",
            "fact_summary": "Наявний виконавчий документ, що підлягає примусовому виконанню.",
            "issue_summary": base.get("fact_summary", ""),
            "request_summary": "Відкрити виконавче провадження та вжити заходів примусового виконання.",
            "attachments": ["Оригінал/дублікат виконавчого документа"],
        }

    if doc_type == "statement_enforcement_asset_search":
        return {
            "court_name": "[потрібно уточнити орган ДВС/приватного виконавця]",
            "case_number": "[потрібно уточнити номер виконавчого провадження]",
            "plaintiff_name": base.get("plaintiff_name") or base.get("party_a") or "[потрібно уточнити стягувача]",
            "plaintiff_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "plaintiff_address": "[потрібно уточнити адресу стягувача]",
            "defendant_name": base.get("defendant_name") or base.get("party_b") or "[потрібно уточнити боржника]",
            "defendant_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ боржника]",
            "defendant_address": "[потрібно уточнити адресу боржника]",
            "fact_summary": base.get("fact_summary", ""),
            "issue_summary": "Боржник не виконує рішення добровільно, необхідно встановити наявне майно для стягнення.",
            "request_summary": "Вжити заходів щодо розшуку майна боржника та повідомити про результати.",
            "attachments": ["Відомості про можливі активи боржника"],
        }

    if doc_type == "complaint_state_inaction":
        return {
            "court_name": "[потрібно уточнити адміністративний суд]",
            "case_number": "[потрібно уточнити номер звернення/провадження]",
            "plaintiff_name": base.get("plaintiff_name") or base.get("party_a") or "[потрібно уточнити позивача]",
            "plaintiff_tax_id": "[потрібно уточнити РНОКПП/ЄДРПОУ]",
            "plaintiff_address": "[потрібно уточнити адресу позивача]",
            "defendant_name": base.get("defendant_name") or "[потрібно уточнити суб'єкта владних повноважень]",
            "defendant_tax_id": "[потрібно уточнити ЄДРПОУ органу]",
            "defendant_address": "[потрібно уточнити адресу органу]",
            "fact_summary": base.get("fact_summary", ""),
            "issue_summary": "Суб'єкт владних повноважень не вчинив обов'язкові дії у встановлений строк.",
            "request_summary": "Визнати бездіяльність протиправною та зобов'язати держорган вчинити визначені законом дії.",
            "attachments": ["Копії звернень до держоргану та докази їх подання"],
        }
    if doc_type == "pretension_debt_return":
        return {
            "party_a": base.get("plaintiff_name") or base.get("party_a") or "[потрібно уточнити кредитора]",
            "party_b": base.get("defendant_name") or base.get("party_b") or "[потрібно уточнити боржника]",
            "fact_summary": base.get("fact_summary", ""),
            "request_summary": f"Вимагаємо добровільно погасити заборгованість у розмірі {amount:.2f} грн.",
        }

    return {
        "party_a": base.get("plaintiff_name") or base.get("party_a") or "[потрібно уточнити сторону 1]",
        "party_b": base.get("defendant_name") or base.get("party_b") or "[потрібно уточнити сторону 2]",
        "fact_summary": base.get("fact_summary", ""),
        "request_summary": base.get("request_summary", ""),
    }


def build_form_data_for_doc_type(doc_type: str, source_text: str) -> dict[str, Any]:
    payload = _build_form_data_for_doc_type_raw(doc_type, source_text)
    base = extract_parties_and_facts(source_text)
    fact_pack = build_document_fact_pack(source_text, max_items=6)
    amount = _extract_amount_uah(source_text) or 10000.0
    payload = _sanitize_form_data_payload(payload, amount=float(amount))
    payload = _merge_extracted_defaults(payload, base, doc_type=doc_type)
    payload = _enrich_form_data_with_fact_pack(payload, fact_pack, doc_type=doc_type)
    return _sanitize_form_data_payload(payload, amount=float(amount))


def _default_request_summary_for_doc_type(doc_type: str) -> str:
    defaults = {
        "lawsuit_debt_loan": "Стягнути основний борг, передбачені законом нарахування та судові витрати.",
        "lawsuit_debt_sale": "Стягнути заборгованість за договором купівлі-продажу та судові витрати.",
        "appeal_complaint": "Скасувати рішення суду першої інстанції та ухвалити нове рішення у справі.",
        "cassation_complaint": "Скасувати оскаржувані рішення та ухвалити нове рішення або направити справу на новий розгляд.",
        "motion_claim_security": "Вжити заходів забезпечення позову для гарантування виконання майбутнього рішення.",
        "motion_evidence_request": "Витребувати докази, що мають істотне значення для вирішення спору.",
        "motion_expertise": "Призначити експертизу з постановкою питань, необхідних для встановлення обставин справи.",
        "motion_court_fee_deferral": "Відстрочити або розстрочити сплату судового збору з огляду на майновий стан заявника.",
        "motion_appeal_deadline_renewal": "Поновити строк апеляційного оскарження та прийняти апеляційну скаргу до розгляду.",
        "objection_response": "Відхилити доводи відзиву та врахувати заперечення під час вирішення спору.",
    }
    return defaults.get(doc_type, "Задовольнити заявлені процесуальні вимоги в повному обсязі.")


def auto_repair_form_data_for_generation(
    doc_type: str,
    source_text: str,
    form_data: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    current_type = (doc_type or "").strip()
    repaired: dict[str, Any] = dict(form_data or {})
    notes: list[str] = []

    base = extract_parties_and_facts(source_text)
    fact_pack = build_document_fact_pack(source_text, max_items=6)
    extracted_dates = _extract_dates(source_text)

    plaintiff = str(repaired.get("plaintiff_name") or repaired.get("party_a") or "").strip()
    if _is_missing_string(plaintiff):
        candidate = str(base.get("plaintiff_name") or base.get("party_a") or "").strip()
        repaired["plaintiff_name"] = candidate or "Позивач уточнюється за матеріалами справи."
        notes.append("Заповнено/уточнено поле позивача.")

        repaired["party_b"] = str(repaired.get("defendant_name") or "").strip()
    if _is_missing_string(defendant):
        candidate = str(base.get("defendant_name") or base.get("party_b") or "").strip()
        repaired["defendant_name"] = candidate or "Відповідач уточнюється за матеріалами справи."
        notes.append("Заповнено/уточнено поле відповідача.")

    if "party_a" in repaired and _is_missing_string(repaired.get("party_a")):
        repaired["party_a"] = str(repaired.get("plaintiff_name") or "").strip()
    if "party_b" in repaired and _is_missing_string(repaired.get("party_b")):
        repaired["party_b"] = str(repaired.get("defendant_name") or "").strip()

    if current_type in {
        "motion_claim_security",
        "motion_evidence_request",
        "motion_expertise",
        "motion_court_fee_deferral",
        "motion_appeal_deadline_renewal",
        "objection_response",
        "complaint_executor_actions",
        "statement_enforcement_opening",
        "statement_enforcement_asset_search",
        "complaint_state_inaction",
    }:
        court_name = str(repaired.get("court_name") or "").strip()
        if _is_missing_string(court_name):
            candidate = str(base.get("court_name") or fact_pack.get("court_name") or "").strip()
            repaired["court_name"] = candidate or "Найменування суду/органу уточнюється за матеріалами справи."
            notes.append("Додано базове найменування суду/органу.")

    fact_summary = str(repaired.get("fact_summary") or "").strip()
    if _is_missing_string(fact_summary):
        fallback_fact = ""
        if fact_pack.get("factual_points"):
            fallback_fact = " ".join(str(item) for item in (fact_pack.get("factual_points") or [])[:3]).strip()
        if not fallback_fact:
            fallback_fact = str(base.get("fact_summary") or "").strip()
        if fallback_fact:
            repaired["fact_summary"] = fallback_fact[:1800]
            notes.append("Дозаповнено фактичний виклад обставин.")

    request_summary = str(repaired.get("request_summary") or "").strip()
    if _is_missing_string(request_summary):
        fallback_request = ""
        request_points = [str(item).strip() for item in (fact_pack.get("request_points") or []) if str(item).strip()]
        if request_points:
            fallback_request = " ".join(request_points[:2]).strip()
        if not fallback_request:
            claim_requests = [str(item).strip() for item in (repaired.get("claim_requests") or []) if str(item).strip()]
            if claim_requests:
                fallback_request = " ".join(claim_requests[:2]).strip()
        repaired["request_summary"] = fallback_request or _default_request_summary_for_doc_type(current_type)
        notes.append("Дозаповнено прохальну частину.")

    if current_type in {"lawsuit_debt_loan", "lawsuit_debt_sale"}:
        debt_start_date = str(repaired.get("debt_start_date") or "").strip()
        if not debt_start_date and extracted_dates:
            repaired["debt_start_date"] = extracted_dates[0].isoformat()
            notes.append("Встановлено дату початку/порушення зобов'язання.")

        try:
            principal = float(repaired.get("principal_debt_uah") or 0)
        except Exception:
            principal = 0.0
        if principal <= 0:
            extracted_amount = _extract_amount_uah(source_text)
            if extracted_amount is None:
                try:
                    extracted_amount = float(repaired.get("total_claim_uah") or 0)
                except Exception:
                    extracted_amount = 0.0
            principal = extracted_amount if extracted_amount and extracted_amount > 0 else 10000.0
            repaired["principal_debt_uah"] = round(float(principal), 2)
            notes.append("Відновлено/нормалізовано суму основного боргу.")

    if current_type == "motion_evidence_request":
        evidence_description = str(repaired.get("evidence_description") or "").strip()
        if _is_missing_string(evidence_description):
            evidence_points = [str(item).strip() for item in (fact_pack.get("evidence_points") or []) if str(item).strip()]
            if evidence_points:
                repaired["evidence_description"] = "; ".join(evidence_points[:3])
            else:
                repaired["evidence_description"] = (
                    "Потрібні докази, що підтверджують істотні факти спору, "
                    "перебувають у володінні іншої сторони/третьої особи."
                )
            notes.append("Дозаповнено опис доказів для клопотання.")

    if current_type == "motion_appeal_deadline_renewal":
        decision_date = str(repaired.get("decision_date") or "").strip()
        if not decision_date and extracted_dates:
            repaired["decision_date"] = extracted_dates[0].isoformat()
            notes.append("Додано дату оскаржуваного рішення.")
        if _is_missing_string(repaired.get("delay_reason")):
            repaired["delay_reason"] = (
                "Строк подання апеляційної скарги пропущено з поважних причин, "
                "що підтверджуються документами, доданими до заяви."
            )
            notes.append("Дозаповнено обґрунтування поважності причин пропуску строку.")

    claim_requests = repaired.get("claim_requests")
    if isinstance(claim_requests, list):
        normalized_claims = [str(item).strip() for item in claim_requests if str(item).strip() and not _is_missing_string(str(item))]
        if not normalized_claims and str(repaired.get("request_summary") or "").strip():
            normalized_claims = [str(repaired.get("request_summary")).strip()]
            notes.append("Відновлено список позовних вимог.")
        repaired["claim_requests"] = normalized_claims

    repaired = _merge_extracted_defaults(repaired, base, doc_type=current_type)
    repaired = _enrich_form_data_with_fact_pack(repaired, fact_pack, doc_type=current_type)

    amount = _extract_amount_uah(source_text)
    if amount is None:
        try:
            amount = float(repaired.get("principal_debt_uah") or repaired.get("total_claim_uah") or 10000.0)
        except Exception:
            amount = 10000.0
    repaired = _sanitize_form_data_payload(repaired, amount=float(amount))
    return repaired, notes


async def build_procedural_conclusions(source_text: str, *, max_items: int = 8) -> list[str]:
    safe_limit = max(1, min(max_items, 20))
    system_prompt = (
        "Ти практикуючий український процесуальний юрист. Поверни лише JSON-масив коротких "
        "процесуальних висновків за текстом. Без markdown і без пояснень."
    )
    user_prompt = (
        "Сформуй процесуальні висновки для підготовки справи за текстом нижче.\n\n"
        f"{(source_text or '')[:12000]}\n\n"
        f"Максимум пунктів: {safe_limit}."
    )

    ai_result = await generate_legal_document(system_prompt, user_prompt)
    if ai_result.used_ai and (ai_result.text or "").strip():
        parsed = _parse_json_array(ai_result.text)
        if parsed:
            return parsed[:safe_limit]

    text = _normalized(source_text)
    amount = _extract_amount_uah(source_text)
    fallback: list[str] = []
    if amount:
        fallback.append(f"Виявлено орієнтовну ціну позову: {amount:.2f} грн.")
    if "\u0431\u043e\u0440\u0433" in text or "debt" in text or "\u0437\u0430\u0431\u043e\u0440\u0433\u043e\u0432\u0430\u043d" in text:
        fallback.append("Спір має ознаки стягнення заборгованості; рекомендовано готувати позов про стягнення боргу.")
    if "\u0440\u043e\u0437\u043f\u0438\u0441\u043a" in text or "\u043f\u043e\u0437\u0438\u043a" in text or "loan" in text:
        fallback.append("Виявлено ознаки позики/розписки; обґрунтуйте вимоги посиланням на ст. 1046, 1049, 625 ЦК України.")
    if "\u0430\u043f\u0435\u043b\u044f\u0446" in text or "appeal" in text:
        fallback.append("Виявлено ознаки апеляційного оскарження; перевірте процесуальні строки подання апеляційної скарги.")
    if "\u0434\u043e\u043a\u0430\u0437" in text or "evidence" in text or "\u0434\u043e\u0434\u0430\u0442" in text:
        fallback.append("Сформуйте матрицю доказів: належність, допустимість і зв'язок з обставинами справи.")
    fallback.append("Перед поданням перевірте підсудність, ціну позову та коректність розрахунку судового збору.")
    return fallback[:safe_limit]


async def build_full_lawyer_brief(
    source_text: str,
    *,
    max_documents: int = 4,
    processual_only: bool = False,
) -> dict[str, Any]:
    safe_limit = max(1, min(max_documents, 5))
    system_prompt = (
        "Ти старший український судовий юрист. Поверни лише JSON-об'єкт з ключами: "
        "dispute_type, procedure, urgency, claim_amount_uah, legal_basis, strategy_steps, "
        "evidence_required, risks, missing_information, recommended_documents. "
        "procedure має бути одним зі значень: civil, commercial, administrative. "
        "urgency має бути одним зі значень: low, medium, high. "
        "Весь текстовий контент (окрім кодів типів документів) подай українською."
    )
    user_prompt = (
        "Проаналізуй завантажений документ і сформуй об'єкт юридичної стратегії.\n\n"
        f"{(source_text or '')[:14000]}\n\n"
        f"Максимум recommended_documents: {safe_limit}. "
        "recommended_documents повинні бути значеннями з набору: lawsuit_debt_loan, lawsuit_debt_sale, "
        "appeal_complaint, motion_claim_security, motion_evidence_request, motion_expertise, "
        "motion_court_fee_deferral, motion_appeal_deadline_renewal, lawsuit_alimony, lawsuit_property_division, lawsuit_damages, "
        "cassation_complaint, objection_response, complaint_executor_actions, statement_enforcement_opening, "
        "statement_enforcement_asset_search, complaint_state_inaction, pretension_debt_return, contract_services. "
        "ВАЖЛИВО: Якщо завантажений документ є РІШЕННЯМ, ПОСТАНОВОЮ чи УХВАЛОЮ суду, пропонуй логічний НАСТУПНИЙ крок "
        "(наприклад, апеляційну чи касаційну скаргу, заяву про видачу виконавчого листа, відкриття провадження), "
        "а не сам позов, у якому це рішення вже винесено. "
        "Стратегія має бути практичною: з конкретними діями, доказами, ризиками та пробілами даних."
    )

    ai_result = await generate_legal_document(system_prompt, user_prompt)
    if ai_result.used_ai and ai_result.text.strip():
        parsed = _parse_json_object(ai_result.text)
        if parsed:
            recommended = _as_known_doc_type_list(parsed.get("recommended_documents"), max_items=safe_limit)
            recommended = _filter_doc_types(
                recommended,
                processual_only=processual_only,
                limit=safe_limit,
            )
            if not recommended:
                recommended = suggest_document_types(
                    source_text,
                    max_documents=safe_limit,
                    processual_only=processual_only,
                )
            urgency_raw = str(parsed.get("urgency") or "medium").strip().lower()
            urgency_mapping = {
                "low": "low",
                "низька": "low",
                "низкий": "low",
                "medium": "medium",
                "середня": "medium",
                "середній": "medium",
                "high": "high",
                "висока": "high",
                "високий": "high",
            }
            urgency = urgency_mapping.get(urgency_raw, "medium")
            procedure_raw = str(parsed.get("procedure") or "civil").strip().lower()
            procedure_mapping = {
                "civil": "civil",
                "цивільна": "civil",
                "цивільний": "civil",
                "commercial": "commercial",
                "господарська": "commercial",
                "господарський": "commercial",
                "administrative": "administrative",
                "адміністративна": "administrative",
                "адміністративний": "administrative",
            }
            procedure = procedure_mapping.get(procedure_raw, "civil")
            claim_amount = parsed.get("claim_amount_uah")
            if claim_amount is not None:
                try:
                    claim_amount = round(float(claim_amount), 2)
                except Exception:
                    claim_amount = _extract_amount_uah(source_text)
            return {
                "dispute_type": str(parsed.get("dispute_type") or "Загальний цивільний спір").strip(),
                "procedure": procedure,
                "urgency": urgency,
                "claim_amount_uah": claim_amount if claim_amount is not None else _extract_amount_uah(source_text),
                "legal_basis": _as_str_list(parsed.get("legal_basis"), max_items=10),
                "strategy_steps": _as_str_list(parsed.get("strategy_steps"), max_items=12),
                "evidence_required": _as_str_list(parsed.get("evidence_required"), max_items=12),
                "risks": _as_str_list(parsed.get("risks"), max_items=10),
                "missing_information": _as_str_list(parsed.get("missing_information"), max_items=12),
                "recommended_documents": recommended,
            }

    text = _normalized(source_text)
    amount = _extract_amount_uah(source_text)
    dispute_type = "Загальний цивільний спір"
    procedure = "civil"
    urgency = "medium"

    if "\u0430\u043f\u0435\u043b\u044f\u0446" in text or "appeal" in text:
        dispute_type = "Апеляційне оскарження"
        procedure = "civil"
        urgency = "high"
    elif "\u0431\u043e\u0440\u0433" in text or "debt" in text or "\u0437\u0430\u0431\u043e\u0440\u0433\u043e\u0432\u0430\u043d" in text:
        dispute_type = "Спір про стягнення заборгованості"
    elif "\u0430\u0434\u043c\u0456\u043d" in text or "administrative" in text:
        dispute_type = "Адміністративний спір"
        procedure = "administrative"

    if "\u0441\u0442\u0440\u043e\u043a" in text or "\u0442\u0435\u0440\u043c\u0456\u043d\u043e\u0432" in text or "urgent" in text:
        urgency = "high"

    legal_basis: list[str] = [
        "ЦПК України: підсудність, форма процесуальних документів, правила доказування.",
        "ЦК України: зобов'язання, відповідальність за порушення, відшкодування.",
    ]
    if dispute_type == "Спір про стягнення заборгованості":
        legal_basis.append("ЦК України: статті 1046, 1049, 625.")
    if dispute_type == "Апеляційне оскарження":
        legal_basis.append("ЦПК України: норми щодо строків і підстав апеляційного оскарження.")

    strategy_steps: list[str] = [
        "Уточнити сторони, підсудність і поточну процесуальну стадію.",
        "Побудувати матрицю «факт -> доказ -> норма права».",
        "Перевірити розрахунок суми вимог, штрафних нарахувань і судового збору.",
        "Підготувати досудову вимогу, якщо це потрібно або тактично доцільно.",
        "Сформувати пакет процесуальних документів і провести юридичну вичитку перед поданням.",
    ]
    evidence_required: list[str] = [
        "Базовий договір і всі додатки/додаткові угоди.",
        "Підтвердження платежів (виписки, інвойси, квитанції).",
        "Листування, що підтверджує порушення і повідомлення контрагента.",
        "Документи про повноваження представника (довіреність тощо).",
    ]
    if "\u0440\u043e\u0437\u043f\u0438\u0441\u043a" in text:
        evidence_required.append("Оригінал розписки та матеріали для підтвердження автентичності підпису.")

    risks: list[str] = [
        "Недостатність первинних доказів виникнення зобов'язання або його порушення.",
        "Неправильна підсудність або хибно обрана процесуальна процедура.",
        "Ризик пропуску позовної давності чи строку оскарження.",
        "Помилки в розрахунку суми вимог і судового збору.",
    ]
    missing_information: list[str] = [
        "Повні ідентифікаційні дані сторін (найменування/ПІБ, ІПН/ЄДРПОУ, адреса).",
        "Точна дата порушення та хронологія комунікації між сторонами.",
        "Підтверджений розклад суми вимог (основний борг, відсотки, штрафи, збір).",
        "Чіткий перелік позовних вимог для прохальної частини.",
    ]

    return {
        "dispute_type": dispute_type,
        "procedure": procedure,
        "urgency": urgency,
        "claim_amount_uah": amount,
        "legal_basis": legal_basis,
        "strategy_steps": strategy_steps,
        "evidence_required": evidence_required,
        "risks": risks,
        "missing_information": missing_information,
        "recommended_documents": suggest_document_types(
            source_text,
            max_documents=safe_limit,
            processual_only=processual_only,
        ),
    }


def build_clarifying_questions(
    source_text: str,
    *,
    missing_information: list[str] | None = None,
    max_items: int = 8,
) -> list[str]:
    safe_limit = max(1, min(max_items, 12))
    base_missing = [item.strip() for item in (missing_information or []) if str(item).strip()]
    questions: list[str] = []
    seen: set[str] = set()

    for item in base_missing:
        q = f"Підтвердіть, будь ласка: {item}"
        if q not in seen:
            seen.add(q)
            questions.append(q)
        if len(questions) >= safe_limit:
            return questions

    text = _normalized(source_text)
    if _extract_amount_uah(source_text) is None:
        questions.append("Який точний розклад суми вимог (основний борг, відсотки, штрафи, судовий збір)?")
    if "appeal" in text or "\u0430\u043f\u0435\u043b\u044f\u0446" in text:
        questions.append("Яка точна дата отримання повного тексту рішення суду першої інстанції?")
    if "debt" in text or "\u0431\u043e\u0440\u0433" in text:
        questions.append("Які саме документи підтверджують передачу коштів і дату настання строку виконання боргу?")

    parties = extract_parties_and_facts(source_text)
    if not parties.get("plaintiff_name"):
        questions.append("Надайте повні дані позивача: найменування/ПІБ, ІПН/ЄДРПОУ, адреса, контакти.")
    if not parties.get("defendant_name"):
        questions.append("Надайте повні дані відповідача: найменування/ПІБ, ІПН/ЄДРПОУ, адреса, контакти.")

    deduped: list[str] = []
    for item in questions:
        key = item.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(key)
        if len(deduped) >= safe_limit:
            break
    return deduped


def parse_clarification_answers(raw_json: str | None) -> dict[str, str]:
    if not raw_json or not raw_json.strip():
        return {}
    try:
        parsed = json.loads(raw_json)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in parsed.items():
        q = str(key).strip()
        answer = str(value).strip()
        if not q or not answer:
            continue
        result[q] = answer
    return result


def resolve_clarifying_questions(
    questions: list[str],
    answers: dict[str, str],
) -> tuple[list[str], list[str]]:
    normalized_answers = {str(k).strip().lower(): str(v).strip() for k, v in (answers or {}).items() if str(v).strip()}
    resolved: list[str] = []
    unresolved: list[str] = []
    for question in questions:
        key = question.strip().lower()
        if key in normalized_answers:
            resolved.append(question)
        else:
            unresolved.append(question)
    return resolved, unresolved


def build_rule_validation_checks(source_text: str, brief: dict[str, Any]) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []

    amount = brief.get("claim_amount_uah")
    if amount is None:
        amount = _extract_amount_uah(source_text)
    try:
        amount_value = round(float(amount), 2) if amount is not None else None
    except Exception:
        amount_value = None

    if amount_value is None or amount_value <= 0:
        checks.append(
            {
                "code": "claim_amount_detected",
                "status": "warn",
                "message": "Суму вимог не визначено. Розрахунок судового збору та штрафних нарахувань може бути неточним.",
            }
        )
    else:
        court_fee = calculate_court_fee(amount_value)
        checks.append(
            {
                "code": "claim_amount_detected",
                "status": "pass",
                "message": f"Суму вимог визначено ({amount_value} грн). Орієнтовний мінімальний судовий збір: {court_fee} грн.",
            }
        )

    parties = extract_parties_and_facts(source_text)
    has_plaintiff = bool(parties.get("plaintiff_name") or parties.get("party_a"))
    has_defendant = bool(parties.get("defendant_name") or parties.get("party_b"))
    if has_plaintiff and has_defendant:
        checks.append(
            {
                "code": "party_identification",
                "status": "pass",
                "message": "У завантаженому матеріалі ідентифіковано обидві сторони спору.",
            }
        )
    else:
        checks.append(
            {
                "code": "party_identification",
                "status": "warn",
                "message": "Дані сторін неповні. Потрібні повні найменування/ПІБ та адреси.",
            }
        )

    extracted_dates = _extract_dates(source_text)
    if extracted_dates:
        earliest = extracted_dates[0]
        age_days = max((date.today() - earliest).days, 0)
        if age_days > 365 * 3:
            checks.append(
                {
                    "code": "limitation_precheck",
                    "status": "warn",
                    "message": (
                        f"Найраніша виявлена дата: {earliest.isoformat()} (понад 3 роки тому). "
                        "Перевірте ризик спливу позовної давності."
                    ),
                }
            )
        else:
            checks.append(
                {
                    "code": "limitation_precheck",
                    "status": "pass",
                    "message": "Виявлені дати не свідчать про очевидний сплив позовної давності.",
                }
            )
    else:
        checks.append(
            {
                "code": "limitation_precheck",
                "status": "warn",
                "message": "Для попередньої перевірки позовної давності не виявлено надійних дат порушення/рішення.",
            }
        )

    procedure = str(brief.get("procedure") or "civil").lower()
    if procedure in {"civil", "commercial", "administrative"}:
        checks.append(
            {
                "code": "procedure_route",
                "status": "pass",
                "message": f"Попередньо визначено процесуальний маршрут: '{procedure}'.",
            }
        )
    else:
        checks.append(
            {
                "code": "procedure_route",
                "status": "warn",
                "message": "Процесуальний маршрут неочевидний. Перевірте юрисдикцію і підсудність вручну.",
            }
        )

    dispute_type = str(brief.get("dispute_type") or "").lower()
    source_text_lower = _normalized(source_text)
    appeal_scope = (
        "appeal" in dispute_type
        or "апеляц" in dispute_type
        or "appeal" in source_text_lower
        or "апеляц" in source_text_lower
    )
    cassation_scope = (
        "cassation" in dispute_type
        or "касац" in dispute_type
        or "cassation" in source_text_lower
        or "касац" in source_text_lower
    )

    if appeal_scope:
        if extracted_dates:
            latest = extracted_dates[-1]
            age_days = max((date.today() - latest).days, 0)
            if age_days > settings.appeal_deadline_days:
                checks.append(
                    {
                        "code": "appeal_deadline_precheck",
                        "status": "warn",
                        "message": (
                            f"Найпізніша виявлена дата: {latest.isoformat()} "
                            f"(понад {settings.appeal_deadline_days} днів). "
                            "Є ризик пропуску строку апеляційного оскарження."
                        ),
                    }
                )
            else:
                checks.append(
                    {
                        "code": "appeal_deadline_precheck",
                        "status": "pass",
                        "message": (
                            f"Строк апеляційного оскарження попередньо вкладається у "
                            f"{settings.appeal_deadline_days}-денне вікно за виявленими датами."
                        ),
                    }
                )
        else:
            checks.append(
                {
                    "code": "appeal_deadline_precheck",
                    "status": "warn",
                    "message": (
                        "Виявлено апеляційний контур спору, але немає надійних дат рішення/вручення "
                        "для перевірки строку."
                    ),
                }
            )

    if cassation_scope:
        if extracted_dates:
            latest = extracted_dates[-1]
            age_days = max((date.today() - latest).days, 0)
            if age_days > settings.cassation_deadline_days:
                checks.append(
                    {
                        "code": "cassation_deadline_precheck",
                        "status": "warn",
                        "message": (
                            f"Найпізніша виявлена дата: {latest.isoformat()} "
                            f"(понад {settings.cassation_deadline_days} днів). "
                            "Є ризик пропуску строку касаційного оскарження."
                        ),
                    }
                )
            else:
                checks.append(
                    {
                        "code": "cassation_deadline_precheck",
                        "status": "pass",
                        "message": (
                            f"Строк касаційного оскарження попередньо вкладається у "
                            f"{settings.cassation_deadline_days}-денне вікно за виявленими датами."
                        ),
                    }
                )
        else:
            checks.append(
                {
                    "code": "cassation_deadline_precheck",
                    "status": "warn",
                    "message": (
                        "Виявлено касаційний контур спору, але немає надійних дат апеляційного акта/вручення "
                        "для перевірки строку."
                    ),
                }
            )

    return checks


def build_financial_snapshot(source_text: str, brief: dict[str, Any]) -> dict[str, Any]:
    amount = brief.get("claim_amount_uah")
    if amount is None:
        amount = _extract_amount_uah(source_text)
    try:
        principal_uah = round(float(amount), 2) if amount is not None else None
    except Exception:
        principal_uah = None

    snapshot: dict[str, Any] = {
        "principal_uah": principal_uah,
        "estimated_court_fee_uah": None,
        "estimated_penalty_uah": None,
        "estimated_total_with_fee_uah": None,
        "debt_start_date": None,
        "debt_end_date": date.today().isoformat(),
    }
    if principal_uah is None or principal_uah <= 0:
        return snapshot

    snapshot["estimated_court_fee_uah"] = calculate_court_fee(principal_uah)
    extracted_dates = _extract_dates(source_text)
    if extracted_dates:
        debt_start = extracted_dates[0]
        snapshot["debt_start_date"] = debt_start.isoformat()
        snapshot["estimated_penalty_uah"] = calculate_penalty(
            principal_uah=principal_uah,
            debt_start_date=debt_start,
            debt_end_date=date.today(),
        )

    total = principal_uah + float(snapshot["estimated_court_fee_uah"] or 0) + float(snapshot["estimated_penalty_uah"] or 0)
    snapshot["estimated_total_with_fee_uah"] = round(total, 2)
    return snapshot


def build_next_actions(
    *,
    recommended_doc_types: list[str],
    clarifying_questions: list[str],
    validation_checks: list[dict[str, str]],
) -> list[str]:
    actions: list[str] = []
    if clarifying_questions:
        actions.append("Надайте відповіді на уточнювальні питання та закрийте всі фактичні прогалини.")
    warn_count = sum(1 for item in validation_checks if str(item.get("status")) == "warn")
    if warn_count:
        actions.append("Усуньте всі попередження pre-check (давність, сторони, сума, строки) до подання.")
    actions.append("Підготуйте належно засвідчений пакет доказів і зв'яжіть кожен факт з підтвердженням.")
    if recommended_doc_types:
        actions.append(f"Згенеруйте та вичитайте пріоритетні документи: {', '.join(recommended_doc_types)}.")
    actions.append("Проведіть фінальну правову перевірку юрисдикції, судового збору та прохальної частини.")
    return actions[:8]


def estimate_confidence_score(
    *,
    summary: dict[str, Any],
    validation_checks: list[dict[str, str]],
    clarifying_questions: list[str],
    unresolved_questions: list[str] | None = None,
    case_law_refs_count: int,
) -> float:
    score = 0.45
    if summary.get("claim_amount_uah") is not None:
        score += 0.1
    if summary.get("dispute_type"):
        score += 0.05
    pass_count = sum(1 for item in validation_checks if str(item.get("status")) == "pass")
    warn_count = sum(1 for item in validation_checks if str(item.get("status")) == "warn")
    score += min(pass_count * 0.05, 0.2)
    score -= min(warn_count * 0.05, 0.2)
    pending_questions = unresolved_questions if unresolved_questions is not None else clarifying_questions
    score -= min(len(pending_questions) * 0.02, 0.2)
    score += min(case_law_refs_count * 0.02, 0.1)
    return round(max(0.05, min(score, 0.99)), 2)


def build_law_context_refs_for_doc_types(doc_types: list[str]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for doc_type in doc_types:
        for item in DOC_TYPE_LAW_REFERENCES.get(doc_type, ()):
            if item in seen:
                continue
            seen.add(item)
            refs.append(
                {
                    "source": "zakon.rada.gov.ua",
                    "ref_type": "law",
                    "reference": item,
                    "note": "Базова правова норма для перевірки актуальної редакції.",
                    "relevance_score": None,
                }
            )
    return refs


async def build_analysis_highlights(
    source_text: str,
    *,
    summary: dict[str, Any],
    max_items: int = 8,
) -> list[str]:
    safe_limit = max(1, min(max_items, 12))
    system_prompt = (
        "Ти практикуючий український судовий юрист. Поверни лише JSON-масив стислих аналітичних тез "
        "для стратегії у справі. Без markdown і без пояснень поза JSON."
    )
    user_prompt = (
        "Сформуй короткі практичні тези для юридичної команди.\n"
        f"Підсумок справи (JSON):\n{json.dumps(summary, ensure_ascii=False)}\n\n"
        f"Текст джерела:\n{(source_text or '')[:12000]}\n\n"
        f"Максимум пунктів: {safe_limit}."
    )

    ai_result = await generate_legal_document(system_prompt, user_prompt)
    if ai_result.used_ai and ai_result.text.strip():
        parsed = _parse_json_array(ai_result.text)
        if parsed:
            return parsed[:safe_limit]

    fallback: list[str] = []
    dispute_type = str(summary.get("dispute_type") or "").strip()
    if dispute_type:
        fallback.append(f"Профіль спору: {dispute_type}.")
    claim_amount = summary.get("claim_amount_uah")
    if claim_amount is not None:
        fallback.append(f"Базова сума вимог за виявленими даними: {claim_amount} грн.")
    for item in _as_str_list(summary.get("strategy_steps"), max_items=4):
        fallback.append(f"Стратегія: {item}")
    for item in _as_str_list(summary.get("risks"), max_items=3):
        fallback.append(f"Ризик: {item}")
    if not fallback:
        fallback.append("Підготуйте повну матрицю доказів і перевірте процесуальний маршрут перед поданням.")
    return fallback[:safe_limit]


def build_document_processual_checks(
    generated_documents: list[dict[str, Any]],
) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    for item in generated_documents:
        doc_type = str(item.get("doc_type") or "").strip()
        text = str(item.get("_generated_text") or "").strip()
        markers = DOC_TYPE_REQUIRED_MARKERS.get(doc_type, ())
        if not markers:
            continue
        lowered = text.lower()
        missing = [marker for marker in markers if marker.lower() not in lowered]
        if missing:
            checks.append(
                {
                    "code": f"doc_quality_{doc_type}",
                    "status": "warn",
                    "message": (
                        f"У згенерованому документі {doc_type} відсутні обов'язкові маркери: {', '.join(missing)}. "
                        "Перевірте та доопрацюйте документ до подання."
                    ),
                }
            )
        else:
            checks.append(
                {
                    "code": f"doc_quality_{doc_type}",
                    "status": "pass",
                    "message": f"Документ {doc_type} містить ключові маркери процесуальної структури.",
                }
            )
    return checks


def build_review_checklist(
    *,
    summary: dict[str, Any],
    validation_checks: list[dict[str, str]],
    recommended_doc_types: list[str],
) -> list[dict[str, Any]]:
    warn_count = sum(1 for item in validation_checks if str(item.get("status")) == "warn")
    items: list[dict[str, Any]] = [
        {
            "code": "confirm_parties_and_addresses",
            "title": "Підтвердити повні ідентифікаційні дані сторін",
            "description": "ПІБ/найменування, ІПН/ЄДРПОУ та адреси мають бути повними і перевіреними.",
            "required": True,
        },
        {
            "code": "confirm_claim_amount_breakdown",
            "title": "Підтвердити розклад суми вимог",
            "description": "Основний борг, відсотки, штрафи та судовий збір мають бути звірені.",
            "required": True,
        },
        {
            "code": "confirm_jurisdiction_and_procedure",
            "title": "Підтвердити юрисдикцію і процесуальний маршрут",
            "description": "Перед поданням має бути обрано правильний суд і процедуру.",
            "required": True,
        },
        {
            "code": "confirm_evidence_matrix",
            "title": "Підтвердити матрицю допустимості доказів",
            "description": "Кожне фактичне твердження має бути пов'язане з належним і допустимим доказом.",
            "required": True,
        },
    ]

    dispute_type = str(summary.get("dispute_type") or "").lower()
    if "appeal" in dispute_type or "апеляц" in dispute_type or "appeal_complaint" in recommended_doc_types:
        items.append(
            {
                "code": "confirm_appeal_deadline",
                "title": "Підтвердити строк апеляційного оскарження",
                "description": "Потрібно перевірити дату отримання повного рішення і кінцевий строк подання.",
                "required": True,
            }
        )

    if warn_count > 0:
        items.append(
            {
                "code": "confirm_warning_overrides",
                "title": "Закрити або погодити всі попередження валідації",
                "description": "Кожне попередження має бути усунуте або явно погоджене відповідальним юристом.",
                "required": True,
            }
        )

    return items


def parse_review_confirmations(raw_json: str | None) -> dict[str, bool]:
    if not raw_json or not raw_json.strip():
        return {}
    try:
        parsed = json.loads(raw_json)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}

    result: dict[str, bool] = {}
    for key, value in parsed.items():
        code = str(key).strip()
        if not code:
            continue
        if isinstance(value, bool):
            result[code] = value
            continue
        raw = str(value).strip().lower()
        result[code] = raw in {"1", "true", "yes", "y", "ok", "confirmed", "підтверджено", "так"}
    return result


def resolve_review_checklist(
    checklist: list[dict[str, Any]],
    confirmations: dict[str, bool],
) -> list[str]:
    unresolved: list[str] = []
    for item in checklist:
        code = str(item.get("code") or "").strip()
        required = bool(item.get("required"))
        if not code or not required:
            continue
        if confirmations.get(code):
            continue
        title = str(item.get("title") or code)
        unresolved.append(title)
    return unresolved


def build_procedural_timeline(
    source_text: str,
    *,
    summary: dict[str, Any],
    recommended_doc_types: list[str],
) -> list[dict[str, Any]]:
    extracted_dates = _extract_dates(source_text)
    today = date.today()
    dispute_type = str(summary.get("dispute_type") or "").lower()
    is_appeal = "appeal" in dispute_type or "апеляц" in dispute_type or "appeal_complaint" in recommended_doc_types
    is_cassation = "cassation" in dispute_type or "касац" in dispute_type or "cassation_complaint" in recommended_doc_types

    timeline: list[dict[str, Any]] = [
        {
            "code": "today_review",
            "title": "Current review date",
            "date": today.isoformat(),
            "status": "info",
            "note": "Baseline date used for deadline pre-checks.",
        }
    ]

    if extracted_dates:
        violation_date = extracted_dates[0]
        limitation_deadline = calculate_limitation_deadline(violation_date, years=3)
        timeline.append(
            {
                "code": "violation_detected",
                "title": "Earliest detected violation/event date",
                "date": violation_date.isoformat(),
                "status": "info",
                "note": "Detected from uploaded text; verify with source evidence.",
            }
        )
        limitation_status = "warn" if limitation_deadline < today else "ok"
        timeline.append(
            {
                "code": "limitation_deadline",
                "title": "Limitation period deadline (3 years)",
                "date": limitation_deadline.isoformat(),
                "status": limitation_status,
                "note": "Calculated under general 3-year civil limitation period.",
            }
        )

        filing_target = calculate_deadline(today, settings.full_lawyer_timeline_target_days)
        timeline.append(
            {
                "code": "target_filing",
                "title": "Recommended target filing date",
                "date": filing_target.isoformat(),
                "status": "info",
                "note": "Internal operational target to keep momentum.",
            }
        )

        if is_appeal:
            decision_date = extracted_dates[-1]
            appeal_deadline = calculate_deadline(decision_date, settings.appeal_deadline_days)
            appeal_status = "warn" if appeal_deadline < today else "ok"
            timeline.append(
                {
                    "code": "appeal_deadline",
                    "title": "Appeal filing deadline pre-check",
                    "date": appeal_deadline.isoformat(),
                    "status": appeal_status,
                    "note": "Pre-check based on configured appeal window; verify procedural specifics.",
                }
            )
        if is_cassation:
            appellate_act_date = extracted_dates[-1]
            cassation_deadline = calculate_deadline(appellate_act_date, settings.cassation_deadline_days)
            cassation_status = "warn" if cassation_deadline < today else "ok"
            timeline.append(
                {
                    "code": "cassation_deadline",
                    "title": "Cassation filing deadline pre-check",
                    "date": cassation_deadline.isoformat(),
                    "status": cassation_status,
                    "note": "Pre-check based on configured cassation window; verify procedural specifics.",
                }
            )
    else:
        timeline.append(
            {
                "code": "missing_dates",
                "title": "Missing reliable case dates",
                "date": None,
                "status": "warn",
                "note": "No reliable dates detected. Deadline control cannot be trusted.",
            }
        )

    return timeline[:8]


def build_evidence_matrix(
    source_text: str,
    *,
    evidence_required: list[str],
) -> list[dict[str, Any]]:
    lowered = _normalized(source_text)
    matrix: list[dict[str, Any]] = []
    for code, pattern in EVIDENCE_HINT_PATTERNS:
        found = bool(re.search(pattern, lowered, flags=re.IGNORECASE))
        matrix.append(
            {
                "code": code,
                "title": code.replace("_", " ").title(),
                "found_in_source": found,
                "status": "ok" if found else "missing",
                "note": "Detected in uploaded text." if found else "Not explicitly detected in uploaded text.",
            }
        )

    for item in evidence_required[:8]:
        matrix.append(
            {
                "code": f"required_{len(matrix)+1}",
                "title": item,
                "found_in_source": None,
                "status": "required",
                "note": "Required by strategy; confirm and attach.",
            }
        )
    return matrix[:12]


def _infer_timeline_actor(snippet: str) -> str:
    lowered = (snippet or "").lower()
    if any(token in lowered for token in ("суд", "court", "ухвал", "постан", "рішення")):
        return "суд"
    if any(token in lowered for token in ("позивач", "заявник", "plaintiff", "кредитор", "банк")):
        return "позивач"
    if any(token in lowered for token in ("відповідач", "боржник", "defendant", "поручител")):
        return "відповідач"
    if any(token in lowered for token in ("виконав", "державн", "приватн")):
        return "виконавець/орган"
    return "невизначено"


def _infer_timeline_event(snippet: str) -> tuple[str, str]:
    lowered = (snippet or "").lower()
    if any(token in lowered for token in ("ухвал", "постан", "рішення", "суд")):
        return "Судова процесуальна подія", "high"
    if any(token in lowered for token in ("догов", "кредит", "позик", "розписк")):
        return "Подія щодо основного зобов'язання", "high"
    if any(token in lowered for token in ("оплат", "переказ", "виписк", "плат")):
        return "Платіжна/фінансова подія", "medium"
    if any(token in lowered for token in ("простроч", "поруш", "невикон")):
        return "Подія порушення або прострочення", "high"
    if any(token in lowered for token in ("лист", "повідом", "претензі", "вимог")):
        return "Комунікаційна подія між сторонами", "medium"
    return "Фактова подія зі справи", "medium"


def _format_ua_date(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "дата не встановлена"
    candidate = raw.split("T", 1)[0]
    try:
        parsed = date.fromisoformat(candidate)
        return parsed.strftime("%d.%m.%Y")
    except Exception:
        return raw


def build_fact_chronology_matrix(
    *,
    source_text: str,
    procedural_timeline: list[dict[str, Any]],
    evidence_matrix: list[dict[str, Any]],
    max_items: int = 10,
) -> list[dict[str, Any]]:
    safe_limit = max(3, min(max_items, 15))
    prepared_text = _repair_mojibake_text(source_text or "")
    dates = _extract_dates(prepared_text)
    sentences = [chunk.strip() for chunk in re.split(r"(?<=[.!?])\s+|\n+", prepared_text) if chunk.strip()]

    items: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for value in dates[:10]:
        variants = (value.isoformat(), value.strftime("%d.%m.%Y"))
        snippet = ""
        for sentence in sentences:
            if any(variant in sentence for variant in variants):
                snippet = sentence
                break
        if not snippet:
            for variant in variants:
                idx = prepared_text.find(variant)
                if idx >= 0:
                    start = max(0, idx - 120)
                    end = min(len(prepared_text), idx + len(variant) + 120)
                    snippet = prepared_text[start:end].strip()
                    break
        snippet = snippet[:260]
        event, relevance = _infer_timeline_event(snippet)
        actor = _infer_timeline_actor(snippet)
        key = f"{value.isoformat()}|{event}|{actor}".lower()
        if key in seen_keys:
            continue
        seen_keys.add(key)
        items.append(
            {
                "event": event,
                "event_date": value.isoformat(),
                "actor": actor,
                "evidence_status": "detected",
                "source_excerpt": snippet or None,
                "relevance": relevance,
            }
        )
        if len(items) >= safe_limit:
            return items

    for item in procedural_timeline:
        status = str(item.get("status") or "").strip().lower()
        if status not in {"warn", "urgent"}:
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        timeline_date = str(item.get("date") or "").strip() or None
        key = f"{timeline_date}|{title}".lower()
        if key in seen_keys:
            continue
        seen_keys.add(key)
        items.append(
            {
                "event": title,
                "event_date": timeline_date,
                "actor": "процесуальний контроль",
                "evidence_status": "inferred",
                "source_excerpt": str(item.get("note") or "").strip() or None,
                "relevance": "high",
            }
        )
        if len(items) >= safe_limit:
            return items

    missing_count = sum(1 for item in evidence_matrix if str(item.get("status") or "").strip() == "missing")
    if not items:
        items.append(
            {
                "event": "Недостатньо дат та подій для побудови надійної хронології",
                "event_date": None,
                "actor": "невизначено",
                "evidence_status": "missing",
                "source_excerpt": "Потрібно додати документи з датами ключових процесуальних і фактичних подій.",
                "relevance": "high",
            }
        )
    elif missing_count > 0 and len(items) < safe_limit:
        items.append(
            {
                "event": "У хронології є потенційні прогалини, пов'язані з відсутніми доказами",
                "event_date": None,
                "actor": "контроль якості",
                "evidence_status": "missing",
                "source_excerpt": f"Виявлено відсутніх доказів: {missing_count}.",
                "relevance": "high",
            }
        )

    return items[:safe_limit]


def build_burden_of_proof_map(
    *,
    legal_argument_map: list[dict[str, Any]],
    evidence_matrix: list[dict[str, Any]],
    party_profile: dict[str, Any],
    max_items: int = 8,
) -> list[dict[str, Any]]:
    safe_limit = max(3, min(max_items, 12))
    missing_titles = [str(item.get("title") or "").strip() for item in evidence_matrix if str(item.get("status")) == "missing"]
    required_titles = [str(item.get("title") or "").strip() for item in evidence_matrix if str(item.get("status")) == "required"]
    ok_titles = [str(item.get("title") or "").strip() for item in evidence_matrix if str(item.get("status")) == "ok"]

    plaintiff_detected = bool(party_profile.get("plaintiff_detected"))
    defendant_detected = bool(party_profile.get("defendant_detected"))
    default_burden = "позивач" if plaintiff_detected else ("відповідач" if defendant_detected else "невизначено")

    items: list[dict[str, Any]] = []
    for idx, row in enumerate(legal_argument_map[:safe_limit], start=1):
        issue = str(row.get("issue") or f"Питання {idx}").strip()
        lowered_issue = issue.lower()
        burden_on = default_burden
        if any(token in lowered_issue for token in ("запереч", "відзив", "objection", "rebuttal")):
            burden_on = "відповідач"

        required_pool = [title for title in [*required_titles[:2], *missing_titles[:1], *ok_titles[:1]] if title]
        if missing_titles and not ok_titles:
            current_status = "gap"
            action = "Терміново додайте первинні докази, інакше доказовий обов'язок не буде виконаний."
        elif missing_titles:
            current_status = "partial"
            action = "Закрийте відсутні докази та деталізуйте посилання на них у тексті документа."
        else:
            current_status = "covered"
            action = "Підтримуйте зв'язку «твердження - доказ - норма» у фінальній редакції."

        items.append(
            {
                "issue": issue,
                "burden_on": burden_on,
                "required_evidence": required_pool or ["Уточніть доказову базу вручну"],
                "current_status": current_status,
                "recommended_action": action,
            }
        )

    if not items:
        items.append(
            {
                "issue": "Базове питання доказування у справі",
                "burden_on": default_burden,
                "required_evidence": (missing_titles[:2] or required_titles[:2] or ["Уточніть ключові докази"]),
                "current_status": "partial" if missing_titles else "covered",
                "recommended_action": "Побудуйте таблицю доказування для кожної позовної вимоги та кожного заперечення.",
            }
        )

    return items[:safe_limit]


def build_drafting_instructions(
    *,
    recommended_doc_types: list[str],
    summary: dict[str, Any],
    legal_basis: list[str],
    evidence_matrix: list[dict[str, Any]],
    deadline_control: list[dict[str, Any]],
    max_items: int = 8,
) -> list[dict[str, Any]]:
    safe_limit = max(2, min(max_items, 10))
    doc_templates: dict[str, dict[str, list[str]]] = {
        "lawsuit_debt_loan": {
            "must_include": [
                "Реквізити сторін і підсудність.",
                "Опис виникнення боргу та момент прострочення.",
                "Розрахунок суми вимог (тіло боргу, 3% річних, інфляція, збір).",
                "Чітка прохальна частина за ст. 175 ЦПК.",
            ],
            "legal_focus": ["ЦК України: ст. 1046, 1049, 625.", "ЦПК України: ст. 175, 177."],
            "style_notes": [
                "Кожен абзац завершуйте посиланням на доказ.",
                "У прохальній частині використовуйте нумерований перелік вимог.",
            ],
        },
        "appeal_complaint": {
            "must_include": [
                "Дата отримання повного рішення першої інстанції.",
                "Конкретні помилки суду першої інстанції (факт/право/процедура).",
                "Формулювання меж апеляційного перегляду.",
                "Окремі прохання: скасувати, змінити або ухвалити нове рішення.",
            ],
            "legal_focus": ["ЦПК України: ст. 352-356.", "Практика ВС щодо меж апеляційного перегляду."],
            "style_notes": [
                "Аргументи подавайте блоками: помилка суду -> норма -> наслідок.",
                "Уникайте загальних оціночних фраз без прив'язки до матеріалів справи.",
            ],
        },
        "cassation_complaint": {
            "must_include": [
                "Касаційний фільтр: конкретне питання права.",
                "Обґрунтування неоднакового застосування норм права або відступу від практики.",
                "Посилання на релевантні постанови ВС/ВП.",
                "Лаконічну та точну прохальну частину.",
            ],
            "legal_focus": ["ЦПК України: ст. 389-392, 400.", "Практика ВС щодо касаційних підстав."],
            "style_notes": [
                "Не переказуйте повністю факти; фокусуйтеся на помилці в застосуванні права.",
                "Окремо виділіть правове питання, важливе для єдності практики.",
            ],
        },
    }

    dispute_type = str(summary.get("dispute_type") or "").strip() or "спір"
    missing_evidence = [str(item.get("title") or "").strip() for item in evidence_matrix if str(item.get("status")) == "missing"]
    supporting_evidence = [str(item.get("title") or "").strip() for item in evidence_matrix if str(item.get("status")) == "ok"]
    urgent_deadline = any(str(item.get("status") or "").strip().lower() in {"warn", "urgent"} for item in deadline_control)

    instructions: list[dict[str, Any]] = []
    for doc_type in recommended_doc_types[:safe_limit]:
        template = doc_templates.get(
            doc_type,
            {
                "must_include": [
                    "Реквізити сторін та суду.",
                    "Виклад обставин з посиланням на докази.",
                    "Належну правову аргументацію та чітку прохальну частину.",
                ],
                "legal_focus": (legal_basis[:2] or ["Уточніть правову базу під цей тип документа."]),
                "style_notes": [
                    "Дотримуйтесь офіційно-ділового процесуального стилю.",
                    "Кожну тезу підкріплюйте доказом або нормативним посиланням.",
                ],
            },
        )
        factual_focus = [item for item in [*missing_evidence[:2], *supporting_evidence[:1]] if item]
        if not factual_focus:
            factual_focus = [f"Уточнити фактичну основу для документа ({dispute_type})."]
        status = "warn" if urgent_deadline or bool(missing_evidence) else "ok"
        instructions.append(
            {
                "doc_type": doc_type,
                "must_include": template.get("must_include", []),
                "factual_focus": factual_focus,
                "legal_focus": template.get("legal_focus", []),
                "style_notes": template.get("style_notes", []),
                "status": status,
            }
        )

    if not instructions:
        instructions.append(
            {
                "doc_type": "general_procedural_draft",
                "must_include": [
                    "Коректні реквізити сторін і суду.",
                    "Структурований опис обставин та доказів.",
                    "Чітка прохальна частина.",
                ],
                "factual_focus": missing_evidence[:2] or ["Уточнити ключові факти спору."],
                "legal_focus": legal_basis[:2] or ["Уточнити нормативну базу."],
                "style_notes": ["Перед поданням виконайте фінальну процесуальну вичитку."],
                "status": "warn",
            }
        )

    return instructions[:safe_limit]


def build_opponent_weakness_map(
    *,
    validation_checks: list[dict[str, Any]],
    contradiction_hotspots: list[dict[str, Any]],
    opponent_objections: list[dict[str, Any]],
    evidence_admissibility_map: list[dict[str, Any]],
    max_items: int = 8,
) -> list[dict[str, str]]:
    safe_limit = max(2, min(max_items, 12))
    map_items: list[dict[str, str]] = []
    preferred_evidence = next(
        (str(item.get("evidence") or "").strip() for item in evidence_admissibility_map if str(item.get("risk") or "") == "low"),
        "первинні письмові докази та офіційні виписки",
    )

    for hotspot in contradiction_hotspots[:4]:
        issue = str(hotspot.get("issue") or "").strip()
        if not issue:
            continue
        severity = str(hotspot.get("severity") or "medium").strip().lower()
        fix = str(hotspot.get("fix") or "Уточнити суперечність у фактах і нормах.").strip()
        map_items.append(
            {
                "weakness": issue,
                "severity": severity,
                "exploitation_step": f"Поставити акцент на суперечності та вимагати її процесуального усунення. {fix}",
                "supporting_basis": "Внутрішня суперечність позиції опонента/матеріалів.",
                "evidentiary_need": preferred_evidence,
            }
        )
        if len(map_items) >= safe_limit:
            return map_items

    for objection in opponent_objections[:4]:
        weakness = str(objection.get("objection") or "").strip()
        rebuttal = str(objection.get("rebuttal") or "").strip()
        likelihood = str(objection.get("likelihood") or "medium").strip().lower()
        if not weakness:
            continue
        map_items.append(
            {
                "weakness": weakness,
                "severity": likelihood if likelihood in {"low", "medium", "high"} else "medium",
                "exploitation_step": rebuttal or "Підготуйте структуроване спростування з опорою на докази.",
                "supporting_basis": "Прогнозована лінія захисту опонента.",
                "evidentiary_need": preferred_evidence,
            }
        )
        if len(map_items) >= safe_limit:
            return map_items

    warn_count = sum(1 for item in validation_checks if str(item.get("status") or "").strip() == "warn")
    if not map_items and warn_count > 0:
        map_items.append(
            {
                "weakness": f"Процесуальна позиція опонента може бути нестійкою через неузгодженість матеріалів (індикаторів: {warn_count}).",
                "severity": "medium",
                "exploitation_step": "Сфокусуватись на процесуальних невідповідностях та ініціювати їх оцінку судом.",
                "supporting_basis": "Попередні валідаційні індикатори ризику.",
                "evidentiary_need": preferred_evidence,
            }
        )

    if not map_items:
        map_items.append(
            {
                "weakness": "Ключові слабкі місця опонента не визначені автоматично.",
                "severity": "low",
                "exploitation_step": "Провести ручний аудит заперечень опонента і уточнити карту атак.",
                "supporting_basis": "Недостатньо сигналів у вхідних даних.",
                "evidentiary_need": "Порівняльна таблиця тверджень сторін та доказів.",
            }
        )

    return map_items[:safe_limit]


def build_evidence_collection_plan(
    *,
    evidence_matrix: list[dict[str, Any]],
    evidence_gap_actions: list[dict[str, Any]],
    deadline_control: list[dict[str, Any]],
    recommended_doc_types: list[str],
    max_items: int = 12,
) -> list[dict[str, str]]:
    safe_limit = max(3, min(max_items, 16))
    urgent_due = next(
        (
            str(item.get("due_date") or "").strip()
            for item in deadline_control
            if str(item.get("status") or "").strip().lower() in {"warn", "urgent"} and str(item.get("due_date") or "").strip()
        ),
        "",
    )
    default_deadline = urgent_due or calculate_deadline(date.today(), 5).isoformat()

    steps: list[dict[str, str]] = []
    seen: set[str] = set()

    for item in evidence_gap_actions[:safe_limit]:
        evidence = str(item.get("evidence") or "").strip()
        if not evidence:
            continue
        key = evidence.lower()
        if key in seen:
            continue
        seen.add(key)
        priority = str(item.get("priority") or "medium").strip().lower() or "medium"
        action = str(item.get("action") or "Отримати та систематизувати доказ.").strip()
        deadline_hint = str(item.get("deadline_hint") or "").strip() or default_deadline
        owner = "юрист команди"
        lowered = evidence.lower()
        if any(token in lowered for token in ("виписк", "банк", "платіж", "догов")):
            owner = "клієнт + юрист"
        elif any(token in lowered for token in ("довірен", "реєстр", "єдрпоу", "ідентиф")):
            owner = "клієнт/корпоративний секретар"
        expected_result = f"Отримано доказ: {evidence} і додано в реєстр додатків."
        steps.append(
            {
                "priority": priority,
                "step": action,
                "owner": owner,
                "deadline_hint": deadline_hint,
                "expected_result": expected_result,
                "status": "queued",
            }
        )
        if len(steps) >= safe_limit:
            return steps

    for item in evidence_matrix:
        status = str(item.get("status") or "").strip().lower()
        if status not in {"missing", "required"}:
            continue
        title = str(item.get("title") or item.get("code") or "").strip()
        if not title:
            continue
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        high_priority = status == "missing" or any(doc in {"appeal_complaint", "cassation_complaint"} for doc in recommended_doc_types)
        steps.append(
            {
                "priority": "high" if high_priority else "medium",
                "step": f"Зібрати/витребувати доказ: {title}.",
                "owner": "юрист команди",
                "deadline_hint": default_deadline,
                "expected_result": f"Доказ '{title}' підготовлено для подання та включено до опису доказів.",
                "status": "queued",
            }
        )
        if len(steps) >= safe_limit:
            return steps

    if not steps:
        steps.append(
            {
                "priority": "low",
                "step": "Провести фінальну звірку наявних доказів з фактичними твердженнями у проєктах документів.",
                "owner": "юрист команди",
                "deadline_hint": default_deadline,
                "expected_result": "Сформовано підтверджений реєстр доказів без критичних прогалин.",
                "status": "queued",
            }
        )

    return steps[:safe_limit]


def build_factual_circumstances_blocks(
    *,
    fact_chronology_matrix: list[dict[str, Any]],
    evidence_matrix: list[dict[str, Any]],
    max_items: int = 8,
) -> list[dict[str, str]]:
    safe_limit = max(3, min(max_items, 12))
    evidence_pool = [
        str(item.get("title") or "").strip()
        for item in evidence_matrix
        if str(item.get("status") or "").strip() == "ok" and str(item.get("title") or "").strip()
    ]
    default_anchor = ", ".join(evidence_pool[:3]) if evidence_pool else "потрібно уточнити доказові джерела"

    rows: list[dict[str, str]] = []
    for item in fact_chronology_matrix[:safe_limit]:
        event = str(item.get("event") or "Істотна обставина").strip()
        actor = str(item.get("actor") or "невизначений учасник").strip()
        event_date = _format_ua_date(str(item.get("event_date") or "").strip() or None)
        excerpt = str(item.get("source_excerpt") or "").strip()
        evidence_status = str(item.get("evidence_status") or "").strip().lower()
        status = "ok" if evidence_status in {"detected", "inferred"} else "warn"
        rows.append(
            {
                "section": f"Обставина {len(rows) + 1}",
                "narrative": f"{event_date}: {actor} вчинив(ла) процесуально значиму дію - {event.lower()}.",
                "evidence_anchor": excerpt or f"Опорні докази: {default_anchor}.",
                "status": status,
            }
        )

    if not rows:
        rows.append(
            {
                "section": "Обставина 1",
                "narrative": "Хронологія фактичних обставин неповна; відсутній надійний ланцюг подій за датами.",
                "evidence_anchor": "Додайте первинні документи (договір, платіжні документи, судові акти, листування).",
                "status": "warn",
            }
        )
    return rows[:safe_limit]


def build_legal_qualification_blocks(
    *,
    legal_argument_map: list[dict[str, Any]],
    burden_of_proof_map: list[dict[str, Any]],
    legal_basis: list[str],
    max_items: int = 8,
) -> list[dict[str, str]]:
    safe_limit = max(3, min(max_items, 12))
    burden_by_issue = {str(item.get("issue") or "").strip().lower(): item for item in burden_of_proof_map}
    basis_pool = [str(item).strip() for item in legal_basis if str(item).strip()]

    rows: list[dict[str, str]] = []
    for index, item in enumerate(legal_argument_map[:safe_limit], start=1):
        issue = str(item.get("issue") or f"Кваліфікація {index}").strip()
        norm_reference = str(item.get("legal_basis") or "").strip() or (basis_pool[index - 1] if index - 1 < len(basis_pool) else "")
        if not norm_reference:
            norm_reference = "Нормативну опору потрібно уточнити вручну."
        burden = burden_by_issue.get(issue.lower()) or {}
        burden_on = str(burden.get("burden_on") or "сторона, що посилається на обставину").strip()
        burden_status = str(burden.get("current_status") or "partial").strip().lower()
        if burden_status == "covered":
            status = "ok"
            risk_note = "Лінія доказування покриває базові вимоги."
        elif burden_status == "gap":
            status = "warn"
            risk_note = "Є розрив у доказуванні; без додаткових доказів аргумент вразливий."
        else:
            status = "warn"
            risk_note = "Покриття доказування часткове; потрібне доопрацювання перед поданням."
        rows.append(
            {
                "qualification": issue,
                "norm_reference": norm_reference,
                "application_to_facts": (
                    f"Ця норма застосовується до встановлених обставин у межах питання '{issue.lower()}', "
                    f"тягар доказування переважно несе: {burden_on}."
                ),
                "risk_note": risk_note,
                "status": status,
            }
        )

    if not rows:
        fallback_basis = basis_pool[0] if basis_pool else "Норми матеріального/процесуального права потребують уточнення."
        rows.append(
            {
                "qualification": "Базова правова кваліфікація спору",
                "norm_reference": fallback_basis,
                "application_to_facts": "Потрібно сформувати зв'язку між ключовими фактами, нормою і процесуальною вимогою.",
                "risk_note": "Без деталізації кваліфікації документ залишатиметься шаблонним.",
                "status": "warn",
            }
        )
    return rows[:safe_limit]


def build_prayer_part_variants(
    *,
    summary: dict[str, Any],
    claim_formula_card: dict[str, Any],
    remedy_coverage: list[dict[str, Any]],
    recommended_doc_types: list[str],
    max_items: int = 8,
) -> list[dict[str, str]]:
    safe_limit = max(3, min(max_items, 12))
    dispute_type = str(summary.get("dispute_type") or "цивільний спір").strip()
    total_claim = float(claim_formula_card.get("total_claim_uah") or 0.0)
    principal = float(claim_formula_card.get("principal_uah") or 0.0)
    penalty = float(claim_formula_card.get("penalty_uah") or 0.0)
    money_text = f"{total_claim:,.2f}".replace(",", " ")
    principal_text = f"{principal:,.2f}".replace(",", " ")
    penalty_text = f"{penalty:,.2f}".replace(",", " ")
    covered = [str(item.get("remedy") or "").strip() for item in remedy_coverage if bool(item.get("covered"))]
    covered_ref = ", ".join(covered[:3]) if covered else "перелік способів захисту уточнюється"

    is_debt = any(doc in {"lawsuit_debt_loan", "lawsuit_debt_sale"} for doc in recommended_doc_types)
    variants: list[dict[str, str]] = [
        {
            "variant": "Основна вимога",
            "request_text": (
                f"Стягнути з відповідача заборгованість у розмірі {principal_text} грн "
                f"та визначити загальну суму стягнення {money_text} грн."
                if is_debt
                else "Задовольнити позовні вимоги в повному обсязі відповідно до викладених обставин і правових підстав."
            ),
            "grounds": f"Предмет спору: {dispute_type}.",
            "priority": "high",
        },
        {
            "variant": "Похідна вимога",
            "request_text": (
                "Стягнути 3% річних, інфляційні втрати та інші передбачені законом нарахування."
                if is_debt
                else "Стягнути судові витрати та інші належні платежі у порядку закону."
            ),
            "grounds": f"Покриття способів захисту: {covered_ref}.",
            "priority": "high",
        },
        {
            "variant": "Процесуальна вимога",
            "request_text": "Долучити всі подані докази, викликати/повідомити учасників та вирішити справу за правилами підсудності.",
            "grounds": "Забезпечення процесуальної повноти подання.",
            "priority": "medium",
        },
    ]

    if penalty > 0:
        variants.append(
            {
                "variant": "Санкційна вимога",
                "request_text": f"Стягнути неустойку/штрафні санкції у розмірі {penalty_text} грн.",
                "grounds": "Порушення строків виконання грошового зобов'язання.",
                "priority": "medium",
            }
        )
    if "appeal_complaint" in recommended_doc_types:
        variants.append(
            {
                "variant": "Апеляційна вимога",
                "request_text": "Скасувати рішення суду першої інстанції та ухвалити нове рішення по суті спору.",
                "grounds": "Істотні помилки у встановленні фактів та/або застосуванні права.",
                "priority": "high",
            }
        )
    if "cassation_complaint" in recommended_doc_types:
        variants.append(
            {
                "variant": "Касаційна вимога",
                "request_text": "Скасувати оскаржувані рішення та застосувати правильну правову позицію суду касаційної інстанції.",
                "grounds": "Неправильне застосування норм матеріального або процесуального права.",
                "priority": "high",
            }
        )

    return variants[:safe_limit]


def build_counterargument_response_matrix(
    *,
    opponent_objections: list[dict[str, Any]],
    opponent_weakness_map: list[dict[str, Any]],
    evidence_admissibility_map: list[dict[str, Any]],
    max_items: int = 8,
) -> list[dict[str, str]]:
    safe_limit = max(3, min(max_items, 12))
    strong_evidence = [
        str(item.get("evidence") or "").strip()
        for item in evidence_admissibility_map
        if str(item.get("risk") or "").strip().lower() in {"low", "medium"} and str(item.get("evidence") or "").strip()
    ]
    default_evidence = strong_evidence[0] if strong_evidence else "первинні письмові докази та офіційні реєстрові дані"

    rows: list[dict[str, str]] = []
    for item in opponent_objections[:safe_limit]:
        objection = str(item.get("objection") or "").strip()
        if not objection:
            continue
        rebuttal = str(item.get("rebuttal") or "").strip() or "Підготуйте точкове спростування з посиланням на доказ і норму."
        likelihood = str(item.get("likelihood") or "medium").strip().lower()
        if likelihood == "high":
            success_probability = "medium"
        elif likelihood == "low":
            success_probability = "high"
        else:
            success_probability = "medium"
        rows.append(
            {
                "opponent_argument": objection,
                "response_strategy": rebuttal,
                "evidence_focus": default_evidence,
                "success_probability": success_probability,
            }
        )
        if len(rows) >= safe_limit:
            return rows

    for item in opponent_weakness_map[:safe_limit]:
        weakness = str(item.get("weakness") or "").strip()
        if not weakness:
            continue
        rows.append(
            {
                "opponent_argument": weakness,
                "response_strategy": str(item.get("exploitation_step") or "Зафіксуйте слабкість та посильте її доказовим блоком.").strip(),
                "evidence_focus": str(item.get("evidentiary_need") or default_evidence).strip(),
                "success_probability": "high" if str(item.get("severity") or "").strip().lower() in {"high", "critical"} else "medium",
            }
        )
        if len(rows) >= safe_limit:
            return rows

    if not rows:
        rows.append(
            {
                "opponent_argument": "Позиція опонента ще не структурована у запереченнях.",
                "response_strategy": "Після отримання відзиву сформуйте таблицю: аргумент опонента -> контрдовід -> доказ.",
                "evidence_focus": default_evidence,
                "success_probability": "medium",
            }
        )
    return rows[:safe_limit]


def build_document_narrative_completeness(
    *,
    generated_documents: list[dict[str, Any]],
    text_section_audit: list[dict[str, Any]],
    cpc_175_requisites_map: list[dict[str, Any]],
    drafting_instructions: list[dict[str, Any]],
    factual_circumstances_blocks: list[dict[str, Any]],
    legal_qualification_blocks: list[dict[str, Any]],
    prayer_part_variants: list[dict[str, Any]],
    max_items: int = 10,
) -> list[dict[str, str]]:
    safe_limit = max(5, min(max_items, 15))
    text_warn_count = sum(1 for item in text_section_audit if str(item.get("status") or "").strip().lower() not in {"ok", "pass"})
    cpc_missing_count = sum(1 for item in cpc_175_requisites_map if str(item.get("status") or "").strip().lower() != "pass")

    rows: list[dict[str, str]] = [
        {
            "section": "Опис фактичних обставин",
            "status": "ok" if factual_circumstances_blocks else "warn",
            "action": (
                "Інтегрувати підготовлені блоки обставин у розділ фактичної частини кожного документа."
                if factual_circumstances_blocks
                else "Додати хронологію подій з датами, ролями сторін і посиланням на первинні докази."
            ),
            "note": f"Кількість змістовних обставин: {len(factual_circumstances_blocks)}.",
        },
        {
            "section": "Правове обґрунтування",
            "status": "ok" if legal_qualification_blocks else "warn",
            "action": (
                "Використати карти правової кваліфікації як каркас мотивувальної частини."
                if legal_qualification_blocks
                else "Побудувати матрицю 'факт -> норма -> висновок' для ключових тез."
            ),
            "note": f"Блоків правової кваліфікації: {len(legal_qualification_blocks)}.",
        },
        {
            "section": "Прохальна частина",
            "status": "ok" if prayer_part_variants else "warn",
            "action": (
                "Оберіть основний та резервний варіант прохальної частини за стадією процесу."
                if prayer_part_variants
                else "Сформулюйте вимоги у нумерованому вигляді з процесуально чіткими дієсловами."
            ),
            "note": f"Варіантів прохальної частини: {len(prayer_part_variants)}.",
        },
        {
            "section": "Реквізити за ст. 175 ЦПК України",
            "status": "ok" if cpc_missing_count == 0 else "warn",
            "action": (
                "Підтримуйте повноту реквізитів перед поданням."
                if cpc_missing_count == 0
                else "Закрийте відсутні реквізити ст. 175 ЦПК до фінальної версії."
            ),
            "note": f"Невідпрацьованих реквізитів: {cpc_missing_count}.",
        },
        {
            "section": "Фінальна вичитка та придатність до подання",
            "status": "ok" if generated_documents and text_warn_count == 0 else "warn",
            "action": (
                "Пакет виглядає готовим; перевірте лише відповідність додатків і підпису."
                if generated_documents and text_warn_count == 0
                else "Виконайте фінальну вичитку: приберіть шаблонні фрази, звірте суми/дати/ПІБ, посиліть опис обставин."
            ),
            "note": f"Згенеровано документів: {len(generated_documents)}; попереджень текстового аудиту: {text_warn_count}.",
        },
    ]

    for instruction in drafting_instructions:
        if len(rows) >= safe_limit:
            break
        status = str(instruction.get("status") or "ok").strip().lower()
        if status == "ok":
            continue
        doc_type = str(instruction.get("doc_type") or "процесуальний документ").strip()
        focus = str((instruction.get("factual_focus") or ["уточнити фактичну частину"])[0]).strip()
        rows.append(
            {
                "section": f"Точкове доопрацювання: {doc_type}",
                "status": "warn",
                "action": f"Розширте опис обставин та доказову прив'язку: {focus}.",
                "note": "Сигнал з блоку drafting_instructions.",
            }
        )

    return rows[:safe_limit]


def build_case_law_application_matrix(
    *,
    legal_argument_map: list[dict[str, Any]],
    citation_pack: dict[str, Any],
    context_refs: list[dict[str, Any]],
    max_items: int = 8,
) -> list[dict[str, str]]:
    safe_limit = max(3, min(max_items, 12))
    citation_case_refs = [
        {
            "source": str(item.get("source") or "").strip(),
            "reference": str(item.get("reference") or "").strip(),
        }
        for item in (citation_pack.get("case_refs") or [])
        if str(item.get("reference") or "").strip()
    ]
    context_case_refs = [
        {
            "source": str(item.get("source") or "").strip(),
            "reference": str(item.get("reference") or item.get("citation") or "").strip(),
        }
        for item in context_refs
        if str(item.get("reference") or item.get("citation") or "").strip()
    ]
    refs_pool = [*citation_case_refs, *context_case_refs]
    if not refs_pool:
        refs_pool = [{"source": "manual", "reference": "Потрібно додати релевантні постанови ВС/ВП ВС вручну."}]

    rows: list[dict[str, str]] = []
    for index, item in enumerate(legal_argument_map[:safe_limit], start=1):
        issue = str(item.get("issue") or f"Питання {index}").strip()
        reference_data = refs_pool[(index - 1) % len(refs_pool)]
        reference = str(reference_data.get("reference") or "").strip()
        source = str(reference_data.get("source") or "unknown").strip()
        lowered_ref = reference.lower()
        if any(token in lowered_ref for token in ("велика палата", "вп вс", "верховний суд", "вс")):
            strength = "high"
        elif reference.startswith("Потрібно"):
            strength = "low"
        else:
            strength = "medium"
        application_note = (
            f"Використати посилання як підтримку аргументу '{issue.lower()}'. "
            f"Спочатку викласти норму і факт, далі - правову позицію ({source})."
        )
        rows.append(
            {
                "legal_issue": issue,
                "reference": reference,
                "application_note": application_note,
                "strength": strength,
            }
        )
    return rows[:safe_limit]


def build_procedural_violation_hypotheses(
    *,
    cpc_compliance_check: list[dict[str, Any]],
    procedural_defect_scan: list[dict[str, Any]],
    pre_filing_red_flags: list[dict[str, Any]],
    max_items: int = 10,
) -> list[dict[str, str]]:
    safe_limit = max(3, min(max_items, 14))
    rows: list[dict[str, str]] = []

    for item in cpc_compliance_check[:8]:
        status = str(item.get("status") or "").strip().lower()
        if status == "pass":
            continue
        requirement = str(item.get("requirement") or "Процесуальна вимога").strip()
        article = str(item.get("article") or "ЦПК України").strip()
        note = str(item.get("note") or "").strip()
        viability = "high" if status in {"fail", "missing"} else "medium"
        rows.append(
            {
                "hypothesis": f"Порушення вимоги: {requirement}.",
                "legal_basis": article,
                "source_signal": note or "Сигнал виявлено в CPC compliance check.",
                "viability": viability,
                "required_proof": "Текст заяви/скарги, додатки, опис вкладення, докази надсилання сторонам.",
            }
        )
        if len(rows) >= safe_limit:
            return rows

    for item in procedural_defect_scan[:6]:
        severity = str(item.get("severity") or "low").strip().lower()
        issue = str(item.get("issue") or "Процесуальний дефект").strip()
        fix = str(item.get("fix") or "Потрібно уточнити спосіб усунення дефекту.").strip()
        rows.append(
            {
                "hypothesis": issue,
                "legal_basis": "ЦПК України (загальні вимоги до форми та змісту процесуальних документів).",
                "source_signal": fix,
                "viability": "high" if severity in {"high", "critical"} else "medium",
                "required_proof": "Порівняльна таблиця: вимога закону -> фактичний недолік -> спосіб усунення.",
            }
        )
        if len(rows) >= safe_limit:
            return rows

    for item in pre_filing_red_flags[:4]:
        severity = str(item.get("severity") or "low").strip().lower()
        flag = str(item.get("flag") or "Pre-filing flag").strip()
        action = str(item.get("action") or "Уточніть дію для усунення ризику.").strip()
        rows.append(
            {
                "hypothesis": flag,
                "legal_basis": "Процесуальні приписи ЦПК України та правила доказування.",
                "source_signal": action,
                "viability": "high" if severity == "high" else "medium",
                "required_proof": "Документи, що закривають виявлений ризик до моменту подання.",
            }
        )
        if len(rows) >= safe_limit:
            return rows

    if not rows:
        rows.append(
            {
                "hypothesis": "Явні процесуальні порушення автоматично не виявлені.",
                "legal_basis": "Потребує ручної перевірки за ЦПК та фактичними матеріалами.",
                "source_signal": "Недостатньо тригерів у вхідних даних.",
                "viability": "low",
                "required_proof": "Ручний аудит тексту документа і комплекту додатків.",
            }
        )
    return rows[:safe_limit]


def build_document_fact_enrichment_plan(
    *,
    generated_documents: list[dict[str, Any]],
    text_section_audit: list[dict[str, Any]],
    document_narrative_completeness: list[dict[str, Any]],
    drafting_instructions: list[dict[str, Any]],
    max_items: int = 10,
) -> list[dict[str, str]]:
    safe_limit = max(3, min(max_items, 14))
    weak_sections = [
        str(item.get("section") or "").strip()
        for item in text_section_audit
        if str(item.get("status") or "").strip().lower() not in {"ok", "pass"} and str(item.get("section") or "").strip()
    ]
    narrative_warnings = [
        str(item.get("action") or "").strip()
        for item in document_narrative_completeness
        if str(item.get("status") or "").strip().lower() == "warn" and str(item.get("action") or "").strip()
    ]
    factual_focus_by_doc = {
        str(item.get("doc_type") or "").strip(): [
            str(x).strip() for x in (item.get("factual_focus") or []) if str(x).strip()
        ]
        for item in drafting_instructions
        if str(item.get("doc_type") or "").strip()
    }

    rows: list[dict[str, str]] = []
    for doc in generated_documents[:safe_limit]:
        doc_type = str(doc.get("doc_type") or "processual_document").strip()
        title = str(doc.get("title") or doc_type).strip()
        missing_fact_block = (
            weak_sections[0]
            if weak_sections
            else (factual_focus_by_doc.get(doc_type, ["уточнити фактичні обставини та дати"])[0])
        )
        instruction = (
            f"У документі '{title}' розширити блок '{missing_fact_block}': додати дати, суми, ролі сторін, "
            "посилання на первинні докази та короткий причинно-наслідковий зв'язок."
        )
        if narrative_warnings:
            instruction = f"{instruction} Додатково: {narrative_warnings[0]}"
        rows.append(
            {
                "doc_type": doc_type,
                "missing_fact_block": missing_fact_block,
                "insert_instruction": instruction,
                "priority": "high" if weak_sections else "medium",
                "status": "queued",
            }
        )
        if len(rows) >= safe_limit:
            return rows

    if not rows:
        rows.append(
            {
                "doc_type": "draft_not_generated",
                "missing_fact_block": "базовий опис обставин",
                "insert_instruction": (
                    "Спочатку згенеруйте хоча б один процесуальний документ, "
                    "після чого виконайте enrichment фактичної частини за планом."
                ),
                "priority": "high",
                "status": "queued",
            }
        )
    return rows[:safe_limit]


def build_hearing_positioning_notes(
    *,
    judge_questions_simulation: list[dict[str, Any]],
    counterargument_response_matrix: list[dict[str, Any]],
    hearing_script_pack: list[dict[str, Any]],
    max_items: int = 8,
) -> list[dict[str, Any]]:
    safe_limit = max(3, min(max_items, 12))
    response_pool = [item for item in counterargument_response_matrix if str(item.get("response_strategy") or "").strip()]
    script_pool = [item for item in hearing_script_pack if str(item.get("script_hint") or "").strip()]
    fallback_script = str((script_pool[0].get("script_hint") if script_pool else "Стисло викласти факт, норму і процесуальний наслідок.")).strip()

    rows: list[dict[str, Any]] = []
    for index, question in enumerate(judge_questions_simulation[:safe_limit], start=1):
        theme = str(question.get("question") or f"Питання суду {index}").strip()
        why = str(question.get("why_it_matters") or "Впливає на юридичну кваліфікацію та результат спору.").strip()
        response_item = response_pool[(index - 1) % len(response_pool)] if response_pool else {}
        risk_counter = str(response_item.get("response_strategy") or "Підготуйте коротку відповідь за схемою: факт -> норма -> висновок.").strip()
        evidence_focus = str(response_item.get("evidence_focus") or "Первинні докази, що прямо підтверджують тезу.").strip()
        courtroom_phrase = f"Шановний суд, ця позиція підтверджується матеріалами справи: {evidence_focus.lower()}."
        rows.append(
            {
                "theme": theme,
                "supporting_points": [why, fallback_script],
                "risk_counter": risk_counter,
                "courtroom_phrase": courtroom_phrase,
            }
        )
    if not rows:
        rows.append(
            {
                "theme": "Базове позиціонування в засіданні",
                "supporting_points": [
                    "Сконцентруйтесь на 2-3 ключових фактах і правових тезах.",
                    "Уникайте оціночних тверджень без доказового підкріплення.",
                ],
                "risk_counter": "Підготуйте короткі відповіді на потенційні заперечення опонента.",
                "courtroom_phrase": "Шановний суд, ключові обставини підтверджуються письмовими доказами в матеріалах справи.",
            }
        )
    return rows[:safe_limit]


def build_process_stage_action_map(
    *,
    workflow_stages: list[dict[str, Any]],
    deadline_control: list[dict[str, Any]],
    final_submission_gate: dict[str, Any],
    max_items: int = 8,
) -> list[dict[str, Any]]:
    safe_limit = max(3, min(max_items, 10))
    urgent_deadline = next(
        (
            str(item.get("title") or "").strip()
            for item in deadline_control
            if str(item.get("status") or "").strip().lower() in {"warn", "urgent"}
        ),
        "",
    )
    hard_stop = bool(final_submission_gate.get("hard_stop"))
    final_gate_status = str(final_submission_gate.get("status") or "blocked").strip().lower()

    objective_map = {
        "block_1_ai_analysis": "Стабілізувати фактичну модель спору та прибрати шаблонність.",
        "block_2_case_law_rag": "Підв'язати правову позицію до актуальної судової практики.",
        "block_3_rule_validation": "Усунути процесуальні дефекти до подання.",
        "block_4_human_review_gate": "Підтвердити готовність пакета після human-review і фінальних гейтів.",
    }

    rows: list[dict[str, Any]] = []
    for item in workflow_stages[:safe_limit]:
        code = str(item.get("code") or "").strip()
        title = str(item.get("title") or code or "stage").strip()
        status = str(item.get("status") or "warn").strip().lower()
        objective = objective_map.get(code, "Забезпечити кероване просування справи на поточній стадії.")
        actions: list[str]
        if status == "ok":
            actions = ["Підтримуйте якість та зафіксуйте результат стадії у контрольному листі."]
        elif status == "blocked":
            actions = ["Негайно усуньте блокери стадії перед переходом далі.", "Проведіть повторну перевірку процесуальних критеріїв."]
        else:
            actions = ["Закрийте попередження стадії та оновіть пакет документів.", "Перевірте відповідність аргументів доказам."]
        if urgent_deadline:
            actions.append(f"Пріоритет: не пропустіть контрольний строк - {urgent_deadline}.")
        if code == "block_4_human_review_gate" and (hard_stop or final_gate_status == "blocked"):
            actions.append("Фінальний гейт подання заблокований: перевірте blockers у final_submission_gate.")
        rows.append(
            {
                "stage_code": code or f"stage_{len(rows)+1}",
                "stage_title": title,
                "objective": objective,
                "actions": actions[:4],
                "trigger": "Оновлення статусу після закриття поточних блокерів.",
                "status": status,
            }
        )
    if not rows:
        rows.append(
            {
                "stage_code": "stage_1",
                "stage_title": "Початкова стадія",
                "objective": "Побудувати базову процесуальну карту справи.",
                "actions": ["Сформуйте workflow_stages на основі актуального аналізу."],
                "trigger": "Після первинного аналізу документа.",
                "status": "warn",
            }
        )
    return rows[:safe_limit]


def build_legal_argument_map(
    *,
    legal_basis: list[str],
    recommended_doc_types: list[str],
) -> list[dict[str, str]]:
    goals: list[str] = []
    if "lawsuit_debt_loan" in recommended_doc_types:
        goals.append("Recover principal debt, 3% annual interest, and inflation losses.")
    if "lawsuit_debt_sale" in recommended_doc_types:
        goals.append("Recover payment debt under sale contract.")
    if "appeal_complaint" in recommended_doc_types:
        goals.append("Challenge lower court decision and seek reversal/new judgment.")
    if "pretension_debt_return" in recommended_doc_types:
        goals.append("Establish pre-trial demand trail for litigation readiness.")
    if not goals:
        goals.append("Align claims with selected procedural path.")

    rows: list[dict[str, str]] = []
    for index, basis in enumerate((legal_basis or [])[:6], start=1):
        goal = goals[(index - 1) % len(goals)]
        rows.append(
            {
                "issue": f"Argument {index}",
                "legal_basis": basis,
                "litigation_goal": goal,
            }
        )

    if not rows:
        rows.append(
            {
                "issue": "Core argument",
                "legal_basis": "Verify and add concrete CPC/CCU references before filing.",
                "litigation_goal": goals[0],
            }
        )
    return rows


def build_readiness_breakdown(
    *,
    validation_checks: list[dict[str, str]],
    unresolved_questions: list[str],
    unresolved_review_items: list[str],
    generated_documents_count: int,
    confidence_score: float,
) -> dict[str, Any]:
    warn_count = sum(1 for item in validation_checks if str(item.get("status")) == "warn")
    pass_count = sum(1 for item in validation_checks if str(item.get("status")) == "pass")

    score = 100.0
    score -= min(warn_count * 7.0, 35.0)
    score -= min(len(unresolved_questions) * 10.0, 30.0)
    score -= min(len(unresolved_review_items) * 8.0, 24.0)
    if generated_documents_count == 0:
        score -= 20.0
    score += min(confidence_score * 10.0, 5.0)
    final_score = round(max(0.0, min(score, 100.0)), 1)

    blockers: list[str] = []
    if unresolved_questions:
        blockers.append(f"Unresolved clarifications: {len(unresolved_questions)}.")
    if unresolved_review_items:
        blockers.append(f"Unresolved human-review items: {len(unresolved_review_items)}.")
    if generated_documents_count == 0:
        blockers.append("No generated procedural documents yet.")
    if warn_count:
        blockers.append(f"Validation warnings: {warn_count}.")

    strengths: list[str] = []
    if pass_count:
        strengths.append(f"Passed validation checks: {pass_count}.")
    if generated_documents_count > 0:
        strengths.append(f"Generated documents: {generated_documents_count}.")
    if confidence_score >= 0.75:
        strengths.append(f"High confidence score: {confidence_score}.")

    return {
        "score": final_score,
        "decision": "ready" if not blockers and final_score >= 80 else "not_ready",
        "blockers": blockers,
        "strengths": strengths,
        "metrics": {
            "warn_count": warn_count,
            "pass_count": pass_count,
            "unresolved_questions": len(unresolved_questions),
            "unresolved_review_items": len(unresolved_review_items),
            "generated_documents": generated_documents_count,
            "confidence_score": confidence_score,
        },
    }


def build_post_filing_plan(
    *,
    recommended_doc_types: list[str],
    ready_for_filing: bool,
) -> list[str]:
    plan: list[str] = []
    if ready_for_filing:
        plan.append("Submit final document set and save submission receipt/tracking ID.")
    else:
        plan.append("Close all blockers before e-filing to avoid procedural rejection.")

    if "appeal_complaint" in recommended_doc_types:
        plan.append("Monitor appeal admissibility and respond to any court deficiency notice immediately.")
    if "lawsuit_debt_loan" in recommended_doc_types or "lawsuit_debt_sale" in recommended_doc_types:
        plan.append("Prepare motion for evidence request or asset securing if debtor non-cooperation is expected.")
    plan.append("Track deadlines for court responses and prepare draft replies in advance.")
    plan.append("Keep evidence index synchronized with each new filing or response.")
    return plan[:6]


def build_party_profile(source_text: str) -> dict[str, Any]:
    parties = extract_parties_and_facts(source_text)
    lowered = _normalized(source_text)
    plaintiff_detected = bool(parties.get("plaintiff_name") or parties.get("party_a"))
    defendant_detected = bool(parties.get("defendant_name") or parties.get("party_b"))
    has_tax_like = bool(re.search(r"\b\d{8,10}\b", source_text or ""))
    has_address_like = "адрес" in lowered or "address" in lowered or "місцезнаход" in lowered

    score = 0.0
    if plaintiff_detected:
        score += 35.0
    if defendant_detected:
        score += 35.0
    if has_tax_like:
        score += 15.0
    if has_address_like:
        score += 15.0

    missing_items: list[str] = []
    if not plaintiff_detected:
        missing_items.append("Missing full plaintiff identification.")
    if not defendant_detected:
        missing_items.append("Missing full defendant identification.")
    if not has_tax_like:
        missing_items.append("Missing tax ID / EDRPOU data.")
    if not has_address_like:
        missing_items.append("Missing full addresses for procedural delivery.")

    final_score = round(max(0.0, min(score, 100.0)), 1)
    if final_score >= 80:
        risk = "low"
    elif final_score >= 55:
        risk = "medium"
    else:
        risk = "high"

    return {
        "completion_score": final_score,
        "risk_level": risk,
        "plaintiff_detected": plaintiff_detected,
        "defendant_detected": defendant_detected,
        "missing_items": missing_items,
    }


def build_jurisdiction_recommendation(
    *,
    summary: dict[str, Any],
    recommended_doc_types: list[str],
    party_profile: dict[str, Any],
) -> dict[str, Any]:
    procedure = str(summary.get("procedure") or "civil").lower()
    route = "Місцевий суд за адресою відповідача з урахуванням правил підсудності."
    legal_basis = ["Перед поданням перевірте правила юрисдикції/підсудності у відповідному процесуальному кодексі."]
    required_inputs = [
        "Повна адреса відповідача.",
        "Суд першої інстанції (для апеляції, якщо застосовно).",
        "Тип спору та процесуальний маршрут.",
    ]

    if "appeal_complaint" in recommended_doc_types:
        route = "Апеляційний суд через суд першої інстанції, який ухвалив оскаржуване рішення."
        legal_basis = [
            "Положення ЦПК України щодо апеляційного перегляду та маршруту подання.",
            "Перевірте точний строк апеляційного оскарження і компетенцію інстанції.",
        ]
    elif procedure == "civil":
        route = "Місцевий загальний суд, переважно за місцем проживання/знаходження відповідача (можливі альтернативи)."
        legal_basis = [
            "Норми ЦПК України про загальну та альтернативну територіальну підсудність.",
            "Уточніть спеціальну підсудність за договором/місцем виконання (за наявності підстав).",
        ]
    elif procedure == "administrative":
        route = "Адміністративний суд за правилами КАС України."
        legal_basis = [
            "Положення КАС України щодо юрисдикції та підсудності.",
            "Уточніть категорію спору та місцезнаходження суб'єкта владних повноважень.",
        ]
    elif procedure == "commercial":
        route = "Господарський суд за правилами ГПК України."
        legal_basis = [
            "Положення ГПК України щодо юрисдикції та підсудності.",
            "Перевірте статус сторін як суб'єктів господарювання та характер спору.",
        ]

    confidence = 0.75 if party_profile.get("completion_score", 0) >= 80 else 0.55
    warning = None
    if party_profile.get("completion_score", 0) < 80:
        warning = "Дані ідентифікації сторін неповні; впевненість у виборі підсудності знижена."

    return {
        "procedure": procedure,
        "suggested_route": route,
        "legal_basis": legal_basis,
        "confidence": round(confidence, 2),
        "required_inputs": required_inputs,
        "warning": warning,
    }


def build_generated_docs_quality(generated_documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    quality: list[dict[str, Any]] = []
    for item in generated_documents:
        doc_type = str(item.get("doc_type") or "").strip()
        text = str(item.get("_generated_text") or "")
        markers = DOC_TYPE_REQUIRED_MARKERS.get(doc_type, ())
        lowered = text.lower()
        found = sum(1 for marker in markers if marker.lower() in lowered)
        missing = [marker for marker in markers if marker.lower() not in lowered]
        marker_component = (found / len(markers) * 35.0) if markers else 0.0
        length_component = min(len(text) / 2500 * 20.0, 20.0)
        factual_signals = 0
        if re.search(r"\b\d{2}\.\d{2}\.\d{4}\b|\b\d{4}-\d{2}-\d{2}\b", text):
            factual_signals += 1
        if re.search(r"\b\d[\d\s]{1,14}(?:грн|uah|₴)\b", lowered):
            factual_signals += 1
        if re.search(r"\b(позивач|відповідач|заявник|скаржник)\b", lowered):
            factual_signals += 1
        factual_component = factual_signals / 3 * 20.0

        cyrillic_count = len(re.findall(r"[А-Яа-яІіЇїЄєҐґ]", text))
        latin_count = len(re.findall(r"[A-Za-z]", text))
        total_letters = cyrillic_count + latin_count
        cyr_ratio = (cyrillic_count / total_letters) if total_letters > 0 else 0.0
        placeholder_present = bool(re.search(r"\[(?:потрібно\s+уточнити|уточнити|needs\s+clarification)[^\]]*\]", lowered))

        score = 25.0 + marker_component + length_component + factual_component
        if placeholder_present:
            score -= 30.0
        if cyr_ratio < 0.45:
            score -= 20.0
        score = round(max(0.0, min(score, 100.0)), 1)

        status = "high" if score >= 85 else ("medium" if score >= 70 else "low")
        issues: list[str] = []
        if len(text) < 900:
            issues.append("Текст документа занадто короткий; перевірте повноту викладу обставин.")
        if missing:
            issues.append(f"Відсутні структурні маркери: {', '.join(missing)}.")
        if placeholder_present:
            issues.append("Виявлено плейсхолдери у тексті; документ потребує доопрацювання перед поданням.")
        if cyr_ratio < 0.45:
            issues.append("Профіль мови недостатньо україномовний; перевірте локалізацію тексту.")
        if factual_signals <= 1:
            issues.append("Недостатньо фактичної конкретики (дати/суми/ролі сторін).")

        quality.append(
            {
                "doc_type": doc_type,
                "score": score,
                "status": status,
                "issues": issues,
            }
        )
    return quality


def build_e_court_submission_preview(
    *,
    generated_items: list[dict[str, Any]],
    ready_for_filing: bool,
    unresolved_questions: list[str],
    unresolved_review_items: list[str],
) -> dict[str, Any]:
    required_attachments = [f"{item.get('doc_type')}:{item.get('id')}" for item in generated_items]
    blockers: list[str] = []
    if unresolved_questions:
        blockers.append(f"Не закрито уточнення: {len(unresolved_questions)}.")
    if unresolved_review_items:
        blockers.append(f"Не закрито підтвердження human-review: {len(unresolved_review_items)}.")
    if not generated_items:
        blockers.append("Немає згенерованих документів для подання.")
    if not ready_for_filing and not blockers:
        blockers.append("Не пройдено гейт готовності до подання.")

    return {
        "can_submit": ready_for_filing and not blockers,
        "provider": "court.gov.ua",
        "signer_methods": ["Дія.Підпис", "КЕП токен"],
        "required_attachments": required_attachments,
        "blockers": blockers,
        "note": "Це попередня перевірка. Фінальне подання потребує інтеграції з e-court.",
    }


def build_priority_queue(
    *,
    next_actions: list[str],
    procedural_timeline: list[dict[str, Any]],
    readiness_breakdown: dict[str, Any],
) -> list[dict[str, Any]]:
    today = date.today()
    queue: list[dict[str, Any]] = []

    for blocker in (readiness_breakdown.get("blockers") or [])[:4]:
        queue.append(
            {
                "priority": "high",
                "task": str(blocker),
                "due_date": calculate_deadline(today, 1).isoformat(),
            }
        )

    for action in next_actions[:5]:
        queue.append(
            {
                "priority": "medium",
                "task": action,
                "due_date": calculate_deadline(today, 3).isoformat(),
            }
        )

    for item in procedural_timeline:
        if str(item.get("status")) != "warn":
            continue
        task = f"Ризик строку: {item.get('title')}"
        queue.append(
            {
                "priority": "high",
                "task": task,
                "due_date": str(item.get("date") or calculate_deadline(today, 1).isoformat()),
            }
        )

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in queue:
        key = str(item.get("task") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= 10:
            break
    return deduped


def build_consistency_report(
    *,
    source_text: str,
    summary: dict[str, Any],
    recommended_doc_types: list[str],
    financial_snapshot: dict[str, Any],
) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    extracted_amount = _extract_amount_uah(source_text)
    principal = financial_snapshot.get("principal_uah")
    try:
        principal_val = float(principal) if principal is not None else None
    except Exception:
        principal_val = None

    if extracted_amount is None:
        checks.append(
            {
                "code": "amount_detection",
                "status": "warn",
                "message": "No reliable monetary amount detected in source text.",
            }
        )
    elif principal_val is None:
        checks.append(
            {
                "code": "amount_alignment",
                "status": "warn",
                "message": "Financial snapshot has no principal amount despite detected amount in source.",
            }
        )
    else:
        delta = abs(extracted_amount - principal_val)
        if delta > max(100.0, extracted_amount * 0.1):
            checks.append(
                {
                    "code": "amount_alignment",
                    "status": "warn",
                    "message": (
                        f"Detected amount ({extracted_amount} UAH) differs from principal "
                        f"({principal_val} UAH). Verify claim amount consistency."
                    ),
                }
            )
        else:
            checks.append(
                {
                    "code": "amount_alignment",
                    "status": "pass",
                    "message": "Detected amount and principal amount are consistent.",
                }
            )

    procedure = str(summary.get("procedure") or "").lower()
    if "appeal_complaint" in recommended_doc_types and procedure != "civil":
        checks.append(
            {
                "code": "appeal_procedure_alignment",
                "status": "warn",
                "message": "Appeal document type selected but procedure is not marked as civil.",
            }
        )
    else:
        checks.append(
            {
                "code": "procedure_alignment",
                "status": "pass",
                "message": f"Procedure/doc-type alignment looks acceptable ({procedure or 'unknown'}).",
            }
        )
    return checks


def build_remedy_coverage(
    *,
    recommended_doc_types: list[str],
) -> list[dict[str, Any]]:
    coverage_map: dict[str, tuple[str, ...]] = {
        "Debt principal recovery": ("lawsuit_debt_loan", "lawsuit_debt_sale"),
        "3% annual interest and inflation losses": ("lawsuit_debt_loan",),
        "Court fee recovery": ("lawsuit_debt_loan", "lawsuit_debt_sale", "appeal_complaint"),
        "Appeal challenge of first-instance decision": ("appeal_complaint",),
        "Pre-trial demand evidence trail": ("pretension_debt_return",),
    }
    doc_set = set(recommended_doc_types)
    items: list[dict[str, Any]] = []
    for remedy, supported_by in coverage_map.items():
        available = [doc for doc in supported_by if doc in doc_set]
        items.append(
            {
                "remedy": remedy,
                "covered": bool(available),
                "covered_by": available,
                "note": "Covered by selected document package." if available else "No selected document type explicitly covers this remedy.",
            }
        )
    return items


def build_citation_pack(
    *,
    legal_basis: list[str],
    context_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    statutory_refs: list[str] = []
    seen_stat: set[str] = set()
    for item in legal_basis:
        text = str(item).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen_stat:
            continue
        seen_stat.add(key)
        statutory_refs.append(text)
        if len(statutory_refs) >= 15:
            break

    case_refs: list[dict[str, str]] = []
    seen_case: set[str] = set()
    for ref in context_refs:
        if str(ref.get("ref_type")) != "case_law":
            continue
        reference = str(ref.get("reference") or "").strip()
        source = str(ref.get("source") or "").strip() or "unknown"
        if not reference:
            continue
        key = f"{source}:{reference}".lower()
        if key in seen_case:
            continue
        seen_case.add(key)
        case_refs.append(
            {
                "source": source,
                "reference": reference,
                "note": str(ref.get("note") or "").strip()[:200],
            }
        )
        if len(case_refs) >= 10:
            break

    return {
        "statutory_refs": statutory_refs,
        "case_refs": case_refs,
        "note": "Use statutory refs as primary basis and case refs for motivation support.",
    }


def build_fee_scenarios(
    *,
    financial_snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    principal = financial_snapshot.get("principal_uah")
    penalty = financial_snapshot.get("estimated_penalty_uah") or 0.0
    try:
        principal_val = float(principal) if principal is not None else None
        penalty_val = float(penalty)
    except Exception:
        principal_val = None
        penalty_val = 0.0

    if principal_val is None or principal_val <= 0:
        return [
            {
                "name": "base",
                "principal_uah": None,
                "court_fee_uah": None,
                "penalty_uah": None,
                "total_with_fee_uah": None,
                "note": "Principal amount unavailable; scenarios cannot be calculated.",
            }
        ]

    scenarios = [
        ("conservative", principal_val * 0.85),
        ("base", principal_val),
        ("aggressive", principal_val * 1.15),
    ]
    result: list[dict[str, Any]] = []
    for name, scenario_principal in scenarios:
        fee = calculate_court_fee(round(scenario_principal, 2))
        total = round(scenario_principal + penalty_val + fee, 2)
        result.append(
            {
                "name": name,
                "principal_uah": round(scenario_principal, 2),
                "court_fee_uah": fee,
                "penalty_uah": round(penalty_val, 2),
                "total_with_fee_uah": total,
                "note": "Scenario uses +/-15% principal sensitivity.",
            }
        )
    return result


def build_filing_risk_simulation(
    *,
    validation_checks: list[dict[str, str]],
    unresolved_questions: list[str],
    unresolved_review_items: list[str],
    readiness_breakdown: dict[str, Any],
) -> list[dict[str, Any]]:
    warn_count = sum(1 for item in validation_checks if str(item.get("status")) == "warn")
    score = float(readiness_breakdown.get("score") or 0)

    risks: list[dict[str, Any]] = []
    risks.append(
        {
            "risk": "Claim return/leave-without-move due to formal defects",
            "probability": min(0.1 + warn_count * 0.08 + len(unresolved_questions) * 0.1, 0.95),
            "impact": "high",
            "mitigation": "Resolve warnings, complete party data, and verify CPC requisites before filing.",
        }
    )
    risks.append(
        {
            "risk": "Deadline-related procedural rejection",
            "probability": min(0.08 + (0 if score >= 80 else 0.2), 0.85),
            "impact": "high",
            "mitigation": "Confirm limitation/appeal dates and lock timeline controls.",
        }
    )
    risks.append(
        {
            "risk": "Weak evidentiary support at early stage",
            "probability": min(0.12 + len(unresolved_review_items) * 0.08, 0.9),
            "impact": "medium",
            "mitigation": "Complete evidence matrix and attach admissibility-focused bundle.",
        }
    )

    for item in risks:
        item["probability"] = round(float(item["probability"]), 2)
    return risks


def build_procedural_defect_scan(
    *,
    validation_checks: list[dict[str, str]],
    unresolved_questions: list[str],
    unresolved_review_items: list[str],
    generated_documents_count: int,
) -> list[dict[str, str]]:
    defects: list[dict[str, str]] = []
    for item in validation_checks:
        if str(item.get("status")) != "warn":
            continue
        defects.append(
            {
                "code": str(item.get("code") or "validation_warn"),
                "severity": "high",
                "issue": str(item.get("message") or "Validation warning detected."),
                "fix": "Resolve the warning and verify procedural requisites before filing.",
            }
        )

    if unresolved_questions:
        defects.append(
            {
                "code": "unresolved_clarifications",
                "severity": "high",
                "issue": f"Unresolved clarifications: {len(unresolved_questions)}.",
                "fix": "Provide factual clarifications for all unresolved questions.",
            }
        )
    if unresolved_review_items:
        defects.append(
            {
                "code": "unresolved_review_items",
                "severity": "high",
                "issue": f"Unresolved review checklist items: {len(unresolved_review_items)}.",
                "fix": "Confirm all mandatory human-review checklist items.",
            }
        )
    if generated_documents_count == 0:
        defects.append(
            {
                "code": "missing_generated_documents",
                "severity": "high",
                "issue": "No generated procedural documents available for filing.",
                "fix": "Complete all gates and generate the procedural document set.",
            }
        )
    if not defects:
        defects.append(
            {
                "code": "no_critical_defects",
                "severity": "low",
                "issue": "No critical procedural defects detected in current pre-check.",
                "fix": "Proceed with final legal review and filing package assembly.",
            }
        )
    return defects[:15]


def build_evidence_admissibility_map(
    *,
    evidence_matrix: list[dict[str, Any]],
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for item in evidence_matrix:
        title = str(item.get("title") or item.get("code") or "Evidence item")
        status = str(item.get("status") or "unknown")
        if status == "ok":
            admissibility = "high"
            relevance = "high"
            risk = "low"
            recommendation = "Attach as primary evidence and reference in factual matrix."
        elif status == "required":
            admissibility = "unknown"
            relevance = "high"
            risk = "medium"
            recommendation = "Collect and attach before filing; map to concrete factual assertions."
        else:
            admissibility = "low"
            relevance = "medium"
            risk = "high"
            recommendation = "Locate equivalent admissible evidence or request evidence from third parties."

        result.append(
            {
                "evidence": title,
                "admissibility": admissibility,
                "relevance": relevance,
                "risk": risk,
                "recommendation": recommendation,
            }
        )
    return result[:15]


def build_motion_recommendations(
    *,
    summary: dict[str, Any],
    recommended_doc_types: list[str],
    evidence_matrix: list[dict[str, Any]],
    procedural_timeline: list[dict[str, Any]],
    validation_checks: list[dict[str, str]],
) -> list[dict[str, str]]:
    motions: list[dict[str, str]] = []
    has_missing_evidence = any(str(item.get("status")) == "missing" for item in evidence_matrix)
    has_timeline_warn = any(str(item.get("status")) == "warn" for item in procedural_timeline)
    has_warn_checks = any(str(item.get("status")) == "warn" for item in validation_checks)
    dispute_type = str(summary.get("dispute_type") or "").lower()

    if has_missing_evidence:
        motions.append(
            {
                "motion_type": "Motion to request evidence",
                "priority": "high",
                "rationale": "Key evidence appears missing in pre-filing matrix.",
                "trigger": "Use when evidence is held by the other party or third parties.",
            }
        )
    if "debt" in dispute_type or any(doc in {"lawsuit_debt_loan", "lawsuit_debt_sale"} for doc in recommended_doc_types):
        motions.append(
            {
                "motion_type": "Motion to secure claim (asset freeze)",
                "priority": "medium",
                "rationale": "Debt recovery path may require interim protection of enforcement potential.",
                "trigger": "Use if risk of asset disposal or evasion is present.",
            }
        )
    if "appeal_complaint" in recommended_doc_types and has_timeline_warn:
        motions.append(
            {
                "motion_type": "Motion to renew procedural deadline",
                "priority": "high",
                "rationale": "Timeline pre-check indicates possible appeal timing risk.",
                "trigger": "Use if filing appears outside standard appeal window.",
            }
        )
    if has_warn_checks:
        motions.append(
            {
                "motion_type": "Motion to defer/install court fee payment",
                "priority": "medium",
                "rationale": "Validation warnings indicate possible filing-friction risks.",
                "trigger": "Use when immediate full fee payment is impractical or needs court approval.",
            }
        )
    if not motions:
        motions.append(
            {
                "motion_type": "No additional motions required at pre-check stage",
                "priority": "low",
                "rationale": "Current package has no explicit trigger for extra motions.",
                "trigger": "Re-evaluate after opponent response or court instructions.",
            }
        )
    return motions[:8]


def build_hearing_preparation_plan(
    *,
    summary: dict[str, Any],
    citation_pack: dict[str, Any],
    priority_queue: list[dict[str, Any]],
) -> list[dict[str, str]]:
    dispute_type = str(summary.get("dispute_type") or "General dispute")
    top_citations = ", ".join((citation_pack.get("statutory_refs") or [])[:3]) or "Key statutory refs to be finalized"
    top_priority = str(priority_queue[0].get("task")) if priority_queue else "Finalize pre-filing blockers"

    return [
        {
            "phase": "Opening statement",
            "task": f"Prepare concise case theory for {dispute_type}.",
            "output": "2-3 minute oral opening with requested remedies.",
        },
        {
            "phase": "Legal argument",
            "task": f"Structure oral argument around: {top_citations}.",
            "output": "Argument sheet with norm-to-fact mapping.",
        },
        {
            "phase": "Evidence presentation",
            "task": "Prepare evidence sequence and admissibility narrative.",
            "output": "Evidence index ordered by probative value.",
        },
        {
            "phase": "Risk handling",
            "task": f"Pre-answer likely court/opponent challenges, starting with: {top_priority}.",
            "output": "Rebuttal checklist for high-risk objections.",
        },
        {
            "phase": "Closing",
            "task": "Draft final prayer and cost allocation ask.",
            "output": "Final hearing closing script aligned with filing package.",
        },
    ]


def build_package_completeness(
    *,
    generated_documents_count: int,
    evidence_matrix: list[dict[str, Any]],
    review_checklist: list[dict[str, Any]],
    unresolved_review_items: list[str],
) -> dict[str, Any]:
    missing_evidence = sum(1 for item in evidence_matrix if str(item.get("status")) == "missing")
    required_items = [item for item in review_checklist if bool(item.get("required"))]
    required_count = len(required_items)
    unresolved_required = len(unresolved_review_items)

    score = 100.0
    if generated_documents_count == 0:
        score -= 40.0
    score -= min(missing_evidence * 7.0, 28.0)
    if required_count:
        score -= (unresolved_required / required_count) * 25.0
    score = round(max(0.0, min(score, 100.0)), 1)

    status = "complete" if score >= 85 and generated_documents_count > 0 and unresolved_required == 0 else "incomplete"
    return {
        "status": status,
        "score": score,
        "generated_documents_count": generated_documents_count,
        "missing_evidence_items": missing_evidence,
        "unresolved_required_review_items": unresolved_required,
        "note": "Pre-filing package completeness estimate based on current workflow outputs.",
    }


def build_opponent_objections(
    *,
    validation_checks: list[dict[str, str]],
    evidence_admissibility_map: list[dict[str, str]],
    dispute_type: str,
) -> list[dict[str, str]]:
    objections: list[dict[str, str]] = []
    warn_count = sum(1 for item in validation_checks if str(item.get("status")) == "warn")
    high_risk_evidence = [
        item for item in evidence_admissibility_map if str(item.get("risk")) in {"high", "medium"}
    ]

    objections.append(
        {
            "objection": "Challenge to procedural admissibility of claim",
            "likelihood": "high" if warn_count >= 2 else "medium",
            "rebuttal": "Demonstrate compliance with procedural requisites and eliminate all validation warnings.",
        }
    )
    objections.append(
        {
            "objection": "Challenge to evidentiary sufficiency/relevance",
            "likelihood": "high" if len(high_risk_evidence) >= 3 else "medium",
            "rebuttal": "Map each fact to admissible evidence and prepare admissibility argument for each item.",
        }
    )
    objections.append(
        {
            "objection": "Challenge to legal qualification and remedy scope",
            "likelihood": "medium",
            "rebuttal": f"Align legal basis and requested remedies with dispute profile: {dispute_type}.",
        }
    )
    return objections[:8]


def build_settlement_strategy(
    *,
    summary: dict[str, Any],
    fee_scenarios: list[dict[str, Any]],
    readiness_breakdown: dict[str, Any],
) -> dict[str, Any]:
    dispute_type = str(summary.get("dispute_type") or "General dispute")
    readiness_score = float(readiness_breakdown.get("score") or 0.0)
    base_total = None
    for scenario in fee_scenarios:
        if str(scenario.get("name")) == "base":
            base_total = scenario.get("total_with_fee_uah")
            break

    if readiness_score >= 80:
        window = "litigation-first"
        recommendation = "Proceed with filing; negotiate only from strong litigation position."
    elif readiness_score >= 60:
        window = "parallel"
        recommendation = "Run parallel path: fix blockers while sending structured settlement offer."
    else:
        window = "settlement-first"
        recommendation = "Prioritize pre-trial settlement while strengthening litigation package."

    return {
        "dispute_type": dispute_type,
        "window": window,
        "target_amount_uah": base_total,
        "recommendation": recommendation,
        "note": "Settlement strategy is advisory and should be approved by responsible lawyer.",
    }


def build_enforcement_plan(
    *,
    recommended_doc_types: list[str],
    ready_for_filing: bool,
) -> list[dict[str, str]]:
    steps: list[dict[str, str]] = [
        {
            "step": "Prepare enforcement-ready document set",
            "timing": "pre-judgment",
            "details": "Maintain clean evidence index and payment details for future enforcement stage.",
        },
        {
            "step": "Obtain enforceable writ",
            "timing": "post-judgment",
            "details": "Request writ immediately after judgment enters into force.",
        },
        {
            "step": "Open enforcement proceeding",
            "timing": "post-writ",
            "details": "File opening motion with executor and attach debtor identification data.",
        },
        {
            "step": "Track assets and measures",
            "timing": "active enforcement",
            "details": "Request asset search, account seizure, and monitor enforcement actions.",
        },
    ]

    if "appeal_complaint" in recommended_doc_types:
        steps.insert(
            1,
            {
                "step": "Control appellate stage effect on enforceability",
                "timing": "appeal window",
                "details": "Track appeal status before initiating forced execution.",
            },
        )
    if not ready_for_filing:
        steps.insert(
            0,
            {
                "step": "Close filing blockers",
                "timing": "immediate",
                "details": "Enforcement planning depends on a valid filing and procedural progression.",
            },
        )
    return steps[:8]


def build_cpc_compliance_check(
    *,
    source_text: str,
    validation_checks: list[dict[str, str]],
    party_profile: dict[str, Any],
    evidence_matrix: list[dict[str, Any]],
    generated_documents_count: int,
) -> list[dict[str, str]]:
    text = _normalized(source_text)
    validation_map = {str(item.get("code")): str(item.get("status")) for item in validation_checks}
    party_score = float(party_profile.get("completion_score") or 0.0)
    party_missing = party_profile.get("missing_items") or []
    evidence_ok_count = sum(1 for item in evidence_matrix if str(item.get("status")) == "ok")

    has_court_marker = any(marker in text for marker in ("суд", "court", "підсуд", "jurisdiction"))
    has_claim_amount = validation_map.get("claim_amount_detected") == "pass"
    has_parties = party_score >= 70 and not party_missing
    has_evidence_mapping = evidence_ok_count > 0
    has_attachments = generated_documents_count > 0

    return [
        {
            "requirement": "Court and jurisdiction details",
            "article": "CPC Art. 175(3), Arts. 27-30",
            "status": "pass" if has_court_marker else "warn",
            "note": "Claim should explicitly identify court and jurisdiction basis.",
        },
        {
            "requirement": "Complete party identifiers and addresses",
            "article": "CPC Art. 175(3)",
            "status": "pass" if has_parties else "warn",
            "note": "Plaintiff/defendant requisites should be complete for proper service.",
        },
        {
            "requirement": "Claim price and monetary calculation",
            "article": "CPC Art. 175(3), Civil Code Art. 625",
            "status": "pass" if has_claim_amount else "warn",
            "note": "Principal, surcharge, and fee should be numerically justified.",
        },
        {
            "requirement": "Factual basis linked to evidence",
            "article": "CPC Art. 175(5), Art. 77",
            "status": "pass" if has_evidence_mapping else "warn",
            "note": "Each material fact should be supported by at least one admissible item.",
        },
        {
            "requirement": "Attachment package under filing rules",
            "article": "CPC Art. 177",
            "status": "pass" if has_attachments else "warn",
            "note": "Attach main procedural document and required annexes before filing.",
        },
    ]


def build_procedural_document_blueprint(
    *,
    recommended_doc_types: list[str],
    cpc_compliance_check: list[dict[str, str]],
    generated_documents_count: int,
) -> list[dict[str, Any]]:
    primary_doc_type = recommended_doc_types[0] if recommended_doc_types else "lawsuit_debt_loan"
    compliance_by_requirement = {
        str(item.get("requirement")): str(item.get("status")) for item in cpc_compliance_check
    }
    has_generated = generated_documents_count > 0

    blueprint: list[dict[str, Any]] = [
        {
            "section": "Header: court and parties",
            "required": True,
            "status": "ok"
            if compliance_by_requirement.get("Court and jurisdiction details") == "pass"
            and compliance_by_requirement.get("Complete party identifiers and addresses") == "pass"
            else "warn",
            "note": "Court name, parties, addresses, identifiers, contact details.",
        },
        {
            "section": "Facts and chronology",
            "required": True,
            "status": "ok"
            if compliance_by_requirement.get("Factual basis linked to evidence") == "pass"
            else "warn",
            "note": "Chronological narrative of legal facts with dates and event links.",
        },
        {
            "section": "Legal qualification",
            "required": True,
            "status": "ok",
            "note": "Structured legal basis by code and article references.",
        },
        {
            "section": "Prayer for relief",
            "required": True,
            "status": "ok"
            if compliance_by_requirement.get("Claim price and monetary calculation") == "pass"
            else "warn",
            "note": "Specific requested remedies and allocation of court costs.",
        },
        {
            "section": "Attachments list",
            "required": True,
            "status": "ok"
            if compliance_by_requirement.get("Attachment package under filing rules") == "pass"
            else "warn",
            "note": "Enumerate evidence, fee proof, and copies for participants.",
        },
        {
            "section": "Signature and date",
            "required": True,
            "status": "ok" if has_generated else "warn",
            "note": "Signer identity, authority, and filing date.",
        },
    ]

    if primary_doc_type == "appeal_complaint":
        blueprint.insert(
            2,
            {
                "section": "Appeal grounds and request to appellate court",
                "required": True,
                "status": "ok",
                "note": "Specify errors of first-instance court and appellate relief requested.",
            },
        )
    return blueprint[:10]


def build_deadline_control(
    *,
    source_text: str,
    recommended_doc_types: list[str],
    unresolved_questions: list[str],
    unresolved_review_items: list[str],
) -> list[dict[str, str | None]]:
    known_dates = _extract_dates(source_text)
    has_known_dates = bool(known_dates)
    base_date = known_dates[-1] if has_known_dates else date.today()
    today = date.today()
    recommended_set = {str(item) for item in recommended_doc_types}
    has_appeal = "appeal_complaint" in recommended_set
    has_cassation = "cassation_complaint" in recommended_set
    has_appellate_flow = bool(recommended_set.intersection(APPELLATE_DOC_TYPES))
    urgent_window_days = settings.full_lawyer_urgent_window_days

    def _deadline_item(
        *,
        code: str,
        title: str,
        due_date: date,
        basis: str,
        note: str,
    ) -> dict[str, str]:
        if due_date < today:
            status = "overdue"
        elif (due_date - today).days <= urgent_window_days:
            status = "urgent"
        else:
            status = "ok"
        return {
            "code": code,
            "title": title,
            "due_date": due_date.isoformat(),
            "status": status,
            "basis": basis,
            "note": note,
        }

    deadlines: list[dict[str, str]] = [
        _deadline_item(
            code="clarification_completion",
            title="Complete clarification and review gate",
            due_date=calculate_deadline(today, settings.full_lawyer_clarification_deadline_days),
            basis="Internal pre-filing control",
            note="Filing should not proceed while required clarifications/review are unresolved.",
        ),
        _deadline_item(
            code="filing_target",
            title="Target filing date for initial package",
            due_date=calculate_deadline(today, settings.full_lawyer_filing_target_days),
            basis="Internal litigation planning",
            note="Baseline filing window for current procedural package.",
        ),
        _deadline_item(
            code="limitation_period_check",
            title="Limitation period checkpoint",
            due_date=calculate_limitation_deadline(base_date),
            basis="Civil Code limitation period (general 3 years)",
            note=f"Computed from latest detected date: {base_date.isoformat()}.",
        ),
    ]

    if has_appellate_flow and not has_known_dates:
        deadlines.append(
            {
                "code": "appellate_decision_date_missing",
                "title": "Missing decision/service date for appellate deadline control",
                "due_date": None,
                "status": "urgent",
                "basis": "Mandatory pre-check for appellate/cassation filing terms",
                "note": "Cannot calculate statutory appeal/cassation windows without court act date and service date.",
            }
        )
    if has_appeal and has_known_dates:
        deadlines.append(
            _deadline_item(
                code="appeal_deadline",
                title="Appeal filing window checkpoint",
                due_date=calculate_deadline(base_date, settings.appeal_deadline_days),
                basis="Procedural appeal timeline control",
                note="Validate exact appeal term under applicable procedure and court act/service date.",
            )
        )
    if has_cassation and has_known_dates:
        deadlines.append(
            _deadline_item(
                code="cassation_deadline",
                title="Cassation filing window checkpoint",
                due_date=calculate_deadline(base_date, settings.cassation_deadline_days),
                basis="Procedural cassation timeline control",
                note="Validate exact cassation term under applicable procedure and date of appellate act/service.",
            )
        )
    if not has_appellate_flow:
        deadlines.append(
            _deadline_item(
                code="response_window",
                title="Expected defendant response window",
                due_date=calculate_deadline(today, settings.full_lawyer_response_window_days),
                basis="Typical civil timeline planning",
                note="Calendar marker for preparing reply/objections package.",
            )
        )

    if unresolved_questions or unresolved_review_items:
        for item in deadlines:
            if item["code"] in {"clarification_completion", "filing_target"} and item["status"] == "ok":
                item["status"] = "urgent"
    return deadlines[:10]


def build_court_fee_breakdown(
    *,
    financial_snapshot: dict[str, Any],
    fee_scenarios: list[dict[str, Any]],
    validation_checks: list[dict[str, str]],
) -> dict[str, Any]:
    base_scenario = next((item for item in fee_scenarios if str(item.get("name")) == "base"), None)
    principal = (
        float(base_scenario.get("principal_uah"))
        if base_scenario and base_scenario.get("principal_uah") is not None
        else float(financial_snapshot.get("principal_uah"))
        if financial_snapshot.get("principal_uah") is not None
        else None
    )
    penalty = (
        float(base_scenario.get("penalty_uah"))
        if base_scenario and base_scenario.get("penalty_uah") is not None
        else float(financial_snapshot.get("estimated_penalty_uah"))
        if financial_snapshot.get("estimated_penalty_uah") is not None
        else None
    )
    court_fee = (
        float(base_scenario.get("court_fee_uah"))
        if base_scenario and base_scenario.get("court_fee_uah") is not None
        else float(financial_snapshot.get("estimated_court_fee_uah"))
        if financial_snapshot.get("estimated_court_fee_uah") is not None
        else None
    )
    total_with_fee = (
        float(base_scenario.get("total_with_fee_uah"))
        if base_scenario and base_scenario.get("total_with_fee_uah") is not None
        else float(financial_snapshot.get("estimated_total_with_fee_uah"))
        if financial_snapshot.get("estimated_total_with_fee_uah") is not None
        else None
    )

    inflation_losses = 0.0
    claim_price = None
    if principal is not None:
        claim_price = round(principal + (penalty or 0.0) + inflation_losses, 2)

    warn_count = sum(1 for item in validation_checks if str(item.get("status")) == "warn")
    status = "estimated_with_warnings" if warn_count > 0 else "estimated"

    return {
        "principal_uah": principal,
        "penalty_uah": penalty,
        "inflation_losses_uah": inflation_losses,
        "claim_price_uah": claim_price,
        "court_fee_uah": court_fee,
        "total_with_fee_uah": total_with_fee,
        "status": status,
        "note": "Court fee is an estimate and must be confirmed against current statutory rates before filing.",
    }


def build_filing_attachments_register(
    *,
    generated_documents_count: int,
    evidence_matrix: list[dict[str, Any]],
    validation_checks: list[dict[str, str]],
    party_profile: dict[str, Any],
) -> list[dict[str, Any]]:
    defendant_present = bool(party_profile.get("defendant_detected"))
    copies_for_court = 2 if defendant_present else 1
    has_fee_warning = any(
        str(item.get("code")) == "court_fee_estimate"
        and str(item.get("status")) == "warn"
        for item in validation_checks
    )

    attachments: list[dict[str, Any]] = [
        {
            "name": "Main procedural document (signed)",
            "required": True,
            "available": generated_documents_count > 0,
            "copies_for_court": 1,
            "status": "ok" if generated_documents_count > 0 else "missing",
            "note": "Primary claim/complaint text ready for filing.",
        },
        {
            "name": "Proof of court fee payment",
            "required": True,
            "available": not has_fee_warning,
            "copies_for_court": 1,
            "status": "ok" if not has_fee_warning else "missing",
            "note": "Payment receipt or fee deferral motion.",
        },
        {
            "name": "Copies for other participants",
            "required": True,
            "available": generated_documents_count > 0 and defendant_present,
            "copies_for_court": copies_for_court,
            "status": "ok" if generated_documents_count > 0 and defendant_present else "warn",
            "note": "Prepare copies by number of participants.",
        },
    ]

    for item in evidence_matrix[:8]:
        title = str(item.get("title") or item.get("code") or "Evidence item")
        status = str(item.get("status") or "")
        available = status == "ok"
        attachments.append(
            {
                "name": f"Evidence: {title}",
                "required": True,
                "available": available,
                "copies_for_court": copies_for_court,
                "status": "ok" if available else "missing",
                "note": "Attach readable copy and mark relevance in evidence index.",
            }
        )
    return attachments[:12]


def build_cpc_175_requisites_map(
    *,
    source_text: str,
    summary: dict[str, Any],
    party_profile: dict[str, Any],
    validation_checks: list[dict[str, str]],
) -> list[dict[str, str]]:
    text = _normalized(source_text)
    validation_map = {str(item.get("code")): str(item.get("status")) for item in validation_checks}
    has_parties = float(party_profile.get("completion_score") or 0.0) >= 70
    has_amount = validation_map.get("claim_amount_detected") == "pass"
    has_dates = bool(_extract_dates(source_text))
    has_strategy = bool(_as_str_list(summary.get("strategy_steps"), max_items=2))
    has_court = any(marker in text for marker in ("суд", "court", "підсуд", "jurisdiction"))

    return [
        {
            "requisite": "Court designation",
            "status": "pass" if has_court else "warn",
            "source_signal": "court marker in source text",
            "note": "Claim header should contain exact court name and jurisdiction route.",
        },
        {
            "requisite": "Parties and identifiers",
            "status": "pass" if has_parties else "warn",
            "source_signal": "party profile completion score",
            "note": "Plaintiff/defendant data must be complete for service and identification.",
        },
        {
            "requisite": "Claim price calculation",
            "status": "pass" if has_amount else "warn",
            "source_signal": "claim amount validation check",
            "note": "Principal, surcharge and fee must be justified and traceable.",
        },
        {
            "requisite": "Factual chronology",
            "status": "pass" if has_dates else "warn",
            "source_signal": "date extraction from source",
            "note": "Material dates should be explicit for causation and limitation analysis.",
        },
        {
            "requisite": "Legal and strategic grounding",
            "status": "pass" if has_strategy else "warn",
            "source_signal": "strategy steps availability",
            "note": "Legal qualification should connect facts to requested remedy.",
        },
    ]


def build_cpc_177_attachments_map(
    *,
    filing_attachments_register: list[dict[str, Any]],
    generated_documents_count: int,
) -> list[dict[str, Any]]:
    available_count = sum(1 for item in filing_attachments_register if bool(item.get("available")))
    total_count = len(filing_attachments_register)
    has_main_doc = generated_documents_count > 0

    return [
        {
            "attachment_group": "Main claim document",
            "required": True,
            "status": "pass" if has_main_doc else "warn",
            "items_total": 1,
            "items_available": 1 if has_main_doc else 0,
            "note": "Signed main procedural text for filing.",
        },
        {
            "attachment_group": "Evidence annexes",
            "required": True,
            "status": "pass" if available_count >= max(2, total_count // 2) else "warn",
            "items_total": total_count,
            "items_available": available_count,
            "note": "Evidence copies and indexing for all material facts.",
        },
        {
            "attachment_group": "Fee and service proof",
            "required": True,
            "status": "pass"
            if any("fee" in str(item.get("name") or "").lower() and bool(item.get("available")) for item in filing_attachments_register)
            else "warn",
            "items_total": 1,
            "items_available": 1
            if any("fee" in str(item.get("name") or "").lower() and bool(item.get("available")) for item in filing_attachments_register)
            else 0,
            "note": "Court fee proof or deferment motion and copies for participants.",
        },
    ]


def build_prayer_part_audit(
    *,
    recommended_doc_types: list[str],
    remedy_coverage: list[dict[str, Any]],
    fee_scenarios: list[dict[str, Any]],
    generated_documents_count: int,
) -> dict[str, Any]:
    covered_remedies = [str(item.get("remedy")) for item in remedy_coverage if bool(item.get("covered"))]
    uncovered_remedies = [str(item.get("remedy")) for item in remedy_coverage if not bool(item.get("covered"))]
    base_total = None
    for item in fee_scenarios:
        if str(item.get("name")) == "base":
            base_total = item.get("total_with_fee_uah")
            break

    score = 100.0
    if generated_documents_count == 0:
        score -= 35.0
    score -= min(len(uncovered_remedies) * 10.0, 30.0)
    if base_total is None:
        score -= 15.0
    score = round(max(0.0, min(score, 100.0)), 1)

    status = "ready" if score >= 80 else "needs_improvement"
    return {
        "status": status,
        "score": score,
        "target_total_uah": base_total,
        "covered_requests": covered_remedies[:8],
        "missing_requests": uncovered_remedies[:8],
        "note": (
            "Prayer part should be concrete: principal claim, surcharge, court costs, and procedural asks."
            if "appeal_complaint" not in recommended_doc_types
            else "Prayer part should specify appellate relief and requested decision outcome."
        ),
    }


def build_fact_norm_evidence_chain(
    *,
    legal_argument_map: list[dict[str, Any]],
    evidence_matrix: list[dict[str, Any]],
) -> list[dict[str, str]]:
    evidence_ok = [item for item in evidence_matrix if str(item.get("status")) == "ok"]
    evidence_missing = [item for item in evidence_matrix if str(item.get("status")) != "ok"]
    chain: list[dict[str, str]] = []

    for idx, argument in enumerate(legal_argument_map[:6]):
        issue = str(argument.get("issue") or "Material issue")
        norm = str(argument.get("legal_basis") or "Legal basis to be finalized")
        if idx < len(evidence_ok):
            evidence_title = str(evidence_ok[idx].get("title") or evidence_ok[idx].get("code") or "Evidence item")
            status = "linked"
        elif evidence_missing:
            evidence_title = str(
                evidence_missing[min(idx, len(evidence_missing) - 1)].get("title")
                or evidence_missing[min(idx, len(evidence_missing) - 1)].get("code")
                or "Evidence item"
            )
            status = "gap"
        else:
            evidence_title = "No mapped evidence"
            status = "gap"
        chain.append(
            {
                "fact_issue": issue,
                "legal_norm": norm,
                "evidence": evidence_title,
                "status": status,
                "note": "Every key fact should map to at least one admissible evidence source.",
            }
        )
    return chain


def build_pre_filing_red_flags(
    *,
    validation_checks: list[dict[str, str]],
    procedural_defect_scan: list[dict[str, str]],
    deadline_control: list[dict[str, Any]],
    cpc_compliance_check: list[dict[str, str]],
) -> list[dict[str, str]]:
    red_flags: list[dict[str, str]] = []

    for item in validation_checks:
        if str(item.get("status")) == "warn":
            red_flags.append(
                {
                    "severity": "high",
                    "flag": str(item.get("message") or "Validation warning"),
                    "action": "Resolve warning before filing submission.",
                }
            )

    for item in procedural_defect_scan:
        severity = str(item.get("severity") or "low")
        if severity in {"high", "medium"}:
            red_flags.append(
                {
                    "severity": severity,
                    "flag": str(item.get("issue") or "Procedural defect risk"),
                    "action": str(item.get("fix") or "Apply procedural correction before filing."),
                }
            )

    for item in deadline_control:
        status = str(item.get("status") or "")
        if status in {"overdue", "urgent"}:
            red_flags.append(
                {
                    "severity": "high" if status == "overdue" else "medium",
                    "flag": f"Deadline risk: {str(item.get('title') or 'Unknown deadline')}",
                    "action": "Escalate deadline handling and update filing plan immediately.",
                }
            )

    for item in cpc_compliance_check:
        if str(item.get("status")) == "warn":
            red_flags.append(
                {
                    "severity": "medium",
                    "flag": f"CPC compliance gap: {str(item.get('requirement') or 'Unknown requirement')}",
                    "action": "Fill missing requisites under CPC before final submission.",
                }
            )

    if not red_flags:
        red_flags.append(
            {
                "severity": "low",
                "flag": "No critical pre-filing red flags detected.",
                "action": "Proceed with final advocate review and submission.",
            }
        )
    return red_flags[:12]


def build_text_section_audit(
    *,
    procedural_document_blueprint: list[dict[str, Any]],
    generated_documents: list[dict[str, Any]],
) -> list[dict[str, str]]:
    generated_text = " ".join(str(item.get("_generated_text") or "") for item in generated_documents).lower()
    has_text = bool(generated_text.strip())
    section_markers: dict[str, tuple[str, ...]] = {
        "header": ("суд", "court", "plaintiff", "defendant", "позивач", "відповідач"),
        "facts": ("обставин", "facts", "дата", "date"),
        "legal": ("ст.", "article", "цпк", "цк"),
        "prayer": ("прошу", "pray", "просимо"),
        "attachments": ("додат", "annex", "attachment"),
        "signature": ("підпис", "signature", "дата"),
    }

    audits: list[dict[str, str]] = []
    for item in procedural_document_blueprint[:10]:
        section = str(item.get("section") or "Document section")
        section_key = section.lower()
        markers = ()
        if "header" in section_key:
            markers = section_markers["header"]
        elif "fact" in section_key:
            markers = section_markers["facts"]
        elif "legal" in section_key:
            markers = section_markers["legal"]
        elif "prayer" in section_key or "relief" in section_key:
            markers = section_markers["prayer"]
        elif "attachment" in section_key:
            markers = section_markers["attachments"]
        elif "signature" in section_key:
            markers = section_markers["signature"]

        marker_hit = has_text and (not markers or any(marker in generated_text for marker in markers))
        blueprint_status = str(item.get("status") or "warn")
        status = "ok" if marker_hit and blueprint_status == "ok" else "warn"
        audits.append(
            {
                "section": section,
                "status": status,
                "note": "Section markers were checked against generated text draft.",
            }
        )
    return audits


def build_service_plan(
    *,
    party_profile: dict[str, Any],
    filing_attachments_register: list[dict[str, Any]],
    deadline_control: list[dict[str, Any]],
) -> list[dict[str, str]]:
    has_defendant = bool(party_profile.get("defendant_detected"))
    has_plaintiff = bool(party_profile.get("plaintiff_detected"))
    has_copies = any(
        "copies" in str(item.get("name") or "").lower() and bool(item.get("available"))
        for item in filing_attachments_register
    )
    urgent_deadline = any(str(item.get("status")) in {"urgent", "overdue"} for item in deadline_control)

    plan: list[dict[str, str]] = [
        {
            "recipient": "Court",
            "method": "E-court or paper filing",
            "status": "ready" if has_plaintiff else "warn",
            "note": "Submit signed claim with annex register and fee proof.",
        },
        {
            "recipient": "Defendant",
            "method": "Registered mail with inventory / e-service where allowed",
            "status": "ready" if has_defendant and has_copies else "warn",
            "note": "Service package should mirror court filing annexes.",
        },
        {
            "recipient": "Other participants",
            "method": "Service copies per procedural role",
            "status": "ready" if has_copies else "warn",
            "note": "Prepare participant-specific copy sets and track delivery evidence.",
        },
    ]
    if urgent_deadline:
        plan.insert(
            0,
            {
                "recipient": "Litigation team",
                "method": "Immediate deadline escalation",
                "status": "urgent",
                "note": "At least one near-term deadline is urgent/overdue.",
            }
        )
    return plan[:8]


def build_prayer_rewrite_suggestions(
    *,
    prayer_part_audit: dict[str, Any],
    remedy_coverage: list[dict[str, Any]],
    summary: dict[str, Any],
) -> list[dict[str, str]]:
    dispute_type = str(summary.get("dispute_type") or "civil dispute")
    missing = [str(item.get("remedy")) for item in remedy_coverage if not bool(item.get("covered"))][:5]
    score = float(prayer_part_audit.get("score") or 0.0)
    target_amount = prayer_part_audit.get("target_total_uah")
    amount_text = f"{target_amount} UAH" if target_amount is not None else "calculated amount"

    suggestions: list[dict[str, str]] = [
        {
            "priority": "high",
            "suggestion": f"State a precise monetary request ({amount_text}) and split principal/surcharge/costs.",
            "rationale": "Courts require a concrete and calculable prayer part.",
        },
        {
            "priority": "high",
            "suggestion": "Add separate line for recovering court fee from defendant.",
            "rationale": "Cost allocation should be explicitly requested in prayer part.",
        },
        {
            "priority": "medium",
            "suggestion": f"Align each requested remedy with legal qualification of {dispute_type}.",
            "rationale": "Prayer should directly follow the legal and factual structure.",
        },
    ]
    for remedy in missing:
        suggestions.append(
            {
                "priority": "medium",
                "suggestion": f"Add missing remedy request: {remedy}.",
                "rationale": "Current package indicates this remedy is not explicitly covered.",
            }
        )
    if score >= 85:
        suggestions.append(
            {
                "priority": "low",
                "suggestion": "Keep prayer concise and avoid duplicating the same remedy with different wording.",
                "rationale": "Current prayer quality score is strong; focus on precision.",
            }
        )
    return suggestions[:10]


def build_contradiction_hotspots(
    *,
    validation_checks: list[dict[str, str]],
    consistency_report: list[dict[str, str]],
    cpc_175_requisites_map: list[dict[str, str]],
) -> list[dict[str, str]]:
    hotspots: list[dict[str, str]] = []

    for item in validation_checks:
        if str(item.get("status")) == "warn":
            hotspots.append(
                {
                    "issue": str(item.get("message") or "Validation inconsistency"),
                    "severity": "high",
                    "fix": "Resolve data mismatch before final drafting.",
                }
            )

    for item in consistency_report:
        status = str(item.get("status") or "")
        if status in {"warn", "error"}:
            hotspots.append(
                {
                    "issue": str(item.get("message") or "Consistency risk"),
                    "severity": "medium",
                    "fix": "Reconcile facts, amounts, and requested remedies.",
                }
            )

    for item in cpc_175_requisites_map:
        if str(item.get("status")) == "warn":
            hotspots.append(
                {
                    "issue": f"Missing CPC requisite: {str(item.get('requisite') or 'Unknown requisite')}",
                    "severity": "medium",
                    "fix": "Complete this requisite in claim body and header.",
                }
            )

    if not hotspots:
        hotspots.append(
            {
                "issue": "No significant contradiction hotspots detected.",
                "severity": "low",
                "fix": "Proceed with advocate quality review.",
            }
        )
    return hotspots[:10]


def build_judge_questions_simulation(
    *,
    legal_argument_map: list[dict[str, Any]],
    evidence_admissibility_map: list[dict[str, str]],
    pre_filing_red_flags: list[dict[str, str]],
) -> list[dict[str, str]]:
    questions: list[dict[str, str]] = []
    top_arguments = legal_argument_map[:3]
    for argument in top_arguments:
        issue = str(argument.get("issue") or "key issue")
        legal_basis = str(argument.get("legal_basis") or "legal basis")
        questions.append(
            {
                "question": f"How exactly does evidence prove: {issue}?",
                "why_it_matters": "Court will test whether factual assertions are actually substantiated.",
                "prep_answer_hint": f"Prepare a direct evidence chain and cite {legal_basis}.",
            }
        )

    risky_evidence = [item for item in evidence_admissibility_map if str(item.get("risk")) in {"high", "medium"}]
    if risky_evidence:
        first = risky_evidence[0]
        questions.append(
            {
                "question": f"Why is '{str(first.get('evidence') or 'this evidence')}' admissible and reliable?",
                "why_it_matters": "Admissibility objections can reduce probative value or exclude evidence.",
                "prep_answer_hint": "Prepare admissibility argument and secondary corroborating evidence.",
            }
        )

    if pre_filing_red_flags:
        red = pre_filing_red_flags[0]
        questions.append(
            {
                "question": f"How did you address this pre-filing risk: {str(red.get('flag') or '')}?",
                "why_it_matters": "Unresolved pre-filing risks often become procedural objections.",
                "prep_answer_hint": "Document the fix and include supporting proof in annex register.",
            }
        )

    if not questions:
        questions.append(
            {
                "question": "Are claims, evidence, and remedies fully aligned?",
                "why_it_matters": "Core alignment determines filing sustainability.",
                "prep_answer_hint": "Run final fact-norm-evidence and remedy consistency pass.",
            }
        )
    return questions[:8]


def build_citation_quality_gate(
    *,
    citation_pack: dict[str, Any],
    legal_argument_map: list[dict[str, Any]],
    recommended_doc_types: list[str],
) -> dict[str, Any]:
    statutory_refs = [str(item) for item in citation_pack.get("statutory_refs") or [] if str(item).strip()]
    case_refs = citation_pack.get("case_refs") or []
    argument_count = len(legal_argument_map)
    cpc_refs_count = sum(1 for ref in statutory_refs if "цпк" in ref.lower() or "civil procedure code" in ref.lower())
    has_case_refs = len(case_refs) > 0
    is_appeal = "appeal_complaint" in recommended_doc_types

    score = 100.0
    if cpc_refs_count == 0:
        score -= 30.0
    if not has_case_refs:
        score -= 15.0
    if argument_count >= 3 and len(statutory_refs) < 2:
        score -= 20.0
    if is_appeal and cpc_refs_count < 1:
        score -= 15.0
    score = round(max(0.0, min(score, 100.0)), 1)

    issues: list[str] = []
    if cpc_refs_count == 0:
        issues.append("No explicit CPC reference detected in citation pack.")
    if not has_case_refs:
        issues.append("No case-law references attached for motivation support.")
    if argument_count >= 3 and len(statutory_refs) < 2:
        issues.append("Legal argument map is richer than citation density; add direct norm links.")

    status = "strong" if score >= 80 else ("medium" if score >= 60 else "weak")
    return {
        "status": status,
        "score": score,
        "cpc_refs_count": cpc_refs_count,
        "case_refs_count": len(case_refs),
        "issues": issues[:8],
        "note": "Citation quality gate is advisory; final legal citation set should be advocate-approved.",
    }


def build_filing_decision_card(
    *,
    readiness_breakdown: dict[str, Any],
    pre_filing_red_flags: list[dict[str, str]],
    validation_checks: list[dict[str, str]],
    unresolved_questions: list[str],
    unresolved_review_items: list[str],
) -> dict[str, Any]:
    readiness_score = float(readiness_breakdown.get("score") or 0.0)
    high_red_flags = [item for item in pre_filing_red_flags if str(item.get("severity")) == "high"]
    warn_checks = [item for item in validation_checks if str(item.get("status")) == "warn"]
    warn_count = len(warn_checks)
    deadline_warn_checks = [
        item
        for item in warn_checks
        if str(item.get("code") or "") in {"appeal_deadline_precheck", "cassation_deadline_precheck"}
    ]

    blockers: list[str] = []
    if unresolved_questions:
        blockers.append(f"Unresolved clarifications: {len(unresolved_questions)}.")
    if unresolved_review_items:
        blockers.append(f"Unresolved review confirmations: {len(unresolved_review_items)}.")
    if high_red_flags:
        blockers.append(f"High severity pre-filing flags: {len(high_red_flags)}.")
    if warn_count > 0:
        blockers.append(f"Validation warnings: {warn_count}.")
    for item in deadline_warn_checks[:2]:
        message = str(item.get("message") or "").strip()
        if message:
            blockers.append(f"Deadline pre-check: {message}")

    if not blockers and readiness_score >= 80:
        decision = "go"
        next_step = "Proceed to final advocate review and filing submission."
    elif readiness_score >= 60:
        decision = "conditional_go"
        next_step = "Resolve listed blockers, rerun checks, then submit."
    else:
        decision = "hold"
        next_step = "Do not file yet; close blockers and rebuild filing package."

    confidence = round(max(0.0, min(1.0, readiness_score / 100.0)), 2)
    return {
        "decision": decision,
        "confidence": confidence,
        "readiness_score": readiness_score,
        "blockers": blockers[:8],
        "next_step": next_step,
        "note": "Decision card is a pre-filing control aid, not a substitute for advocate sign-off.",
    }


def build_processual_language_audit(
    *,
    generated_documents: list[dict[str, Any]],
    cpc_175_requisites_map: list[dict[str, str]],
) -> dict[str, Any]:
    combined_text = " ".join(str(item.get("_generated_text") or "") for item in generated_documents).lower()
    has_generated = bool(combined_text.strip())
    formal_markers = ("позовна заява", "прошу суд", "встановив", "обґрунтування", "ст.")
    informal_markers = ("я думаю", "мені здається", "типу", "короче")

    formal_hits = sum(1 for marker in formal_markers if marker in combined_text)
    informal_hits = sum(1 for marker in informal_markers if marker in combined_text)
    cpc_warns = sum(1 for item in cpc_175_requisites_map if str(item.get("status")) == "warn")

    score = 100.0
    if not has_generated:
        score -= 50.0
    score -= max(0, 3 - formal_hits) * 10.0
    score -= min(informal_hits * 20.0, 40.0)
    score -= min(cpc_warns * 5.0, 20.0)
    score = round(max(0.0, min(score, 100.0)), 1)

    status = "strong" if score >= 80 else ("medium" if score >= 60 else "weak")
    return {
        "status": status,
        "score": score,
        "formal_markers_found": formal_hits,
        "informal_markers_found": informal_hits,
        "note": "Language audit checks whether draft uses formal procedural style suitable for court filing.",
    }


def build_evidence_gap_actions(
    *,
    evidence_matrix: list[dict[str, Any]],
    evidence_admissibility_map: list[dict[str, str]],
) -> list[dict[str, str]]:
    admissibility_by_evidence = {
        str(item.get("evidence") or "").lower(): str(item.get("admissibility") or "")
        for item in evidence_admissibility_map
    }
    actions: list[dict[str, str]] = []

    for item in evidence_matrix[:12]:
        title = str(item.get("title") or item.get("code") or "Evidence item")
        status = str(item.get("status") or "")
        key = title.lower()
        admissibility = admissibility_by_evidence.get(key, "unknown")
        if status == "ok" and admissibility in {"high", "medium"}:
            continue
        priority = "high" if status == "missing" else "medium"
        actions.append(
            {
                "evidence": title,
                "priority": priority,
                "action": "Collect original/certified copy and map this evidence to specific fact statements.",
                "deadline_hint": "Before final filing package assembly.",
            }
        )

    if not actions:
        actions.append(
            {
                "evidence": "No critical evidence gaps",
                "priority": "low",
                "action": "Maintain current evidence bundle and monitor for opponent objections.",
                "deadline_hint": "Continuous.",
            }
        )
    return actions[:10]


def build_deadline_alert_board(
    *,
    deadline_control: list[dict[str, Any]],
) -> list[dict[str, str | int]]:
    board: list[dict[str, str | int]] = []
    today = date.today()
    for item in deadline_control[:12]:
        code = str(item.get("code") or "")
        due_date_raw = str(item.get("due_date") or "")
        try:
            due_date = datetime.strptime(due_date_raw, "%Y-%m-%d").date()
            days_left = (due_date - today).days
        except ValueError:
            days_left = 999
        status = str(item.get("status") or "ok")
        if code in CRITICAL_APPELLATE_DEADLINE_CODES and not due_date_raw:
            level = "critical"
            recommended_action = "Provide decision/service date and recalculate appellate deadline immediately."
        elif status == "overdue" or days_left < 0:
            level = "critical"
            recommended_action = "Escalate immediately."
        elif code in CRITICAL_APPELLATE_DEADLINE_CODES and status == "urgent":
            level = "critical"
            recommended_action = "Escalate immediately and prepare filing package without delay."
        elif status == "urgent" or days_left <= 5:
            level = "warning"
            recommended_action = "Track and prepare filing step."
        else:
            level = "normal"
            recommended_action = "Track and prepare filing step."
        board.append(
            {
                "title": str(item.get("title") or "Deadline"),
                "level": level,
                "days_left": days_left,
                "recommended_action": recommended_action,
            }
        )
    return board


def build_filing_packet_order(
    *,
    filing_attachments_register: list[dict[str, Any]],
    generated_documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    packet: list[dict[str, Any]] = []
    order = 1
    if generated_documents:
        for item in generated_documents[:5]:
            packet.append(
                {
                    "order": order,
                    "item": f"Procedural document: {str(item.get('doc_type') or 'document')}",
                    "required": True,
                    "status": "ready",
                    "note": str(item.get("id") or ""),
                }
            )
            order += 1
    for attachment in filing_attachments_register[:10]:
        packet.append(
            {
                "order": order,
                "item": str(attachment.get("name") or "Attachment"),
                "required": bool(attachment.get("required")),
                "status": "ready" if bool(attachment.get("available")) else "missing",
                "note": str(attachment.get("note") or ""),
            }
        )
        order += 1
    return packet[:15]


def build_opponent_response_playbook(
    *,
    opponent_objections: list[dict[str, str]],
    contradiction_hotspots: list[dict[str, str]],
) -> list[dict[str, str]]:
    playbook: list[dict[str, str]] = []
    for item in opponent_objections[:6]:
        objection = str(item.get("objection") or "Likely objection")
        rebuttal = str(item.get("rebuttal") or "Prepare legal and factual rebuttal.")
        playbook.append(
            {
                "scenario": objection,
                "counter_step": rebuttal,
                "evidence_focus": "Link rebuttal to documentary proof and norm references.",
            }
        )
    for hotspot in contradiction_hotspots[:3]:
        playbook.append(
            {
                "scenario": f"Internal inconsistency attack: {str(hotspot.get('issue') or '')}",
                "counter_step": str(hotspot.get("fix") or "Reconcile inconsistency and update draft."),
                "evidence_focus": "Provide corrected amount/date/party data in annexes.",
            }
        )
    if not playbook:
        playbook.append(
            {
                "scenario": "General denial by opponent",
                "counter_step": "Use fact-norm-evidence chain as default structured rebuttal.",
                "evidence_focus": "Present original agreement, payment trace, and correspondence chronology.",
            }
        )
    return playbook[:10]


def build_limitation_period_card(
    *,
    source_text: str,
    procedural_timeline: list[dict[str, Any]],
    validation_checks: list[dict[str, str]],
) -> dict[str, Any]:
    dates = _extract_dates(source_text)
    reference_date = dates[-1] if dates else date.today()
    limitation_deadline = calculate_limitation_deadline(reference_date)
    today = date.today()
    days_remaining = (limitation_deadline - today).days
    timeline_overdue = any(str(item.get("status")) == "overdue" for item in procedural_timeline)
    warn_count = sum(1 for item in validation_checks if str(item.get("status")) == "warn")

    if days_remaining < 0:
        risk = "high"
        status = "expired"
    elif days_remaining <= 30 or timeline_overdue:
        risk = "medium"
        status = "urgent"
    else:
        risk = "low" if warn_count <= 1 else "medium"
        status = "ok"

    return {
        "status": status,
        "risk": risk,
        "reference_date": reference_date.isoformat(),
        "limitation_deadline": limitation_deadline.isoformat(),
        "days_remaining": days_remaining,
        "note": "Limitation period card is an estimate and must be confirmed by lawyer for specific claim type.",
    }


def build_jurisdiction_challenge_guard(
    *,
    jurisdiction_recommendation: dict[str, Any],
    party_profile: dict[str, Any],
    cpc_compliance_check: list[dict[str, str]],
) -> dict[str, Any]:
    confidence = float(jurisdiction_recommendation.get("confidence") or 0.0)
    route = str(jurisdiction_recommendation.get("suggested_route") or "")
    has_party_gaps = bool(party_profile.get("missing_items"))
    cpc_warns = [item for item in cpc_compliance_check if str(item.get("status")) == "warn"]

    weak_points: list[str] = []
    mitigations: list[str] = []
    if confidence < 0.6:
        weak_points.append("Jurisdiction confidence is below recommended threshold.")
        mitigations.append("Collect full defendant/plaintiff address and venue facts before filing.")
    if has_party_gaps:
        weak_points.append("Party profile has missing identification data.")
        mitigations.append("Complete identifiers and service addresses in claim header.")
    if cpc_warns:
        weak_points.append(f"CPC compliance warnings detected: {len(cpc_warns)}.")
        mitigations.append("Close all CPC header and jurisdiction-related gaps.")

    risk_level = "low" if not weak_points else ("medium" if len(weak_points) <= 2 else "high")
    return {
        "risk_level": risk_level,
        "route": route or "Route to be finalized",
        "weak_points": weak_points[:8],
        "mitigations": mitigations[:8],
        "note": "Guard focuses on potential jurisdiction objections from court or opponent.",
    }


def build_claim_formula_card(
    *,
    fee_scenarios: list[dict[str, Any]],
    court_fee_breakdown: dict[str, Any],
    prayer_part_audit: dict[str, Any],
) -> dict[str, Any]:
    base = next((item for item in fee_scenarios if str(item.get("name")) == "base"), {})
    principal = base.get("principal_uah")
    penalty = base.get("penalty_uah")
    fee = base.get("court_fee_uah")
    if principal is None:
        principal = court_fee_breakdown.get("principal_uah")
    if penalty is None:
        penalty = court_fee_breakdown.get("penalty_uah")
    if fee is None:
        fee = court_fee_breakdown.get("court_fee_uah")

    principal_f = float(principal or 0.0)
    penalty_f = float(penalty or 0.0)
    fee_f = float(fee or 0.0)
    total = round(principal_f + penalty_f + fee_f, 2)
    formula = f"{principal_f:.2f} + {penalty_f:.2f} + {fee_f:.2f} = {total:.2f} UAH"

    prayer_score = float(prayer_part_audit.get("score") or 0.0)
    status = "ok" if total > 0 and prayer_score >= 70 else "warn"
    return {
        "status": status,
        "principal_uah": round(principal_f, 2),
        "penalty_uah": round(penalty_f, 2),
        "court_fee_uah": round(fee_f, 2),
        "total_claim_uah": total,
        "formula": formula,
        "note": "Claim formula card should match the final prayer part before filing.",
    }


def build_filing_cover_letter(
    *,
    summary: dict[str, Any],
    filing_decision_card: dict[str, Any],
    filing_packet_order: list[dict[str, Any]],
) -> dict[str, Any]:
    dispute_type = str(summary.get("dispute_type") or "Civil dispute")
    decision = str(filing_decision_card.get("decision") or "hold")
    ready_items = sum(1 for item in filing_packet_order if str(item.get("status")) == "ready")
    total_items = len(filing_packet_order)

    subject = f"Filing package submission: {dispute_type}"
    body_preview = (
        f"Please accept procedural package for {dispute_type}. "
        f"Current filing decision: {decision}. Ready packet items: {ready_items}/{total_items}."
    )
    status = "ready" if decision in {"go", "conditional_go"} and ready_items > 0 else "draft"
    return {
        "status": status,
        "subject": subject,
        "recipient": "Court registry / E-court portal",
        "body_preview": body_preview,
        "note": "Cover letter preview is generated for internal workflow and should be reviewed before sending.",
    }


def build_execution_step_tracker(
    *,
    enforcement_plan: list[dict[str, str]],
    filing_decision_card: dict[str, Any],
    deadline_alert_board: list[dict[str, Any]],
) -> list[dict[str, str]]:
    decision = str(filing_decision_card.get("decision") or "hold")
    has_critical_deadline = any(str(item.get("level")) == "critical" for item in deadline_alert_board)
    steps: list[dict[str, str]] = []
    for item in enforcement_plan[:8]:
        stage = str(item.get("step") or "Execution stage")
        if decision == "hold":
            status = "blocked"
            trigger = "Close filing blockers before execution planning."
        elif has_critical_deadline:
            status = "attention"
            trigger = "Critical deadline alert present; sequence may shift."
        else:
            status = "planned"
            trigger = "Proceed when judgment/writ prerequisites are met."
        steps.append(
            {
                "stage": stage,
                "status": status,
                "trigger": trigger,
            }
        )
    if not steps:
        steps.append(
            {
                "stage": "Execution plan pending",
                "status": "blocked",
                "trigger": "Generate enforcement plan after filing stage.",
            }
        )
    return steps


def build_document_version_control_card(
    *,
    generated_documents: list[dict[str, Any]],
    filing_packet_order: list[dict[str, Any]],
) -> dict[str, Any]:
    generated_count = len(generated_documents)
    doc_types = [str(item.get("doc_type") or "") for item in generated_documents if str(item.get("doc_type") or "")]
    unique_doc_types = len(set(doc_types))
    has_packet = len(filing_packet_order) > 0
    has_duplicates = generated_count > unique_doc_types if generated_count > 0 else False

    if generated_count == 0:
        status = "draft_only"
    elif has_duplicates:
        status = "review"
    elif has_packet:
        status = "stable"
    else:
        status = "prepare_packet"

    revision_tag = f"v{max(1, generated_count)}"
    return {
        "status": status,
        "generated_documents": generated_count,
        "unique_doc_types": unique_doc_types,
        "revision_tag": revision_tag,
        "note": "Version control card tracks draft maturity before e-court submission.",
    }


def build_e_court_packet_readiness(
    *,
    e_court_submission_preview: dict[str, Any],
    filing_attachments_register: list[dict[str, Any]],
    filing_decision_card: dict[str, Any],
) -> dict[str, Any]:
    blockers = [str(item) for item in e_court_submission_preview.get("blockers") or [] if str(item).strip()]
    missing_attachments = [
        str(item.get("name") or "Attachment")
        for item in filing_attachments_register
        if bool(item.get("required")) and not bool(item.get("available"))
    ][:12]
    decision = str(filing_decision_card.get("decision") or "hold")

    if blockers or missing_attachments:
        status = "not_ready"
    elif decision == "go":
        status = "ready"
    else:
        status = "conditional"

    recommended_submit_mode = "e-court with KEP" if status in {"ready", "conditional"} else "hold submission"
    return {
        "status": status,
        "blockers": blockers[:10],
        "missing_attachments": missing_attachments,
        "recommended_submit_mode": recommended_submit_mode,
        "note": "Readiness check is technical and processual pre-check before real court API submission.",
    }


def build_hearing_script_pack(
    *,
    legal_argument_map: list[dict[str, Any]],
    judge_questions_simulation: list[dict[str, str]],
    citation_pack: dict[str, Any],
) -> list[dict[str, str]]:
    statutory_refs = [str(item) for item in citation_pack.get("statutory_refs") or [] if str(item).strip()]
    basis_hint = statutory_refs[0] if statutory_refs else "Key statutory basis to be finalized"
    pack: list[dict[str, str]] = []

    phases = [
        "Opening",
        "Facts",
        "Legal qualification",
        "Rebuttal",
        "Closing",
    ]
    for idx, phase in enumerate(phases):
        if idx < len(legal_argument_map):
            argument = legal_argument_map[idx]
            script_hint = f"{str(argument.get('issue') or 'Issue')} -> {str(argument.get('litigation_goal') or 'Goal')}."
            linked_basis = str(argument.get("legal_basis") or basis_hint)
        elif idx < len(judge_questions_simulation):
            question = judge_questions_simulation[idx]
            script_hint = f"Pre-answer judge concern: {str(question.get('question') or '')}"
            linked_basis = basis_hint
        else:
            script_hint = "Keep concise and aligned with filed prayer part."
            linked_basis = basis_hint
        pack.append(
            {
                "phase": phase,
                "script_hint": script_hint,
                "linked_basis": linked_basis,
            }
        )
    return pack[:8]


def build_settlement_offer_card(
    *,
    settlement_strategy: dict[str, Any],
    claim_formula_card: dict[str, Any],
    opponent_response_playbook: list[dict[str, str]],
) -> dict[str, Any]:
    target = settlement_strategy.get("target_amount_uah")
    if target is None:
        target = claim_formula_card.get("total_claim_uah")
    target_value = float(target or 0.0)
    target_min = round(target_value * 0.85, 2) if target_value > 0 else 0.0
    target_max = round(target_value * 1.0, 2) if target_value > 0 else 0.0
    strategy_window = str(settlement_strategy.get("window") or "parallel")
    has_objection_pressure = len(opponent_response_playbook) >= 3

    status = "active" if strategy_window in {"parallel", "settlement-first"} else "optional"
    fallback_position = "Proceed to filing stage if offer rejected."
    if has_objection_pressure:
        fallback_position = "Use objection playbook and shift to litigation-first path if talks fail."

    return {
        "status": status,
        "target_min_uah": target_min,
        "target_max_uah": target_max,
        "strategy_note": f"Settlement window: {strategy_window}.",
        "fallback_position": fallback_position,
        "note": "Offer card is advisory and should be approved by responsible lawyer.",
    }


def build_appeal_reserve_card(
    *,
    recommended_doc_types: list[str],
    deadline_control: list[dict[str, Any]],
    procedural_timeline: list[dict[str, Any]],
) -> dict[str, Any]:
    appeal_in_scope = "appeal_complaint" in recommended_doc_types
    appeal_deadline = None
    for item in deadline_control:
        if str(item.get("code")) == "appeal_deadline":
            appeal_deadline = item.get("due_date")
            break
    if appeal_deadline is None:
        for item in procedural_timeline:
            title = str(item.get("title") or "").lower()
            if "appeal" in title:
                appeal_deadline = item.get("date")
                break

    trigger_conditions = [
        "Court decision partially/fully rejects core relief.",
        "Material procedural violation detected after judgment.",
        "New evidence or legal position affects outcome.",
    ]
    if appeal_in_scope:
        status = "prepare_now"
    elif appeal_deadline:
        status = "monitor"
    else:
        status = "standby"

    return {
        "status": status,
        "reserve_deadline": str(appeal_deadline) if appeal_deadline else None,
        "trigger_conditions": trigger_conditions,
        "note": "Appeal reserve card keeps appellate path prepared even during first-instance strategy.",
    }


def build_procedural_costs_allocator_card(
    *,
    claim_formula_card: dict[str, Any],
    filing_decision_card: dict[str, Any],
    settlement_offer_card: dict[str, Any],
) -> dict[str, Any]:
    principal = float(claim_formula_card.get("principal_uah") or 0.0)
    court_fee = float(claim_formula_card.get("court_fee_uah") or 0.0)
    penalty = float(claim_formula_card.get("penalty_uah") or 0.0)
    total = float(claim_formula_card.get("total_claim_uah") or 0.0)
    decision = str(filing_decision_card.get("decision") or "hold")
    settlement_active = str(settlement_offer_card.get("status") or "") == "active"

    plaintiff_costs_share = round(court_fee, 2)
    defendant_target_recovery = round(total, 2)
    status = "preliminary"
    if decision == "go" and total > 0:
        status = "litigation_ready"
    elif settlement_active:
        status = "settlement_mode"

    return {
        "status": status,
        "plaintiff_upfront_costs_uah": plaintiff_costs_share,
        "defendant_target_recovery_uah": defendant_target_recovery,
        "cost_components": {
            "principal_uah": round(principal, 2),
            "penalty_uah": round(penalty, 2),
            "court_fee_uah": round(court_fee, 2),
        },
        "note": "Costs allocation card is indicative; court has final discretion on costs distribution.",
    }


def build_document_export_readiness(
    *,
    generated_documents: list[dict[str, Any]],
    text_section_audit: list[dict[str, str]],
    version_control_card: dict[str, Any],
) -> dict[str, Any]:
    generated_count = len(generated_documents)
    warn_sections = [item for item in text_section_audit if str(item.get("status")) != "ok"]
    version_status = str(version_control_card.get("status") or "draft_only")
    has_ai_errors = any(str(item.get("ai_error") or "").strip() for item in generated_documents)

    if generated_count == 0:
        status = "not_ready"
    elif has_ai_errors or warn_sections:
        status = "review_required"
    elif version_status in {"stable", "prepare_packet"}:
        status = "ready"
    else:
        status = "draft"

    formats = ["pdf", "docx"] if generated_count > 0 else []
    blockers: list[str] = []
    if has_ai_errors:
        blockers.append("Some generated documents contain AI generation errors.")
    if warn_sections:
        blockers.append(f"Text audit warnings: {len(warn_sections)}.")
    if generated_count == 0:
        blockers.append("No generated documents available for export.")

    return {
        "status": status,
        "formats": formats,
        "blockers": blockers[:8],
        "note": "Export readiness verifies draft quality before producing final PDF/DOCX package.",
    }


def build_filing_submission_checklist_card(
    *,
    e_court_packet_readiness: dict[str, Any],
    filing_packet_order: list[dict[str, Any]],
    filing_cover_letter: dict[str, Any],
) -> list[dict[str, str]]:
    missing_items = [item for item in filing_packet_order if str(item.get("status")) == "missing"]
    e_court_status = str(e_court_packet_readiness.get("status") or "not_ready")
    cover_status = str(filing_cover_letter.get("status") or "draft")

    checklist: list[dict[str, str]] = [
        {
            "step": "Finalize filing packet composition",
            "status": "ok" if not missing_items else "warn",
            "detail": f"Missing items: {len(missing_items)}.",
        },
        {
            "step": "Verify e-court submission readiness",
            "status": "ok" if e_court_status in {"ready", "conditional"} else "warn",
            "detail": f"Current e-court packet status: {e_court_status}.",
        },
        {
            "step": "Approve filing cover letter",
            "status": "ok" if cover_status == "ready" else "warn",
            "detail": f"Cover letter status: {cover_status}.",
        },
        {
            "step": "Complete advocate final sign-off",
            "status": "ok" if e_court_status == "ready" and not missing_items else "warn",
            "detail": "Final legal responsibility remains with licensed lawyer.",
        },
    ]
    return checklist[:8]


def build_post_filing_monitoring_board(
    *,
    post_filing_plan: list[str],
    deadline_alert_board: list[dict[str, Any]],
    execution_step_tracker: list[dict[str, str]],
) -> list[dict[str, str]]:
    critical_deadlines = [item for item in deadline_alert_board if str(item.get("level")) == "critical"]
    execution_blocked = [item for item in execution_step_tracker if str(item.get("status")) == "blocked"]

    board: list[dict[str, str]] = []
    for action in post_filing_plan[:6]:
        board.append(
            {
                "track": action,
                "priority": "high" if critical_deadlines else "medium",
                "signal": "Deadline pressure detected." if critical_deadlines else "Routine monitoring.",
            }
        )
    if execution_blocked:
        board.append(
            {
                "track": "Execution preparation status",
                "priority": "high",
                "signal": f"Blocked execution steps: {len(execution_blocked)}.",
            }
        )
    if not board:
        board.append(
            {
                "track": "Post-filing board initialization",
                "priority": "medium",
                "signal": "Populate board after first court movement.",
            }
        )
    return board[:10]


def build_legal_research_backlog(
    *,
    citation_quality_gate: dict[str, Any],
    contradiction_hotspots: list[dict[str, str]],
    judge_questions_simulation: list[dict[str, str]],
) -> list[dict[str, str]]:
    issues = [str(item) for item in citation_quality_gate.get("issues") or [] if str(item).strip()]
    backlog: list[dict[str, str]] = []

    for issue in issues[:5]:
        backlog.append(
            {
                "task": issue,
                "priority": "high",
                "expected_output": "Add stronger statute/case citation support in motivation part.",
            }
        )
    for item in contradiction_hotspots[:3]:
        backlog.append(
            {
                "task": f"Resolve hotspot: {str(item.get('issue') or '')}",
                "priority": "medium",
                "expected_output": "Updated fact and law matrix without internal contradictions.",
            }
        )
    for item in judge_questions_simulation[:2]:
        backlog.append(
            {
                "task": f"Prepare answer memo: {str(item.get('question') or '')}",
                "priority": "medium",
                "expected_output": "Short rebuttal memo with evidence references.",
            }
        )
    if not backlog:
        backlog.append(
            {
                "task": "No critical research backlog items detected.",
                "priority": "low",
                "expected_output": "Maintain monitoring of fresh Supreme Court positions.",
            }
        )
    return backlog[:12]


def build_procedural_consistency_scorecard(
    *,
    validation_checks: list[dict[str, str]],
    text_section_audit: list[dict[str, str]],
    cpc_compliance_check: list[dict[str, str]],
) -> dict[str, Any]:
    validation_warn = sum(1 for item in validation_checks if str(item.get("status")) == "warn")
    text_warn = sum(1 for item in text_section_audit if str(item.get("status")) != "ok")
    cpc_warn = sum(1 for item in cpc_compliance_check if str(item.get("status")) == "warn")

    score = 100.0
    score -= min(validation_warn * 8.0, 32.0)
    score -= min(text_warn * 6.0, 24.0)
    score -= min(cpc_warn * 8.0, 32.0)
    score = round(max(0.0, min(score, 100.0)), 1)

    status = "strong" if score >= 80 else ("medium" if score >= 60 else "weak")
    return {
        "status": status,
        "score": score,
        "validation_warn_count": validation_warn,
        "text_warn_count": text_warn,
        "cpc_warn_count": cpc_warn,
        "note": "Consistency scorecard aggregates key quality gates before final submission.",
    }


def build_hearing_evidence_order_card(
    *,
    evidence_matrix: list[dict[str, Any]],
    fact_norm_evidence_chain: list[dict[str, str]],
) -> list[dict[str, Any]]:
    linked_titles = [str(item.get("evidence") or "").lower() for item in fact_norm_evidence_chain if str(item.get("evidence") or "").strip()]
    order_items: list[dict[str, Any]] = []
    order = 1
    for evidence in evidence_matrix[:12]:
        title = str(evidence.get("title") or evidence.get("code") or "Evidence item")
        status = str(evidence.get("status") or "")
        if title.lower() in linked_titles:
            priority = "high"
        elif status == "ok":
            priority = "medium"
        else:
            priority = "low"
        order_items.append(
            {
                "order": order,
                "evidence": title,
                "priority": priority,
                "status": "ready" if status == "ok" else "pending",
                "note": "Order for oral presentation at hearing stage.",
            }
        )
        order += 1
    return order_items[:12]


def build_digital_signature_readiness(
    *,
    e_court_packet_readiness: dict[str, Any],
    filing_cover_letter: dict[str, Any],
    document_export_readiness: dict[str, Any],
) -> dict[str, Any]:
    e_court_status = str(e_court_packet_readiness.get("status") or "not_ready")
    cover_status = str(filing_cover_letter.get("status") or "draft")
    export_status = str(document_export_readiness.get("status") or "not_ready")

    blockers: list[str] = []
    if e_court_status not in {"ready", "conditional"}:
        blockers.append(f"E-court packet status is {e_court_status}.")
    if cover_status != "ready":
        blockers.append("Filing cover letter is not marked ready.")
    if export_status not in {"ready", "review_required"}:
        blockers.append(f"Document export status is {export_status}.")

    status = "ready" if not blockers and e_court_status == "ready" else ("conditional" if not blockers else "not_ready")
    signer_methods = ["Дія.Підпис", "КЕП токен", "File-based key"]
    return {
        "status": status,
        "signer_methods": signer_methods,
        "blockers": blockers[:8],
        "note": "Digital signature readiness is a pre-check for external submission flow.",
    }


def build_case_law_update_watchlist(
    *,
    context_refs: list[dict[str, Any]],
    citation_pack: dict[str, Any],
) -> list[dict[str, str]]:
    watchlist: list[dict[str, str]] = []
    for ref in context_refs[:8]:
        source = str(ref.get("source") or "case-law")
        reference = str(ref.get("reference") or "reference")
        watchlist.append(
            {
                "source": source,
                "reference": reference,
                "watch_reason": "Track if newer position changes argument strength.",
            }
        )
    for ref in (citation_pack.get("case_refs") or [])[:4]:
        source = str(ref.get("source") or "case-law")
        reference = str(ref.get("reference") or "reference")
        key = f"{source}|{reference}"
        if any(f"{item.get('source')}|{item.get('reference')}" == key for item in watchlist):
            continue
        watchlist.append(
            {
                "source": source,
                "reference": reference,
                "watch_reason": "Maintain updated jurisprudence in motivation section.",
            }
        )
    if not watchlist:
        watchlist.append(
            {
                "source": "internal",
                "reference": "No linked case law yet",
                "watch_reason": "Add relevant Supreme Court references for stronger support.",
            }
        )
    return watchlist[:12]


def build_final_submission_gate(
    *,
    filing_decision_card: dict[str, Any],
    e_court_packet_readiness: dict[str, Any],
    digital_signature_readiness: dict[str, Any],
    procedural_consistency_scorecard: dict[str, Any],
    deadline_control: list[dict[str, Any]],
    recommended_doc_types: list[str],
) -> dict[str, Any]:
    decision = str(filing_decision_card.get("decision") or "hold")
    e_court_status = str(e_court_packet_readiness.get("status") or "not_ready")
    signature_status = str(digital_signature_readiness.get("status") or "not_ready")
    score = float(procedural_consistency_scorecard.get("score") or 0.0)
    recommended_set = {str(item) for item in recommended_doc_types}
    deadline_index = {
        str(item.get("code") or ""): item
        for item in deadline_control
        if str(item.get("code") or "").strip()
    }

    blockers: list[str] = []
    critical_deadlines: list[str] = []
    if decision == "hold":
        blockers.append("Filing decision card is HOLD.")
    if e_court_status == "not_ready":
        blockers.append("E-court packet is not ready.")
    if signature_status == "not_ready":
        blockers.append("Digital signature readiness failed.")
    if score < 70:
        blockers.append(f"Procedural consistency score is too low: {score}.")
    if "appellate_decision_date_missing" in deadline_index:
        blockers.append("Missing decision/service date for appellate or cassation deadline control.")
        critical_deadlines.append("appellate_decision_date_missing")

    required_deadline_codes: list[str] = []
    if "appeal_complaint" in recommended_set:
        required_deadline_codes.append("appeal_deadline")
    if "cassation_complaint" in recommended_set:
        required_deadline_codes.append("cassation_deadline")

    for code in required_deadline_codes:
        item = deadline_index.get(code)
        if item is None:
            blockers.append(f"Required deadline checkpoint is missing: {code}.")
            critical_deadlines.append(f"{code}:missing")
            continue
        status = str(item.get("status") or "ok")
        due_date = str(item.get("due_date") or "")
        if not due_date:
            blockers.append(f"Required deadline {code} has no due date.")
            critical_deadlines.append(f"{code}:no_due_date")
            continue
        if status == "overdue":
            blockers.append(f"Required deadline {code} is overdue ({due_date}).")
            critical_deadlines.append(f"{code}:overdue:{due_date}")
        elif status == "urgent":
            blockers.append(f"Required deadline {code} is urgent ({due_date}).")
            critical_deadlines.append(f"{code}:urgent:{due_date}")

    if not blockers and decision == "go" and e_court_status == "ready" and signature_status == "ready":
        status = "pass"
    elif not blockers:
        status = "conditional_pass"
    else:
        status = "blocked"

    if settings.strict_filing_mode and status != "pass":
        if not any("Strict filing mode requires PASS status" in item for item in blockers):
            blockers.append("Strict filing mode requires PASS status at final submission gate.")
        status = "blocked"
    hard_stop = status == "blocked" or bool(blockers)

    return {
        "status": status,
        "blockers": blockers[:10],
        "critical_deadlines": critical_deadlines[:10],
        "next_step": "Proceed to submission." if status == "pass" else "Resolve blockers and rerun Full Lawyer.",
        "hard_stop": hard_stop,
        "note": "Final submission gate is the last internal checkpoint before actual filing action.",
    }


def build_court_behavior_forecast_card(
    *,
    filing_risk_simulation: list[dict[str, Any]],
    judge_questions_simulation: list[dict[str, str]],
    pre_filing_red_flags: list[dict[str, str]],
) -> dict[str, Any]:
    high_risk_count = sum(1 for item in filing_risk_simulation if str(item.get("impact")) == "high")
    hard_questions = len(judge_questions_simulation)
    high_flags = sum(1 for item in pre_filing_red_flags if str(item.get("severity")) == "high")

    if high_risk_count >= 2 or high_flags >= 2:
        stance = "strict"
        confidence = 0.45
    elif hard_questions >= 4:
        stance = "inquisitive"
        confidence = 0.62
    else:
        stance = "balanced"
        confidence = 0.75

    return {
        "stance": stance,
        "confidence": round(confidence, 2),
        "high_impact_risks": high_risk_count,
        "high_severity_flags": high_flags,
        "question_load": hard_questions,
        "note": "Forecast card is heuristic and helps prepare hearing behavior scenarios.",
    }


def build_evidence_pack_compression_plan(
    *,
    hearing_evidence_order_card: list[dict[str, Any]],
    evidence_gap_actions: list[dict[str, str]],
) -> list[dict[str, str]]:
    high_priority = [item for item in hearing_evidence_order_card if str(item.get("priority")) == "high"]
    pending_items = [item for item in hearing_evidence_order_card if str(item.get("status")) != "ready"]
    gap_count = len(evidence_gap_actions)

    plan: list[dict[str, str]] = [
        {
            "step": "Create core hearing pack",
            "status": "ok" if high_priority else "warn",
            "detail": f"High-priority evidence items selected: {len(high_priority)}.",
        },
        {
            "step": "Move low-value attachments to reserve annex",
            "status": "ok" if len(hearing_evidence_order_card) >= len(high_priority) else "warn",
            "detail": "Keep oral presentation set compact, move excess to reserve annex.",
        },
        {
            "step": "Close pending evidence gaps",
            "status": "warn" if pending_items or gap_count > 0 else "ok",
            "detail": f"Pending items: {len(pending_items)}. Gap actions: {gap_count}.",
        },
    ]
    return plan[:8]


def build_filing_channel_strategy_card(
    *,
    e_court_packet_readiness: dict[str, Any],
    digital_signature_readiness: dict[str, Any],
    filing_submission_checklist_card: list[dict[str, str]],
) -> dict[str, Any]:
    e_status = str(e_court_packet_readiness.get("status") or "not_ready")
    sign_status = str(digital_signature_readiness.get("status") or "not_ready")
    checklist_warn = sum(1 for item in filing_submission_checklist_card if str(item.get("status")) != "ok")

    if e_status == "ready" and sign_status in {"ready", "conditional"} and checklist_warn == 0:
        primary_channel = "e_court"
        backup_channel = "paper_filing"
        status = "ready"
    elif e_status in {"conditional", "ready"}:
        primary_channel = "hybrid"
        backup_channel = "paper_filing"
        status = "conditional"
    else:
        primary_channel = "paper_filing"
        backup_channel = "e_court_after_fixes"
        status = "fallback"

    return {
        "status": status,
        "primary_channel": primary_channel,
        "backup_channel": backup_channel,
        "checklist_warn_count": checklist_warn,
        "note": "Channel strategy balances technical readiness and procedural reliability.",
    }


def build_legal_budget_timeline_card(
    *,
    claim_formula_card: dict[str, Any],
    settlement_offer_card: dict[str, Any],
    deadline_control: list[dict[str, Any]],
) -> dict[str, Any]:
    total_claim = float(claim_formula_card.get("total_claim_uah") or 0.0)
    plaintiff_upfront = float(claim_formula_card.get("court_fee_uah") or 0.0)
    settlement_min = float(settlement_offer_card.get("target_min_uah") or 0.0)
    urgent_deadlines = sum(1 for item in deadline_control if str(item.get("status")) in {"urgent", "overdue"})

    reserve_recommended = round(max(plaintiff_upfront * 1.5, total_claim * 0.03), 2) if total_claim > 0 else round(plaintiff_upfront * 1.5, 2)
    timeline_mode = "accelerated" if urgent_deadlines > 0 else "standard"
    return {
        "timeline_mode": timeline_mode,
        "estimated_upfront_uah": round(plaintiff_upfront, 2),
        "recommended_reserve_uah": reserve_recommended,
        "settlement_floor_uah": round(settlement_min, 2),
        "urgent_deadlines": urgent_deadlines,
        "note": "Budget timeline card is planning-only and should be validated with client strategy.",
    }


def build_counterparty_pressure_map(
    *,
    opponent_objections: list[dict[str, str]],
    opponent_response_playbook: list[dict[str, str]],
) -> list[dict[str, str]]:
    playbook_keys = {str(item.get("scenario") or "").lower() for item in opponent_response_playbook}
    pressure_map: list[dict[str, str]] = []
    for item in opponent_objections[:10]:
        objection = str(item.get("objection") or "Potential objection")
        likelihood = str(item.get("likelihood") or "medium")
        covered = objection.lower() in playbook_keys
        pressure = "high" if likelihood == "high" else ("medium" if likelihood == "medium" else "low")
        pressure_map.append(
            {
                "vector": objection,
                "pressure": pressure,
                "coverage": "covered" if covered else "gap",
                "action": "Strengthen rebuttal memo and evidence links." if not covered else "Keep rebuttal updated for hearing.",
            }
        )
    if not pressure_map:
        pressure_map.append(
            {
                "vector": "No active counterparty pressure vectors detected.",
                "pressure": "low",
                "coverage": "covered",
                "action": "Continue monitoring opponent filings and court reactions.",
            }
        )
    return pressure_map


def build_courtroom_timeline_scenarios(
    *,
    procedural_timeline: list[dict[str, Any]],
    deadline_alert_board: list[dict[str, Any]],
) -> list[dict[str, str]]:
    critical_count = sum(1 for item in deadline_alert_board if str(item.get("level")) == "critical")
    warning_count = sum(1 for item in deadline_alert_board if str(item.get("level")) == "warning")
    has_appeal_step = any("appeal" in str(item.get("title") or "").lower() for item in procedural_timeline)

    scenarios: list[dict[str, str]] = [
        {
            "scenario": "Base litigation path",
            "probability": "high" if critical_count == 0 else "medium",
            "focus": "Keep filing and hearing milestones within current calendar.",
        },
        {
            "scenario": "Compressed deadline path",
            "probability": "high" if critical_count > 0 or warning_count >= 2 else "medium",
            "focus": "Prioritize urgent procedural steps and freeze non-critical actions.",
        },
    ]
    if has_appeal_step:
        scenarios.append(
            {
                "scenario": "Appeal branch",
                "probability": "medium",
                "focus": "Prepare appellate package in parallel with first-instance activity.",
            }
        )
    return scenarios[:8]


def build_evidence_authenticity_checklist(
    *,
    evidence_matrix: list[dict[str, Any]],
    evidence_admissibility_map: list[dict[str, str]],
) -> list[dict[str, str]]:
    admissibility_by_evidence = {
        str(item.get("evidence") or "").lower(): str(item.get("admissibility") or "")
        for item in evidence_admissibility_map
    }
    checklist: list[dict[str, str]] = []
    for item in evidence_matrix[:12]:
        title = str(item.get("title") or item.get("code") or "Evidence item")
        status = str(item.get("status") or "")
        admissibility = admissibility_by_evidence.get(title.lower(), "unknown")
        if status == "ok" and admissibility in {"high", "medium"}:
            check_status = "ok"
            action = "Keep original/certified copy and include source metadata."
        else:
            check_status = "warn"
            action = "Verify origin, integrity, and certification before filing."
        checklist.append(
            {
                "evidence": title,
                "status": check_status,
                "action": action,
            }
        )
    return checklist


def build_remedy_priority_matrix(
    *,
    remedy_coverage: list[dict[str, Any]],
    prayer_part_audit: dict[str, Any],
) -> list[dict[str, str]]:
    score = float(prayer_part_audit.get("score") or 0.0)
    matrix: list[dict[str, str]] = []
    for item in remedy_coverage[:10]:
        remedy = str(item.get("remedy") or "Remedy")
        covered = bool(item.get("covered"))
        if covered and score >= 80:
            priority = "high"
            rationale = "Core remedy is already covered and should remain first in prayer part."
        elif covered:
            priority = "medium"
            rationale = "Covered remedy exists but prayer structure still needs tightening."
        else:
            priority = "high"
            rationale = "Uncovered remedy should be explicitly added or intentionally removed."
        matrix.append(
            {
                "remedy": remedy,
                "priority": priority,
                "rationale": rationale,
            }
        )
    if not matrix:
        matrix.append(
            {
                "remedy": "No remedies detected",
                "priority": "high",
                "rationale": "Define at least one concrete requested relief before filing.",
            }
        )
    return matrix


def build_judge_question_drill_card(
    *,
    judge_questions_simulation: list[dict[str, str]],
    contradiction_hotspots: list[dict[str, str]],
) -> dict[str, Any]:
    question_count = len(judge_questions_simulation)
    hotspot_count = len(contradiction_hotspots)
    rounds = max(1, min(5, question_count + (1 if hotspot_count > 0 else 0)))
    complexity = "high" if question_count >= 4 or hotspot_count >= 2 else ("medium" if question_count >= 2 else "low")
    return {
        "complexity": complexity,
        "rounds": rounds,
        "question_count": question_count,
        "hotspot_count": hotspot_count,
        "note": "Drill card defines how intense oral prep should be before hearing.",
    }


def build_client_instruction_packet(
    *,
    filing_decision_card: dict[str, Any],
    legal_budget_timeline_card: dict[str, Any],
    next_actions: list[str],
) -> list[dict[str, str]]:
    decision = str(filing_decision_card.get("decision") or "hold")
    timeline_mode = str(legal_budget_timeline_card.get("timeline_mode") or "standard")
    packet: list[dict[str, str]] = [
        {
            "instruction": "Confirm filing mandate and risk tolerance.",
            "priority": "high",
            "note": f"Current decision mode: {decision}.",
        },
        {
            "instruction": "Approve litigation budget and reserve.",
            "priority": "high",
            "note": f"Timeline mode: {timeline_mode}.",
        },
    ]
    for action in next_actions[:3]:
        packet.append(
            {
                "instruction": action,
                "priority": "medium",
                "note": "Operational step from automated next-actions queue.",
            }
        )
    return packet[:8]


def build_procedural_risk_heatmap(
    *,
    filing_risk_simulation: list[dict[str, Any]],
    procedural_defect_scan: list[dict[str, str]],
    pre_filing_red_flags: list[dict[str, str]],
) -> list[dict[str, str]]:
    heatmap: list[dict[str, str]] = []
    for item in filing_risk_simulation[:6]:
        impact = str(item.get("impact") or "medium")
        probability = float(item.get("probability") or 0.0)
        if impact == "high" and probability >= 0.5:
            level = "critical"
        elif impact == "high" or probability >= 0.35:
            level = "high"
        elif probability >= 0.2:
            level = "medium"
        else:
            level = "low"
        heatmap.append(
            {
                "risk": str(item.get("risk") or "Risk"),
                "level": level,
                "source": "filing_risk_simulation",
            }
        )
    for item in procedural_defect_scan[:4]:
        severity = str(item.get("severity") or "low")
        if severity in {"high", "critical"}:
            level = "high"
        elif severity == "medium":
            level = "medium"
        else:
            level = "low"
        heatmap.append(
            {
                "risk": str(item.get("issue") or "Procedural defect"),
                "level": level,
                "source": "procedural_defect_scan",
            }
        )
    for item in pre_filing_red_flags[:4]:
        severity = str(item.get("severity") or "low")
        level = "critical" if severity == "high" else ("high" if severity == "medium" else "low")
        heatmap.append(
            {
                "risk": str(item.get("flag") or "Pre-filing flag"),
                "level": level,
                "source": "pre_filing_red_flags",
            }
        )
    return heatmap[:14]


def build_evidence_disclosure_plan(
    *,
    evidence_authenticity_checklist: list[dict[str, str]],
    hearing_evidence_order_card: list[dict[str, Any]],
) -> list[dict[str, str]]:
    by_evidence_order = {str(item.get("evidence") or ""): item for item in hearing_evidence_order_card}
    plan: list[dict[str, str]] = []
    for item in evidence_authenticity_checklist[:12]:
        evidence = str(item.get("evidence") or "Evidence")
        status = str(item.get("status") or "warn")
        order_item = by_evidence_order.get(evidence)
        phase = "hearing_core" if order_item and str(order_item.get("priority")) == "high" else "annex_bundle"
        disclosure_status = "ready" if status == "ok" else "pending"
        plan.append(
            {
                "evidence": evidence,
                "phase": phase,
                "status": disclosure_status,
                "note": "Disclose in structured order with provenance and relevance references.",
            }
        )
    return plan


def build_settlement_negotiation_script(
    *,
    settlement_offer_card: dict[str, Any],
    counterparty_pressure_map: list[dict[str, str]],
    remedy_priority_matrix: list[dict[str, str]],
) -> list[dict[str, str]]:
    min_amount = float(settlement_offer_card.get("target_min_uah") or 0.0)
    max_amount = float(settlement_offer_card.get("target_max_uah") or 0.0)
    pressure_high = sum(1 for item in counterparty_pressure_map if str(item.get("pressure")) in {"high", "critical"})
    top_remedy = str((remedy_priority_matrix[0].get("remedy") if remedy_priority_matrix else "Core remedy"))

    script: list[dict[str, str]] = [
        {
            "stage": "Opening position",
            "line": f"Our structured claim range is {min_amount:.2f}-{max_amount:.2f} UAH with documented legal basis.",
            "goal": "Anchor negotiation around litigable numbers.",
        },
        {
            "stage": "Value justification",
            "line": f"Primary protected remedy is '{top_remedy}', supported by evidence and statutory references.",
            "goal": "Prevent drift away from core relief.",
        },
        {
            "stage": "Pressure handling",
            "line": "If objections persist, we activate full filing package and hearing strategy.",
            "goal": "Signal readiness to litigate if settlement stalls.",
        },
    ]
    if pressure_high > 0:
        script.append(
            {
                "stage": "Escalation fallback",
                "line": "Given current objection pressure, we require fast-track settlement response window.",
                "goal": "Reduce delay risk and preserve filing leverage.",
            }
        )
    return script[:8]


def build_hearing_readiness_scorecard(
    *,
    hearing_script_pack: list[dict[str, str]],
    hearing_evidence_order_card: list[dict[str, Any]],
    judge_question_drill_card: dict[str, Any],
) -> dict[str, Any]:
    script_count = len(hearing_script_pack)
    evidence_ready = sum(1 for item in hearing_evidence_order_card if str(item.get("status")) == "ready")
    evidence_total = len(hearing_evidence_order_card)
    drill_rounds = int(judge_question_drill_card.get("rounds") or 0)
    complexity = str(judge_question_drill_card.get("complexity") or "low")

    score = 100.0
    if script_count < 3:
        score -= 20.0
    if evidence_total > 0:
        score -= max(0.0, (1 - (evidence_ready / evidence_total)) * 35.0)
    if drill_rounds < 2:
        score -= 15.0
    if complexity == "high":
        score -= 10.0
    score = round(max(0.0, min(score, 100.0)), 1)
    status = "ready" if score >= 80 else ("partial" if score >= 60 else "not_ready")
    return {
        "status": status,
        "score": score,
        "script_count": script_count,
        "evidence_ready": evidence_ready,
        "evidence_total": evidence_total,
        "drill_rounds": drill_rounds,
        "note": "Hearing readiness scorecard is a practical prep KPI, not legal advice.",
    }


def build_advocate_signoff_packet(
    *,
    final_submission_gate: dict[str, Any],
    filing_decision_card: dict[str, Any],
    procedural_consistency_scorecard: dict[str, Any],
    document_export_readiness: dict[str, Any],
) -> dict[str, Any]:
    gate_status = str(final_submission_gate.get("status") or "blocked")
    decision = str(filing_decision_card.get("decision") or "hold")
    consistency_score = float(procedural_consistency_scorecard.get("score") or 0.0)
    export_status = str(document_export_readiness.get("status") or "not_ready")

    required_checks = [
        {"check": "Final submission gate", "status": gate_status},
        {"check": "Filing decision", "status": decision},
        {"check": "Procedural consistency score", "status": f"{consistency_score}"},
        {"check": "Document export readiness", "status": export_status},
    ]

    if gate_status == "pass" and decision in {"go", "conditional_go"} and consistency_score >= 75 and export_status in {"ready", "review_required"}:
        status = "ready_for_signoff"
    elif gate_status == "blocked":
        status = "blocked"
    else:
        status = "review_needed"

    return {
        "status": status,
        "required_checks": required_checks,
        "note": "Packet summarizes minimum controls before advocate sign-off decision.",
    }


def build_workflow_stages(
    *,
    procedural_conclusions: list[str],
    context_refs_count: int,
    validation_checks: list[dict[str, str]],
    unresolved_questions: list[str],
    unresolved_review_items: list[str],
    generated_documents_count: int,
    filing_package_generated: bool,
) -> tuple[list[dict[str, Any]], bool]:
    warn_count = sum(1 for item in validation_checks if str(item.get("status")) == "warn")
    pass_count = sum(1 for item in validation_checks if str(item.get("status")) == "pass")
    has_analysis = bool(procedural_conclusions)
    has_context = context_refs_count > 0
    has_unresolved = bool(unresolved_questions)
    has_docs = generated_documents_count > 0
    has_unresolved_review = bool(unresolved_review_items)

    stage_1_status = "ok" if has_analysis else "warn"
    stage_2_status = "ok" if has_context else "warn"
    stage_3_status = "ok" if warn_count == 0 else "warn"
    stage_4_status = "blocked" if (has_unresolved or has_unresolved_review) else ("ok" if has_docs else "warn")

    stages: list[dict[str, Any]] = [
        {
            "code": "block_1_ai_analysis",
            "title": "Block 1 â€” AI Analysis & Drafting",
            "status": stage_1_status,
            "details": [
                "LLM analyzed uploaded text and produced procedural conclusions.",
                f"Conclusions generated: {len(procedural_conclusions)}.",
            ],
            "metrics": {"procedural_conclusions": len(procedural_conclusions)},
        },
        {
            "code": "block_2_case_law_rag",
            "title": "Block 2 â€” Case Law Retrieval (RAG)",
            "status": stage_2_status,
            "details": [
                "Relevant case-law and legal references were selected for drafting context.",
                f"Context references attached: {context_refs_count}.",
            ],
            "metrics": {"context_refs_count": context_refs_count},
        },
        {
            "code": "block_3_rule_validation",
            "title": "Block 3 â€” Rule Validation",
            "status": stage_3_status,
            "details": [
                "Automated checks for amount, parties, limitation period, and procedure route.",
                f"Checks passed: {pass_count}, warnings: {warn_count}.",
            ],
            "metrics": {"checks_passed": pass_count, "checks_warn": warn_count},
        },
        {
            "code": "block_4_human_review_gate",
            "title": "Block 4 â€” Human Review & Approval",
            "status": stage_4_status,
            "details": [
                "Unresolved clarifications block final procedural package generation.",
                f"Unresolved questions: {len(unresolved_questions)}.",
                f"Unresolved review checklist items: {len(unresolved_review_items)}.",
                f"Generated documents: {generated_documents_count}.",
            ],
            "metrics": {
                "unresolved_questions": len(unresolved_questions),
                "unresolved_review_items": len(unresolved_review_items),
                "generated_documents": generated_documents_count,
                "filing_package_generated": bool(filing_package_generated),
            },
        },
    ]

    ready_for_filing = bool(has_docs and not has_unresolved and not has_unresolved_review and warn_count == 0)
    return stages, ready_for_filing


DECISION_ISSUE_RULES: tuple[dict[str, Any], ...] = (
    {
        "topic": "Whether a prior judgment terminates the monetary obligation",
        "keywords": ("court decision", "judgment", "\u0440\u0456\u0448\u0435\u043d\u043d\u044f \u0441\u0443\u0434\u0443"),
        "court_position": (
            "Existing court practice usually treats the monetary obligation as ongoing until actual enforcement."
        ),
        "legal_basis": ["Civil Code of Ukraine: art. 599, art. 625"],
        "practical_effect": "Creditor may claim additional monetary liability for delay until factual execution.",
    },
    {
        "topic": "Application of Civil Code article 625 (3% annual + inflation losses)",
        "keywords": ("625", "3%", "inflation", "\u0442\u0440\u0438 \u0432\u0456\u0434\u0441\u043e\u0442\u043a\u0438"),
        "court_position": (
            "Courts generally apply article 625 as a special monetary liability mechanism for delay."
        ),
        "legal_basis": ["Civil Code of Ukraine: art. 625"],
        "practical_effect": "Delay period and cut-off dates become the primary battleground.",
    },
    {
        "topic": "Surety continuity and preclusive terms",
        "keywords": ("surety", "guarantor", "\u043f\u043e\u0440\u0443\u043a", "\u043f\u043e\u0440\u0443\u0447\u0438\u0442\u0435\u043b"),
        "court_position": (
            "Courts assess whether surety termination conditions occurred and whether timely demand existed."
        ),
        "legal_basis": ["Civil Code of Ukraine: arts. 553-559"],
        "practical_effect": "If surety remains valid, liability can be joint and several with the principal debtor.",
    },
    {
        "topic": "War-time liability carve-outs",
        "keywords": ("\u0432\u043e\u0454\u043d", "martial", "transition provisions"),
        "court_position": (
            "Courts tend to split liability periods before and after the legal war-time threshold date."
        ),
        "legal_basis": ["Civil Code of Ukraine: Transitional Provisions, p. 18"],
        "practical_effect": "Precise periodization directly affects recoverable amount.",
    },
    {
        "topic": "Limitation period strategy",
        "keywords": ("limitation", "\u043f\u043e\u0437\u043e\u0432\u043d", "time-bar", "statute of limitations"),
        "court_position": "Courts examine whether the debtor raised limitation objections and their scope.",
        "legal_basis": ["Civil Code of Ukraine: arts. 256-267"],
        "practical_effect": "Part of the claimed period may be excluded if limitation is upheld.",
    },
    {
        "topic": "Procedural format: simplified vs general proceedings",
        "keywords": ("simplified", "written procedure", "\u0441\u043f\u0440\u043e\u0449\u0435\u043d", "\u0431\u0435\u0437 \u0432\u0438\u043a\u043b\u0438\u043a\u0443"),
        "court_position": (
            "Courts generally keep simplified written review for standard claims with limited price and complexity."
        ),
        "legal_basis": ["Civil Procedure Code of Ukraine: art. 369 and related procedural norms"],
        "practical_effect": "Arguments on hearing format succeed only with specific complexity/proof justifications.",
    },
)


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(str(keyword).lower() in text for keyword in keywords)


def _extract_article_references(source_text: str, *, max_items: int = 10) -> list[str]:
    safe_limit = max(1, min(max_items, 30))
    refs: list[str] = []
    seen: set[str] = set()
    for raw in re.findall(r"(?:\u0441\u0442\.?\s*\d{1,4}(?:[\-\u2013]\d{1,4})?)", source_text or "", flags=re.IGNORECASE):
        cleaned = re.sub(r"\s+", " ", str(raw)).strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        refs.append(cleaned)
        if len(refs) >= safe_limit:
            break
    return refs


def _extract_case_number(source_text: str) -> str | None:
    match = re.search(r"(?:\u2116\s*[0-9A-Za-z\u0410-\u042f\u0430-\u044f\-\/]+)", source_text or "")
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(0)).strip()


def build_decision_key_issues(
    source_text: str,
    *,
    max_items: int = 6,
) -> list[dict[str, Any]]:
    safe_limit = max(1, min(max_items, 10))
    text = _normalized(source_text)
    article_refs = _extract_article_references(source_text, max_items=8)
    issues: list[dict[str, Any]] = []

    for rule in DECISION_ISSUE_RULES:
        keywords = tuple(str(item).lower() for item in (rule.get("keywords") or ()))
        if not _contains_any(text, keywords):
            continue
        legal_basis = [str(item).strip() for item in (rule.get("legal_basis") or []) if str(item).strip()]
        if article_refs:
            legal_basis = [*legal_basis, *article_refs[:2]]
        issues.append(
            {
                "topic": str(rule.get("topic") or "Core legal issue"),
                "court_position": str(rule.get("court_position") or "Court position requires document-specific verification."),
                "legal_basis": legal_basis[:6],
                "practical_effect": str(rule.get("practical_effect") or ""),
            }
        )
        if len(issues) >= safe_limit:
            break

    if issues:
        return issues

    fallback_basis = article_refs[:4] if article_refs else ["Норми ЦК/ЦПК та інших актів, що прямо згадані в тексті."]
    return [
        {
            "topic": "Ключова правова кваліфікація спору",
            "court_position": (
                "Ймовірна позиція суду залежить від повноти доказів, хронології та нормативного обґрунтування."
            ),
            "legal_basis": fallback_basis,
            "practical_effect": "Результат найбільш чутливий до фактів, строків та розподілу тягаря доказування.",
        }
    ]


def build_decision_key_questions(
    *,
    key_issues: list[dict[str, Any]],
    max_items: int = 8,
) -> list[str]:
    safe_limit = max(1, min(max_items, 15))
    questions: list[str] = []
    for item in key_issues:
        topic = str(item.get("topic") or "").strip()
        if not topic:
            continue
        questions.append(f"Чи правильно суд вирішив питання: {topic.lower()}?")
        if len(questions) >= safe_limit:
            break
    if not questions:
        questions.append("Чи повно суд дослідив істотні обставини та правові аргументи сторін?")
    return questions[:safe_limit]


def build_decision_cassation_vulnerabilities(
    source_text: str,
    *,
    key_issues: list[dict[str, Any]],
    recent_practice_count: int,
    max_items: int = 6,
) -> list[str]:
    safe_limit = max(1, min(max_items, 12))
    text = _normalized(source_text)
    vulnerabilities: list[str] = []

    if "limitation" not in text and "\u043f\u043e\u0437\u043e\u0432\u043d" not in text:
        vulnerabilities.append(
            "Лінія позовної давності може бути недостатньо опрацьована; перевірте, чи було заявлено та оцінено відповідний заперечний аргумент."
        )
    if recent_practice_count == 0:
        vulnerabilities.append(
            "Не додано посилань на актуальну судову практику; касаційна аргументація може виглядати відірваною від поточної позиції судів."
        )
    if not any("procedural" in str(item.get("topic") or "").lower() for item in key_issues):
        vulnerabilities.append(
            "Процесуальний вектор оскарження виглядає слабко; додайте конкретні процесуальні порушення, якщо вони підтверджуються матеріалами справи."
        )
    if _extract_case_number(source_text) is None:
        vulnerabilities.append("У джерелі неповні реквізити справи; перевірте ідентифікатори та процесуальну хронологію.")

    if not vulnerabilities:
        vulnerabilities.append(
            "За текстом не виявлено очевидної високої касаційної вразливості."
        )
    return vulnerabilities[:safe_limit]


def build_decision_stage_recommendations(
    *,
    cassation_vulnerabilities: list[str],
) -> list[dict[str, Any]]:
    top_risk = cassation_vulnerabilities[0] if cassation_vulnerabilities else "Ризик неповноти матеріалів справи."
    return [
        {
            "stage": "Досудова підготовка",
            "actions": [
                "Сформуйте повну хронологію фактів із датами та посиланнями на первинні документи.",
                "До подання побудуйте карту правових норм і матрицю розподілу тягаря доказування.",
            ],
            "risks": [top_risk],
        },
        {
            "stage": "Перша інстанція",
            "actions": [
                "Забезпечте допустимість ключових доказів і відповідність процесуальним вимогам.",
                "Узгодьте правову кваліфікацію спору та прохальну частину в єдиній логіці.",
            ],
            "risks": ["Неповна карта доказів може звузити обсяг задоволення вимог."],
        },
        {
            "stage": "Апеляція",
            "actions": [
                "Фокусуйтеся на конкретних правових і процесуальних помилках першої інстанції.",
                "Додайте релевантну актуальну практику, що збігається за фактажем і нормою права.",
            ],
            "risks": ["Загальна незгода без карти помилок зазвичай не спрацьовує."],
        },
        {
            "stage": "Касація",
            "actions": [
                "Будуйте аргументи навколо єдності практики та неправильного застосування норм матеріального/процесуального права.",
                "Залишайте лише найсильніші правові пункти, уникайте переоцінки фактичних обставин.",
            ],
            "risks": ["Касаційна перспектива низька, якщо аргументи переважно фактичні."],
        },
        {
            "stage": "Виконання",
            "actions": [
                "Паралельно підготуйте пакет для виконання та стратегію пошуку активів боржника.",
                "Контролюйте строки та процесуальні події після набрання рішенням законної сили.",
            ],
            "risks": ["Затримка запуску виконання знижує ефективність стягнення."],
        },
    ]


def _parse_iso_date(raw_value: Any) -> date | None:
    raw_text = str(raw_value or "").strip()
    if not raw_text:
        return None
    try:
        return date.fromisoformat(raw_text[:10])
    except ValueError:
        return None


def _detect_instance_level(court_name: str | None, court_type: str | None) -> str:
    normalized_name = str(court_name or "").strip().lower()
    normalized_type = str(court_type or "").strip().lower()
    haystack = f"{normalized_name} {normalized_type}".strip()
    if not haystack:
        return "unknown"
    if any(token in haystack for token in ("supreme", "\u0432\u0435\u0440\u0445\u043e\u0432", "cassation", "\u043a\u0430\u0441\u0430\u0446")):
        return "supreme"
    if any(token in haystack for token in ("appeal", "\u0430\u043f\u0435\u043b\u044f\u0446")):
        return "appeal"
    if any(token in haystack for token in ("district", "local", "first", "\u0440\u0430\u0439\u043e\u043d", "\u043c\u0456\u0441\u0446\u0435\u0432", "\u043e\u043a\u0440\u0443\u0436")):
        return "first_instance"
    return "unknown"


def build_decision_stage_packets(
    *,
    key_issues: list[dict[str, Any]],
    cassation_vulnerabilities: list[str],
) -> list[dict[str, Any]]:
    core_issue = str((key_issues[0].get("topic") if key_issues else "") or "базове правове питання").strip()
    top_risk = str((cassation_vulnerabilities[0] if cassation_vulnerabilities else "") or "ризик неповноти матеріалів").strip()
    return [
        {
            "stage": "Досудова підготовка",
            "objective": "Сформувати повну рамку «факти-право-докази» до подання.",
            "key_documents": [
                "Мемо структури вимог",
                "Таблиця хронології фактів",
                "Інвентар доказів із посиланнями на джерела",
            ],
            "checklist": [
                f"Перевірте правову рамку для питання: {core_issue}.",
                "Підтвердьте хронологію позовної давності та події її переривання.",
                "Звірте прохальну частину з наявними доказами.",
            ],
            "exit_criteria": [
                "Немає критичних фактичних прогалин.",
                "Карта норм і карта доказів зв'язані пункт-до-пункту.",
            ],
        },
        {
            "stage": "Перша інстанція",
            "objective": "Забезпечити допустимість доказів і процесуальну чистоту вимог.",
            "key_documents": [
                "Пакет позовної заяви/заперечень",
                "Реєстр додатків (карта ст. 177 ЦПК)",
                "Пакет процесуальних клопотань (за потреби)",
            ],
            "checklist": [
                "До подання перевірте відповідність реквізитів і додатків.",
                "Підготуйте карту аргументів щодо кожного спірного питання.",
                "Заздалегідь підготуйте відповіді на очікувані заперечення.",
            ],
            "exit_criteria": [
                "Ключові докази допущені або заперечення щодо допустимості нейтралізовані.",
                "Прохальна частина узгоджена з формулою вимог і правовою базою.",
            ],
        },
        {
            "stage": "Апеляція",
            "objective": "Перетворити незгоду на конкретну карту правових/процесуальних помилок.",
            "key_documents": [
                "Матриця апеляційних помилок",
                "Додаток з релевантною актуальною практикою",
                "Нотатка щодо коригування прохальної частини",
            ],
            "checklist": [
                "Відокремте незгоду з фактами від претензій щодо правових помилок.",
                "Прив'яжіть кожен апеляційний аргумент до матеріалів справи.",
                "Залиште 3-5 найвпливовіших помилок.",
            ],
            "exit_criteria": [
                "Кожен апеляційний довід містить норму права і фрагмент матеріалів.",
                "Відсутні загальні аргументи без процесуальної/правової прив'язки.",
            ],
        },
        {
            "stage": "Касація",
            "objective": "Сфокусуватися на єдності практики та неправильному застосуванні норм права.",
            "key_documents": [
                "Бриф допуску до касації",
                "Порівняльна таблиця єдності практики",
                "Стисла формула правового питання",
            ],
            "checklist": [
                "Виключіть пункти, що зводяться лише до переоцінки фактів.",
                f"Протестуйте ключову вразливість: {top_risk}.",
                "Прив'яжіть кожен касаційний пункт до конкретного неправильного застосування норми.",
            ],
            "exit_criteria": [
                "Касаційний пакет вузький за фокусом і сильний за правовим впливом.",
                "Колізія практики або помилка застосування норми показані чітко.",
            ],
        },
        {
            "stage": "Виконання",
            "objective": "Скоротити час до фактичного стягнення після набрання рішенням законної сили.",
            "key_documents": [
                "Пакет відкриття виконавчого провадження",
                "Запити на розшук активів",
                "Трекер контролю виконання рішення",
            ],
            "checklist": [
                "Готуйте пакет виконання паралельно з фінальною стадією спору.",
                "Впорядкуйте запити на пошук активів і контроль строків.",
                "Моніторте дії виконавця та оперативно оскаржуйте бездіяльність.",
            ],
            "exit_criteria": [
                "Виконання ініційовано без зайвих затримок.",
                "Запущено цикл пошуку активів і регулярного контролю.",
            ],
        },
    ]


def build_decision_side_assessment(
    source_text: str,
    *,
    key_issues: list[dict[str, Any]],
) -> dict[str, Any]:
    text = _normalized(source_text)
    scores: dict[str, int] = {"plaintiff": 0, "defendant": 0, "guarantor": 0}
    rationale: list[str] = []

    plaintiff_tokens = (
        "plaintiff",
        "\u043f\u043e\u0437\u0438\u0432\u0430\u0447",
        "\u043a\u0440\u0435\u0434\u0438\u0442\u043e\u0440",
        "\u0441\u0442\u044f\u0433\u043d\u0435\u043d",
        "recover",
    )
    defendant_tokens = (
        "defendant",
        "\u0432\u0456\u0434\u043f\u043e\u0432\u0456\u0434\u0430\u0447",
        "\u0431\u043e\u0440\u0436\u043d\u0438\u043a",
        "\u0432\u0456\u0434\u0437\u0438\u0432",
        "\u0437\u0430\u043f\u0435\u0440\u0435\u0447",
        "objection",
    )
    guarantor_tokens = (
        "guarantor",
        "surety",
        "\u043f\u043e\u0440\u0443\u0447\u0438\u0442\u0435\u043b",
        "\u043f\u043e\u0440\u0443\u043a",
    )

    if any(token in text for token in plaintiff_tokens):
        scores["plaintiff"] += 4
        rationale.append("Виявлено мовні маркери позиції позивача/кредитора.")
    if any(token in text for token in defendant_tokens):
        scores["defendant"] += 4
        rationale.append("Виявлено мовні маркери позиції відповідача/боржника.")
    if any(token in text for token in guarantor_tokens):
        scores["guarantor"] += 5
        rationale.append("Виявлено маркери поручителя/гаранта.")

    if "appeal" in text or "\u0430\u043f\u0435\u043b\u044f\u0446" in text:
        scores["defendant"] += 1
        rationale.append("Апеляційна стадія часто вказує на захисну стратегію.")
    if any("surety" in str(item.get("topic") or "").lower() or "\u043f\u043e\u0440\u0443\u043a" in str(item.get("topic") or "").lower() for item in key_issues):
        scores["guarantor"] += 2
        rationale.append("Ключові питання містять вимір поруки/гарантії.")

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_side, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0
    if top_score < 2:
        return {
            "side": "unknown",
            "opposing_side": "unknown",
            "confidence": 0.35,
            "rationale": ["У джерелі недостатньо маркерів для надійного визначення сторони."],
        }

    confidence = round(max(0.35, min(0.95, 0.55 + (top_score - second_score) * 0.08 + top_score * 0.03)), 2)
    opposing_side = "defendant" if top_side == "plaintiff" else "plaintiff"
    if top_side == "guarantor":
        opposing_side = "creditor_or_debtor"
    return {
        "side": top_side,
        "opposing_side": opposing_side,
        "confidence": confidence,
        "rationale": rationale[:6] or ["Сторону визначено за процесуальними мовними ознаками."],
    }


def build_decision_evidence_gaps(
    source_text: str,
    *,
    side: str,
) -> list[dict[str, Any]]:
    text = _normalized(source_text)
    has_dates = bool(_extract_dates(source_text))
    has_contract = any(token in text for token in ("contract", "\u0434\u043e\u0433\u043e\u0432", "\u0443\u0433\u043e\u0434"))
    has_payment = any(token in text for token in ("payment", "\u043f\u043b\u0430\u0442\u0456\u0436", "\u043a\u0432\u0438\u0442\u0430\u043d", "\u0431\u0430\u043d\u043a\u0456\u0432"))
    has_court_act = any(token in text for token in ("judgment", "decision", "\u0440\u0456\u0448\u0435\u043d", "\u043f\u043e\u0441\u0442\u0430\u043d\u043e\u0432", "\u0443\u0445\u0432\u0430\u043b"))
    has_enforcement = any(token in text for token in ("enforcement", "\u0432\u0438\u043a\u043e\u043d\u0430\u0432", "\u0432\u0438\u043a\u043e\u043d\u0430\u043d\u043d"))
    has_notice = any(token in text for token in ("notice", "\u043f\u043e\u0432\u0456\u0434\u043e\u043c", "\u043b\u0438\u0441\u0442", "\u0432\u0438\u043c\u043e\u0433"))

    def _item(code: str, title: str, ok: bool, missing_hint: str, action: str) -> dict[str, Any]:
        return {
            "code": code,
            "title": title,
            "status": "ok" if ok else "missing",
            "detail": "Ознаку виявлено в джерелі." if ok else missing_hint,
            "recommended_actions": [] if ok else [action],
        }

    gaps: list[dict[str, Any]] = [
        _item(
            "timeline_core_dates",
            "Ключові дати хронології",
            has_dates,
            "Матеріальні дати для позовної давності/процесуальних вікон не визначені явно.",
            "Складіть хронологію подій із точними датами та посиланнями на документи.",
        ),
        _item(
            "contract_or_obligation_source",
            "Джерело договору/зобов'язання",
            has_contract,
            "Не знайдено явних маркерів договору або підстави зобов'язання.",
            "Додайте договір/позику/інший базовий документ і позначте релевантні пункти.",
        ),
        _item(
            "payment_and_amount_trail",
            "Ланцюг платежів і суми вимог",
            has_payment,
            "Не виявлено чітких доказових маркерів платежів/суми.",
            "Додайте платіжні доручення, виписки банку, акти звірки.",
        ),
        _item(
            "court_act_and_reasoning",
            "Судовий акт і база мотивувальної частини",
            has_court_act,
            "У джерелі відсутні явні посилання на рішення/ухвали.",
            "Додайте оскаржувані судові акти та витяги з мотивувальної частини.",
        ),
        _item(
            "enforcement_or_notice_trace",
            "Трасування виконання/повідомлень",
            has_enforcement or has_notice,
            "Не знайдено чіткого ланцюга виконання/повідомлень.",
            "Додайте матеріали виконавчого провадження та листування щодо досудових вимог.",
        ),
    ]

    if side == "defendant":
        gaps.append(
            _item(
                "defense_objection_evidence",
                "Докази заперечень сторони захисту",
                any(token in text for token in ("\u0437\u0430\u043f\u0435\u0440\u0435\u0447", "objection", "\u043d\u0435 \u043f\u043e\u0433\u043e\u0434\u0436")),
                "Не виявлено явної лінії доказування заперечень.",
                "Підготуйте матрицю заперечень: пункт вимоги -> контраргумент -> доказ.",
            )
        )
    return gaps[:8]


def build_decision_defense_plan(
    *,
    side_assessment: dict[str, Any],
    key_issues: list[dict[str, Any]],
    cassation_vulnerabilities: list[str],
) -> list[dict[str, Any]]:
    side = str(side_assessment.get("side") or "unknown")
    primary_issue = str((key_issues[0].get("topic") if key_issues else "") or "ключове питання спору").strip()
    top_vulnerability = str((cassation_vulnerabilities[0] if cassation_vulnerabilities else "") or "ризик якості матеріалів").strip()

    if side == "plaintiff":
        primary_goal = "Забезпечити стягуваність вимог і зберегти правову базу для повного задоволення."
    elif side == "defendant":
        primary_goal = "Обмежити обсяг відповідальності та атакувати слабкі правові/процесуальні місця."
    elif side == "guarantor":
        primary_goal = "Звузити ризик поручителя та відмежувати межі його відповідальності."
    else:
        primary_goal = "Стабілізувати позицію сторони перед вибором наступного процесуального маршруту."

    return [
        {
            "code": "defense_01_positioning",
            "stage": "Позиціювання",
            "goal": primary_goal,
            "actions": [
                f"Зафіксуйте рамку ключового питання: {primary_issue}.",
                "Побудуйте матрицю «вимога-відповідь» з правовими опорами по кожному пункту.",
            ],
            "target_documents": ["position_memo", "claim_response_matrix"],
        },
        {
            "code": "defense_02_evidence",
            "stage": "Контроль доказів",
            "goal": "Закрити суттєві доказові прогалини до подання/розгляду.",
            "actions": [
                "Прив'яжіть кожне фактичне твердження щонайменше до одного допустимого доказу.",
                "Підготуйте пакет клопотань про витребування доказів у третіх осіб (за потреби).",
            ],
            "target_documents": ["evidence_matrix", "motion_evidence_request"],
        },
        {
            "code": "defense_03_procedural",
            "stage": "Процесуальний захист",
            "goal": "Уникнути процесуальної відмови та зберегти можливості оскарження.",
            "actions": [
                "Перевірте повноту процесуальних реквізитів і додатків.",
                "Заздалегідь підготуйте відповіді на очікувані процесуальні заперечення.",
            ],
            "target_documents": ["cpc_requisites_check", "procedural_objection_brief"],
        },
        {
            "code": "defense_04_appeal",
            "stage": "Резерв апеляції",
            "goal": "Тримати готову карту помилок для апеляційного оскарження.",
            "actions": [
                "Фіксуйте та архівуйте правові/процесуальні помилки першої інстанції під час розгляду.",
                "Підтримуйте компактний перелік апеляційних доводів для швидкого подання.",
            ],
            "target_documents": ["appeal_error_map", "appeal_reserve_card"],
        },
        {
            "code": "defense_05_cassation",
            "stage": "Контур касації",
            "goal": "Фокус лише на найсильніших аргументах щодо єдності застосування права.",
            "actions": [
                f"Протестуйте ключову вразливість: {top_vulnerability}.",
                "Виключіть із касаційної чернетки пункти, що зводяться до переоцінки фактів.",
            ],
            "target_documents": ["cassation_threshold_brief", "uniformity_argument_table"],
        },
    ]


def build_decision_document_preparation(
    *,
    source_text: str,
    side_assessment: dict[str, Any],
    evidence_gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    def _parse_flexible_date(raw_value: str) -> date | None:
        raw = str(raw_value or "").strip()
        if not raw:
            return None
        for parser in ("%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, parser).date()
            except ValueError:
                continue
        return None

    def _extract_decision_date_for_appeal(text_value: str) -> date | None:
        text = str(text_value or "")
        patterns = (
            r"(?:дата\s+ухвалення|дата\s+постановлення|рішення\s+від|ухвала\s+від|постанова\s+від)\s*[:\-]?\s*(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})",
            r"(?:ухвалено|постановлено)\s*[:\-]?\s*(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})",
        )
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            parsed = _parse_flexible_date(match.group(1))
            if parsed is not None:
                return parsed

        header = text[:1800]
        for raw in re.findall(r"\b(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})\b", header):
            parsed = _parse_flexible_date(raw)
            if parsed is not None:
                return parsed

        extracted = _extract_dates(text)
        if extracted:
            return max(extracted)
        return None

    def _detect_decision_stage_for_package(text_value: str) -> str:
        text = _normalized(text_value)
        header = _normalized(str(text_value or "")[:2400])

        if any(marker in header for marker in ("верховний суд", "касаційний", "суд касаційної інстанції")):
            return "cassation"
        if (
            "апеляційний суд" in header
            or "суд апеляційної інстанції" in header
            or "розглянув апеляційну скаргу" in text
        ):
            return "appeal"
        if any(marker in text for marker in ("виконавче провадження", "державний виконавець", "приватний виконавець")):
            return "enforcement"
        if any(marker in header for marker in ("районний суд", "міський суд", "міськрайонний суд", "місцевий суд")):
            return "first_instance"
        if "апеляційна скарга може бути подана" in text or "суд першої інстанції" in text:
            return "first_instance"
        return "unknown"

    side = str(side_assessment.get("side") or "unknown")
    missing_count = sum(1 for item in evidence_gaps if str(item.get("status")) == "missing")
    has_heavy_gaps = missing_count >= 3
    stage_signal = _detect_decision_stage_for_package(source_text)
    decision_date = _extract_decision_date_for_appeal(source_text) if stage_signal == "first_instance" else None
    appeal_deadline_due = (
        calculate_deadline(decision_date, settings.appeal_deadline_days)
        if decision_date is not None
        else None
    )
    appeal_deadline_overdue = bool(appeal_deadline_due and appeal_deadline_due < date.today())

    if stage_signal == "first_instance":
        template = [
            (
                "appeal_complaint",
                "Апеляційна скарга",
                "Оскарження рішення суду першої інстанції за процесуальними та матеріально-правовими помилками",
                "high",
            ),
        ]
        if appeal_deadline_overdue:
            template.append(
                (
                    "motion_appeal_deadline_renewal",
                    "Заява про поновлення строку апеляційного оскарження",
                    "Поновлення процесуального строку перед поданням апеляційної скарги",
                    "high",
                )
            )
    elif stage_signal == "appeal":
        template = [
            (
                "cassation_complaint",
                "Касаційна скарга (підготовка)",
                "Ескалаційний пакет після апеляційної інстанції за наявності правових підстав",
                "high",
            ),
            (
                "objection_response",
                "Письмові заперечення/пояснення",
                "Посилення позиції в апеляційній інстанції та нейтралізація доводів опонента",
                "medium",
            ),
        ]
    elif stage_signal == "cassation":
        template = [
            (
                "cassation_complaint",
                "Касаційна скарга",
                "Вузький касаційний контур за питаннями правильного застосування норм права",
                "high",
            ),
        ]
    elif stage_signal == "enforcement":
        template = [
            (
                "statement_enforcement_opening",
                "Заява про відкриття виконавчого провадження",
                "Запуск примусового виконання рішення",
                "high",
            ),
            (
                "statement_enforcement_asset_search",
                "Заява про розшук майна боржника",
                "Підвищення ефективності стягнення через пошук активів боржника",
                "high",
            ),
            (
                "complaint_executor_actions",
                "Скарга на дії/бездіяльність виконавця",
                "Резервний процесуальний інструмент у разі бездіяльності виконавця",
                "medium",
            ),
        ]
    elif side == "defendant":
        template = [
            ("objection_response", "Заперечення на відзив", "Базовий документ захисту проти доводів позивача", "high"),
            ("motion_evidence_request", "Клопотання про витребування доказів", "Отримання документів від третіх осіб на підтримку захисту", "high"),
            ("appeal_complaint", "Апеляційна скарга (резерв)", "Резервний маршрут у разі несприятливого рішення першої інстанції", "medium"),
            ("cassation_complaint", "Касаційна скарга (резерв)", "Вузький ескалаційний проєкт за правовими питаннями", "low"),
        ]
    elif side == "plaintiff":
        template = [
            ("lawsuit_debt_loan", "Позовна заява", "Основний документ для стягнення заборгованості", "high"),
            ("motion_claim_security", "Заява про забезпечення позову", "Захистити майбутнє виконання рішення під час розгляду", "medium"),
            ("objection_response", "Заперечення на відзив відповідача", "Нейтралізувати заперечення сторони захисту", "high"),
            ("appeal_complaint", "Апеляційна скарга (резерв)", "Маршрут ескалації в разі несприятливого рішення першої інстанції", "medium"),
        ]
    else:
        template = [
            ("objection_response", "Пакет заперечень/пояснень", "Базовий пакет до моменту підтвердження процесуальної ролі сторони", "high"),
            ("motion_evidence_request", "Клопотання про витребування доказів", "Зібрати відсутню документальну базу", "high"),
            ("appeal_complaint", "Апеляційна скарга (резерв)", "Резервний пакет для ескалації", "medium"),
        ]

    items: list[dict[str, Any]] = []
    stage_critical_docs = {
        "appeal_complaint",
        "motion_appeal_deadline_renewal",
        "cassation_complaint",
        "statement_enforcement_opening",
        "statement_enforcement_asset_search",
    }
    for doc_type, title, purpose, priority in template:
        if stage_signal != "unknown" and doc_type in stage_critical_docs:
            readiness = "ready"
            blockers = []
        elif has_heavy_gaps and priority == "high":
            readiness = "blocked"
            blockers = [f"Не закрито доказові прогалини: {missing_count}."]
        elif has_heavy_gaps:
            readiness = "warn"
            blockers = [f"Не закрито доказові прогалини: {missing_count}."]
        else:
            readiness = "ready"
            blockers = []
        items.append(
            {
                "doc_type": doc_type,
                "title": title,
                "purpose": purpose,
                "priority": priority,
                "readiness": readiness,
                "blockers": blockers,
                "stage_signal": stage_signal,
                "appeal_deadline_due": appeal_deadline_due.isoformat() if appeal_deadline_due else None,
                "appeal_deadline_overdue": appeal_deadline_overdue,
            }
        )
    return items[:8]


def build_decision_practice_coverage(
    *,
    recent_practice: list[dict[str, Any]],
    stale_threshold_days: int = 365,
) -> dict[str, Any]:
    safe_threshold = max(30, min(int(stale_threshold_days or 365), 3650))
    court_types: dict[str, int] = {}
    instance_levels: dict[str, int] = {
        "supreme": 0,
        "appeal": 0,
        "first_instance": 0,
        "unknown": 0,
    }
    court_names: set[str] = set()
    decision_dates: list[date] = []

    for item in recent_practice:
        if not isinstance(item, dict):
            continue
        court_name = str(item.get("court_name") or "").strip()
        court_type = str(item.get("court_type") or "").strip().lower()
        if court_name:
            court_names.add(court_name.lower())
        if court_type:
            court_types[court_type] = int(court_types.get(court_type) or 0) + 1

        level = _detect_instance_level(court_name, court_type)
        instance_levels[level] = int(instance_levels.get(level) or 0) + 1

        parsed = _parse_iso_date(item.get("decision_date"))
        if parsed is not None:
            decision_dates.append(parsed)

    latest = max(decision_dates) if decision_dates else None
    oldest = min(decision_dates) if decision_dates else None
    freshness_days = (date.today() - latest).days if latest else None
    stale = freshness_days is None or freshness_days > safe_threshold
    return {
        "total_items": len(recent_practice),
        "distinct_courts": len(court_names),
        "court_types": court_types,
        "instance_levels": instance_levels,
        "latest_decision_date": latest.isoformat() if latest else None,
        "oldest_decision_date": oldest.isoformat() if oldest else None,
        "freshness_days": freshness_days,
        "stale": stale,
    }


def build_decision_dispute_summary(
    source_text: str,
    *,
    brief: dict[str, Any],
    financial_snapshot: dict[str, Any],
) -> str:
    dispute_type = str(brief.get("dispute_type") or "Правовий спір").strip()
    amount = financial_snapshot.get("principal_uah")
    case_number = _extract_case_number(source_text)
    parts = [f"Профіль спору: {dispute_type}."]
    if case_number:
        parts.append(f"Виявлено номер справи: {case_number}.")
    if amount is not None:
        parts.append(f"Виявлено грошову базу вимог: {amount:.2f} грн.")
    return " ".join(parts)


def build_decision_procedural_context(source_text: str, *, brief: dict[str, Any]) -> str:
    text = _normalized(source_text)
    procedure = str(brief.get("procedure") or "civil").strip() or "civil"
    stage = "перша_інстанція"
    if "cassation" in text or "\u043a\u0430\u0441\u0430\u0446" in text:
        stage = "касація"
    elif "appeal" in text or "\u0430\u043f\u0435\u043b\u044f\u0446" in text:
        stage = "апеляція"
    elif "enforcement" in text or "\u0432\u0438\u043a\u043e\u043d\u0430\u0432" in text:
        stage = "виконання"

    written_review = (
        "виявлено ознаки письмового/спрощеного розгляду"
        if ("simplified" in text or "\u0441\u043f\u0440\u043e\u0449\u0435\u043d" in text or "\u0431\u0435\u0437 \u0432\u0438\u043a\u043b\u0438\u043a\u0443" in text)
        else "явних ознак спрощеного формату не виявлено"
    )
    return f"Процедура: {procedure}. Поточний процесуальний сигнал: {stage}. Сигнал формату: {written_review}."


def build_decision_final_conclusion(
    *,
    cassation_vulnerabilities: list[str],
    recent_practice_count: int,
) -> str:
    vulnerability_count = len(cassation_vulnerabilities)
    if vulnerability_count == 0:
        return "Попередній висновок: позиція у справі виглядає стабільною; рекомендовано адресний контроль якості перед поданням."
    if vulnerability_count <= 2 and recent_practice_count >= 3:
        return "Попередній висновок: касаційна перспектива обмежена, якщо не виділено конкретну правову помилку."
    if vulnerability_count <= 3:
        return "Попередній висновок: касаційна перспектива помірна і залежить від точності правового формулювання."
    return "Попередній висновок: касаційна перспектива суттєва; потрібні таргетована карта помилок і аудит доказів."


def _quality_status(score: float) -> str:
    if score >= 80:
        return "pass"
    if score >= 60:
        return "warn"
    return "fail"


def _clamp_score(score: float) -> float:
    return round(max(0.0, min(score, 100.0)), 1)


def build_decision_quality_blocks(
    source_text: str,
    *,
    key_issues: list[dict[str, Any]],
    key_questions: list[str],
    cassation_vulnerabilities: list[str],
    recent_practice: list[dict[str, Any]],
    stage_recommendations: list[dict[str, Any]],
    stage_packets: list[dict[str, Any]],
    practice_coverage: dict[str, Any],
) -> list[dict[str, Any]]:
    source_len = len((source_text or "").strip())
    article_refs = _extract_article_references(source_text, max_items=20)
    case_number = _extract_case_number(source_text)

    source_integrity_score = 40.0
    if source_len >= 500:
        source_integrity_score += 20.0
    if source_len >= 2000:
        source_integrity_score += 15.0
    if case_number:
        source_integrity_score += 10.0
    source_integrity_score += min(len(article_refs) * 3.0, 15.0)
    source_integrity_score = _clamp_score(source_integrity_score)

    basis_total = sum(len(item.get("legal_basis") or []) for item in key_issues)
    issue_count = len(key_issues)
    normative_score = 35.0 + min(basis_total * 6.0, 45.0) + min(issue_count * 4.0, 20.0)
    normative_score = _clamp_score(normative_score)

    fresh_recent_count = 0
    for item in recent_practice:
        parsed = _parse_iso_date(item.get("decision_date") if isinstance(item, dict) else None)
        if parsed is not None and (date.today() - parsed).days <= 180:
            fresh_recent_count += 1

    instance_levels = practice_coverage.get("instance_levels") if isinstance(practice_coverage, dict) else {}
    represented_instances = 0
    if isinstance(instance_levels, dict):
        represented_instances = sum(1 for count in instance_levels.values() if int(count or 0) > 0)
    distinct_courts = int(practice_coverage.get("distinct_courts") or 0) if isinstance(practice_coverage, dict) else 0
    latest_decision_date = (
        str(practice_coverage.get("latest_decision_date") or "")
        if isinstance(practice_coverage, dict)
        else ""
    )
    freshness_days = practice_coverage.get("freshness_days") if isinstance(practice_coverage, dict) else None
    stale_practice = bool(practice_coverage.get("stale")) if isinstance(practice_coverage, dict) else True

    case_law_score = (
        20.0
        + min(len(recent_practice) * 5.0, 30.0)
        + min(fresh_recent_count * 4.0, 20.0)
        + min(represented_instances * 10.0, 30.0)
        + min(distinct_courts * 1.5, 20.0)
    )
    if stale_practice:
        case_law_score = min(case_law_score, 55.0)
    case_law_score = _clamp_score(case_law_score)

    cassation_score = 30.0 + min(len(key_questions) * 4.0, 30.0) + min(len(cassation_vulnerabilities) * 6.0, 30.0)
    if len(cassation_vulnerabilities) == 1 and "no obvious high-probability" in str(cassation_vulnerabilities[0]).lower():
        cassation_score = min(cassation_score, 55.0)
    cassation_score = _clamp_score(cassation_score)

    stage_count = len(stage_recommendations)
    stage_packet_count = len(stage_packets)
    packet_doc_count = sum(len(item.get("key_documents") or []) for item in stage_packets)
    action_count = sum(len(item.get("actions") or []) for item in stage_recommendations)
    risk_count = sum(len(item.get("risks") or []) for item in stage_recommendations)
    actionability_score = (
        30.0
        + min(stage_count * 6.0, 30.0)
        + min(stage_packet_count * 8.0, 30.0)
        + min(action_count * 1.5, 15.0)
        + min(packet_doc_count * 1.2, 15.0)
        + min(risk_count * 0.8, 8.0)
    )
    actionability_score = _clamp_score(actionability_score)

    return [
        {
            "code": "block_1_source_integrity",
            "title": "Блок 1: Цілісність джерела",
            "status": _quality_status(source_integrity_score),
            "score": source_integrity_score,
            "summary": "Перевірка повноти джерела: обсяг, реквізити справи, маркери правових норм.",
            "details": [
                f"Виділено символів: {source_len}.",
                f"Знайдено посилань на статті: {len(article_refs)}.",
                f"Номер справи виявлено: {'так' if case_number else 'ні'}.",
            ],
        },
        {
            "code": "block_2_normative_grounding",
            "title": "Блок 2: Нормативне підґрунтя",
            "status": _quality_status(normative_score),
            "score": normative_score,
            "summary": "Оцінка, наскільки ключові питання підкріплені нормами права.",
            "details": [
                f"Ключових питань: {issue_count}.",
                f"Загальна кількість правових посилань: {basis_total}.",
            ],
        },
        {
            "code": "block_3_recent_case_law",
            "title": "Блок 3: Покриття актуальною практикою",
            "status": _quality_status(case_law_score),
            "score": case_law_score,
            "summary": "Оцінка ширини та актуальності пов'язаної судової практики.",
            "details": [
                f"Додано рішень практики: {len(recent_practice)}.",
                f"Актуальних рішень (<=180 днів): {fresh_recent_count}.",
                f"Покрито рівнів інстанцій: {represented_instances}.",
                f"У вибірці різних судів: {distinct_courts}.",
                f"Дата найновішого рішення: {latest_decision_date or 'n/a'}.",
                f"Давність практики (днів): {freshness_days if freshness_days is not None else 'n/a'}.",
                f"Ознака застарілості практики: {'так' if stale_practice else 'ні'}.",
            ],
        },
        {
            "code": "block_4_cassation_signal",
            "title": "Блок 4: Якість касаційного сигналу",
            "status": _quality_status(cassation_score),
            "score": cassation_score,
            "summary": "Оцінка чіткості касаційних питань і карти вразливостей.",
            "details": [
                f"Ключових правових питань: {len(key_questions)}.",
                f"Касаційних вразливостей: {len(cassation_vulnerabilities)}.",
            ],
        },
        {
            "code": "block_5_actionability",
            "title": "Блок 5: Операційна готовність за стадіями",
            "status": _quality_status(actionability_score),
            "score": actionability_score,
            "summary": "Оцінка готовності покрокового плану дій для процесуального маршруту.",
            "details": [
                f"Покрито стадій: {stage_count}.",
                f"Детальних пакетів стадій: {stage_packet_count}.",
                f"Запропонованих дій: {action_count}.",
                f"Ключових документів у пакетах: {packet_doc_count}.",
                f"Картованих ризиків: {risk_count}.",
            ],
        },
    ]


def build_decision_traceability(
    *,
    key_issues: list[dict[str, Any]],
    recent_practice: list[dict[str, Any]],
    max_items: int = 20,
) -> list[dict[str, Any]]:
    safe_limit = max(1, min(max_items, 50))
    traces: list[dict[str, Any]] = []
    practice_size = len(recent_practice)

    for index, issue in enumerate(key_issues):
        claim = str(issue.get("topic") or "Legal issue").strip()
        basis_items = [str(item).strip() for item in (issue.get("legal_basis") or []) if str(item).strip()]
        if basis_items:
            traces.append(
                {
                    "claim": claim,
                    "support_type": "law",
                    "reference": basis_items[0],
                    "confidence": 0.82,
                }
            )
        if practice_size > 0:
            practice = recent_practice[index % practice_size]
            case_ref = str(practice.get("case_number") or practice.get("decision_id") or "").strip()
            source = str(practice.get("source") or "").strip()
            if case_ref:
                traces.append(
                    {
                        "claim": claim,
                        "support_type": "case_law",
                        "reference": f"{source}:{case_ref}" if source else case_ref,
                        "confidence": 0.74,
                    }
                )
        if len(traces) >= safe_limit:
            break

    return traces[:safe_limit]


def estimate_decision_overall_confidence(
    *,
    quality_blocks: list[dict[str, Any]],
    traceability: list[dict[str, Any]],
) -> float:
    if not quality_blocks:
        return 0.0
    score_avg = sum(float(item.get("score") or 0.0) for item in quality_blocks) / max(len(quality_blocks), 1)
    trace_bonus = min(len(traceability) * 0.6, 8.0)
    return round(max(0.0, min(score_avg + trace_bonus, 100.0)), 1)


def build_decision_quality_gate(
    *,
    quality_blocks: list[dict[str, Any]],
    overall_confidence_score: float,
    traceability_count: int,
    practice_coverage: dict[str, Any] | None = None,
    require_multi_instance: bool = False,
    enforce_practice_freshness: bool = False,
) -> dict[str, Any]:
    status_by_code = {str(item.get("code") or ""): str(item.get("status") or "") for item in quality_blocks}
    fail_codes = [str(item.get("code") or "") for item in quality_blocks if str(item.get("status") or "") == "fail"]
    coverage = practice_coverage if isinstance(practice_coverage, dict) else {}
    coverage_total = int(coverage.get("total_items") or 0)
    coverage_instance_levels = coverage.get("instance_levels") if isinstance(coverage.get("instance_levels"), dict) else {}
    represented_instances = sum(1 for count in coverage_instance_levels.values() if int(count or 0) > 0)
    coverage_stale = bool(coverage.get("stale"))
    latest_decision_date = str(coverage.get("latest_decision_date") or "").strip() or None
    freshness_days = coverage.get("freshness_days")
    blockers: list[str] = []

    if status_by_code.get("block_1_source_integrity") == "fail":
        blockers.append("Недостатня цілісність джерела для надійних правових висновків.")
    if status_by_code.get("block_2_normative_grounding") == "fail":
        blockers.append("Недостатнє нормативне підґрунтя; потрібно розширити правову базу.")
    if status_by_code.get("block_3_recent_case_law") == "fail":
        blockers.append("Недостатнє покриття актуальною практикою для рівня подання до суду.")
    if overall_confidence_score < 60:
        blockers.append("Загальний бал довіри нижчий за мінімальний поріг (60).")
    if traceability_count < 2:
        blockers.append("Карта трасованості занадто слабка для обґрунтування рівня подання.")
    if enforce_practice_freshness and coverage_total > 0 and coverage_stale:
        blockers.append(
            "Набір актуальної практики застарілий"
            f" (остання дата: {latest_decision_date or 'n/a'}, давність у днях: {freshness_days if freshness_days is not None else 'n/a'})."
        )
    if require_multi_instance and coverage_total > 0 and represented_instances < 2:
        blockers.append("Для цього режиму практика має покривати щонайменше два рівні судових інстанцій.")

    recommendations: list[str] = []
    if fail_codes:
        recommendations.append("Усуньте провалені блоки якості перед використанням результату для подання.")
    if overall_confidence_score < 75:
        recommendations.append("Проведіть додаткову правову ревізію та оновіть контекст актуальної практики.")
    if traceability_count < 5:
        recommendations.append("Підвищте трасованість ключових правових тверджень до джерел.")
    if coverage_total == 0:
        recommendations.append("Наповніть кеш актуальної практики перед використанням для стратегічних рішень щодо подання.")
    if coverage_total > 0 and represented_instances < 3:
        recommendations.append("За можливості розширте вибірку практики до щонайменше трьох рівнів інстанцій.")
    if enforce_practice_freshness and coverage_total > 0 and coverage_stale:
        recommendations.append("Оновіть набір практики та повторіть аналіз, щоб зменшити ризик неактуальності.")
    if not recommendations:
        recommendations.append("Гейт якості пройдено. Підтримуйте періодичні перевірки актуальності перед поданням.")

    can_proceed = len(blockers) == 0
    gate_status = "pass" if can_proceed else "blocked"
    return {
        "status": gate_status,
        "can_proceed_to_filing": can_proceed,
        "blockers": blockers,
        "recommendations": recommendations,
    }


async def generate_ai_dissent(source_text: str) -> str:
    """Analyze a lawsuit and generate a draft of an objection/dissent."""
    from app.services.ai_generator import generate_legal_document
    prompt = f"""Я ЮРИДИЧНИЙ AI-АСИСТЕНТ. Проаналізуй позов та напиши проект Заперечення (Відзиву).
    Виділи слабкі місця в аргументації, підбери контр-аргументи та норми права.
    
    ТЕКСТ ПОЗОВУ:
    {source_text}
    """
    ai_result = await generate_legal_document("Ти досвідчений український адвокат-процесуаліст.", prompt)
    return ai_result.text or "Не вдалося згенерувати відзив."