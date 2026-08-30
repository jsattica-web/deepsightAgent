import unittest
from decimal import Decimal
from unittest.mock import patch

from app.schemas.tool_schema import (
    CompetitorNewsRequest,
    CompetitorNewsResponse,
)
from app.tools.news_tool import (
    _impact_level,
    search_competitor_news,
)


class FakeCursor:
    """기존 DB SELECT 결과를 흉내 내는 테스트용 커서입니다."""

    def execute(self, query, params):
        self.query = query
        self.params = params

    def fetchall(self):
        return [
            {
                "news_date": "2026-06-20",
                "company": "BOE",
                "category": "capacity",
                "title": "BOE DB 뉴스",
                "summary": "DB에 저장된 경쟁사 뉴스",
                "impact_score": Decimal("6.0"),
                "related_product_group": "OLED",
            }
        ]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class FakeConnection:
    """get_connection()을 흉내 내는 테스트용 연결입니다."""

    def cursor(self, cursor_factory=None):
        return FakeCursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


def make_request():
    return CompetitorNewsRequest(
        start_date="2026-01-01",
        end_date="2026-06-30",
        companies=["BOE"],
        category=None,
        impact_level=None,
        keyword="OLED",
        product_group=None,
    )


class CompetitorNewsTests(unittest.TestCase):

    def test_impact_level(self):
        self.assertEqual(
            _impact_level(5),
            "HIGH",
        )
        self.assertEqual(
            _impact_level(4),
            "MEDIUM",
        )
        self.assertEqual(
            _impact_level(2),
            "LOW",
        )

    def test_db_and_naver_are_both_returned(self):
        """
        DB 1건 + NAVER 1건이면 최종 data가 2건인지 확인합니다.
        """

        fake_naver_result = {
            "searched_news_count": 1,
            "news_count": 1,
            "news": [
                {
                    "published_at": "2026-08-30 10:00:00",
                    "company": "BOE",
                    "category": "it",
                    "title": "BOE OLED NAVER 뉴스",
                    "description": "BOE OLED 관련 NAVER 기사",
                    "relevance_score": 8,
                    "product_group": "OLED",
                }
            ],
        }

        with (
            patch(
                "app.tools.news_tool.get_connection",
                return_value=FakeConnection(),
            ),
            patch(
                "app.tools.news_tool.crawl_news",
                return_value=fake_naver_result,
            ),
        ):
            result = search_competitor_news(
                make_request()
            )

        self.assertIsInstance(
            result,
            CompetitorNewsResponse,
        )

        self.assertEqual(
            len(result.data),
            2,
        )

        self.assertEqual(
            result.data[0].source,
            "DB",
        )

        self.assertEqual(
            result.data[1].source,
            "NAVER",
        )

        self.assertIn(
            "DB 검색 1건",
            result.summary,
        )

        self.assertIn(
            "NAVER 전일 뉴스 1건",
            result.summary,
        )

    def test_naver_error_still_returns_db_result(self):
        """
        NAVER API가 실패해도 기존 DB 뉴스는 반환되는지 확인합니다.
        """

        with (
            patch(
                "app.tools.news_tool.get_connection",
                return_value=FakeConnection(),
            ),
            patch(
                "app.tools.news_tool.crawl_news",
                side_effect=RuntimeError(
                    "NAVER unavailable"
                ),
            ),
        ):
            result = search_competitor_news(
                make_request()
            )

        self.assertEqual(
            len(result.data),
            1,
        )

        self.assertEqual(
            result.data[0].source,
            "DB",
        )

        self.assertIn(
            "NAVER 전일 뉴스 0건",
            result.summary,
        )


if __name__ == "__main__":
    unittest.main()
