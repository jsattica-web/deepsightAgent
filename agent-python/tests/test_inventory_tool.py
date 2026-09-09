import unittest
from unittest.mock import patch

from app.schemas.common import ErrorResponse
from app.schemas.tool_schema import InventoryRiskRequest, InventoryRiskResponse
from app.tools.inventory_tool import calculate_risk_level, get_inventory_risk


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


def make_request(product_group="TV OLED"):
    return InventoryRiskRequest(
        start_month="2026-04",
        end_month="2026-06",
        product_group=product_group,
    )


class InventoryRiskTests(unittest.TestCase):
    def test_calculates_risk_levels(self):
        self.assertEqual(calculate_risk_level(0), "LOW")
        self.assertEqual(calculate_risk_level(1), "MEDIUM")
        self.assertEqual(calculate_risk_level(2), "HIGH")
        self.assertEqual(calculate_risk_level(4), "HIGH")

    def test_returns_high_risk_for_multiple_conditions(self):
        cursor = FakeCursor(
            [
                {
                    "month": "2026-04",
                    "ending_stock": 350,
                    "safety_stock": 200,
                    "production_qty": 160,
                    "sales_qty": 130,
                },
                {
                    "month": "2026-05",
                    "ending_stock": 410,
                    "safety_stock": 200,
                    "production_qty": 150,
                    "sales_qty": 110,
                },
                {
                    "month": "2026-06",
                    "ending_stock": 500,
                    "safety_stock": 200,
                    "production_qty": 140,
                    "sales_qty": 90,
                },
            ]
        )
        with patch(
            "app.tools.inventory_tool.get_connection",
            return_value=FakeConnection(cursor),
        ):
            result = get_inventory_risk(make_request())

        self.assertIsInstance(result, InventoryRiskResponse)
        self.assertTrue(result.risk_signals)
        self.assertTrue(all(signal.level == "HIGH" for signal in result.risk_signals))
        signal_types = {signal.type for signal in result.risk_signals}
        self.assertIn("OVER_STOCK", signal_types)
        self.assertIn("SALES_SLOWDOWN", signal_types)
        self.assertIn("INVENTORY_GROWTH", signal_types)
        self.assertEqual(result.chart_data["type"], "line")
        self.assertIn("%(product_group)s", cursor.query)
        self.assertEqual(cursor.params["product_group"], "TV OLED")

    def test_returns_medium_risk_for_safety_stock_shortage(self):
        cursor = FakeCursor(
            [
                {
                    "month": "2026-06",
                    "ending_stock": 80,
                    "safety_stock": 100,
                    "production_qty": 50,
                    "sales_qty": 100,
                }
            ]
        )
        with patch(
            "app.tools.inventory_tool.get_connection",
            return_value=FakeConnection(cursor),
        ):
            result = get_inventory_risk(make_request())

        self.assertIsInstance(result, InventoryRiskResponse)
        self.assertEqual(len(result.risk_signals), 1)
        self.assertEqual(result.risk_signals[0].level, "MEDIUM")
        self.assertEqual(result.risk_signals[0].type, "BELOW_SAFETY_STOCK")

    def test_returns_success_when_no_data_exists(self):
        cursor = FakeCursor([])
        with patch(
            "app.tools.inventory_tool.get_connection",
            return_value=FakeConnection(cursor),
        ):
            result = get_inventory_risk(make_request())

        self.assertIsInstance(result, InventoryRiskResponse)
        self.assertEqual(result.status, "success")
        self.assertEqual(result.data, [])
        self.assertIn("데이터가 없습니다", result.summary)

    def test_filters_and_groups_customers_and_products_independently(self):
        rows = [dict(month="2026-06", customer_id=customer, customer_name=customer,
                     product_group=product, ending_stock=stock, safety_stock=100,
                     production_qty=50, sales_qty=100)
                for customer, product, stock in [("CUST_A", "TV OLED", 80),
                                                  ("CUST_B", "TV OLED", 150),
                                                  ("CUST_A", "IT OLED", 150)]]
        cursor = FakeCursor(rows)
        request = InventoryRiskRequest(start_month="2026-04", end_month="2026-06",
            product_group=None, customer_id=None,
            group_by_customer=True, group_by_product_group=True)
        with patch("app.tools.inventory_tool.get_connection", return_value=FakeConnection(cursor)):
            result = get_inventory_risk(request)
        self.assertNotIn("customer_id", cursor.params)
        self.assertNotIn("CUST_A", cursor.query)
        self.assertIn("group by i.inventory_month, p.product_group, i.customer_id, c.customer_name", cursor.query)
        self.assertEqual(len(result.data), 3)
        self.assertEqual(len(result.risk_signals), 1)
        self.assertEqual(result.risk_signals[0].customer_id, "CUST_A")
        self.assertEqual(result.risk_signals[0].product_group, "TV OLED")
        self.assertEqual(len(result.chart_data["series"]), 12)

    def test_aggregate_without_customer_or_product_group(self):
        cursor = FakeCursor([])
        request = make_request().model_copy(update={"group_by_product_group": False})
        with patch("app.tools.inventory_tool.get_connection", return_value=FakeConnection(cursor)):
            get_inventory_risk(request)
        self.assertNotIn("customer_id", cursor.params)
        self.assertIn("group by i.inventory_month\n", cursor.query)
        self.assertIn("left join public.dim_customer", cursor.query)

    def test_rejects_invalid_customer_lists(self):
        from pydantic import ValidationError
        for customers in ([], [""], ["CUST_A", "CUST_A"]):
            with self.subTest(customers=customers), self.assertRaises(ValidationError):
                InventoryRiskRequest(start_month="2026-04", end_month="2026-06",
                    product_group="TV OLED", customer_id=customers)

    def test_missing_month_does_not_trigger_continuous_trend(self):
        cursor = FakeCursor([dict(month=month, ending_stock=100, safety_stock=50,
            production_qty=200, sales_qty=sales) for month, sales in
            [("2026-03", 130), ("2026-05", 110), ("2026-06", 90)]])
        request = make_request().model_copy(update={"start_month": "2026-03"})
        with patch("app.tools.inventory_tool.get_connection", return_value=FakeConnection(cursor)):
            result = get_inventory_risk(request)
        self.assertEqual(result.risk_signals, [])

    def test_no_product_filter_when_null_or_omitted(self):
        for product_options in ({}, {"product_group": None}):
            with self.subTest(product_options=product_options):
                request = InventoryRiskRequest(
                    start_month="2026-04", end_month="2026-06",
                    customer_id="CUST_A", group_by_customer=True,
                    group_by_product_group=False, **product_options,
                )
                cursor = FakeCursor([{
                    "month": "2026-06", "customer_id": "CUST_A",
                    "ending_stock": 80, "safety_stock": 100,
                    "production_qty": 50, "sales_qty": 100,
                }])
                with patch("app.tools.inventory_tool.get_connection",
                           return_value=FakeConnection(cursor)):
                    result = get_inventory_risk(request)
                self.assertIsNone(request.product_group)
                self.assertNotIn("%(product_group)s", cursor.query)
                self.assertNotIn("product_group", cursor.params)
                self.assertEqual(cursor.params["customer_id"], "CUST_A")
                self.assertIn("i.customer_id = %(customer_id)s", cursor.query)
                self.assertIn("전체 제품군", result.summary)
                self.assertEqual(result.data[0].customer_id, "CUST_A")

    def test_returns_error_response_on_database_error(self):
        cursor = FakeCursor(error=RuntimeError("database unavailable"))
        with patch(
            "app.tools.inventory_tool.get_connection",
            return_value=FakeConnection(cursor),
        ):
            result = get_inventory_risk(make_request())

        self.assertIsInstance(result, ErrorResponse)
        self.assertEqual(result.status, "error")
        self.assertNotIn("database unavailable", result.message)


if __name__ == "__main__":
    unittest.main()
