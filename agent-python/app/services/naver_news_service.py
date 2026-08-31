# agent-python/app/services/naver_news_service.py

import html
import os
import re
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime

import requests
from dotenv import load_dotenv


# ---------------------------------------------------------
# Mobile / IT 분류용 키워드
# ---------------------------------------------------------

MOBILE_KEYWORDS = [
    "mobile",
    "smartphone",
    "스마트폰",
    "휴대폰",
    "폴더블",
    "foldable",
    "galaxy",
    "갤럭시",
    "iphone",
    "아이폰",
    "mobile oled",
]

IT_KEYWORDS = [
    "it",
    "notebook",
    "노트북",
    "tablet",
    "태블릿",
    "monitor",
    "모니터",
    "laptop",
    "맥북",
    "ipad",
    "아이패드",
    "it oled",
]


# ---------------------------------------------------------
# 기업 / 산업 / 고객사·경쟁사 관련도 점수용 키워드
# ---------------------------------------------------------

COMPANY_KEYWORDS = {
    "삼성디스플레이": 3,
    "samsung display": 3,
    "lg디스플레이": 3,
    "lg display": 3,
    "boe": 3,
    "csot": 3,
    "tcl csot": 3,
    "visionox": 3,
}

INDUSTRY_KEYWORDS = {
    "oled": 3,
    "amoled": 3,
    "display": 2,
    "디스플레이": 2,
    "panel": 2,
    "패널": 2,
    "micro oled": 3,
    "microled": 3,
    "micro led": 3,
    "ltpo": 2,
    "qd-oled": 3,
}

CUSTOMER_COMPETITOR_KEYWORDS = {
    "apple": 2,
    "애플": 2,
    "samsung electronics": 2,
    "삼성전자": 2,
    "xiaomi": 2,
    "샤오미": 2,
    "oppo": 2,
    "vivo": 2,
    "huawei": 2,
    "화웨이": 2,
    "lenovo": 2,
    "레노버": 2,
    "dell": 2,
    "hp": 2,
}


# ---------------------------------------------------------
# 대표 회사명 정규화용 맵
# ---------------------------------------------------------

COMPANY_NAME_MAP = {
    "삼성디스플레이": "Samsung Display",
    "samsung display": "Samsung Display",
    "lg디스플레이": "LG Display",
    "lg display": "LG Display",
    "boe": "BOE",
    "csot": "CSOT",
    "tcl csot": "CSOT",
    "visionox": "Visionox",
}


def clean_text(text: str) -> str:
    """
    NAVER 뉴스 API 결과에 포함될 수 있는 HTML 태그와
    HTML 특수문자를 일반 텍스트로 정리합니다.
    """

    if not text:
        return ""

    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def parse_pub_date(pub_date: str) -> str:
    """
    NAVER 뉴스 날짜를 'YYYY-MM-DD HH:MM:SS' 형태로 변환합니다.
    """

    if not pub_date:
        return ""

    try:
        date_value = parsedate_to_datetime(pub_date)
        return date_value.strftime("%Y-%m-%d %H:%M:%S")

    except (TypeError, ValueError):
        return pub_date


def normalize_title(title: str) -> str:
    """
    제목 유사도 및 중복 비교를 위해 제목을 단순한 형태로 정리합니다.
    """

    title = clean_text(title).lower()
    title = re.sub(r"[^0-9a-z가-힣]+", " ", title)
    title = re.sub(r"\s+", " ", title)

    return title.strip()


def calculate_title_similarity(
    title1: str,
    title2: str,
) -> float:
    """
    두 제목의 유사도를 0~100 점으로 반환합니다.
    """

    normalized_title1 = normalize_title(title1)
    normalized_title2 = normalize_title(title2)

    if not normalized_title1 or not normalized_title2:
        return 0.0

    similarity = SequenceMatcher(
        None,
        normalized_title1,
        normalized_title2,
    ).ratio()

    return round(similarity * 100, 2)


