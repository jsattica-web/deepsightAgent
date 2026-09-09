import logging
from datetime import date
from typing import Any

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


def _chart_data(groups: dict, months: list[str]) -> dict[str, Any]:
    """고객사·제품군마다 재고 지표 4개를 차트에 표시한다."""
    series = []
    for group in groups.values():
        label = group["label"]
        points = group["points"]
        ending_stock = []
        safety_stock = []
        sales_qty = []
        production_qty = []

        for month in months:
            matched = None
            for point in points:
                if point.month == month:
                    matched = point
                    break

            # 해당 월의 데이터가 없으면 0 대신 빈 값으로 표시한다.
            ending_stock.append(matched.ending_stock if matched else None)
            safety_stock.append(matched.safety_stock if matched else None)
            sales_qty.append(matched.sales_qty if matched else None)
            production_qty.append(matched.production_qty if matched else None)

        series.append({"name": f"{label} / ending_stock", "data": ending_stock})
        series.append({"name": f"{label} / safety_stock", "data": safety_stock})
        series.append({"name": f"{label} / sales_qty", "data": sales_qty})
        series.append({"name": f"{label} / production_qty", "data": production_qty})

    return {"type": "line", "x": months, "series": series}


def get_inventory_risk(
    request: InventoryRiskRequest,
) -> InventoryRiskResponse | ErrorResponse:
    # 1. 조회 기간과 필터를 준비한다.
    start_month = _parse_month(request.start_month)
    end_month = _parse_month(request.end_month)
    product_filter = ""
    customer_filter = ""
    params: dict[str, object] = {
        "start_month": start_month,
        "end_month": end_month,
    }
    if request.product_group:
        product_filter = "and p.product_group = %(product_group)s"
        params["product_group"] = request.product_group

    if request.customer_id:
        customer_filter = "and i.customer_id = %(customer_id)s"
        params["customer_id"] = request.customer_id

    product_select = ""
    product_group = ""
    if request.group_by_product_group:
        product_select = "p.product_group,"
        product_group = ", p.product_group"

    customer_select = ""
    customer_group = ""
    if request.group_by_customer:
        customer_select = "i.customer_id, c.customer_name,"
        customer_group = ", i.customer_id, c.customer_name"

    query = f"""
        select
            to_char(i.inventory_month, 'YYYY-MM') as month,
            {product_select}
            {customer_select}
            sum(i.ending_stock)::bigint as ending_stock,
            sum(i.safety_stock)::bigint as safety_stock,
            sum(i.production_qty)::bigint as production_qty,
            sum(i.sales_qty)::bigint as sales_qty
        from public.fact_inventory as i
        join public.dim_product as p on p.product_id = i.product_id
        left join public.dim_customer as c on c.customer_id = i.customer_id
        where i.inventory_month >= %(start_month)s
          and i.inventory_month <= %(end_month)s
          {product_filter}
          {customer_filter}
        group by i.inventory_month{product_group}{customer_group}
        order by i.inventory_month{product_group}{customer_group}
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

    # 3. 조회 결과를 응답 데이터로 변환한다.
    points = [
        InventoryTrendPoint(
            month=row["month"],
            customer_id=row.get("customer_id"),
            customer_name=row.get("customer_name"),
            product_group=row.get("product_group"),
            ending_stock=row["ending_stock"],
            safety_stock=row["safety_stock"],
            production_qty=row["production_qty"],
            sales_qty=row["sales_qty"],
        )
        for row in rows
    ]

    # 고객사·제품군이 다른 재고는 따로 분석한다.
    groups = {}
    for point in points:
        key = (point.customer_id, point.product_group)
        if key not in groups:
            label = point.product_group or "전체 제품군"
            if not point.product_group and request.product_group:
                label = request.product_group
            if request.group_by_customer:
                customer = point.customer_name or point.customer_id or "고객 미지정"
                label = f"{customer} / {label}"
            groups[key] = {"label": label, "points": []}
        groups[key]["points"].append(point)

    # 4. 각 그룹의 재고 위험을 분석한다.
    summaries: list[str] = []
    insights: list[str] = []
    risk_signals: list[InventoryRiskSignal] = []
    actions: list[str] = []

    if not points:
        summary = "조건에 해당하는 재고 데이터가 없습니다."
        actions.append("조회 기간, 고객사 또는 제품군 조건을 확인하세요.")
    else:
        for group in groups.values():
            result = _analyze_group(
                group["points"], request.end_month, group["label"]
            )
            summaries.append(result["summary"])
            insights.extend(result["insights"])
            risk_signals.extend(result["risk_signals"])
            for action in result["actions"]:
                if action not in actions:
                    actions.append(action)
        summary = " ".join(summaries)

    # 5. 분석 결과와 차트를 반환한다.
    months = sorted({point.month for point in points})
    return InventoryRiskResponse(
        tool_name="get_inventory_risk",
        status="success",
        summary=summary,
        data=points,
        insights=insights,
        risk_signals=risk_signals,
        chart_data=_chart_data(groups, months),
        actions=actions,
    )


def _analyze_group(
    points: list[InventoryTrendPoint], end_month: str, label: str,
) -> dict[str, Any]:
    """한 고객사·제품군의 최근 3개월 재고 위험을 분석한다."""
    if points[-1].month != end_month:
        return {
            "summary": f"{label}의 {end_month} 재고 데이터가 없습니다.",
            "insights": [],
            "risk_signals": [],
            "actions": ["조회 종료 월의 재고 데이터를 확인하세요."],
        }

    cutoff = _months_before(_parse_month(end_month), 2)
    points = [point for point in points if _parse_month(point.month) >= cutoff]
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

    # 조회 결과는 월순으로 정렬되어 있고, 최근 3개월만 남아 있다.
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
        InventoryRiskSignal(
            customer_id=latest.customer_id,
            customer_name=latest.customer_name,
            product_group=latest.product_group,
            month=end_month,
            level=risk_level,
            type=signal_type,
            message=message,
        )
        for signal_type, message in conditions
    ]
    insights = [
        f"최근 {len(points)}개월 평균 판매량은 {average_sales_qty:,.1f}개입니다.",
        (
            f"{end_month} 기말재고는 {latest.ending_stock:,}개, "
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
        actions.append(f"{label} 안전재고 확보 계획을 검토하세요.")
    if "OVER_STOCK" in signal_types or "INVENTORY_GROWTH" in signal_types:
        actions.append(f"{label} 생산 계획 조정 여부를 검토하세요.")
    if "SALES_SLOWDOWN" in signal_types:
        actions.append("판매 둔화 원인과 수요 전망을 점검하세요.")
    if not actions:
        actions.append("현재 재고 수준을 지속적으로 모니터링하세요.")

    if "OVER_STOCK" in signal_types:
        summary = f"{label} 제품군은 과잉재고 가능성이 있습니다."
    elif "BELOW_SAFETY_STOCK" in signal_types:
        summary = f"{label} 제품군은 안전재고 미달 상태입니다."
    elif conditions:
        summary = f"{label} 제품군에서 재고 위험 신호가 감지됐습니다."
    else:
        summary = f"{label} 제품군의 재고 위험은 낮습니다."

    return {
        "summary": summary,
        "insights": [f"{label}: {insight}" for insight in insights],
        "risk_signals": risk_signals,
        "actions": actions,
    }
