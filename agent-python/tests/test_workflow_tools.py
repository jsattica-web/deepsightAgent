import unittest
from unittest.mock import patch

from app.graph.agent import run_agent
from app.schemas.tool_schema import (
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

        with patch("app.graph.agent.get_sales_trend", return_value=response_model) as tool:
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

        with patch("app.graph.agent.get_order_status", return_value=response_model) as tool:
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

        with patch("app.graph.agent.get_inventory_risk", return_value=response_model) as tool:
            response = run_agent("TV OLED 재고 리스크 확인해줘")

        self.assertEqual(response["status"], "success")
        self.assertIn("재고 리스크", response["data"]["answer"])
        tool.assert_called_once()


if __name__ == "__main__":
    unittest.main()