def remove_duplicate_news(
    news_list: list[dict],
    similarity_threshold: float = 85.0,
) -> list[dict]:
    """
    다음 조건 중 하나에 해당하면 중복 뉴스로 판단합니다.

    1. 원문 URL 동일
    2. 정규화한 제목 동일
    3. 제목 유사도가 similarity_threshold 이상
    """

    result = []

    seen_links = set()
    seen_titles = set()

    for news in news_list:

        original_link = news.get("originallink", "")
        title = news.get("title", "")
        normalized_title = normalize_title(title)

        if original_link and original_link in seen_links:
            continue

        if normalized_title and normalized_title in seen_titles:
            continue

        is_similar = False

        for saved_news in result:

            saved_title = saved_news.get("title", "")

            similarity_score = calculate_title_similarity(
                title,
                saved_title,
            )

            if similarity_score >= similarity_threshold:
                is_similar = True
                break

        if is_similar:
            continue

        result.append(news)

        if original_link:
            seen_links.add(original_link)

        if normalized_title:
            seen_titles.add(normalized_title)

    return result


def calculate_keyword_score(
    text: str,
    keywords: list[str],
) -> int:
    """
    텍스트에 포함된 키워드 개수를 점수로 계산합니다.
    """

    if not text:
        return 0

    lower_text = text.lower()

    score = 0

    for keyword in keywords:

        if keyword.lower() in lower_text:
            score += 1

    return score


def classify_news_category(
    title: str,
    description: str,
) -> dict:
    """
    뉴스가 mobile / it / mixed / unknown 중 어디에 가까운지
    키워드 점수를 이용해 분류합니다.
    """

    full_text = f"{title} {description}"

    mobile_score = calculate_keyword_score(
        full_text,
        MOBILE_KEYWORDS,
    )

    it_score = calculate_keyword_score(
        full_text,
        IT_KEYWORDS,
    )

    if mobile_score > it_score:
        category = "mobile"

    elif it_score > mobile_score:
        category = "it"

    elif mobile_score == 0 and it_score == 0:
        category = "unknown"

    else:
        category = "mixed"

    return {
        "category": category,
        "mobile_score": mobile_score,
        "it_score": it_score,
    }


def calculate_weighted_keyword_score(
    text: str,
    keyword_weights: dict[str, int],
) -> int:
    """
    키워드별 가중치를 합산해서 점수를 계산합니다.
    """

    if not text:
        return 0

    lower_text = text.lower()

    total_score = 0

    for keyword, weight in keyword_weights.items():

        if keyword.lower() in lower_text:
            total_score += weight

    return total_score


def calculate_relevance_score(
    title: str,
    description: str,
) -> dict:
    """
    기업, 산업, 고객/경쟁사, mobile, it 점수를 합산해
    최종 relevance_score를 계산합니다.
    """

    full_text = f"{title} {description}"

    company_score = calculate_weighted_keyword_score(
        full_text,
        COMPANY_KEYWORDS,
    )

    industry_score = calculate_weighted_keyword_score(
        full_text,
        INDUSTRY_KEYWORDS,
    )

    customer_competitor_score = calculate_weighted_keyword_score(
        full_text,
        CUSTOMER_COMPETITOR_KEYWORDS,
    )

    category_result = classify_news_category(
        title,
        description,
    )

    mobile_score = category_result["mobile_score"]
    it_score = category_result["it_score"]

    relevance_score = (
        company_score
        + industry_score
        + customer_competitor_score
        + mobile_score
        + it_score
    )

    return {
        "company_score": company_score,
        "industry_score": industry_score,
        "customer_competitor_score": customer_competitor_score,
        "mobile_score": mobile_score,
        "it_score": it_score,
        "relevance_score": relevance_score,
    }


def extract_company(
    title: str,
    description: str,
) -> str:
    """
    제목과 요약에서 대표 디스플레이 기업명을 찾습니다.
    """

    full_text = f"{title} {description}".lower()

    for keyword, company_name in COMPANY_NAME_MAP.items():

        if keyword.lower() in full_text:
            return company_name

    return "Unknown"


