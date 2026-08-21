import json
import logging
from datetime import date

from psycopg2.extras import RealDictCursor

from app.db import get_connection
from app.schemas.common import ErrorResponse
from app.schemas.tool_schema import (
    InventoryRiskRequest,
    InventoryRiskResponse,
    InventoryRiskSignal,
    InventoryTrendPoint,
)

logger = logging.getLogger(__name__)


def _parse_month(value: str) -> date:
    year, month = map(int, value.split("-"))
    return date(year, month, 1)


def _months_before(value: date, count: int) -> date:
    month_index = value.year * 12 + value.month - 1 - count
    return date(month_index // 12, month_index % 12 + 1, 1)


def calculate_risk_level(condition_count: int) -> str:
    if condition_count >= 2:
        return "HIGH"
    if condition_count == 1:
        return "MEDIUM"
    return "LOW"


def get_inventory_risk(
    request: InventoryRiskRequest,
) -> InventoryRiskResponse | ErrorResponse:
    inventory_month = _parse_month(request.inventory_month)
    params: dict[str, object] = {
        "start_month": _months_before(inventory_month, 2),
        "inventory_month": inventory_month,
        "product_group": request.product_group,
    }
    query = """
        select
            to_char(i.inventory_month, 'YYYY-MM') as month,
            sum(i.ending_stock)::bigint as ending_stock,
            sum(i.safety_stock)::bigint as safety_stock,
            sum(i.production_qty)::bigint as production_qty,
            sum(i.sales_qty)::bigint as sales_qty
        from public.fact_inventory as i
        join public.dim_product as p on p.product_id = i.product_id
        where i.inventory_month >= %(start_month)s
          and i.inventory_month <= %(inventory_month)s
          and p.product_group = %(product_group)s
        group by i.inventory_month
        order by i.inventory_month
    """

    try:
        with get_connection() as conn, conn.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
    except Exception:
        logger.exception("Failed to execute get_inventory_risk")
        return ErrorResponse(
            status="error",
            message="재고 리스크 데이터를 조회하는 중 오류가 발생했습니다.",
        )

    points = [
        InventoryTrendPoint(
            month=row["month"],
            ending_stock=row["ending_stock"],
            safety_stock=row["safety_stock"],
            production_qty=row["production_qty"],
            sales_qty=row["sales_qty"],
        )
        for row in rows
    ]

    if not points or points[-1].month != request.inventory_month:
        return InventoryRiskResponse(
            tool_name="get_inventory_risk",
            status="success",
            summary=f"{request.product_group} 조건에 해당하는 재고 데이터가 없습니다.",
            data=points,
            insights=[],
            risk_signals=[],
            chart_data={
                "type": "line",
                "x": [point.month for point in points],
                "series": [],
            },
            actions=["조회 월 또는 제품군 조건을 확인하세요."],
        )

    latest = points[-1]
    average_sales_qty = sum(point.sales_qty for point in points) / len(points)
    conditions: list[tuple[str, str]] = []

    if latest.ending_stock < latest.safety_stock:
        conditions.append(
            (
                "BELOW_SAFETY_STOCK",
                "기말재고가 안전재고보다 낮습니다.",
            )
        )
    if latest.ending_stock > average_sales_qty * 2:
        conditions.append(
            (
                "OVER_STOCK",
                "기말재고가 최근 3개월 평균 판매량의 2배를 초과했습니다.",
            )
        )

    has_three_months = len(points) == 3
    if has_three_months and points[0].sales_qty > points[1].sales_qty > points[2].sales_qty:
        conditions.append(
            (
                "SALES_SLOWDOWN",
                "판매량이 2개월 연속 감소했습니다.",
            )
        )
    if has_three_months and all(
        point.production_qty > point.sales_qty for point in points
    ):
        conditions.append(
            (
                "INVENTORY_GROWTH",
                "최근 3개월 동안 생산량이 판매량보다 계속 높았습니다.",
            )
        )

    risk_level = calculate_risk_level(len(conditions))
    risk_signals = [
        InventoryRiskSignal(level=risk_level, type=signal_type, message=message)
        for signal_type, message in conditions
    ]
    insights = [
        f"최근 {len(points)}개월 평균 판매량은 {average_sales_qty:,.1f}개입니다.",
        (
            f"{request.inventory_month} 기말재고는 {latest.ending_stock:,}개, "
            f"안전재고는 {latest.safety_stock:,}개입니다."
        ),
        f"재고 위험 수준은 {risk_level}입니다.",
    ]
    if not has_three_months:
        insights.append(
            "최근 3개월 데이터가 모두 없어 연속 추세 조건은 평가하지 않았습니다."
        )

    signal_types = {signal_type for signal_type, _ in conditions}
    actions: list[str] = []
    if "BELOW_SAFETY_STOCK" in signal_types:
        actions.append(f"{request.product_group} 안전재고 확보 계획을 검토하세요.")
    if "OVER_STOCK" in signal_types or "INVENTORY_GROWTH" in signal_types:
        actions.append(f"{request.product_group} 생산 계획 조정 여부를 검토하세요.")
    if "SALES_SLOWDOWN" in signal_types:
        actions.append("판매 둔화 원인과 수요 전망을 점검하세요.")
    if not actions:
        actions.append("현재 재고 수준을 지속적으로 모니터링하세요.")

    if "OVER_STOCK" in signal_types:
        summary = f"{request.product_group} 제품군은 과잉재고 가능성이 있습니다."
    elif "BELOW_SAFETY_STOCK" in signal_types:
        summary = f"{request.product_group} 제품군은 안전재고 미달 상태입니다."
    elif conditions:
        summary = f"{request.product_group} 제품군에서 재고 위험 신호가 감지됐습니다."
    else:
        summary = f"{request.product_group} 제품군의 재고 위험은 낮습니다."

    return InventoryRiskResponse(
        tool_name="get_inventory_risk",
        status="success",
        summary=summary,
        data=points,
        insights=insights,
        risk_signals=risk_signals,
        chart_data={
            "type": "line",
            "x": [point.month for point in points],
            "series": [
                {
                    "name": "ending_stock",
                    "data": [point.ending_stock for point in points],
                },
                {
                    "name": "safety_stock",
                    "data": [point.safety_stock for point in points],
                },
                {
                    "name": "sales_qty",
                    "data": [point.sales_qty for point in points],
                },
                {
                    "name": "production_qty",
                    "data": [point.production_qty for point in points],
                },
            ],
        },
        actions=actions,
    )


if __name__ == "__main__":
    sample_request = InventoryRiskRequest(
        inventory_month="2026-06",
        product_group="TV OLED",
    )
    sample_response = get_inventory_risk(sample_request)
    print(
        json.dumps(
            sample_response.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
    )
