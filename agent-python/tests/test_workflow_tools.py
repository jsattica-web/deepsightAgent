import unittest
from unittest.mock import patch

from app.agent.agent import run_agent
from app.schemas.tool_schema import (
    BriefingResponse,
    BriefingSection,
    CompetitorNewsPoint,
    CompetitorNewsResponse,
    CustomerProfilePoint,
    CustomerProfileResponse,
    InventoryRiskResponse,
    InventoryTrendPoint,
    OrderStatusPoint,
    OrderStatusResponse,
    SalesTrendPoint,
    SalesTrendResponse,
)


class WorkflowToolTests(unittest.TestCase):
    def test_agent_chat_routes_sales_question_to_sales_tool(self):
        response_model = SalesTrendResponse(
            tool_name="get_sales_trend",
            status="success",
            summary="판매 동향 테스트 응답입니다.",
            data=[
                SalesTrendPoint(month="2026-01", qty=100, revenue=1000.0, asp=10.0),
                SalesTrendPoint(month="2026-06", qty=120, revenue=1320.0, asp=11.0),
            ],
            insights=[],
            risk_signals=[],
            chart_data={
                "type": "line",
                "x": ["2026-01", "2026-06"],
                "series": [{"name": "qty", "data": [100, 120]}],
            },
            actions=[],
        )

        with patch("app.agent.agent.get_sales_trend", return_value=response_model) as tool:
            response = run_agent("최근 6개월 OLED 판매 동향 분석해줘")

        self.assertEqual(response["status"], "success")
        self.assertIn("판매 동향", response["data"]["answer"])
        tool.assert_called_once()

    def test_agent_chat_routes_order_question_to_order_tool(self):
        response_model = OrderStatusResponse(
            tool_name="get_order_status",
            status="success",
            summary="수주 현황 테스트 응답입니다.",
            data=[
                OrderStatusPoint(
                    month="2026-01",
                    total_orders=2,
                    total_order_qty=300,
                    confirmed_count=1,
                    pending_count=0,
                    delayed_count=1,
                    cancelled_count=0,
                    shipped_count=0,
                    risk_order_count=1,
                )
            ],
            insights=[],
            risk_signals=[],
            chart_data={
                "type": "bar",
                "x": ["2026-01"],
                "series": [{"name": "delayed", "data": [1]}],
            },
            actions=[],
        )

        with patch("app.agent.agent.get_order_status", return_value=response_model) as tool:
            response = run_agent("OLED 수주 현황과 납기 지연 확인해줘")

        self.assertEqual(response["status"], "success")
        self.assertIn("수주 현황", response["data"]["answer"])
        tool.assert_called_once()

    def test_agent_chat_routes_inventory_question_to_inventory_tool(self):
        response_model = InventoryRiskResponse(
            tool_name="get_inventory_risk",
            status="success",
            summary="재고 리스크 테스트 응답입니다.",
            data=[
                InventoryTrendPoint(
                    month="2026-06",
                    ending_stock=500,
                    safety_stock=300,
                    production_qty=200,
                    sales_qty=150,
                )
            ],
            insights=[],
            risk_signals=[],
            chart_data={
                "type": "line",
                "x": ["2026-06"],
                "series": [{"name": "ending_stock", "data": [500]}],
            },
            actions=[],
        )

        with patch("app.agent.agent.get_inventory_risk", return_value=response_model) as tool:
            response = run_agent("TV OLED 재고 리스크 확인해줘")

        self.assertEqual(response["status"], "success")
        self.assertIn("재고 리스크", response["data"]["answer"])
        tool.assert_called_once()

    def test_agent_chat_routes_customer_question_to_customer_tool(self):
        response_model = CustomerProfileResponse(
            tool_name="get_customer_profile",
            status="success",
            summary="고객 프로필 테스트 응답입니다.",
            data=[
                CustomerProfilePoint(
                    customer_id="CUST_A",
                    customer_name="Aster Mobile Systems",
                    segment="Mobile",
                    region="North America",
                    tier="Tier 1",
                    main_application="Premium smartphone display",
                    sales_qty=1200,
                    sales_revenue=1450000.0,
                    order_count=8,
                    order_qty=1500,
                    delayed_order_count=1,
                )
            ],
            insights=[],
            risk_signals=[],
            chart_data={"type": "bar", "categories": ["Sales Qty", "Order Qty"], "series": []},
            actions=[],
        )

        with patch("app.agent.agent.get_customer_profile", return_value=response_model) as tool:
            response = run_agent("CUST_A 고객사 프로필 확인해줘")

        self.assertEqual(response["status"], "success")
        self.assertIn("고객사 프로필", response["data"]["answer"])
        tool.assert_called_once()

    def test_agent_chat_routes_news_question_to_news_tool(self):
        response_model = CompetitorNewsResponse(
            tool_name="search_competitor_news",
            status="success",
            summary="경쟁사 뉴스 테스트 응답입니다.",
            data=[
                CompetitorNewsPoint(
                    news_date="2026-06-18",
                    company="LGD",
                    category="capacity",
                    title="LGD adjusts TV OLED utilization plan",
                    summary="Synthetic TV OLED demand signal",
                    impact_score=5.0,
                    impact_level="HIGH",
                    product_group="TV OLED",
                )
            ],
            insights=[],
            risk_signals=[],
            chart_data={"type": "bar", "x": ["LGD"], "series": []},
            actions=[],
        )

        with patch("app.agent.agent.search_competitor_news", return_value=response_model) as tool:
            response = run_agent("LGD 경쟁사 뉴스 확인해줘")

        self.assertEqual(response["status"], "success")
        self.assertIn("경쟁사 뉴스", response["data"]["answer"])
        tool.assert_called_once()

    def test_agent_chat_routes_briefing_question_to_briefing_tool(self):
        response_model = BriefingResponse(
            tool_name="create_briefing_report",
            status="success",
            summary="브리핑 테스트 응답입니다.",
            data=[
                BriefingSection(
                    order=1,
                    section="판매 실적 요약",
                    key_message="판매 동향을 요약했습니다.",
                )
            ],
            insights=[],
            risk_signals=[],
            chart_data={},
            actions=[],
        )

        with patch("app.agent.agent.create_briefing_report", return_value=response_model) as tool:
            response = run_agent("CUST_A 대상 브리핑 보고서 만들어줘")

        self.assertEqual(response["status"], "success")
        self.assertIn("브리핑 초안", response["data"]["answer"])
        tool.assert_called_once()

if __name__ == "__main__":
    unittest.main()