def extract_product_group(
    title: str,
    description: str,
) -> str:
    """
    기사에서 대표 제품군을 찾습니다.
    """

    full_text = f"{title} {description}".lower()

    # 더 구체적인 키워드를 먼저 검사합니다.
    if "micro oled" in full_text:
        return "Micro OLED"

    if "qd-oled" in full_text:
        return "QD-OLED"

    if "amoled" in full_text:
        return "AMOLED"

    if "microled" in full_text or "micro led" in full_text:
        return "Micro LED"

    if "oled" in full_text:
        return "OLED"

    return "DISPLAY"


def filter_recent_days_news(
    news_list: list[dict],
    days: int = 3,
) -> list[dict]:
    """
    오늘을 포함해 최근 days일 동안 발행된 기사만 반환합니다.

    예: 오늘이 2026-08-31이고 days=3이면
    2026-08-29 ~ 2026-08-31 기사를 남깁니다.
    """
    today = date.today()
    start_date = today - timedelta(days=days - 1)

    result = []

    for news in news_list:
        published_at = news.get("published_at", "")

        if not published_at:
            continue

        try:
            news_datetime = datetime.strptime(
                published_at,
                "%Y-%m-%d %H:%M:%S",
            )
        except ValueError:
            continue

        news_date = news_datetime.date()

        if start_date <= news_date <= today:
            result.append(news)

    return result


def search_naver_news(
    keyword: str,
    display: int = 10,
    minimum_relevance_score: int = 5,
) -> list[dict]:
    """
    NAVER API HUB 뉴스 검색 API를 호출하고
    전처리 + 분류 + 관련도 계산 + 중복 제거 후 반환합니다.
    """

    # 함수 실행 시 .env를 읽습니다.
    load_dotenv()

    client_id = os.getenv("NAVER_API_CLIENT_ID")
    client_secret = os.getenv("NAVER_API_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError("NAVER API 인증 정보가 설정되지 않았습니다.")

    # 현재 프로젝트에서 실제 호출 성공을 확인한 NAVER API HUB 주소입니다.
    url = "https://naverapihub.apigw.ntruss.com/search/v1/news"

    headers = {
        "X-NCP-APIGW-API-KEY-ID": client_id,
        "X-NCP-APIGW-API-KEY": client_secret,
    }

    params = {
        "query": keyword,
        "display": display,
        "sort": "date",
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    raw_news_list = data.get("items", [])

    cleaned_news_list = []

    for item in raw_news_list:

        title = clean_text(
            item.get("title", "")
        )

        description = clean_text(
            item.get("description", "")
        )

        category_result = classify_news_category(
            title,
            description,
        )

        relevance_result = calculate_relevance_score(
            title,
            description,
        )

        company = extract_company(
            title,
            description,
        )

        product_group = extract_product_group(
            title,
            description,
        )

        news = {
            "title": title,
            "description": description,
            "originallink": item.get("originallink", ""),
            "link": item.get("link", ""),
            "published_at": parse_pub_date(
                item.get("pubDate", "")
            ),
            "search_keyword": keyword,
            "company": company,
            "product_group": product_group,
            "category": category_result["category"],
            "mobile_score": relevance_result["mobile_score"],
            "it_score": relevance_result["it_score"],
            "company_score": relevance_result["company_score"],
            "industry_score": relevance_result["industry_score"],
            "customer_competitor_score": relevance_result[
                "customer_competitor_score"
            ],
            "relevance_score": relevance_result["relevance_score"],
        }

        # 관련도 기준 미달 기사는 제외합니다.
        if news["relevance_score"] < minimum_relevance_score:
            continue

        cleaned_news_list.append(news)

    # 검색 결과 전체에서 마지막으로 중복 제거합니다.
    cleaned_news_list = remove_duplicate_news(
        cleaned_news_list,
    )

    return cleaned_news_list
