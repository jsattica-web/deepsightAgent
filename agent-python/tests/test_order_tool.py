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

    def test_optional_filters_and_grouping_combinations(self):
        for customer_grouped in (False, True):
            for product_grouped in (False, True):
                with self.subTest(customer=customer_grouped, product=product_grouped):
                    request = OrderStatusRequest(
                        start_date="2026-01-01", end_date="2026-06-30",
                        group_by_customer=customer_grouped,
                        group_by_product_group=product_grouped,
                    )
                    cursor = FakeCursor([])
                    with patch("app.tools.order_tool.get_connection",
                               return_value=FakeConnection(cursor)):
                        result = get_order_status(request)
                    self.assertEqual(result.status, "success")
                    for field in ("product_group", "customer_id", "status"):
                        self.assertNotIn(field, cursor.params)
                        self.assertNotIn("%(" + field + ")s", cursor.query)
                    group_sql = cursor.query.split("group by")[1].split("order by")[0]
                    self.assertEqual("c.customer_id" in group_sql, customer_grouped)
                    self.assertEqual("p.product_group" in group_sql, product_grouped)

    def test_customer_product_results_and_risks_stay_separate(self):
        rows = []
        for month, customer, product, delayed in [
            ("2026-01", "CUST_A", "TV OLED", 3),
            ("2026-02", "CUST_B", "TV OLED", 0),
            ("2026-02", "CUST_A", "IT OLED", 0),
        ]:
            rows.append(dict(month=month, customer_id=customer, customer_name=customer,
                product_group=product, total_orders=10, total_order_qty=100,
                confirmed_count=10-delayed, pending_count=0, delayed_count=delayed,
                cancelled_count=0, shipped_count=0, risk_order_count=delayed))
        cursor = FakeCursor(rows)
        request = OrderStatusRequest(start_date="2026-01-01", end_date="2026-06-30",
            product_group=None, customer_id=None, status=None,
            group_by_customer=True, group_by_product_group=True)
        with patch("app.tools.order_tool.get_connection", return_value=FakeConnection(cursor)):
            result = get_order_status(request)
        self.assertEqual(len(result.data), 3)
        self.assertEqual(result.chart_data["x"], ["2026-01", "2026-02"])
        self.assertEqual(len(result.chart_data["series"]), 12)
        delayed_series = result.chart_data["series"][2]
        self.assertEqual(delayed_series["data"], [3, 0])
        self.assertIn("CUST_A / TV OLED", delayed_series["name"])
        self.assertTrue(result.risk_signals)
        self.assertTrue(all("CUST_A / TV OLED" in item for item in result.risk_signals))

    def test_invalid_filters_are_rejected(self):
        from pydantic import ValidationError
        for invalid in ({"product_group": []}, {"customer_id": " "}, {"status": "INVALID"}):
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                OrderStatusRequest(start_date="2026-01-01", end_date="2026-06-30", **invalid)


if __name__ == "__main__":
    unittest.main()
