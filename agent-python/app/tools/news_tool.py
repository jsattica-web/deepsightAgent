import logging
from decimal import Decimal
from datetime import datetime

from psycopg2.extras import RealDictCursor

from app.db import get_connection
from app.schemas.common import ErrorResponse
from app.schemas.tool_schema import (
    CompetitorNewsPoint,
    CompetitorNewsRequest,
    CompetitorNewsResponse,
)
from app.services.news_crawler_service import crawl_news

logger = logging.getLogger(__name__)


def _impact_level(score: float) -> str:
    """
    뉴스 영향도 점수를 HIGH / MEDIUM / LOW로 바꿉니다.

    5점 이상 : HIGH
    3점 이상 : MEDIUM
    3점 미만 : LOW
    """
    if score >= 5:
        return "HIGH"

    if score >= 3:
        return "MEDIUM"

    return "LOW"


def _as_float(value: Decimal | int | float) -> float:
    """DB의 Decimal 값을 API 응답용 float 값으로 변환합니다."""
    return round(float(value), 2)


def _normalize_company_for_naver(company: str) -> str:
    """
    DB에서 쓰는 회사 약어를 NAVER 검색에 자연스러운 이름으로 바꿉니다.
    """
    aliases = {
        "LGD": "LG Display",
        "SDC": "Samsung Display",
        "SAMSUNG": "Samsung Display",
        "TCL CSOT": "CSOT",
    }

    cleaned = company.strip()

    return aliases.get(
        cleaned.upper(),
        cleaned,
    )


def _build_naver_search_keywords(
    request: CompetitorNewsRequest,
) -> list[str]:
    """
    Tool 14 요청값을 NAVER 검색어 목록으로 만듭니다.
    """

    search_word = (
        request.keyword
        or request.product_group
        or "OLED"
    )

    keywords: list[str] = []

    if request.companies:
        for company in request.companies:
            company_name = _normalize_company_for_naver(
                company
            )

            keywords.append(
                f"{company_name} {search_word}"
            )

    else:
        default_companies = [
            "Samsung Display",
            "LG Display",
            "BOE",
            "CSOT",
        ]

        for company in default_companies:
            keywords.append(
                f"{company} {search_word}"
            )

    return keywords


def _matches_product_group(
    news_product_group: str,
    request_product_group: str,
) -> bool:
    """
    NAVER 기사 제품군과 사용자 요청 제품군을 비교합니다.

    OLED 계열은 정확히 같은 문자열이 아니더라도 같은 OLED 계열로
    판단합니다. 예: OLED, AMOLED, QD-OLED, Mobile OLED.
    """
    news_value = news_product_group.lower().strip()
    request_value = request_product_group.lower().strip()

    if "oled" in news_value and "oled" in request_value:
        return True

    return news_value == request_value


def _matches_naver_filters(
    news: dict,
    request: CompetitorNewsRequest,
) -> bool:
    """
    NAVER 뉴스 결과에 Tool 14의 선택 조건을 적용합니다.
    """

    if request.companies:
        requested_companies = []

        for company in request.companies:
            requested_companies.append(
                _normalize_company_for_naver(
                    company
                ).lower()
            )

        news_company = str(
            news.get(
                "company",
                "",
            )
        ).lower()

        if news_company not in requested_companies:
            return False

    if request.category:
        news_category = str(
            news.get(
                "category",
                "",
            )
        ).lower()

        if (
            news_category
            != request.category.lower()
        ):
            return False

    if request.keyword:
        search_text = (
            f"{news.get('title', '')} "
            f"{news.get('description', '')}"
        ).lower()

        if (
            request.keyword.lower()
            not in search_text
        ):
            return False

    if request.product_group:
        news_product_group = str(
            news.get(
                "product_group",
                "",
            )
        )

        if not _matches_product_group(
            news_product_group,
            request.product_group,
        ):
            return False

    if request.impact_level:
        score = float(
            news.get(
                "relevance_score",
                0,
            )
        )

        if (
            _impact_level(score)
            != request.impact_level
        ):
            return False

    return True


