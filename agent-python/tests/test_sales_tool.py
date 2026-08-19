import unittest
from decimal import Decimal
from unittest.mock import patch

from app.schemas.common import ErrorResponse
from app.schemas.tool_schema import SalesTrendRequest, SalesTrendResponse
from app.tools.sales_tool import get_sales_trend


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


def make_request(customer_id=None):
    return SalesTrendRequest(
        start_month="2026-01",
        end_month="2026-06",
        product_group="Mobile OLED",
        customer_id=customer_id,
    )


class SalesTrendTests(unittest.TestCase):
    def test_returns_monthly_data_and_analysis(self):
        cursor = FakeCursor(
            [
                {
                    "month": "2026-01",
                    "total_qty": 100,
                    "total_revenue": Decimal("6000.00"),
                    "avg_asp": Decimal("60.00"),
                },
                {
                    "month": "2026-06",
                    "total_qty": 120,
                    "total_revenue": Decimal("6960.00"),
                    "avg_asp": Decimal("58.00"),
                },
            ]
        )
        with patch(
            "app.tools.sales_tool.get_connection",
            return_value=FakeConnection(cursor),
        ):
            result = get_sales_trend(make_request("CUST_A"))

        self.assertIsInstance(result, SalesTrendResponse)
        self.assertEqual(result.data[0].month, "2026-01")
        self.assertEqual(result.data[-1].qty, 120)
        self.assertEqual(result.chart_data["type"], "line")
        self.assertEqual(result.chart_data["series"][0]["data"], [100, 120])
        self.assertTrue(any("20.0% 증가" in item for item in result.insights))
        self.assertTrue(any("소폭 하락" in item for item in result.insights))
        self.assertIn("join public.dim_customer", cursor.query)
        self.assertEqual(cursor.params["customer_id"], "CUST_A")

    def test_returns_success_when_no_data_exists(self):
        cursor = FakeCursor([])
        with patch(
            "app.tools.sales_tool.get_connection",
            return_value=FakeConnection(cursor),
        ):
            result = get_sales_trend(make_request())

        self.assertIsInstance(result, SalesTrendResponse)
        self.assertEqual(result.status, "success")
        self.assertEqual(result.data, [])
        self.assertIn("데이터가 없습니다", result.summary)
        self.assertNotIn("customer_id", cursor.params)

    def test_returns_common_error_response_on_database_error(self):
        cursor = FakeCursor(error=RuntimeError("database unavailable"))
        with patch(
            "app.tools.sales_tool.get_connection",
            return_value=FakeConnection(cursor),
        ):
            result = get_sales_trend(make_request())

        self.assertIsInstance(result, ErrorResponse)
        self.assertEqual(result.status, "error")
        self.assertNotIn("database unavailable", result.message)


if __name__ == "__main__":
    unittest.main()
