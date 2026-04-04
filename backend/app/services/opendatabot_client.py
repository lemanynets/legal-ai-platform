from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from app.config import settings


class OpendatabotError(Exception):
    """Base exception for Opendatabot API errors."""


class OpendatabotClient:
    def __init__(self) -> None:
        self.api_key = settings.opendatabot_api_key
        self.base_url = settings.opendatabot_api_url.rstrip("/")
        self.timeout = 15.0

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    def _build_court_cases_url(self, number: str) -> str:
        root = self.base_url if self.base_url.endswith("/v2") else f"{self.base_url}/v2"
        return f"{root}/court-cases/{quote(number, safe='/')}"

    def get_company_details(self, code: str) -> dict[str, Any]:
        """Fetch details for a company by EDRPOU code."""
        if not self.api_key:
            return self._stub_company_details(code)

        url = f"{self.base_url}/company/{code}"
        try:
            response = httpx.get(url, headers=self._get_headers(), timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            return self._stub_company_details(code)
        except Exception:
            return self._stub_company_details(code)

    def search_court_decisions(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search court decisions by keyword or case number."""
        if not self.api_key:
            return []

        root = self.base_url if self.base_url.endswith("/v2") else f"{self.base_url}/v2"
        url = f"{root}/court"
        params = {"apiKey": self.api_key, "text": query, "limit": limit}
        try:
            response = httpx.get(url, headers={"Accept": "application/json"}, params=params, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data.get("items"), list):
                    return data.get("items") or []
                if isinstance(data.get("data"), dict):
                    return data["data"].get("items") or []
            return []
        except Exception:
            return []

    def get_court_case(self, number: str, judgment_code: int | None = None) -> dict[str, Any]:
        """Fetch full court case information by case number."""
        if not self.api_key:
            raise OpendatabotError("OPENDATABOT_API_KEY is not configured.")

        url = self._build_court_cases_url(number)
        params: dict[str, Any] = {"apiKey": self.api_key}
        if judgment_code is not None:
            params["judgment_code"] = judgment_code

        try:
            response = httpx.get(
                url,
                params=params,
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )

            if response.status_code == 200:
                raw = response.json()
                return self._normalize_court_case(raw, requested_number=number)

            if response.status_code == 404:
                raise OpendatabotError(f"Справу '{number}' не знайдено в реєстрі Опендатабот.")

            if response.status_code in {401, 403}:
                raise OpendatabotError("Недійсний або прострочений API-ключ Опендатабот.")

            if response.status_code == 400:
                detail = response.text[:300]
                if "not unique" in detail.lower():
                    raise OpendatabotError(
                        "Результат пошуку неунікальний. Уточніть вид судочинства через judgment_code."
                    )
                raise OpendatabotError(f"Некоректний запит до Опендатабот: {detail}")

            if response.status_code == 429:
                raise OpendatabotError("Перевищено ліміт запитів до Опендатабот API.")

            raise OpendatabotError(
                f"Опендатабот API повернув статус {response.status_code}: {response.text[:200]}"
            )

        except OpendatabotError:
            raise
        except httpx.TimeoutException:
            raise OpendatabotError("Timeout при запиті до Опендатабот API.")
        except Exception as exc:
            raise OpendatabotError(f"Помилка підключення до Опендатабот: {exc}") from exc

    def _normalize_court_case(self, raw: dict[str, Any], *, requested_number: str) -> dict[str, Any]:
        sides: list[dict[str, str]] = []
        sides_raw = raw.get("sides") or raw.get("parties") or []
        if isinstance(sides_raw, list):
            for side in sides_raw:
                if not isinstance(side, dict):
                    continue
                sides.append(
                    {
                        "role": str(side.get("role") or side.get("type") or ""),
                        "name": str(side.get("name") or side.get("full_name") or ""),
                        "code": str(side.get("code") or side.get("edrpou") or ""),
                    }
                )

        if not sides:
            grouped_roles = (
                ("plaintiff", raw.get("plaintiffs") or []),
                ("defendant", raw.get("defendants") or []),
                ("third_party", raw.get("third_persons") or []),
                ("appeal_party", raw.get("appeals") or []),
                ("cassation_party", raw.get("cassations") or []),
            )
            for role, items in grouped_roles:
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    sides.append(
                        {
                            "role": role,
                            "name": str(item.get("name") or item.get("full_name") or ""),
                            "code": str(item.get("code") or item.get("edrpou") or ""),
                        }
                    )

        decisions: list[dict[str, str]] = []
        decisions_raw = raw.get("decisions") or raw.get("court_decisions") or raw.get("links") or []
        if isinstance(decisions_raw, list):
            for item in decisions_raw:
                if not isinstance(item, dict):
                    continue
                decisions.append(
                    {
                        "id": str(item.get("id") or item.get("decision_id") or ""),
                        "date": str(item.get("date") or item.get("decision_date") or ""),
                        "type": str(item.get("type") or item.get("document_type") or ""),
                        "url": str(item.get("url") or item.get("link") or ""),
                        "summary": str(item.get("summary") or item.get("text") or "")[:300],
                    }
                )
        elif isinstance(decisions_raw, str) and decisions_raw:
            decisions.append({"id": "", "date": "", "type": "", "url": decisions_raw, "summary": ""})

        stages_raw = raw.get("stages") or {}
        normalized_stages: dict[str, Any] = {}
        if isinstance(stages_raw, dict):
            for stage_name, stage_payload in stages_raw.items():
                if not isinstance(stage_payload, dict):
                    continue
                stage_decisions: list[dict[str, str]] = []
                stage_items = stage_payload.get("decisions") or []
                if isinstance(stage_items, list):
                    for item in stage_items:
                        if not isinstance(item, dict):
                            continue
                        normalized = {
                            "id": str(item.get("id") or item.get("decision_id") or ""),
                            "date": str(
                                item.get("adjudication_date")
                                or item.get("date_publ")
                                or item.get("receipt_date")
                                or ""
                            ),
                            "type": str(item.get("justice_name") or item.get("judgment_name") or ""),
                            "url": str(item.get("link") or item.get("url") or ""),
                            "summary": str(item.get("description") or item.get("result") or "")[:300],
                        }
                        stage_decisions.append(normalized)
                        decisions.append(normalized)
                normalized_stages[str(stage_name)] = {
                    "court_code": stage_payload.get("court_code"),
                    "court_name": str(stage_payload.get("court_name") or ""),
                    "judge": str(stage_payload.get("judge") or ""),
                    "consideration": str(stage_payload.get("consideration") or ""),
                    "description": str(stage_payload.get("description") or ""),
                    "decisions": stage_decisions,
                }

        instance_info_raw = raw.get("instance_info") or raw.get("instance") or {}
        if isinstance(instance_info_raw, str):
            instance_info_raw = {"description": instance_info_raw}

        return {
            "number": raw.get("number") or raw.get("case_number") or requested_number,
            "court": raw.get("court") or raw.get("court_name") or "",
            "judge": raw.get("judge") or raw.get("judge_name") or "",
            "sides": sides,
            "proceeding_type": raw.get("proceeding_type") or raw.get("type") or raw.get("category") or "",
            "subject": raw.get("subject") or raw.get("description") or raw.get("subject_of_dispute") or "",
            "claim_price": raw.get("claim_price") or raw.get("cost") or raw.get("price") or raw.get("amount"),
            "date": raw.get("date") or "",
            "start_date": raw.get("date_start") or raw.get("start_date") or raw.get("registration_date") or raw.get("date") or "",
            "next_hearing_date": raw.get("last_schedule_date") or raw.get("next_hearing_date") or raw.get("hearing_date") or raw.get("next_session_date") or "",
            "last_status": raw.get("last_status") or raw.get("status") or raw.get("current_status") or "",
            "schedule_count": raw.get("schedule_count"),
            "judgment_code": raw.get("judgment_code"),
            "live": raw.get("live"),
            "last_document_date": raw.get("last_document_date") or "",
            "instance_info": instance_info_raw,
            "instance_result": raw.get("instance_result") or raw.get("result") or raw.get("verdict") or "",
            "decisions": self._dedupe_decisions(decisions),
            "stages": normalized_stages,
            "_raw": raw,
        }

    def _dedupe_decisions(self, decisions: list[dict[str, str]]) -> list[dict[str, str]]:
        seen: set[tuple[str, str, str]] = set()
        unique: list[dict[str, str]] = []
        for item in decisions:
            key = (item.get("id", ""), item.get("url", ""), item.get("date", ""))
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    def _stub_company_details(self, code: str) -> dict[str, Any]:
        if code == "39806182":
            return {
                "full_name": 'ТОВАРИСТВО З ОБМЕЖЕНОЮ ВІДПОВІДАЛЬНІСТЮ "ЛЕМАНИНЕЦЬ І ПАРТНЕРИ"',
                "short_name": 'ТОВ "ЛЕМАНИНЕЦЬ І ПАРТНЕРИ"',
                "code": code,
                "status": "registered",
                "address": "Україна",
                "ceo": "Невідомо",
                "authorized_capital": 10000.0,
                "activities": ["69.10 Діяльність у сфері права"],
                "founders": ["Леманинець Вячеслав"],
                "is_sanctioned": False,
                "has_tax_debt": False,
            }
        return {
            "full_name": f'DEMO COMPANY {code}',
            "short_name": "DEMO COMPANY",
            "code": code,
            "status": "active",
            "address": "м. Київ",
            "ceo": "Demo CEO",
            "authorized_capital": 1000000.0,
            "activities": ["62.01 Комп'ютерне програмування"],
            "founders": ["Невідомо"],
            "is_sanctioned": False,
            "has_tax_debt": False,
        }


opendatabot = OpendatabotClient()