def search_competitor_news(
    request: CompetitorNewsRequest,
) -> CompetitorNewsResponse | ErrorResponse:
    """
    14번 Competitor News Tool입니다.

    DB와 NAVER를 둘 다 조회합니다.

    [처리 순서]
    1. 기존 PostgreSQL market_news를 기존 조건 그대로 조회합니다.
    2. DB 결과를 CompetitorNewsPoint로 변환합니다.
    3. 같은 요청 조건으로 NAVER 뉴스 API도 추가 조회합니다.
    4. NAVER 최근 3일 뉴스에 필터를 적용합니다.
    5. DB 결과 + NAVER 결과를 합쳐 반환합니다.

    DB에는 INSERT하지 않습니다.
    기존 DB는 SELECT 전용으로 그대로 사용합니다.
    """

    # ---------------------------------------------------------
    # A. 기존 DB 조회
    # 아래 DB 필터/SQL 로직은 기존 Tool 14의 구조를 그대로 유지합니다.
    # ---------------------------------------------------------

    filters: list[str] = []

    params: dict[str, object] = {
        "start_date": request.start_date,
        "end_date": request.end_date,
    }

    if request.companies:
        filters.append(
            "and n.company = any(%(companies)s)"
        )
        params["companies"] = request.companies

    if request.category:
        filters.append(
            "and lower(n.category) = lower(%(category)s)"
        )
        params["category"] = request.category

    if request.keyword:
        filters.append(
            "and (n.title ilike %(keyword)s or n.summary ilike %(keyword)s)"
        )
        params["keyword"] = (
            f"%{request.keyword}%"
        )

    if request.product_group:
        filters.append(
            "and n.related_product_group = %(product_group)s"
        )
        params["product_group"] = (
            request.product_group
        )

    if request.impact_level == "HIGH":
        filters.append(
            "and n.impact_score >= 5"
        )

    elif request.impact_level == "MEDIUM":
        filters.append(
            "and n.impact_score >= 3 and n.impact_score < 5"
        )

    elif request.impact_level == "LOW":
        filters.append(
            "and n.impact_score < 3"
        )

    filter_sql = " ".join(
        filters
    )

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
          {filter_sql}
        order by
            n.impact_score desc,
            n.news_date desc,
            n.news_id desc
    """

    try:
        with get_connection() as conn:
            with conn.cursor(
                cursor_factory=RealDictCursor
            ) as cursor:

                cursor.execute(
                    query,
                    params,
                )

                rows = cursor.fetchall()

    except Exception:
        logger.exception(
            "Failed to execute DB search_competitor_news"
        )

        return ErrorResponse(
            status="error",
            message=(
                "경쟁사 뉴스 DB 데이터를 조회하는 중 "
                "오류가 발생했습니다."
            ),
        )

    db_news_list: list[
        CompetitorNewsPoint
    ] = []

    for row in rows:
        impact_score = _as_float(
            row["impact_score"]
        )

        news = CompetitorNewsPoint(
            news_date=row["news_date"],
            company=row["company"],
            category=row["category"],
            title=row["title"],
            summary=row["summary"],
            impact_score=impact_score,
            impact_level=_impact_level(
                impact_score
            ),
            product_group=(
                row["related_product_group"]
            ),
            source="DB",
        )

        db_news_list.append(
            news
        )

    # ---------------------------------------------------------
    # B. NAVER 뉴스 추가 조회
    # DB 결과가 있든 없든 항상 실행합니다.
    # ---------------------------------------------------------

    naver_search_keywords = (
        _build_naver_search_keywords(
            request
        )
    )

    try:
        crawl_result = crawl_news(
            keywords=naver_search_keywords,
            recent_days=3,
        )

    except Exception:
        # NAVER 장애가 나더라도 기존 DB 결과는 살려서 반환합니다.
        logger.exception(
            "Failed to execute NAVER search_competitor_news"
        )

        crawl_result = {
            "news": [],
        }

    raw_naver_news = crawl_result.get(
        "news",
        [],
    )

    naver_news_list: list[
        CompetitorNewsPoint
    ] = []

    for naver_news in raw_naver_news:

        if not _matches_naver_filters(
            naver_news,
            request,
        ):
            continue

        published_at = naver_news.get(
            "published_at",
            "",
        )

        try:
            news_date = datetime.strptime(
                published_at,
                "%Y-%m-%d %H:%M:%S",
            ).date()

        except ValueError:
            continue

        impact_score = round(
            float(
                naver_news.get(
                    "relevance_score",
                    0,
                )
            ),
            2,
        )

        news = CompetitorNewsPoint(
            news_date=news_date,
            company=naver_news.get(
                "company",
                "Unknown",
            ),
            category=naver_news.get(
                "category",
                "unknown",
            ),
            title=naver_news.get(
                "title",
                "",
            ),
            summary=naver_news.get(
                "description",
                "",
            ),
            impact_score=impact_score,
            impact_level=_impact_level(
                impact_score
            ),
            product_group=naver_news.get(
                "product_group",
                "DISPLAY",
            ),
            source="NAVER",
        )

        naver_news_list.append(
            news
        )

    # ---------------------------------------------------------
    # C. DB + NAVER 결과 합치기
    # ---------------------------------------------------------

    news_list = (
        db_news_list
        + naver_news_list
    )

    db_count = len(
        db_news_list
    )

    naver_count = len(
        naver_news_list
    )

    total_count = len(
        news_list
    )

    if not news_list:
        return CompetitorNewsResponse(
            tool_name="search_competitor_news",
            status="success",
            summary=(
                f"DB 검색 0건, NAVER 최근 3일 뉴스 0건, "
                f"총 0건입니다."
            ),
            data=[],
            insights=[
                (
                    f"DB 조회 기간: "
                    f"{request.start_date} ~ {request.end_date}"
                ),
                "NAVER 뉴스 조회 기준: 최근 3일",
            ],
            risk_signals=[],
            chart_data={
                "type": "bar",
                "x": [],
                "series": [],
            },
            actions=[
                (
                    "조회 기간 또는 뉴스 검색 조건을 "
                    "확인하세요."
                )
            ],
        )

    company_counts: dict[
        str,
        int,
    ] = {}

    category_counts: dict[
        str,
        int,
    ] = {}

    for news in news_list:

        company_counts[
            news.company
        ] = (
            company_counts.get(
                news.company,
                0,
            )
            + 1
        )

        category_counts[
            news.category
        ] = (
            category_counts.get(
                news.category,
                0,
            )
            + 1
        )

    top_company = ""
    top_company_count = -1

    for company, count in (
        company_counts.items()
    ):
        if count > top_company_count:
            top_company = company
            top_company_count = count

    top_category = ""
    top_category_count = -1

    for category, count in (
        category_counts.items()
    ):
        if count > top_category_count:
            top_category = category
            top_category_count = count

    high_impact_news: list[
        CompetitorNewsPoint
    ] = []

    for news in news_list:
        if news.impact_level == "HIGH":
            high_impact_news.append(
                news
            )

    insights = [
        (
            f"DB 검색 {db_count}건, "
            f"NAVER 최근 3일 뉴스 {naver_count}건, "
            f"총 {total_count}건을 확인했습니다."
        ),
        (
            f"DB 조회 기간은 "
            f"{request.start_date}부터 "
            f"{request.end_date}까지입니다."
        ),
        "NAVER 뉴스는 최근 3일 기준으로 추가 검색했습니다.",
        (
            f"가장 많은 뉴스가 확인된 회사는 "
            f"{top_company}입니다."
        ),
        (
            f"가장 빈번한 뉴스 유형은 "
            f"{top_category}입니다."
        ),
    ]

    risk_signals: list[str] = []

    for news in high_impact_news[:3]:
        risk_signals.append(
            (
                f"[{news.source}] "
                f"{news.company}: "
                f"{news.title}"
            )
        )

    actions: list[str] = []

    if high_impact_news:
        actions.append(
            (
                "고영향 경쟁사 뉴스의 고객 및 "
                "제품별 파급효과를 점검하세요."
            )
        )

    has_price_news = False

    for news in news_list:
        if news.category == "price":
            has_price_news = True
            break

    if has_price_news:
        actions.append(
            (
                "경쟁사 가격 움직임에 따른 "
                "ASP 협상 영향을 점검하세요."
            )
        )

    has_capacity_news = False

    for news in news_list:
        if news.category == "capacity":
            has_capacity_news = True
            break

    if has_capacity_news:
        actions.append(
            (
                "경쟁사 공급능력 변화에 따른 "
                "수급 리스크를 점검하세요."
            )
        )

    if not actions:
        actions.append(
            (
                "주요 경쟁사의 후속 움직임을 "
                "지속적으로 모니터링하세요."
            )
        )

    company_names = list(
        company_counts.keys()
    )

    company_news_counts = list(
        company_counts.values()
    )

    return CompetitorNewsResponse(
        tool_name="search_competitor_news",
        status="success",
        summary=(
            f"DB 검색 {db_count}건, "
            f"NAVER 최근 3일 뉴스 {naver_count}건, "
            f"총 {total_count}건을 확인했습니다."
        ),
        data=news_list,
        insights=insights,
        risk_signals=risk_signals,
        chart_data={
            "type": "bar",
            "x": company_names,
            "series": [
                {
                    "name": "news_count",
                    "data": (
                        company_news_counts
                    ),
                }
            ],
        },
        actions=actions,
    )
