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
        inventory_month="2026-06",
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
