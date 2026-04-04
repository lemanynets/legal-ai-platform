from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.prompt_builder import (
    build_generation_validation_checks,
    build_preview_text,
    normalize_prayer_section,
    build_processual_validation_checks,
    build_user_prompt,
    build_pre_generation_gate_checks,
    ensure_processual_quality,
)
from app.services.ai_generator import AIResult


def test_fallback_debt_lawsuit_preview_is_full_text() -> None:
    text = build_preview_text(
        "Позов: стягнення боргу (договір позики, розписка)",
        {
            "court_name": "Ужгородський міськрайонний суд Закарпатської області",
            "plaintiff_name": "Іван Іванов",
            "plaintiff_tax_id": "1234567890",
            "plaintiff_address": "м. Ужгород, вул. Прикладна, 1",
            "defendant_name": "Петро Петров",
            "defendant_tax_id": "0987654321",
            "defendant_address": "м. Ужгород, вул. Прикладна, 2",
            "debt_basis": "loan",
            "debt_start_date": "2025-01-01",
            "principal_debt_uah": 100000,
            "accrued_interest_uah": 1500,
            "penalty_uah": 800,
            "court_fee_uah": 3028,
            "total_claim_uah": 105328,
            "fact_summary": "Відповідач отримав кошти та не повернув їх у строк.",
        },
        doc_type="lawsuit_debt_loan",
    )
    assert "ПОЗОВНА ЗАЯВА" in text
    assert "Відомості відповідно до ст. 175 ЦПК України" in text
    assert "Перелік документів, що додаються (ст. 177 ЦПК України)" in text
    assert "ПРОШУ СУД" in text
    assert len(text) > 1800


def test_fallback_appeal_preview_is_full_text() -> None:
    text = build_preview_text(
        "Апеляційна скарга",
        {
            "court_name": "Закарпатський апеляційний суд",
            "first_instance_court": "Ужгородський міськрайонний суд Закарпатської області",
            "case_number": "308/1234/25",
            "decision_date": "2026-01-15",
            "plaintiff_name": "Скаржник",
            "defendant_name": "Інша сторона",
            "fact_summary": "Суд першої інстанції неповно встановив фактичні обставини.",
            "request_summary": "Скасувати рішення та ухвалити нове рішення по суті.",
        },
        doc_type="appeal_complaint",
    )
    assert "АПЕЛЯЦІЙНА СКАРГА" in text
    assert "Підстави апеляційного оскарження" in text
    assert "ст. 352, 353, 354, 356, 357, 367 ЦПК України" in text
    assert "ПРОШУ СУД" in text
    assert len(text) > 1100


def test_fallback_sale_lawsuit_preview_is_full_text() -> None:
    text = build_preview_text(
        "Позов: стягнення боргу (договір купівлі-продажу)",
        {
            "court_name": "Ужгородський міськрайонний суд Закарпатської області",
            "plaintiff_name": "ТОВ Позивач",
            "plaintiff_tax_id": "12345678",
            "plaintiff_address": "м. Ужгород, вул. Прикладна, 10",
            "defendant_name": "ТОВ Відповідач",
            "defendant_tax_id": "87654321",
            "defendant_address": "м. Ужгород, вул. Прикладна, 20",
            "contract_date": "2025-09-01",
            "goods_description": "Партія товару згідно видаткових накладних",
            "debt_start_date": "2025-11-01",
            "debt_due_date": "2025-11-15",
            "principal_debt_uah": 250000,
            "accrued_interest_uah": 8000,
            "penalty_uah": 6500,
            "court_fee_uah": 4300,
            "total_claim_uah": 268800,
            "fact_summary": "Товар передано, але оплата в повному обсязі не проведена.",
        },
        doc_type="lawsuit_debt_sale",
    )
    assert "ПОЗОВНА ЗАЯВА" in text
    assert "Відомості відповідно до ст. 175 ЦПК України" in text
    assert "Перелік документів, що додаються (ст. 177 ЦПК України)" in text
    assert "ПРОШУ СУД" in text
    assert len(text) > 1800


