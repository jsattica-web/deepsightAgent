import unittest
from datetime import date
from unittest.mock import patch

from app.schemas.common import ErrorResponse
from app.schemas.tool_schema import CompetitorNewsRequest, CompetitorNewsResponse
from app.tools.news_tool import _impact_level, search_competitor_news


class FakeCursor:
    def __init__(self, rows=None, error=None):
        self.rows = rows or []
        self.error = error
        self.query = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, query, params):
        if self.error:
            raise self.error
        self.query = query
        self.params = params

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self, **_):
        return self.fake_cursor


def make_request(**kwargs):
    values = {
        "start_date": "2026-04-01",
        "end_date": "2026-06-30",
        "companies": ["LGD", "CSOT"],
        "keyword": "OLED",
    }
    values.update(kwargs)
    return CompetitorNewsRequest(**values)


class CompetitorNewsTests(unittest.TestCase):
    def test_impact_level(self):
        self.assertEqual(_impact_level(5), "HIGH")
        self.assertEqual(_impact_level(4), "MEDIUM")
        self.assertEqual(_impact_level(2), "LOW")

    def test_returns_news_and_uses_filters(self):
        cursor = FakeCursor([
            {
                "news_date": date(2026, 6, 18),
                "company": "LGD",
                "category": "capacity",
                "title": "LGD adjusts TV OLED utilization plan",
                "summary": "Synthetic TV OLED demand signal",
                "impact_score": 5,
                "related_product_group": "TV OLED",
            },
            {
                "news_date": date(2026, 4, 6),
                "company": "CSOT",
                "category": "capacity",
                "title": "CSOT increases TV OLED pilot output",
                "summary": "Synthetic TV OLED competition signal",
                "impact_score": 4,
                "related_product_group": "TV OLED",
            },
        ])
        with patch("app.tools.news_tool.get_connection", return_value=FakeConnection(cursor)):
            result = search_competitor_news(make_request())

        self.assertIsInstance(result, CompetitorNewsResponse)
        self.assertEqual(result.tool_name, "search_competitor_news")
        self.assertEqual(len(result.data), 2)
        self.assertEqual(result.data[0].impact_level, "HIGH")
        self.assertTrue(result.risk_signals)
        self.assertIn("any(%(companies)s)", cursor.query)
        self.assertEqual(cursor.params["companies"], ["LGD", "CSOT"])
        self.assertEqual(cursor.params["keyword"], "%OLED%")

    def test_returns_empty_success(self):
        cursor = FakeCursor([])
        with patch("app.tools.news_tool.get_connection", return_value=FakeConnection(cursor)):
            result = search_competitor_news(make_request())
        self.assertIsInstance(result, CompetitorNewsResponse)
        self.assertEqual(result.data, [])
        self.assertIn("없습니다", result.summary)

    def test_returns_error_response_on_database_error(self):
        cursor = FakeCursor(error=RuntimeError("database unavailable"))
        with patch("app.tools.news_tool.get_connection", return_value=FakeConnection(cursor)):
            result = search_competitor_news(make_request())
        self.assertIsInstance(result, ErrorResponse)
        self.assertNotIn("database unavailable", result.message)


if __name__ == "__main__":
    unittest.main()
