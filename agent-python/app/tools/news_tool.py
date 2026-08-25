import logging
from decimal import Decimal

from psycopg2.extras import RealDictCursor

from app.db import get_connection
from app.schemas.common import ErrorResponse
from app.schemas.tool_schema import (
    CompetitorNewsPoint,
    CompetitorNewsRequest,
    CompetitorNewsResponse,
)

logger = logging.getLogger(__name__)


def _impact_level(score: float) -> str:
    if score >= 5:
        return "HIGH"
    if score >= 3:
        return "MEDIUM"
    return "LOW"


def _as_float(value: Decimal | int | float) -> float:
    return round(float(value), 2)


def search_competitor_news(
    request: CompetitorNewsRequest,
) -> CompetitorNewsResponse | ErrorResponse:
    filters: list[str] = []
    params: dict[str, object] = {
        "start_date": request.start_date,
        "end_date": request.end_date,
    }

    if request.companies:
        filters.append("and n.company = any(%(companies)s)")
        params["companies"] = request.companies
    if request.category:
        filters.append("and lower(n.category) = lower(%(category)s)")
        params["category"] = request.category
    if request.keyword:
        filters.append(
            "and (n.title ilike %(keyword)s or n.summary ilike %(keyword)s)"
        )
        params["keyword"] = f"%{request.keyword}%"
    if request.product_group:
        filters.append("and n.related_product_group = %(product_group)s")
        params["product_group"] = request.product_group
    if request.impact_level == "HIGH":
        filters.append("and n.impact_score >= 5")
    elif request.impact_level == "MEDIUM":
        filters.append("and n.impact_score >= 3 and n.impact_score < 5")
    elif request.impact_level == "LOW":
        filters.append("and n.impact_score < 3")

    query = f"""
        select
            n.news_date,
            n.company,
            n.category,
            n.title,
            n.summary,
            n.impact_score,
            n.related_product_group
        from public.market_news as n
        where n.news_date >= %(start_date)s
          and n.news_date <= %(end_date)s
          {' '.join(filters)}
        order by n.impact_score desc, n.news_date desc, n.news_id desc
    """

    try:
        with get_connection() as conn, conn.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
    except Exception:
        logger.exception("Failed to execute search_competitor_news")
        return ErrorResponse(
            status="error",
            message="경쟁사 뉴스 데이터를 조회하는 중 오류가 발생했습니다.",
        )

    points = []
    for row in rows:
        score = _as_float(row["impact_score"])
        points.append(
            CompetitorNewsPoint(
                news_date=row["news_date"],
                company=row["company"],
                category=row["category"],
                title=row["title"],
                summary=row["summary"],
                impact_score=score,
                impact_level=_impact_level(score),
                product_group=row["related_product_group"],
            )
        )

    if not points:
        return CompetitorNewsResponse(
            tool_name="search_competitor_news",
            status="success",
            summary="조건에 해당하는 경쟁사 뉴스가 없습니다.",
            data=[],
            insights=[],
            risk_signals=[],
            chart_data={"type": "bar", "x": [], "series": []},
            actions=["조회 기간 또는 뉴스 검색 조건을 확인하세요."],
        )

    company_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    for point in points:
        company_counts[point.company] = company_counts.get(point.company, 0) + 1
        category_counts[point.category] = category_counts.get(point.category, 0) + 1

    top_company = max(company_counts, key=company_counts.get)
    top_category = max(category_counts, key=category_counts.get)
    high_impact = [point for point in points if point.impact_level == "HIGH"]

    insights = [
        f"조회 기간에 경쟁사 뉴스 {len(points)}건이 확인됐습니다.",
        f"가장 많은 뉴스가 확인된 회사는 {top_company}입니다.",
        f"가장 빈번한 뉴스 유형은 {top_category}입니다.",
    ]
    risk_signals = [
        f"{point.company}: {point.title}"
        for point in high_impact[:3]
    ]
    actions = []
    if high_impact:
        actions.append("고영향 경쟁사 뉴스의 고객 및 제품별 파급효과를 점검하세요.")
    if any(point.category == "price" for point in points):
        actions.append("경쟁사 가격 움직임에 따른 ASP 협상 영향을 점검하세요.")
    if any(point.category == "capacity" for point in points):
        actions.append("경쟁사 공급능력 변화에 따른 수급 리스크를 점검하세요.")
    if not actions:
        actions.append("주요 경쟁사의 후속 움직임을 지속적으로 모니터링하세요.")

    return CompetitorNewsResponse(
        tool_name="search_competitor_news",
        status="success",
        summary=(
            f"{request.start_date}부터 {request.end_date}까지 "
            f"경쟁사 뉴스 {len(points)}건을 확인했습니다."
        ),
        data=points,
        insights=insights,
        risk_signals=risk_signals,
        chart_data={
            "type": "bar",
            "x": list(company_counts.keys()),
            "series": [
                {
                    "name": "news_count",
                    "data": list(company_counts.values()),
                }
            ],
        },
        actions=actions,
    )