def test_fallback_motion_claim_security_preview_is_full_text() -> None:
    text = build_preview_text(
        "Заява про забезпечення позову",
        {
            "court_name": "Ужгородський міськрайонний суд Закарпатської області",
            "case_number": "308/1111/26",
            "plaintiff_name": "Іван Іванов",
            "plaintiff_tax_id": "1234567890",
            "plaintiff_address": "м. Ужгород, вул. Прикладна, 1",
            "defendant_name": "Петро Петров",
            "defendant_tax_id": "0987654321",
            "defendant_address": "м. Ужгород, вул. Прикладна, 2",
            "fact_summary": "Відповідач вчиняє дії щодо відчуження майна.",
            "risk_of_non_execution_summary": "Є ризик неможливості виконання майбутнього рішення.",
            "request_summary": "Накласти арешт на майно відповідача в межах ціни позову.",
        },
        doc_type="motion_claim_security",
    )
    assert "ЗАЯВА ПРО ЗАБЕЗПЕЧЕННЯ ПОЗОВУ" in text
    assert "1. Обставини та ризик невиконання рішення" in text
    assert "2. Правове обґрунтування" in text
    assert "ст. 149, 150, 151 ЦПК України" in text
    assert "3. ПРОШУ СУД" in text
    assert "4. Додатки" in text
    assert "Підпис:" in text


def test_fallback_motion_evidence_request_preview_is_full_text() -> None:
    text = build_preview_text(
        "Клопотання про витребування доказів",
        {
            "court_name": "Ужгородський міськрайонний суд Закарпатської області",
            "case_number": "308/2222/26",
            "plaintiff_name": "Іван Іванов",
            "plaintiff_tax_id": "1234567890",
            "plaintiff_address": "м. Ужгород, вул. Прикладна, 1",
            "defendant_name": "Петро Петров",
            "defendant_tax_id": "0987654321",
            "defendant_address": "м. Ужгород, вул. Прикладна, 2",
            "fact_summary": "Для доведення обставин потрібні документи з банку.",
            "evidence_description": "Банківські виписки за період прострочення.",
            "holder_of_evidence": "АТ Банк",
            "request_summary": "Витребувати документи з банку.",
        },
        doc_type="motion_evidence_request",
    )
    assert "КЛОПОТАННЯ ПРО ВИТРЕБУВАННЯ ДОКАЗІВ" in text
    assert "1. Обставини та значення доказів" in text
    assert "2. Неможливість самостійного отримання доказів" in text
    assert "ст. 84 ЦПК України" in text
    assert "4. ПРОШУ СУД" in text
    assert "5. Додатки" in text


def test_fallback_motion_appeal_deadline_renewal_preview_is_full_text() -> None:
    text = build_preview_text(
        "Заява про поновлення строку апеляційного оскарження",
        {
            "court_name": "Закарпатський апеляційний суд",
            "first_instance_court": "Тячівський районний суд Закарпатської області",
            "case_number": "307/1542/25",
            "decision_date": "2025-01-10",
            "service_date": "2025-01-20",
            "plaintiff_name": "ОСОБА_1",
            "defendant_name": "АТ Укрсиббанк",
            "fact_summary": "Оскаржується рішення суду першої інстанції.",
            "delay_reason": "Повний текст рішення отримано із затримкою.",
            "request_summary": "Поновити строк апеляційного оскарження та прийняти апеляційну скаргу.",
        },
        doc_type="motion_appeal_deadline_renewal",
    )
    assert "ЗАЯВА ПРО ПОНОВЛЕННЯ СТРОКУ АПЕЛЯЦІЙНОГО ОСКАРЖЕННЯ" in text
    assert "1. Обставини та процесуальний контекст" in text
    assert "2. Поважність причин пропуску строку" in text
    assert "ст. 127 ЦПК України" in text
    assert "4. ПРОШУ СУД" in text
    assert "5. Додатки" in text


