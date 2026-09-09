import logging

from psycopg2.extras import RealDictCursor

from app.db import get_connection
from app.schemas.common import ErrorResponse
from app.schemas.tool_schema import (
    OrderStatusPoint,
    OrderStatusRequest,
    OrderStatusResponse,
)

logger = logging.getLogger(__name__)


def _chart_data(groups: dict, months: list[str]) -> dict:
    """STATUS 지표 4개 별로 분기하여 각 차트에 표시한다."""
    series = []
    for group in groups.values():
        label = group["label"]
        confirmed = []
        pending = []
        delayed = []
        cancelled = []
        for month in months:
            matched = None
            for point in group["points"]:
                if point.month == month:
                    matched = point
                    break
            confirmed.append(matched.confirmed_count if matched else 0)
            pending.append(matched.pending_count if matched else 0)
            delayed.append(matched.delayed_count if matched else 0)
            cancelled.append(matched.cancelled_count if matched else 0)
        series.append({"name": f"{label} / confirmed", "data": confirmed})
        series.append({"name": f"{label} / pending", "data": pending})
        series.append({"name": f"{label} / delayed", "data": delayed})
        series.append({"name": f"{label} / cancelled", "data": cancelled})
    return {"type": "bar", "x": months, "series": series}


def get_order_status(
    request: OrderStatusRequest,
) -> OrderStatusResponse | ErrorResponse:
    # 1. 값이 있는 조건만 SQL 필터에 추가한다.
    product_filter = ""
    customer_filter = ""
    status_filter = ""
    params: dict[str, object] = {
        "start_date": request.start_date,
        "end_date": request.end_date,
    }

    if request.product_group:
        product_filter = "and p.product_group = %(product_group)s"
        params["product_group"] = request.product_group
    if request.customer_id:
        customer_filter = "and o.customer_id = %(customer_id)s"
        params["customer_id"] = request.customer_id
    if request.status:
        status_filter = "and o.status = %(status)s"
        params["status"] = request.status

    # 2. 선택한 집계 기준을 SELECT와 GROUP BY에 함께 추가한다.
    product_select = ""
    product_group = ""
    if request.group_by_product_group:
        product_select = "p.product_group,"
        product_group = ", p.product_group"

    customer_select = ""
    customer_group = ""
    if request.group_by_customer:
        customer_select = "c.customer_id, c.customer_name,"
        customer_group = ", c.customer_id, c.customer_name"

    query = f"""
        select
            to_char(date_trunc('month', o.order_date), 'YYYY-MM') as month,
            {product_select}
            {customer_select}
            count(*)::integer as total_orders,
            coalesce(sum(o.order_qty), 0)::bigint as total_order_qty,
            count(*) filter (where o.status = 'CONFIRMED')::integer
                as confirmed_count,
            count(*) filter (where o.status = 'REQUESTED')::integer
                as pending_count,
            count(*) filter (where o.status = 'SHIPPED')::integer
                as shipped_count,
            count(*) filter (where o.status = 'CANCELLED')::integer
                as cancelled_count,
            count(*) filter (
                where o.status = 'DELAYED'
                   or (
                       o.confirmed_delivery_date is not null
                       and o.confirmed_delivery_date > o.requested_delivery_date
                   )
            )::integer as delayed_count,
            count(*) filter (
                where o.status in ('DELAYED', 'CANCELLED')
                   or (
                       o.confirmed_delivery_date is not null
                       and o.confirmed_delivery_date > o.requested_delivery_date
                   )
            )::integer as risk_order_count
        from public.fact_orders as o
        join public.dim_customer as c on c.customer_id = o.customer_id
        join public.dim_product as p on p.product_id = o.product_id
        where o.order_date >= %(start_date)s
          and o.order_date <= %(end_date)s
          {product_filter}
          {customer_filter}
          {status_filter}
        group by date_trunc('month', o.order_date){product_group}{customer_group}
        order by date_trunc('month', o.order_date){product_group}{customer_group}
    """

    try:
        with get_connection() as conn, conn.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
    except Exception:
        logger.exception("Failed to execute get_order_status")
        return ErrorResponse(
            status="error",
            message="수주 현황 데이터를 조회하는 중 오류가 발생했습니다.",
        )

    points = [
        OrderStatusPoint(
            month=row["month"],
            product_group=row.get("product_group"),
            customer_id=row.get("customer_id"),
            customer_name=row.get("customer_name"),
            total_orders=row["total_orders"],
            total_order_qty=row["total_order_qty"],
            confirmed_count=row["confirmed_count"],
            pending_count=row["pending_count"],
            delayed_count=row["delayed_count"],
            cancelled_count=row["cancelled_count"],
            shipped_count=row["shipped_count"],
            risk_order_count=row["risk_order_count"],
        )
        for row in rows
    ]

    if not points:
        return OrderStatusResponse(
            tool_name="get_order_status",
            status="success",
            summary=f"{request.product_group or "전체 제품군"} 조건에 해당하는 수주 데이터가 없습니다.",
            data=[],
            insights=[],
            risk_signals=[],
            chart_data={"type": "bar", "x": [], "series": []},
            actions=["조회 기간, 제품군, 고객사 또는 상태 조건을 확인하세요."],
        )

    # 3. 고객사·제품군별로 나눠 분석한다.
    groups = {}
    for point in points:
        key = (point.customer_id, point.product_group)
        if key not in groups:
            label = point.product_group or request.product_group or "전체 제품군"
            if request.group_by_customer:
                customer = point.customer_name or point.customer_id or "고객 미지정"
                label = f"{customer} / {label}"
            groups[key] = {"label": label, "points": []}
        groups[key]["points"].append(point)

    summaries = []
    insights = []
    risk_signals = []
    actions = []
    for group in groups.values():
        result = _analyze_group(group["points"], group["label"])
        summaries.append(result["summary"])
        insights.extend(result["insights"])
        risk_signals.extend(result["risk_signals"])
        for action in result["actions"]:
            if action not in actions:
                actions.append(action)

    # 4. 분석 결과와 월별 차트를 반환한다.
    months = sorted({point.month for point in points})
    return OrderStatusResponse(
        tool_name="get_order_status",
        status="success",
        summary=f"{request.start_date}부터 {request.end_date}까지 " + " ".join(summaries),
        data=points,
        insights=insights,
        risk_signals=risk_signals,
        chart_data=_chart_data(groups, months),
        actions=actions,
    )


