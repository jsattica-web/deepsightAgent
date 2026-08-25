import unittest

from app.schemas.tool_schema import BriefingRequest, BriefingResponse
from app.tools.briefing_tool import create_briefing_report


class BriefingToolTests(unittest.TestCase):
    def test_combines_tool_results_into_sections(self):
        request = BriefingRequest(
            topic="2026년 2분기 사업 리뷰",
            customer_id="CUST_A",
            start_date="2026-04-01",
            end_date="2026-06-30",
            sections=[
                "sales",
                "orders",
                "inventory",
                "competitor_news",
                "recommended_actions",
            ],
            tool_results={
                "sales": {
                    "summary": "OLED 판매량은 증가 추세입니다.",
                    "insights": ["판매량이 8.1% 증가했습니다."],
                    "actions": ["추가 수주 가능성을 확인하세요."],
                },
                "orders": {
                    "summary": "지연 수주 2건이 있습니다.",
                    "risk_signals": ["지연 비율이 높습니다."],
                    "actions": ["납기 원인을 점검하세요."],
                },
                "inventory": {
                    "summary": "TV OLED 과잉재고 가능성이 있습니다.",
                    "risk_signals": [
                        {"level": "HIGH", "type": "OVER_STOCK", "message": "과잉재고 신호"}
                    ],
                    "actions": ["생산 계획 조정을 검토하세요."],
                },
                "competitor_news": {
                    "summary": "경쟁사 뉴스 3건이 확인됐습니다.",
                    "insights": ["가격 경쟁 가능성이 있습니다."],
                },
            },
        )
        result = create_briefing_report(request)

        self.assertIsInstance(result, BriefingResponse)
        self.assertEqual(result.tool_name, "create_briefing_report")
        self.assertEqual(len(result.data), 5)
        self.assertEqual(result.data[0].section, "판매 실적 요약")
        self.assertIn("OLED 판매량", result.data[0].key_message)
        self.assertTrue(any("지연 비율" in item for item in result.risk_signals))
        self.assertIn("과잉재고 신호", result.risk_signals)
        self.assertTrue(result.actions)

    def test_creates_outline_without_tool_results(self):
        request = BriefingRequest(
            topic="회의 준비",
            start_date="2026-04-01",
            end_date="2026-06-30",
            sections=["sales", "recommended_actions"],
        )
        result = create_briefing_report(request)
        self.assertIsInstance(result, BriefingResponse)
        self.assertEqual(len(result.data), 2)
        self.assertIn("아직 제공되지 않았습니다", result.data[0].key_message)
        self.assertTrue(result.actions)


if __name__ == "__main__":
    unittest.main()