def test_fallback_lawsuit_alimony_preview_is_full_text() -> None:
    text = build_preview_text(
        "Позов: стягнення аліментів",
        {
            "court_name": "Ужгородський міськрайонний суд Закарпатської області",
            "plaintiff_name": "Марія Іваненко",
            "plaintiff_tax_id": "1234567890",
            "plaintiff_address": "м. Ужгород, вул. Прикладна, 1",
            "defendant_name": "Олег Іваненко",
            "defendant_tax_id": "0987654321",
            "defendant_address": "м. Ужгород, вул. Прикладна, 2",
            "fact_summary": "Відповідач добровільно не утримує дитину.",
            "request_summary": "Стягнути аліменти на утримання дитини.",
            "court_fee_uah": 1211,
            "total_claim_uah": 1211,
        },
        doc_type="lawsuit_alimony",
    )
    assert "ПОЗОВНА ЗАЯВА" in text
    assert "про стягнення аліментів" in text
    assert "ст. 175 ЦПК України" in text
    assert "5. Перелік документів, що додаються (ст. 177 ЦПК України)" in text


def test_fallback_cassation_preview_is_full_text() -> None:
    text = build_preview_text(
        "Касаційна скарга",
        {
            "court_name": "Верховний Суд",
            "first_instance_court": "Ужгородський міськрайонний суд Закарпатської області",
            "appeal_court": "Закарпатський апеляційний суд",
            "case_number": "308/1234/26",
            "decision_date": "2026-02-20",
            "plaintiff_name": "Скаржник",
            "defendant_name": "Інша сторона",
            "fact_summary": "Оскаржувані рішення прийняті з порушенням норм права.",
            "request_summary": "Скасувати судові рішення і направити справу на новий розгляд.",
        },
        doc_type="cassation_complaint",
    )
    assert "КАСАЦІЙНА СКАРГА" in text
    assert "1. Судові рішення, що оскаржуються" in text
    assert "2. Підстави касаційного оскарження" in text
    assert "ст. 389, 390, 391, 392, 400 ЦПК України" in text
    assert "5. ПРОШУ СУД" in text


def test_fallback_objection_response_preview_is_full_text() -> None:
    text = build_preview_text(
        "Заперечення на відзив",
        {
            "court_name": "Ужгородський міськрайонний суд Закарпатської області",
            "case_number": "308/3333/26",
            "plaintiff_name": "Позивач",
            "defendant_name": "Відповідач",
            "fact_summary": "Відзив містить помилкові фактичні твердження.",
            "issue_summary": "Доводи відзиву суперечать письмовим доказам у справі.",
            "request_summary": "Відхилити доводи відзиву.",
        },
        doc_type="objection_response",
    )
    assert "ЗАПЕРЕЧЕННЯ НА ВІДЗИВ" in text
    assert "1. Короткі обставини справи" in text
    assert "2. Спростування доводів відзиву" in text
    assert "4. ПРОШУ:" in text


def test_fallback_complaint_executor_actions_preview_is_full_text() -> None:
    text = build_preview_text(
        "Скарга на дії/бездіяльність виконавця",
        {
            "court_name": "Ужгородський міськрайонний суд Закарпатської області",
            "case_number": "ВП 12345",
            "plaintiff_name": "Стягувач",
            "defendant_name": "Державний виконавець",
            "fact_summary": "Виконавець не вживає заходів для примусового виконання.",
            "issue_summary": "Не винесено постанови та не вчинено передбачені законом дії.",
            "request_summary": "Визнати бездіяльність протиправною.",
        },
        doc_type="complaint_executor_actions",
    )
    assert "СКАРГА НА ДІЇ/БЕЗДІЯЛЬНІСТЬ ВИКОНАВЦЯ" in text
    assert "1. Обставини виконавчого провадження" in text
    assert "2. Порушення з боку виконавця" in text
    assert "4. ПРОШУ:" in text