def _analyze_group(points: list[OrderStatusPoint], label: str) -> dict:
    """한 고객사·제품군의 수주 현황과 위험을 분석한다."""
    total_orders = sum(point.total_orders for point in points)
    total_order_qty = sum(point.total_order_qty for point in points)
    confirmed_count = sum(point.confirmed_count for point in points)
    pending_count = sum(point.pending_count for point in points)
    delayed_count = sum(point.delayed_count for point in points)
    cancelled_count = sum(point.cancelled_count for point in points)
    delayed_rate = delayed_count / total_orders * 100
    cancelled_rate = cancelled_count / total_orders * 100
    # 지연이면서 취소인 주문을 중복 계산하지 않는다.
    risk_order_count = sum(point.risk_order_count for point in points)
    combined_risk_rate = risk_order_count / total_orders * 100

    insights = [
        f"전체 수주량은 {total_order_qty:,}개입니다.",
        (
            f"확정 {confirmed_count}건, 대기 {pending_count}건, "
            f"지연 {delayed_count}건, 취소 {cancelled_count}건입니다."
        ),
    ]
    risk_signals: list[str] = []
    actions: list[str] = []

    if delayed_count:
        risk_signals.append(
            f"지연 수주가 {delayed_count}건이며 전체의 {delayed_rate:.1f}%입니다."
        )
    if cancelled_count:
        risk_signals.append(
            f"취소 수주가 {cancelled_count}건이며 전체의 {cancelled_rate:.1f}%입니다."
        )

    if combined_risk_rate >= 20:
        risk_signals.append(
            f"지연·취소 비율이 {combined_risk_rate:.1f}%로 높습니다."
        )
        actions.append(
            "지연 및 취소 고객사의 납기와 수주 변경 원인을 우선 점검하세요."
        )
    elif combined_risk_rate >= 10:
        risk_signals.append(
            f"지연·취소 비율이 {combined_risk_rate:.1f}%로 주의가 필요합니다."
        )
        actions.append("리스크 수주의 납기 변경 가능성을 모니터링하세요.")
    else:
        actions.append("현재 수주 상태를 지속적으로 모니터링하세요.")

    return {
        "summary": f"{label} 수주는 총 {total_orders}건, {total_order_qty:,}개입니다.",
        "insights": [f"{label}: {item}" for item in insights],
        "risk_signals": [f"{label}: {item}" for item in risk_signals],
        "actions": [f"{label}: {item}" for item in actions],
    }
