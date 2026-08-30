# agent-python/app/services/news_crawler_service.py

from app.services.naver_news_service import (
    filter_previous_day_news,
    remove_duplicate_news,
    search_naver_news,
)


def crawl_news(
    keywords: list[str],
    previous_day_only: bool = True,
) -> dict:
    """
    여러 검색 키워드로 NAVER 뉴스를 조회한 뒤 정제해서 반환합니다.

    DB에는 저장하지 않습니다.

    처리 순서
    1. 검색어별 NAVER 뉴스 API 호출
    2. 검색어 사이에서 다시 한 번 중복 제거
    3. previous_day_only=True이면 전일 기사만 남김
    """

    all_news: list[dict] = []

    for keyword in keywords:
        news_list = search_naver_news(
            keyword=keyword,
            display=100,
            minimum_relevance_score=5,
        )

        all_news.extend(news_list)

    all_news = remove_duplicate_news(
        all_news
    )

    if previous_day_only:
        final_news = filter_previous_day_news(
            all_news
        )
    else:
        final_news = all_news

    return {
        "searched_news_count": len(all_news),
        "news_count": len(final_news),
        "news": final_news,
    }