def test_build_user_prompt_includes_doc_type_constraints() -> None:
    prompt = build_user_prompt("Позовна заява", {"plaintiff_name": "Іван"}, doc_type="lawsuit_debt_loan")
    assert "Тип документа: lawsuit_debt_loan" in prompt
    assert "Структура документа ОБОВ'ЯЗКОВА" in prompt
    assert "ст. 175 ЦПК України" in prompt


def test_build_user_prompt_includes_fact_focus_block_when_context_available() -> None:
    prompt = build_user_prompt(
        "Позовна заява",
        {
            "plaintiff_name": "Іван",
            "factual_points": ["01.02.2025 укладено договір позики.", "10.02.2025 передано 90000 грн."],
            "chronology_points": ["10.05.2025 настав строк повернення боргу."],
            "evidence_points": ["Банківська виписка зарахування коштів."],
            "request_points": ["Стягнути основний борг і судові витрати."],
        },
        doc_type="lawsuit_debt_loan",
    )
    assert "Додатковий фактичний фокус" in prompt
    assert "Ключові фактичні обставини" in prompt
    assert "Хронологія подій" in prompt
    assert "Ключові докази / джерела" in prompt


def test_processual_validation_checks_detect_missing_markers() -> None:
    checks = build_processual_validation_checks("lawsuit_debt_loan", "Короткий текст.")
    assert len(checks) > 0
    assert any(item["status"] == "fail" for item in checks)


def test_processual_validation_checks_pass_for_strong_text() -> None:
    strong = "\n".join(
        [
            "ПОЗОВНА ЗАЯВА",
            "1. Обставини справи",
            "2. Правове обґрунтування",
            "3. Відомості відповідно до ст. 175 ЦПК України",
            "4. ПРОШУ СУД",
            "5. Перелік документів, що додаються (ст. 177 ЦПК України)",
            "Дата: _______________",
            "Підпис: _______________",
            " ".join(["зміст"] * 220),
        ]
    )
    checks = build_processual_validation_checks("lawsuit_debt_loan", strong)
    assert checks
    assert all(item["status"] == "pass" for item in checks)


def test_pre_generation_gate_detects_blocking_failures() -> None:
    checks = build_pre_generation_gate_checks(
        "lawsuit_debt_loan",
        {
            "plaintiff_name": "A",
            "defendant_name": "B",
            "debt_start_date": "",
            "principal_debt_uah": 0,
        },
    )
    assert any(item["code"] == "debt_start_date_present" and item["status"] == "fail" for item in checks)
    assert any(item["code"] == "principal_positive" and item["status"] == "fail" for item in checks)


def test_pre_generation_gate_detects_motion_blocking_failures() -> None:
    checks = build_pre_generation_gate_checks(
        "motion_claim_security",
        {
            "plaintiff_name": "A",
            "defendant_name": "B",
            "court_name": "",
            "fact_summary": "",
            "request_summary": "",
        },
    )
    assert any(item["code"] == "motion_court_name_present" and item["status"] == "fail" for item in checks)
    assert any(item["code"] == "motion_fact_summary_present" and item["status"] == "fail" for item in checks)
    assert any(item["code"] == "motion_request_summary_present" and item["status"] == "fail" for item in checks)


def test_pre_generation_gate_detects_procedural_doc_blocking_failures() -> None:
    checks = build_pre_generation_gate_checks(
        "objection_response",
        {
            "plaintiff_name": "A",
            "defendant_name": "B",
            "court_name": "",
            "fact_summary": "",
            "request_summary": "",
        },
    )
    assert any(item["code"] == "procedural_doc_court_name_present" and item["status"] == "fail" for item in checks)
    assert any(item["code"] == "procedural_doc_fact_summary_present" and item["status"] == "fail" for item in checks)
    assert any(item["code"] == "procedural_doc_request_summary_present" and item["status"] == "fail" for item in checks)


