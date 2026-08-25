import unittest
from decimal import Decimal
from unittest.mock import patch

from app.schemas.common import ErrorResponse
from app.schemas.tool_schema import CustomerProfileRequest, CustomerProfileResponse
from app.tools.customer_tool import get_customer_profile


class FakeCursor:
    def __init__(self, row=None, error=None):
        self.row = row
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

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self, **_):
        return self.fake_cursor


def make_request(customer_id="CUST_A"):
    return CustomerProfileRequest(
        customer_id=customer_id,
        start_month="2026-01",
        end_month="2026-06",
    )


class CustomerProfileTests(unittest.TestCase):
    def test_returns_customer_profile_with_sales_and_orders(self):
        cursor = FakeCursor(
            {
                "customer_id": "CUST_A",
                "customer_name": "Aster Mobile Systems",
                "segment": "Mobile",
                "region": "North America",
                "tier": "Tier 1",
                "main_application": "Premium smartphone display",
                "sales_qty": 1200,
                "sales_revenue": Decimal("1450000.00"),
                "order_count": 8,
                "order_qty": 1500,
                "delayed_order_count": 1,
            }
        )
        with patch(
            "app.tools.customer_tool.get_connection",
            return_value=FakeConnection(cursor),
        ):
            result = get_customer_profile(make_request())

        self.assertIsInstance(result, CustomerProfileResponse)
        self.assertEqual(result.tool_name, "get_customer_profile")
        self.assertEqual(result.data[0].customer_id, "CUST_A")
        self.assertEqual(result.data[0].sales_qty, 1200)
        self.assertEqual(result.data[0].order_count, 8)
        self.assertTrue(result.risk_signals)
        self.assertIn("public.dim_customer", cursor.query)
        self.assertIn("public.fact_sales", cursor.query)
        self.assertIn("public.fact_orders", cursor.query)
        self.assertEqual(cursor.params["customer_id"], "CUST_A")

    def test_returns_success_when_customer_does_not_exist(self):
        cursor = FakeCursor(None)
        with patch(
            "app.tools.customer_tool.get_connection",
            return_value=FakeConnection(cursor),
        ):
            result = get_customer_profile(make_request("UNKNOWN"))

        self.assertIsInstance(result, CustomerProfileResponse)
        self.assertEqual(result.status, "success")
        self.assertEqual(result.data, [])
        self.assertIn("찾을 수 없습니다", result.summary)

    def test_returns_error_response_on_database_error(self):
        cursor = FakeCursor(error=RuntimeError("database unavailable"))
        with patch(
            "app.tools.customer_tool.get_connection",
            return_value=FakeConnection(cursor),
        ):
            result = get_customer_profile(make_request())

        self.assertIsInstance(result, ErrorResponse)
        self.assertEqual(result.status, "error")
        self.assertNotIn("database unavailable", result.message)

    def test_rejects_invalid_month_range(self):
        with self.assertRaises(ValueError):
            CustomerProfileRequest(
                customer_id="CUST_A",
                start_month="2026-07",
                end_month="2026-06",
            )


if __name__ == "__main__":
    unittest.main()
