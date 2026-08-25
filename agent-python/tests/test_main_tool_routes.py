import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.tool_schema import (
    InventoryRiskResponse,
    InventoryTrendPoint,
    OrderStatusPoint,
    OrderStatusResponse,
    SalesTrendPoint,
    SalesTrendResponse,
)


client = TestClient(app)


class MainToolRouteTests(unittest.TestCase):
    def test_sales_trend_route_calls_sales_tool(self):
        response_model = SalesTrendResponse(
            tool_name="get_sales_trend",
            status="success",
            summary="판매 동향 테스트 응답입니다.",
            data=[SalesTrendPoint(month="2026-01", qty=100, revenue=1000.0, asp=10.0)],
            insights=[],
            risk_signals=[],
            chart_data={"type": "line", "x": ["2026-01"], "series": []},
            actions=[],
        )

        with patch("app.main.get_sales_trend", return_value=response_model) as tool:
            response = client.post(
                "/tools/sales-trend",
                json={
                    "start_month": "2026-01",
                    "end_month": "2026-06",
                    "product_group": "Mobile OLED",
                    "customer_id": None,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tool_name"], "get_sales_trend")
        tool.assert_called_once()

    def test_order_status_route_calls_order_tool(self):
        response_model = OrderStatusResponse(
            tool_name="get_order_status",
            status="success",
            summary="수주 현황 테스트 응답입니다.",
            data=[
                OrderStatusPoint(
                    month="2026-01",
                    total_orders=1,
                    total_order_qty=100,
                    confirmed_count=1,
                    pending_count=0,
                    delayed_count=0,
                    cancelled_count=0,
                    shipped_count=0,
                    risk_order_count=0,
                )
            ],
            insights=[],
            risk_signals=[],
            chart_data={"type": "bar", "x": ["2026-01"], "series": []},
            actions=[],
        )

        with patch("app.main.get_order_status", return_value=response_model) as tool:
            response = client.post(
                "/tools/order-status",
                json={
                    "start_date": "2026-01-01",
                    "end_date": "2026-06-30",
                    "customer_id": None,
                    "product_group": "Mobile OLED",
                    "status": None,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tool_name"], "get_order_status")
        tool.assert_called_once()

    def test_inventory_risk_route_calls_inventory_tool(self):
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
            chart_data={"type": "line", "x": ["2026-06"], "series": []},
            actions=[],
        )

        with patch("app.main.get_inventory_risk", return_value=response_model) as tool:
            response = client.post(
                "/tools/inventory-risk",
                json={
                    "inventory_month": "2026-06",
                    "product_group": "TV OLED",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tool_name"], "get_inventory_risk")
        tool.assert_called_once()


if __name__ == "__main__":
    unittest.main()