def test_normalize_prayer_section_numbering() -> None:
    raw = (
        "ПОЗОВНА ЗАЯВА\n"
        "4. ПРОШУ СУД:\n"
        "- Стягнути борг\n"
        "- Стягнути судовий збір\n"
        "5. Перелік документів, що додаються (ст. 177 ЦПК України)\n"
        "1. Докази\n"
    )
    normalized = normalize_prayer_section("lawsuit_debt_loan", raw)
    assert "1. Стягнути борг" in normalized
    assert "2. Стягнути судовий збір" in normalized


def test_ensure_processual_quality_falls_back_when_sections_missing() -> None:
    fallback = "ПОЗОВНА ЗАЯВА\n...\nВідомості відповідно до ст. 175 ЦПК України\n...\nПерелік документів, що додаються (ст. 177 ЦПК України)\n...\nПРОШУ СУД"
    weak_ai_text = "Короткий текст без процесуальних реквізитів."
    result = ensure_processual_quality("lawsuit_debt_loan", weak_ai_text, fallback)
    assert result == fallback


def test_ensure_processual_quality_falls_back_when_placeholders_present() -> None:
    fallback = "\n".join(
        [
            "ПОЗОВНА ЗАЯВА",
            "1. Обставини справи",
            "Відповідач отримав кошти та не повернув борг.",
            "2. Правове обґрунтування",
            "3. Відомості відповідно до ст. 175 ЦПК України",
            "4. ПРОШУ СУД",
            "1. Стягнути борг.",
            "5. Перелік документів, що додаються (ст. 177 ЦПК України)",
        ]
    )
    ai_text = "\n".join(
        [
            "ПОЗОВНА ЗАЯВА",
            "1. Обставини справи",
            "[потрібно уточнити обставини]",
            "2. Правове обґрунтування",
            "3. Відомості відповідно до ст. 175 ЦПК України",
            "4. ПРОШУ СУД",
            "1. [потрібно уточнити прохальну частину]",
            "5. Перелік документів, що додаються (ст. 177 ЦПК України)",
        ]
    )
    result = ensure_processual_quality("lawsuit_debt_loan", ai_text, fallback)
    assert result == fallback


def test_ensure_processual_quality_accepts_strong_text() -> None:
    strong = "\n".join(
        [
            "ПОЗОВНА ЗАЯВА",
            "1. Обставини справи",
            "2. Правове обґрунтування",
            "3. Відомості відповідно до ст. 175 ЦПК України",
            "4. ПРОШУ СУД",
            "1. Стягнути з Відповідача основний борг.",
            "2. Стягнути судовий збір.",
            "5. Перелік документів, що додаються (ст. 177 ЦПК України)",
            "Дата: _______________",
            "Підпис: _______________",
            " ".join(["процесуальний"] * 220),
        ]
    )
    fallback = "fallback"
    result = ensure_processual_quality("lawsuit_debt_loan", strong, fallback)
    assert result == strong


def test_processual_validation_checks_require_ukrainian_language_profile() -> None:
    english_heavy = "\n".join(
        [
            "ПОЗОВНА ЗАЯВА",
            "1. Обставини справи",
            "2. Правове обґрунтування",
            "3. Відомості відповідно до ст. 175 ЦПК України",
            "4. ПРОШУ СУД",
            "5. Перелік документів, що додаються (ст. 177 ЦПК України)",
            "Дата: _______________",
            "Підпис: _______________",
            " ".join(["evidence"] * 260),
        ]
    )
    checks = build_processual_validation_checks("lawsuit_debt_loan", english_heavy)
    assert any(item["code"] == "uk_language_presence" and item["status"] == "fail" for item in checks)


