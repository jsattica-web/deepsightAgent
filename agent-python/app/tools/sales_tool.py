from datetime import date
from decimal import Decimal

from psycopg2.extras import RealDictCursor

from app.db import db
from app.schemas.tool_schema import SalesTrendPoint, SalesTrendRequest, SalesTrendResponse


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


def get_sales_trend(request: SalesTrendRequest) -> SalesTrendResponse:
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
            s.sales_month,
            sum(s.qty)::bigint as total_qty,
            sum(s.revenue)::numeric(20, 2) as total_revenue,
            case when sum(s.qty) = 0 then 0
                 else round(sum(s.revenue) / sum(s.qty), 2)
            end as avg_asp
        from public.fact_sales as s
        join public.dim_product as p on p.product_id = s.product_id
        where s.sales_month >= %(start_date)s
          and s.sales_month < %(end_exclusive)s
          and p.product_group = %(product_group)s
          {customer_filter}
        group by s.sales_month
        order by s.sales_month
    """

    with db.connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    points = [
        SalesTrendPoint(
            sales_month=row["sales_month"],
            total_qty=row["total_qty"],
            total_revenue=_as_float(row["total_revenue"]),
            avg_asp=_as_float(row["avg_asp"]),
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
        first_qty = points[0].total_qty
        last_qty = points[-1].total_qty
        change_rate = 0.0 if first_qty == 0 else ((last_qty - first_qty) / first_qty) * 100
        if change_rate >= 5:
            direction = "증가"
            actions.append("수요 증가에 맞춰 생산 및 재고 계획을 검토하세요.")
        elif change_rate <= -5:
            direction = "감소"
            risk_signals.append(f"기간 내 판매량이 {abs(change_rate):.1f}% 감소했습니다.")
            actions.append("수요 감소 원인과 고객별 주문 변화를 점검하세요.")
        else:
            direction = "보합"
            actions.append("현재 판매 흐름을 지속적으로 모니터링하세요.")
        summary = f"최근 {months}개월 {request.product_group} 판매량은 {direction} 추세입니다."
        insights.append(
            f"첫 달 {first_qty:,}개에서 마지막 달 {last_qty:,}개로 {change_rate:+.1f}% 변동했습니다."
        )

    return SalesTrendResponse(
        tool_name="get_sales_trend",
        status="success",
        summary=summary,
        data=points,
        insights=insights,
        risk_signals=risk_signals,
        chart_data={
            "labels": [point.sales_month.strftime("%Y-%m") for point in points],
            "sales_qty": [point.total_qty for point in points],
            "revenue": [point.total_revenue for point in points],
            "avg_asp": [point.avg_asp for point in points],
        },
        actions=actions,
    )
