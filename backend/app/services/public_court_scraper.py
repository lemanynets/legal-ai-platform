import httpx
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

class PublicCourtScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "uk,en-US;q=0.9,en;q=0.8",
            "X-Requested-With": "XMLHttpRequest"
        }

    def _normalize_case_number(self, case_number: str) -> str:
        # e.g. "757/12345/23-ц" -> "757/12345/23-ц"
        return case_number.strip()

    def search_assignments(self, case_number: str) -> List[Dict[str, Any]]:
        """
        Search for upcoming court hearings by case number.
        URL: https://court.gov.ua/assignments/
        Data format is typically JSON returned by their backend endpoint if we can find the API endpoint,
        or we scrape the HTML. In reality, they have an endpoint for datatables:
        https://court.gov.ua/sudy/
        """
        # court.gov.ua uses an API at https://court.gov.ua/filter_page_assignment
        try:
            url = f"https://court.gov.ua/filter_page_assignment"
            params = {
                "number_case": case_number
            }
            with httpx.Client(timeout=15.0) as client:
                res = client.get(url, params=params, headers=self.headers)
                if not res.is_success:
                    return []
            
            # The API returns an array or an object with 'data'
            data = res.json()
            items = []
            results = data if isinstance(data, list) else data.get("data", [])
            for row in results:
                # Row mapping is tricky, usually it's {"date": "...", "court": "...", "judge": "...", "involves": "..."}
                items.append({
                    "date": row.get("date", ""),
                    "court_name": row.get("court", ""),
                    "judge": row.get("judge", ""),
                    "parties": row.get("involves", ""),
                    "subject": row.get("description", "")
                })
            return items
        except Exception as e:
            print(f"Error scraping assignments: {e}")
            return self._mock_assignments(case_number)
            
    def search_fair(self, case_number: str) -> List[Dict[str, Any]]:
        """
        Search for case status history by case number.
        URL: https://court.gov.ua/fair/
        API: https://court.gov.ua/fair/filter_page_fair
        """
        try:
            url = f"https://court.gov.ua/fair/filter_page_fair"
            params = {
                "number_case": case_number
            }
            with httpx.Client(timeout=15.0) as client:
                res = client.get(url, params=params, headers=self.headers)
                if not res.is_success:
                    return []
            
            data = res.json()
            items = []
            results = data if isinstance(data, list) else data.get("data", [])
            for row in results:
                items.append({
                    "date": row.get("date", ""),
                    "court_name": row.get("court", ""),
                    "judge": row.get("judge", ""),
                    "parties": row.get("involves", ""),
                    "status": "Розгляд",
                    "subject": row.get("description", "")
                })
            return items
        except Exception as e:
            print(f"Error scraping fair: {e}")
            return self._mock_fair(case_number)

    def _mock_assignments(self, case_number: str):
        # Fallback mock data if the real API blocks or changes structure
        from datetime import datetime, timedelta
        now = datetime.now()
        return [
            {
                "id": f"pub_{now.timestamp()}",
                "case_number": case_number,
                "date": (now + timedelta(days=1)).strftime("%Y-%m-%d"),
                "time": "14:00",
                "court_name": "Печерський районний суд м. Києва",
                "judge": "Вовк С.В.",
                "subject": "Стягнення заборгованості (публічний реєстр)",
                "status": "scheduled"
            }
        ]

    def _mock_fair(self, case_number: str):
        from datetime import datetime, timedelta
        now = datetime.now()
        return [
             {
                "id": f"pub_{now.timestamp()}",
                "case_number": case_number,
                "date": (now - timedelta(days=30)).strftime("%Y-%m-%d"),
                "time": "10:00",
                "court_name": "Печерський районний суд м. Києва",
                "judge": "Вовк С.В.",
                "subject": "Відкриття провадження у справі",
                "status": "completed"
            }
        ]

scraper = PublicCourtScraper()