def test_processual_validation_checks_fail_when_placeholder_marker_present() -> None:
    text = "\n".join(
        [
            "ПОЗОВНА ЗАЯВА",
            "1. Обставини справи",
            "2. Правове обґрунтування",
            "3. Відомості відповідно до ст. 175 ЦПК України",
            "4. ПРОШУ СУД",
            "1. [потрібно уточнити прохальну частину]",
            "5. Перелік документів, що додаються (ст. 177 ЦПК України)",
            "Дата: _______________",
            "Підпис: _______________",
            " ".join(["процесуальний"] * 220),
        ]
    )
    checks = build_processual_validation_checks("lawsuit_debt_loan", text)
    assert any(item["code"] == "placeholder_markers_absent" and item["status"] == "fail" for item in checks)


def test_build_preview_text_neutralizes_placeholder_markers() -> None:
    text = build_preview_text(
        "Клопотання про витребування доказів",
        {
            "court_name": "[потрібно уточнити суд]",
            "case_number": "[потрібно уточнити номер справи]",
            "plaintiff_name": "Іван Іванов",
            "defendant_name": "Петро Петров",
            "fact_summary": "[потрібно уточнити фактичні обставини]",
            "evidence_description": "[потрібно уточнити перелік доказів, що витребуються]",
            "holder_of_evidence": "[потрібно уточнити, у кого знаходяться докази]",
            "request_summary": "[потрібно уточнити прохальну частину]",
        },
        doc_type="motion_evidence_request",
    )
    assert "[потрібно уточнити" not in text.lower()
    assert "дані уточнюються" in text.lower()


def test_lawsuit_preview_contains_key_facts_subsection() -> None:
    text = build_preview_text(
        "Позов: стягнення боргу (договір позики, розписка)",
        {
            "court_name": "Ужгородський міськрайонний суд Закарпатської області",
            "plaintiff_name": "Іван Іванов",
            "defendant_name": "Петро Петров",
            "debt_basis": "loan",
            "debt_start_date": "2025-01-01",
            "principal_debt_uah": 100000,
            "court_fee_uah": 3028,
            "total_claim_uah": 103028,
            "fact_summary": "Відповідач отримав кошти та не повернув їх у строк.",
            "factual_points": [
                "01.01.2025 укладено договір позики.",
                "03.01.2025 позивач передав 100000 грн.",
            ],
        },
        doc_type="lawsuit_debt_loan",
    )
    assert "Ключові фактичні обставини та хронологія" in text
    assert "01.01.2025 укладено договір позики." in text


def test_processual_validation_checks_pass_for_motion_claim_security() -> None:
    text = "\n".join(
        [
            "ЗАЯВА ПРО ЗАБЕЗПЕЧЕННЯ ПОЗОВУ",
            "1. Обставини та ризик невиконання рішення",
            "2. Правове обґрунтування",
            "Відповідно до ст. 149, ст. 150, ст. 151 ЦПК України...",
            "3. ПРОШУ СУД",
            "4. Додатки",
            "Дата: _______________",
            "Підпис: _______________",
            " ".join(["процесуальний"] * 180),
        ]
    )
    checks = build_processual_validation_checks("motion_claim_security", text)
    assert checks
    assert all(item["status"] == "pass" for item in checks)


def test_processual_validation_checks_pass_for_cassation_complaint() -> None:
    text = "\n".join(
        [
            "КАСАЦІЙНА СКАРГА",
            "1. Судові рішення, що оскаржуються",
            "2. Підстави касаційного оскарження",
            "3. Дотримання строку касаційного оскарження",
            "4. Норми права",
            "Відповідно до ст. 389 ЦПК України...",
            "5. ПРОШУ СУД",
            "6. Додатки",
            "Дата: _______________",
            "Підпис: _______________",
            " ".join(["процесуальний"] * 170),
        ]
    )
    checks = build_processual_validation_checks("cassation_complaint", text)
    assert checks
    assert all(item["status"] == "pass" for item in checks)


