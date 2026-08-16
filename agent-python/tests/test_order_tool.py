import unittest
from unittest.mock import patch

from app.schemas.common import ErrorResponse
from app.schemas.tool_schema import OrderStatusRequest, OrderStatusResponse
from app.tools.order_tool import get_order_status


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


def make_request(customer_id=None, status=None):
    return OrderStatusRequest(
        start_date="2026-01-01",
        end_date="2026-06-30",
        customer_id=customer_id,
        product_group="Mobile OLED",
        status=status,
    )


class OrderStatusTests(unittest.TestCase):
    def test_returns_order_status_and_risk_analysis(self):
        cursor = FakeCursor(
            [
                {
                    "month": "2026-01",
                    "total_orders": 10,
                    "total_order_qty": 1000,
                    "confirmed_count": 5,
                    "pending_count": 2,
                    "delayed_count": 2,
                    "cancelled_count": 1,
                    "shipped_count": 0,
                    "risk_order_count": 3,
                }
            ]
        )
        with patch(
            "app.tools.order_tool.get_connection",
            return_value=FakeConnection(cursor),
        ):
            result = get_order_status(make_request())

        self.assertIsInstance(result, OrderStatusResponse)
        self.assertEqual(result.data[0].total_order_qty, 1000)
        self.assertEqual(result.chart_data["type"], "bar")
        self.assertTrue(any("30.0%" in item for item in result.risk_signals))
        self.assertIn("join public.dim_customer", cursor.query)
        self.assertIn("join public.dim_product", cursor.query)

    def test_applies_customer_and_status_filters(self):
        cursor = FakeCursor([])
        with patch(
            "app.tools.order_tool.get_connection",
            return_value=FakeConnection(cursor),
        ):
            result = get_order_status(make_request("CUST_A", "delayed"))

        self.assertIsInstance(result, OrderStatusResponse)
        self.assertEqual(cursor.params["customer_id"], "CUST_A")
        self.assertEqual(cursor.params["status"], "DELAYED")
        self.assertIn("%(customer_id)s", cursor.query)
        self.assertIn("%(status)s", cursor.query)

    def test_returns_success_when_no_data_exists(self):
        cursor = FakeCursor([])
        with patch(
            "app.tools.order_tool.get_connection",
            return_value=FakeConnection(cursor),
        ):
            result = get_order_status(make_request())

        self.assertIsInstance(result, OrderStatusResponse)
        self.assertEqual(result.status, "success")
        self.assertEqual(result.data, [])
        self.assertIn("데이터가 없습니다", result.summary)

    def test_returns_error_response_on_database_error(self):
        cursor = FakeCursor(error=RuntimeError("database unavailable"))
        with patch(
            "app.tools.order_tool.get_connection",
            return_value=FakeConnection(cursor),
        ):
            result = get_order_status(make_request())

        self.assertIsInstance(result, ErrorResponse)
        self.assertEqual(result.status, "error")
        self.assertNotIn("database unavailable", result.message)


if __name__ == "__main__":
    unittest.main()
