import logging
from datetime import date
from decimal import Decimal

from psycopg2.extras import RealDictCursor

from app.db import get_connection
from app.schemas.common import ErrorResponse
from app.schemas.tool_schema import (
    CustomerProfilePoint,
    CustomerProfileRequest,
    CustomerProfileResponse,
)

logger = logging.getLogger(__name__)


def _parse_month(value: str) -> date:
    year, month = map(int, value.split("-"))
    return date(year, month, 1)


def _next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _as_float(value: Decimal | int | float | None) -> float:
    if value is None:
        return 0.0
    return round(float(value), 2)


def get_customer_profile(
    request: CustomerProfileRequest,
) -> CustomerProfileResponse | ErrorResponse:
    """Return customer master information with sales/order summary for a period."""

    start_date = _parse_month(request.start_month)
    end_exclusive = _next_month(_parse_month(request.end_month))
    params = {
        "customer_id": request.customer_id,
        "start_date": start_date,
        "end_exclusive": end_exclusive,
    }

    query = """
        select
            c.customer_id,
            c.customer_name,
            c.segment,
            c.region,
            c.tier,
            c.main_application,
            coalesce(s.sales_qty, 0)::bigint as sales_qty,
            coalesce(s.sales_revenue, 0)::numeric(20, 2) as sales_revenue,
            coalesce(o.order_count, 0)::bigint as order_count,
            coalesce(o.order_qty, 0)::bigint as order_qty,
            coalesce(o.delayed_order_count, 0)::bigint as delayed_order_count
        from public.dim_customer as c
        left join (
            select
                customer_id,
                sum(qty)::bigint as sales_qty,
                sum(revenue)::numeric(20, 2) as sales_revenue
            from public.fact_sales
            where sales_month >= %(start_date)s
              and sales_month < %(end_exclusive)s
              and customer_id = %(customer_id)s
            group by customer_id
        ) as s on s.customer_id = c.customer_id
        left join (
            select
                customer_id,
                count(*)::bigint as order_count,
                sum(order_qty)::bigint as order_qty,
                count(*) filter (where status = 'DELAYED')::bigint as delayed_order_count
            from public.fact_orders
            where order_date >= %(start_date)s
              and order_date < %(end_exclusive)s
              and customer_id = %(customer_id)s
            group by customer_id
        ) as o on o.customer_id = c.customer_id
        where c.customer_id = %(customer_id)s
    """

    try:
        with get_connection() as conn, conn.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()
    except Exception:
        logger.exception("Failed to execute get_customer_profile")
        return ErrorResponse(
            status="error",
            message="고객사 프로필 데이터를 조회하는 중 오류가 발생했습니다.",
        )

    if not row:
        return CustomerProfileResponse(
            tool_name="get_customer_profile",
            status="success",
            summary=f"{request.customer_id}에 해당하는 Synthetic 고객사를 찾을 수 없습니다.",
            data=[],
            insights=[],
            risk_signals=["고객사 ID가 고객 마스터에 존재하지 않습니다."],
            chart_data={},
            actions=["customer_id를 확인한 뒤 다시 조회하세요."],
        )

    point = CustomerProfilePoint(
        customer_id=row["customer_id"],
        customer_name=row["customer_name"],
        segment=row["segment"],
        region=row["region"],
        tier=row["tier"],
        main_application=row["main_application"],
        sales_qty=int(row["sales_qty"]),
        sales_revenue=_as_float(row["sales_revenue"]),
        order_count=int(row["order_count"]),
        order_qty=int(row["order_qty"]),
        delayed_order_count=int(row["delayed_order_count"]),
    )

    insights = [
        f"{point.customer_name}은(는) {point.region} 지역의 {point.tier} {point.segment} 고객사입니다.",
        f"조회 기간 판매량은 {point.sales_qty:,}, 매출은 {point.sales_revenue:,.2f}입니다.",
        f"수주 {point.order_count:,}건, 수주량 {point.order_qty:,}이 집계되었습니다.",
    ]
    risk_signals: list[str] = []
    actions: list[str] = []

    if point.delayed_order_count > 0:
        risk_signals.append(
            f"지연 수주가 {point.delayed_order_count}건 존재합니다."
        )
        actions.append("지연 수주의 납기 일정과 고객 커뮤니케이션 계획을 확인하세요.")
    else:
        actions.append("판매 및 수주 추이를 지속적으로 모니터링하세요.")

    if point.sales_qty == 0 and point.order_count == 0:
        risk_signals.append("조회 기간 내 판매 및 수주 실적이 없습니다.")
        actions.append("고객 접점과 신규 수주 가능성을 점검하세요.")

    summary = (
        f"{point.customer_name} 고객 프로필과 "
        f"{request.start_month}~{request.end_month} 판매·수주 요약입니다."
    )

    return CustomerProfileResponse(
        tool_name="get_customer_profile",
        status="success",
        summary=summary,
        data=[point],
        insights=insights,
        risk_signals=risk_signals,
        chart_data={
            "type": "bar",
            "categories": ["Sales Qty", "Order Qty"],
            "series": [
                {
                    "name": point.customer_name,
                    "data": [point.sales_qty, point.order_qty],
                }
            ],
        },
        actions=actions,
    )
