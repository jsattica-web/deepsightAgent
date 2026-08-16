import json
import logging
from datetime import date
from decimal import Decimal

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

    query = f"""
        select
            to_char(s.sales_month, 'YYYY-MM') as month,
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
        group by s.sales_month
        order by s.sales_month
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
        chart_data={
            "type": "line",
            "x": [point.month for point in points],
            "series": [
                {"name": "qty", "data": [point.qty for point in points]},
                {"name": "revenue", "data": [point.revenue for point in points]},
                {"name": "asp", "data": [point.asp for point in points]},
            ],
        },
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
