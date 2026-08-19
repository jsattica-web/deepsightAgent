import json
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


def get_order_status(
    request: OrderStatusRequest,
) -> OrderStatusResponse | ErrorResponse:
    customer_filter = ""
    status_filter = ""
    params: dict[str, object] = {
        "start_date": request.start_date,
        "end_date": request.end_date,
        "product_group": request.product_group,
    }

    if request.customer_id:
        customer_filter = "and o.customer_id = %(customer_id)s"
        params["customer_id"] = request.customer_id
    if request.status:
        status_filter = "and o.status = %(status)s"
        params["status"] = request.status

    query = f"""
        select
            to_char(date_trunc('month', o.order_date), 'YYYY-MM') as month,
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
          and p.product_group = %(product_group)s
          {customer_filter}
          {status_filter}
        group by date_trunc('month', o.order_date)
        order by date_trunc('month', o.order_date)
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
            summary=f"{request.product_group} 조건에 해당하는 수주 데이터가 없습니다.",
            data=[],
            insights=[],
            risk_signals=[],
            chart_data={"type": "bar", "x": [], "series": []},
            actions=["조회 기간, 제품군, 고객사 또는 상태 조건을 확인하세요."],
        )

    total_orders = sum(point.total_orders for point in points)
    total_order_qty = sum(point.total_order_qty for point in points)
    confirmed_count = sum(point.confirmed_count for point in points)
    pending_count = sum(point.pending_count for point in points)
    delayed_count = sum(point.delayed_count for point in points)
    cancelled_count = sum(point.cancelled_count for point in points)
    delayed_rate = delayed_count / total_orders * 100
    cancelled_rate = cancelled_count / total_orders * 100
    combined_risk_rate = (delayed_count + cancelled_count) / total_orders * 100

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

    return OrderStatusResponse(
        tool_name="get_order_status",
        status="success",
        summary=(
            f"{request.start_date}부터 {request.end_date}까지 "
            f"{request.product_group} 수주는 총 {total_orders}건, "
            f"{total_order_qty:,}개입니다."
        ),
        data=points,
        insights=insights,
        risk_signals=risk_signals,
        chart_data={
            "type": "bar",
            "x": [point.month for point in points],
            "series": [
                {
                    "name": "confirmed",
                    "data": [point.confirmed_count for point in points],
                },
                {
                    "name": "pending",
                    "data": [point.pending_count for point in points],
                },
                {
                    "name": "delayed",
                    "data": [point.delayed_count for point in points],
                },
                {
                    "name": "cancelled",
                    "data": [point.cancelled_count for point in points],
                },
            ],
        },
        actions=actions,
    )


# if __name__ == "__main__":
#     sample_request = OrderStatusRequest(
#         start_date="2026-01-01",
#         end_date="2026-06-30",
#         customer_id=None,
#         product_group="Mobile OLED",
#         status=None,
#     )
#     sample_response = get_order_status(sample_request)
#     print(
#         json.dumps(
#             sample_response.model_dump(mode="json"),
#             ensure_ascii=False,
#             indent=2,
#         )
#     )