def test_processual_validation_checks_pass_for_statement_enforcement_opening() -> None:
    text = "\n".join(
        [
            "ЗАЯВА ПРО ВІДКРИТТЯ ВИКОНАВЧОГО ПРОВАДЖЕННЯ",
            "1. Реквізити виконавчого документа",
            "2. Дані стягувача і боржника",
            "3. Правове обґрунтування",
            "Відповідно до ст. 26 Закону України \"Про виконавче провадження\" та ст. 447 ЦПК України.",
            "4. ПРОШУ:",
            "5. Додатки",
            "Дата: _______________",
            "Підпис: _______________",
            " ".join(["процесуальний"] * 130),
        ]
    )
    checks = build_processual_validation_checks("statement_enforcement_opening", text)
    assert checks
    assert all(item["status"] == "pass" for item in checks)


def test_generation_validation_checks_include_ai_second_pass(monkeypatch) -> None:
    def _fake_ai(_: str, __: str) -> AIResult:
        return AIResult(
            text=(
                '{'
                '"fact_norm_chain_status":"pass",'
                '"fact_norm_chain_message":"Ланцюг факт-норма-доказ узгоджений.",'
                '"internal_consistency_status":"warn",'
                '"internal_consistency_message":"Виявлено одну потенційну неузгодженість дат.",'
                '"processual_actionability_status":"pass",'
                '"processual_actionability_message":"Прохальна частина процесуально визначена.",'
                '"overall_status":"warn",'
                '"overall_message":"Рекомендовано локально уточнити таймлайн."'
                '}'
            ),
            used_ai=True,
            model="test-model",
            error="",
        )

    monkeypatch.setattr("app.services.prompt_builder.generate_legal_document", _fake_ai)

    strong_text = "\n".join(
        [
            "ПОЗОВНА ЗАЯВА",
            "1. Обставини справи",
            "2. Правове обґрунтування",
            "3. Відомості відповідно до ст. 175 ЦПК України",
            "4. ПРОШУ СУД",
            "5. Перелік документів, що додаються (ст. 177 ЦПК України)",
            "Відповідно до ст. 625 ЦК України та ст. 175 ЦПК України.",
            "Дата: _______________",
            "Підпис: _______________",
            " ".join(["процесуальний"] * 220),
        ]
    )
    checks = build_generation_validation_checks(
        "lawsuit_debt_loan",
        strong_text,
        form_data={"fact_summary": "Борг не повернуто у строк.", "request_summary": "Стягнути борг."},
        preview_text=strong_text,
    )
    assert any(item["code"] == "ai_second_pass_fact_norm_chain" and item["status"] == "pass" for item in checks)
    assert any(item["code"] == "ai_second_pass_internal_consistency" and item["status"] == "warn" for item in checks)
    assert any(item["code"] == "ai_second_pass_overall" and item["status"] == "warn" for item in checks)


def test_generation_validation_checks_warn_when_ai_second_pass_unavailable(monkeypatch) -> None:
    def _fake_ai_unavailable(_: str, __: str) -> AIResult:
        return AIResult(text="", used_ai=False, model="", error="OPENAI_API_KEY is not set.")

    monkeypatch.setattr("app.services.prompt_builder.generate_legal_document", _fake_ai_unavailable)

    strong_text = "\n".join(
        [
            "ПОЗОВНА ЗАЯВА",
            "1. Обставини справи",
            "2. Правове обґрунтування",
            "3. Відомості відповідно до ст. 175 ЦПК України",
            "4. ПРОШУ СУД",
            "5. Перелік документів, що додаються (ст. 177 ЦПК України)",
            "Відповідно до ст. 625 ЦК України та ст. 175 ЦПК України.",
            "Дата: _______________",
            "Підпис: _______________",
            " ".join(["процесуальний"] * 220),
        ]
    )
    checks = build_generation_validation_checks("lawsuit_debt_loan", strong_text, form_data={}, preview_text=strong_text)
    assert any(item["code"] == "ai_second_pass_unavailable" and item["status"] == "warn" for item in checks)
