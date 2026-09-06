import json
import logging
from datetime import date
from decimal import Decimal
from typing import Any

from psycopg2.extras import RealDictCursor

from app.db import get_connection
from app.schemas.common import ErrorResponse
from app.schemas.tool_schema import SalesTrendPoint, SalesTrendRequest, SalesTrendResponse

logger = logging.getLogger(__name__)


def _parse_month(value: str) -> date:
    year, month = map(int, value.split("-"))
    return date(year, month, 1)


def _next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _month_count(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month + 1


def _as_float(value: Decimal | int | float) -> float:
    return round(float(value), 2)


def _change_rate(first: int | float, last: int | float) -> float | None:
    if first == 0:
        return None
    return ((last - first) / first) * 100


def _asp_direction(change_rate: float | None) -> str:
    if change_rate is None:
        return "첫 달 ASP가 0이어서 변화율을 계산할 수 없습니다."
    if change_rate >= 5:
        return "ASP는 상승했습니다."
    if change_rate > 1:
        return "ASP는 소폭 상승했습니다."
    if change_rate <= -5:
        return "ASP는 하락했습니다."
    if change_rate < -1:
        return "ASP는 소폭 하락했습니다."
    return "ASP는 보합 수준입니다."


def _chart_data(points: list[SalesTrendPoint], group_by_customer: bool) -> dict[str, Any]:
    """화면 차트에 맞는 데이터를 만든다.

    고객별 조회에서는 고객마다 매출 시리즈를 하나씩 만든다. 월별 전체 조회에서는
    기존처럼 판매량, 매출, ASP를 함께 보여준다.
    """
    if not group_by_customer:
        return {
            "type": "line",
            "x": [point.month for point in points],
            "series": [
                {"name": "qty", "data": [point.qty for point in points]},
                {"name": "revenue", "data": [point.revenue for point in points]},
                {"name": "asp", "data": [point.asp for point in points]},
            ],
        }

    months = sorted({point.month for point in points})
    customers = []
    for point in points:
        name = point.customer_name or point.customer_id or "Unknown"
        if name not in customers:
            customers.append(name)

    series = []
    for customer in customers:
        values = []
        for month in months:
            matched = next(
                (
                    point
                    for point in points
                    if point.month == month
                    and (point.customer_name or point.customer_id or "Unknown") == customer
                ),
                None,
            )
            values.append(matched.revenue if matched else 0)
        series.append({"name": customer, "data": values})

    return {"type": "line", "x": months, "series": series}


def get_sales_trend(
    request: SalesTrendRequest,
) -> SalesTrendResponse | ErrorResponse:
    start_date = _parse_month(request.start_month)
    end_date = _parse_month(request.end_month)
    customer_filter = ""
    params: dict[str, object] = {
        "start_date": start_date,
        "end_exclusive": _next_month(end_date),
        "product_group": request.product_group,
    }
    if request.customer_id:
        customer_filter = "and s.customer_id = %(customer_id)s"
        params["customer_id"] = request.customer_id

    # 고객별 요청이면 select/group/order에 고객 컬럼을 추가한다.
    # 문자열로 직접 조립하는 부분은 SQL 값이 아니라 고정된 SQL 조각만 사용한다.
    customer_select = ""
    customer_group = ""
    customer_order = ""
    if request.group_by_customer:
        customer_select = """
            c.customer_id,
            c.customer_name,
        """
        customer_group = ", c.customer_id, c.customer_name"
        customer_order = ", c.customer_name"

    query = f"""
        select
            to_char(s.sales_month, 'YYYY-MM') as month,
            {customer_select}
            sum(s.qty)::bigint as total_qty,
            sum(s.revenue)::numeric(20, 2) as total_revenue,
            case when sum(s.qty) = 0 then 0
                 else round(sum(s.revenue) / sum(s.qty), 2)
            end as avg_asp
        from public.fact_sales as s
        join public.dim_product as p on p.product_id = s.product_id
        join public.dim_customer as c on c.customer_id = s.customer_id
        where s.sales_month >= %(start_date)s
          and s.sales_month < %(end_exclusive)s
          and p.product_group = %(product_group)s
          {customer_filter}
        group by s.sales_month{customer_group}
        order by s.sales_month{customer_order}
    """

    try:
        with get_connection() as conn, conn.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
    except Exception:
        logger.exception("Failed to execute get_sales_trend")
        return ErrorResponse(
            status="error",
            message="판매 동향 데이터를 조회하는 중 오류가 발생했습니다.",
        )

    points = [
        SalesTrendPoint(
            month=row["month"],
            customer_id=row.get("customer_id"),
            customer_name=row.get("customer_name"),
            qty=row["total_qty"],
            revenue=_as_float(row["total_revenue"]),
            asp=_as_float(row["avg_asp"]),
        )
        for row in rows
    ]

    months = _month_count(start_date, end_date)
    insights: list[str] = []
    risk_signals: list[str] = []
    actions: list[str] = []

    if not points:
        summary = f"{request.product_group} 조건에 해당하는 판매 데이터가 없습니다."
        actions.append("조회 기간, 제품군 또는 고객사 조건을 확인하세요.")
    elif request.group_by_customer:
        customer_count = len({point.customer_id for point in points if point.customer_id})
        total_revenue = sum(point.revenue for point in points)
        top_customer = max(points, key=lambda point: point.revenue)
        summary = (
            f"최근 {months}개월 {request.product_group} 판매 매출을 "
            f"{customer_count}개 고객 기준으로 월별 집계했습니다."
        )
        insights.append(f"조회 기간 총 매출은 {total_revenue:,.2f}입니다.")
        insights.append(
            f"단일 월 기준 최고 매출은 {top_customer.month} "
            f"{top_customer.customer_name or top_customer.customer_id}의 {top_customer.revenue:,.2f}입니다."
        )
        actions.append("매출 비중이 큰 고객의 월별 증감 원인을 우선 확인하세요.")
        actions.append("감소 고객은 수주 현황과 함께 확인해 이탈 가능성을 점검하세요.")
    else:
        first_qty = points[0].qty
        last_qty = points[-1].qty
        qty_change_rate = _change_rate(first_qty, last_qty)
        asp_change_rate = _change_rate(points[0].asp, points[-1].asp)

        if qty_change_rate is None:
            direction = "판단 불가"
            insights.append("첫 달 판매량이 0이어서 판매량 증감률을 계산할 수 없습니다.")
            actions.append("첫 달 판매 데이터와 집계 기준을 확인하세요.")
        elif qty_change_rate >= 5:
            direction = "증가"
            insights.append(f"{months}개월간 판매량이 {qty_change_rate:.1f}% 증가했습니다.")
            actions.append("수요 증가에 맞춰 생산 및 재고 계획을 검토하세요.")
            actions.append("판매 증가 고객사의 추가 수주 가능성을 확인하세요.")
        elif qty_change_rate <= -5:
            direction = "감소"
            insights.append(f"{months}개월간 판매량이 {abs(qty_change_rate):.1f}% 감소했습니다.")
            risk_signals.append(f"기간 내 판매량이 {abs(qty_change_rate):.1f}% 감소했습니다.")
            actions.append("수요 감소 원인과 고객별 주문 변화를 점검하세요.")
        else:
            direction = "보합"
            insights.append(f"{months}개월간 판매량 변동은 {qty_change_rate:+.1f}%로 보합 수준입니다.")
            actions.append("현재 판매 흐름을 지속적으로 모니터링하세요.")

        asp_insight = _asp_direction(asp_change_rate)
        if asp_change_rate is not None:
            asp_insight = f"{asp_insight} ({asp_change_rate:+.1f}%)"
        insights.append(asp_insight)
        if asp_change_rate is not None and asp_change_rate <= -5:
            risk_signals.append(f"ASP가 기간 내 {abs(asp_change_rate):.1f}% 하락했습니다.")
        summary = f"최근 {months}개월 {request.product_group} 판매량은 {direction} 추세입니다."

    return SalesTrendResponse(
        tool_name="get_sales_trend",
        status="success",
        summary=summary,
        data=points,
        insights=insights,
        risk_signals=risk_signals,
        chart_data=_chart_data(points, request.group_by_customer),
        actions=actions,
    )


# if __name__ == "__main__":
#     example_request = SalesTrendRequest(
#         start_month="2026-01",
#         end_month="2026-06",
#         product_group="Mobile OLED",
#         customer_id=None,
#     )
#     example_response = get_sales_trend(example_request)
#     print(json.dumps(example_response.model_dump(mode="json"), ensure_ascii=False, indent=2))
