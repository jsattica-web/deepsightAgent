import json
from typing import Any, Sequence

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from pydantic import PrivateAttr

from app.schemas.tool_schema import (
    BriefingRequest,
    CompetitorNewsRequest,
    CustomerProfileRequest,
    InventoryRiskRequest,
    OrderStatusRequest,
    SalesTrendRequest,
)
from app.tools.briefing_tool import create_briefing_report
from app.tools.customer_tool import get_customer_profile
from app.tools.inventory_tool import get_inventory_risk
from app.tools.news_tool import search_competitor_news
from app.tools.order_tool import get_order_status
from app.tools.sales_tool import get_sales_trend


DEFAULT_START_MONTH = "2026-01"
DEFAULT_END_MONTH = "2026-06"
DEFAULT_START_DATE = "2026-01-01"
DEFAULT_END_DATE = "2026-06-30"
DEFAULT_INVENTORY_MONTH = "2026-06"
DEFAULT_CUSTOMER_ID = "CUST_A"


@tool
def sales_trend_tool(question: str) -> dict[str, Any]:
    """판매, 매출, 동향, 추이 질문에 대해 판매 동향을 조회한다."""
    request = SalesTrendRequest(
        start_month=DEFAULT_START_MONTH,
        end_month=DEFAULT_END_MONTH,
        product_group=extract_product_group(question),
        customer_id=None,
        group_by_customer=should_group_sales_by_customer(question),
    )
    result = get_sales_trend(request)
    return build_sales_answer(request.model_dump(mode="json"), result.model_dump(mode="json"))


@tool
def order_status_tool(question: str) -> dict[str, Any]:
    """수주, 주문, 납기, 지연 질문에 대해 수주 현황을 조회한다."""
    request = OrderStatusRequest(
        start_date=DEFAULT_START_DATE,
        end_date=DEFAULT_END_DATE,
        customer_id=None,
        product_group=extract_product_group(question),
        status=extract_order_status(question),
    )
    result = get_order_status(request)
    return build_order_answer(request.model_dump(mode="json"), result.model_dump(mode="json"))


@tool
def inventory_risk_tool(question: str) -> dict[str, Any]:
    """재고, 안전재고, 과잉, 부족 질문에 대해 재고 리스크를 조회한다."""
    request = InventoryRiskRequest(
        inventory_month=DEFAULT_INVENTORY_MONTH,
        product_group=extract_product_group(question),
    )
    result = get_inventory_risk(request)
    return build_inventory_answer(request.model_dump(mode="json"), result.model_dump(mode="json"))

@tool
def customer_profile_tool(question: str) -> dict[str, Any]:
    """고객, 고객사, 프로필 질문에 대해 고객사 정보를 조회한다."""
    request = CustomerProfileRequest(
        customer_id=extract_customer_id(question),
        start_month=DEFAULT_START_MONTH,
        end_month=DEFAULT_END_MONTH,
    )
    result = get_customer_profile(request)
    return build_customer_answer(request.model_dump(mode="json"), result.model_dump(mode="json"))


@tool
def competitor_news_tool(question: str) -> dict[str, Any]:
    """경쟁사, 뉴스, 시장 이슈 질문에 대해 경쟁사 뉴스를 조회한다."""
    request = CompetitorNewsRequest(
        start_date=DEFAULT_START_DATE,
        end_date=DEFAULT_END_DATE,
        companies=extract_companies(question),
        category=None,
        impact_level=extract_impact_level(question),
        keyword=extract_news_keyword(question),
        product_group=extract_news_product_group(question),
    )
    result = search_competitor_news(request)
    return build_news_answer(request.model_dump(mode="json"), result.model_dump(mode="json"))


@tool
def briefing_report_tool(question: str) -> dict[str, Any]:
    """브리핑에 필요한 Tool 결과를 모아서 브리프북 초안을 생성한다.

    Briefing Tool은 DB를 직접 조회하지 않는다.
    대신 판매/수주/재고/경쟁사 뉴스 Tool의 실제 조회 함수를 먼저 호출하고,
    그 결과를 tool_results에 모아서 create_briefing_report()에 전달한다.
    """

    # 1. 사용자의 질문에서 여러 Tool이 공통으로 사용할 조건을 먼저 꺼낸다.
    customer_id = extract_customer_id(question)
    product_group = extract_product_group(question)

    # 2. 판매 동향 Tool을 실행한다.
    #    특정 고객의 브리핑이므로 customer_id도 함께 전달한다.
    sales_request = SalesTrendRequest(
        start_month=DEFAULT_START_MONTH,
        end_month=DEFAULT_END_MONTH,
        product_group=product_group,
        customer_id=customer_id,
    )
    sales_result = get_sales_trend(sales_request)

    # 3. 수주 현황 Tool을 실행한다.
    order_request = OrderStatusRequest(
        start_date=DEFAULT_START_DATE,
        end_date=DEFAULT_END_DATE,
        customer_id=customer_id,
        product_group=product_group,
        status=extract_order_status(question),
    )
    order_result = get_order_status(order_request)

    # 4. 재고 리스크 Tool을 실행한다.
    #    현재 Inventory Tool은 고객사 조건 없이 제품군 기준으로 조회한다.
    inventory_request = InventoryRiskRequest(
        inventory_month=DEFAULT_INVENTORY_MONTH,
        product_group=product_group,
    )
    inventory_result = get_inventory_risk(inventory_request)

    # 5. 경쟁사 뉴스 Tool을 실행한다.
    news_request = CompetitorNewsRequest(
        start_date=DEFAULT_START_DATE,
        end_date=DEFAULT_END_DATE,
        companies=extract_companies(question),
        category=None,
        impact_level=extract_impact_level(question),
        keyword=extract_news_keyword(question),
        product_group=product_group,
    )
    news_result = search_competitor_news(news_request)

    # 6. 각 Tool의 결과를 하나의 딕셔너리에 모은다.
    #    DB나 파일에 저장하는 것이 아니라, 이번 브리핑 요청 동안만 사용하는 변수이다.
    #    아래 key(sales, orders, inventory, competitor_news)는
    #    briefing_tool.py의 section_key와 같은 이름을 사용해야 한다.
    tool_results = {
        "sales": sales_result,
        "orders": order_result,
        "inventory": inventory_result,
        "competitor_news": news_result,
    }

    # 7. 모아 둔 Tool 결과를 BriefingRequest의 tool_results에 넣는다.
    request = BriefingRequest(
        topic=question,
        customer_id=customer_id,
        start_date=DEFAULT_START_DATE,
        end_date=DEFAULT_END_DATE,
        tool_results=tool_results,
    )

    # 8. briefing_tool.py는 tool_results를 읽어서 하나의 브리핑으로 조립한다.
    result = create_briefing_report(request)

    return build_briefing_answer(
        request.model_dump(mode="json"),
        result.model_dump(mode="json"),
    )

class RuleBasedChatModel(BaseChatModel):
    """PoC용 ChatModel이다.

    공식 `create_agent` 구조를 사용하되, 실제 LLM API가 붙기 전까지는
    키워드 규칙으로 Tool을 선택한다. 나중에 OpenAI, Anthropic 같은
    ChatModel로 교체할 때는 `build_agent()`의 model만 바꾸면 된다.
    """

    _tools: Sequence[Any] = PrivateAttr(default_factory=list)

    @property
    def _llm_type(self) -> str:
        """LangChain 내부 로그에서 모델 종류를 구분하기 위한 이름이다."""
        return "rule-based-chat-model"

    def bind_tools(
        self,
        tools: Sequence[Any],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> "RuleBasedChatModel":
        """공식 create_agent가 전달하는 Tool 목록을 모델에 보관한다."""
        self._tools = tools
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """첫 호출에서는 Tool을 선택하고, Tool 실행 후에는 최종 답변을 반환한다."""
        tool_message = last_tool_message(messages)
        if tool_message is not None:
            return chat_result(AIMessage(content=tool_message.content))

        question = last_user_question(messages)
        tool_name = choose_tool_name(question)
        if tool_name is None:
            return chat_result(
                AIMessage(content=json.dumps(unsupported_answer(question), ensure_ascii=False))
            )

        return chat_result(
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": tool_name,
                        "args": {"question": question},
                        "id": f"call_{tool_name}",
                    }
                ],
            )
        )


def build_agent():
    """Display Market Intelligence Agent를 생성한다."""
    return create_agent(
        model=RuleBasedChatModel(),
        tools=[
            sales_trend_tool,
            order_status_tool,
            inventory_risk_tool,
            customer_profile_tool,
            competitor_news_tool,
            briefing_report_tool,
        ],
        system_prompt=(
            "You are a Display Market Intelligence Agent. "
            "Select the best tool and return its JSON result."
        ),
    )


agent = build_agent()


def run_agent(question: str) -> dict[str, Any]:
    """FastAPI의 `/agent/chat`에서 호출하는 Agent 실행 함수이다."""
    result = agent.invoke({"messages": [HumanMessage(content=question)]})
    last_message = result["messages"][-1]
    return parse_agent_response(last_message.content)


def choose_tool_name(question: str) -> str | None:
    """질문 키워드를 기준으로 공식 Agent가 호출할 Tool 이름을 선택한다."""
    normalized = question.lower()

    # 여러 키워드가 섞일 수 있어 더 구체적인 업무 질문부터 먼저 확인한다.
    if has_any_keyword(
        normalized,
        ["브리핑", "브리프", "보고서", "리포트", "briefing", "report"],
    ):
        return "briefing_report_tool"
    if has_any_keyword(
        normalized,
        ["뉴스", "경쟁사", "시장 이슈", "competitor", "news", "boe", "csot", "lgd"],
    ):
        return "competitor_news_tool"
    if has_any_keyword(
        normalized,
        ["재고", "안전재고", "과잉", "부족", "inventory", "stock", "risk"],
    ):
        return "inventory_risk_tool"
    if has_any_keyword(
        normalized,
        ["수주", "주문", "납기", "지연", "order", "delivery", "delayed"],
    ):
        return "order_status_tool"
    if has_any_keyword(
        normalized,
        ["판매", "매출", "동향", "추이", "sales", "revenue", "trend", "oled"],
    ):
        return "sales_trend_tool"
    if has_any_keyword(
        normalized,
        ["고객", "고객사", "프로필", "customer", "profile", "cust_"],
    ):
        return "customer_profile_tool"
    return None


def should_group_sales_by_customer(question: str) -> bool:
    """판매 질문에서 고객별 집계가 필요한지 판단한다.

    "고객별"은 고객 프로필 조회가 아니라 판매 데이터를 고객 단위로 나누라는 뜻이다.
    이 값을 SalesTrendRequest에 넘기면 판매 Tool이 월별+고객별로 group by 한다.
    """
    normalized = question.lower()
    return any(keyword in normalized for keyword in ["고객별", "고객사별", "customer by", "by customer"])

def extract_product_group(question: str) -> str:
    """질문에 포함된 키워드로 제품군을 추정한다."""
    normalized = question.lower()

    if "tv" in normalized and "oled" in normalized:
        return "TV OLED"
    if "it" in normalized and "oled" in normalized:
        return "IT OLED"
    if "tablet" in normalized or "태블릿" in normalized:
        return "Tablet OLED"
    if "lcd" in normalized or "monitor" in normalized or "모니터" in normalized:
        return "LCD Monitor"
    if "automotive" in normalized or "차량" in normalized or "전장" in normalized:
        return "Automotive Display"
    return "Mobile OLED"

def extract_news_product_group(question: str) -> str | None:
    """
    뉴스 검색 전용 제품군 추출 함수입니다.

    일반 Tool은 제품군이 없을 때 Mobile OLED를 기본값으로 사용하지만,
    뉴스 검색에서는 사용자가 단순히 OLED라고 질문한 것을
    Mobile OLED로 임의 변환하지 않습니다.
    """
    normalized = question.lower()

    if "tv oled" in normalized:
        return "TV OLED"
    if "it oled" in normalized:
        return "IT OLED"
    if (
        "mobile oled" in normalized
        or "모바일 oled" in normalized
        or "스마트폰 oled" in normalized
    ):
        return "Mobile OLED"
    if "oled" in normalized:
        return "OLED"
    if "lcd" in normalized:
        return "LCD"

    return None


def extract_customer_id(question: str) -> str:
    """질문에서 CUST_A 같은 고객사 ID를 찾고, 없으면 기본 고객사를 사용한다."""
    normalized = question.upper()
    for letter in "ABCDEFGHIJKLMNOPQRSTUV":
        customer_id = f"CUST_{letter}"
        if customer_id in normalized:
            return customer_id
    return DEFAULT_CUSTOMER_ID


def extract_companies(question: str) -> list[str] | None:
    """
    질문에 포함된 경쟁사 이름을 찾아 뉴스 검색 조건으로 사용합니다.
    한글 회사명과 영문/약어를 함께 처리합니다.
    """
    normalized = question.upper()

    company_keywords = {
        "BOE": "BOE",
        "CSOT": "CSOT",
        "LGD": "LGD",
        "LG디스플레이": "LGD",
        "LG DISPLAY": "LGD",
        "SAMSUNG": "SAMSUNG",
        "삼성디스플레이": "SAMSUNG",
        "SAMSUNG DISPLAY": "SAMSUNG",
        "VISIONOX": "VISIONOX",
        "TIANMA": "TIANMA",
    }

    companies: list[str] = []

    for keyword, company_code in company_keywords.items():
        if keyword in normalized and company_code not in companies:
            companies.append(company_code)

    return companies or None


def extract_impact_level(question: str) -> str | None:
    """질문에 영향도 표현이 있으면 HIGH, MEDIUM, LOW 중 하나로 변환한다."""
    normalized = question.lower()
    if "high" in normalized or "고영향" in normalized or "높은" in normalized:
        return "HIGH"
    if "medium" in normalized or "중간" in normalized:
        return "MEDIUM"
    if "low" in normalized or "저영향" in normalized or "낮은" in normalized:
        return "LOW"
    return None


def extract_news_keyword(question: str) -> str | None:
    """뉴스 검색용 간단 키워드를 고른다."""
    normalized = question.lower()
    for keyword in ["oled", "lcd", "capacity", "price", "supply", "demand"]:
        if keyword in normalized:
            return keyword.upper()
    return None

def extract_order_status(question: str) -> str | None:
    """질문에 주문 상태 키워드가 있으면 Tool 요청값으로 변환한다."""
    normalized = question.lower()

    if "지연" in normalized or "delay" in normalized:
        return "DELAYED"
    if "취소" in normalized or "cancel" in normalized:
        return "CANCELLED"
    if "출하" in normalized or "배송" in normalized or "ship" in normalized:
        return "SHIPPED"
    if "확정" in normalized or "confirm" in normalized:
        return "CONFIRMED"
    if "요청" in normalized or "request" in normalized or "대기" in normalized:
        return "REQUESTED"
    return None


def has_any_keyword(text: str, keywords: list[str]) -> bool:
    """문장 안에 키워드 목록 중 하나라도 있으면 True를 반환한다."""
    return any(keyword in text for keyword in keywords)


def build_sales_answer(
    tool_args: dict[str, Any],
    tool_result: dict[str, Any],
) -> dict[str, Any]:
    """판매 Tool 결과를 화면 공통 응답 구조로 바꾼다."""
    product_group = tool_args.get("product_group", "Mobile OLED")
    start_month = tool_args.get("start_month", DEFAULT_START_MONTH)
    end_month = tool_args.get("end_month", DEFAULT_END_MONTH)
    data = tool_result.get("data", [])

    if not data:
        answer = f"{start_month}부터 {end_month}까지 {product_group} 판매 데이터가 없습니다."
    else:
        first_qty = int(data[0].get("qty", 0))
        last_qty = int(data[-1].get("qty", 0))
        change_rate = ((last_qty - first_qty) / first_qty) * 100 if first_qty else 0.0
        answer = (
            f"{start_month}부터 {end_month}까지 {product_group} 판매 동향을 분석했습니다. "
            f"판매량은 {first_qty:,}개에서 {last_qty:,}개로 {change_rate:+.1f}% 변동했습니다."
        )

    return success_answer(
        answer=answer,
        summary=tool_result.get("summary", ""),
        table_title=f"{product_group} 판매 동향",
        table_columns=sales_table_columns(tool_args),
        table_data=data,
        chart_title=f"{product_group} 월별 판매 추이",
        tool_result=tool_result,
    )



def sales_table_columns(tool_args: dict[str, Any]) -> list[str]:
    """판매 조회 결과를 표로 보여줄 때 사용할 컬럼을 정한다.

    일반 월별 조회는 기존 4개 컬럼만 보여준다. 고객별 조회에서는 고객 ID와
    고객명을 앞에 붙여 같은 월 안에서도 고객별 매출 차이를 볼 수 있게 한다.
    """
    if tool_args.get("group_by_customer"):
        return ["month", "customer_id", "customer_name", "qty", "revenue", "asp"]
    return ["month", "qty", "revenue", "asp"]


def build_order_answer(
    tool_args: dict[str, Any],
    tool_result: dict[str, Any],
) -> dict[str, Any]:
    """수주 Tool 결과를 화면 공통 응답 구조로 바꾼다."""
    product_group = tool_args.get("product_group", "Mobile OLED")
    start_date = tool_args.get("start_date", DEFAULT_START_DATE)
    end_date = tool_args.get("end_date", DEFAULT_END_DATE)
    data = tool_result.get("data", [])

    if not data:
        answer = f"{start_date}부터 {end_date}까지 {product_group} 수주 데이터가 없습니다."
    else:
        total_orders = sum(int(item.get("total_orders", 0)) for item in data)
        total_order_qty = sum(int(item.get("total_order_qty", 0)) for item in data)
        risk_order_count = sum(int(item.get("risk_order_count", 0)) for item in data)
        answer = (
            f"{start_date}부터 {end_date}까지 {product_group} 수주 현황을 분석했습니다. "
            f"총 {total_orders}건, {total_order_qty:,}개이며 리스크 수주는 {risk_order_count}건입니다."
        )

    return success_answer(
        answer=answer,
        summary=tool_result.get("summary", ""),
        table_title=f"{product_group} 수주 현황",
        table_columns=[
            "month",
            "total_orders",
            "total_order_qty",
            "confirmed_count",
            "pending_count",
            "delayed_count",
            "cancelled_count",
            "shipped_count",
            "risk_order_count",
        ],
        table_data=data,
        chart_title=f"{product_group} 월별 수주 상태",
        tool_result=tool_result,
    )


def build_inventory_answer(
    tool_args: dict[str, Any],
    tool_result: dict[str, Any],
) -> dict[str, Any]:
    """재고 Tool 결과를 화면 공통 응답 구조로 바꾼다."""
    product_group = tool_args.get("product_group", "Mobile OLED")
    inventory_month = tool_args.get("inventory_month", DEFAULT_INVENTORY_MONTH)
    data = tool_result.get("data", [])

    if not data:
        answer = f"{inventory_month} 기준 {product_group} 재고 데이터가 없습니다."
    else:
        latest = data[-1]
        answer = (
            f"{inventory_month} 기준 {product_group} 재고 리스크를 분석했습니다. "
            f"기말재고는 {int(latest.get('ending_stock', 0)):,}개, "
            f"안전재고는 {int(latest.get('safety_stock', 0)):,}개입니다."
        )

    return success_answer(
        answer=answer,
        summary=tool_result.get("summary", ""),
        table_title=f"{product_group} 재고 리스크",
        table_columns=[
            "month",
            "ending_stock",
            "safety_stock",
            "production_qty",
            "sales_qty",
        ],
        table_data=data,
        chart_title=f"{product_group} 월별 재고 추이",
        tool_result=tool_result,
    )

def build_customer_answer(
    tool_args: dict[str, Any],
    tool_result: dict[str, Any],
) -> dict[str, Any]:
    """고객 Tool 결과를 화면 공통 응답 구조로 바꾼다."""
    customer_id = tool_args.get("customer_id", DEFAULT_CUSTOMER_ID)
    data = tool_result.get("data", [])

    if not data:
        answer = f"{customer_id} 고객사 프로필 데이터가 없습니다."
    else:
        customer = data[0]
        answer = (
            f"{customer.get('customer_name', customer_id)} 고객사 프로필을 조회했습니다. "
            f"판매량은 {int(customer.get('sales_qty', 0)):,}개, "
            f"수주량은 {int(customer.get('order_qty', 0)):,}개입니다."
        )

    return success_answer(
        answer=answer,
        summary=tool_result.get("summary", ""),
        table_title=f"{customer_id} 고객사 프로필",
        table_columns=[
            "customer_id",
            "customer_name",
            "segment",
            "region",
            "tier",
            "main_application",
            "sales_qty",
            "sales_revenue",
            "order_count",
            "order_qty",
            "delayed_order_count",
        ],
        table_data=data,
        chart_title=f"{customer_id} 판매·수주 요약",
        tool_result=tool_result,
    )


def build_news_answer(
    tool_args: dict[str, Any],
    tool_result: dict[str, Any],
) -> dict[str, Any]:
    """
    DB + NAVER 뉴스 Tool 결과를 화면 공통 응답 구조로 바꾼다.
    """

    data = tool_result.get(
        "data",
        [],
    )

    db_count = 0
    naver_count = 0

    for news in data:
        source = news.get(
            "source"
        )

        if source == "DB":
            db_count += 1

        elif source == "NAVER":
            naver_count += 1

    total_count = len(
        data
    )

    if not data:
        answer = (
            "DB와 NAVER 뉴스 검색 결과 "
            "조건에 맞는 경쟁사 뉴스가 없습니다."
        )

    else:
        answer = (
            f"DB 검색 {db_count}건, "
            f"NAVER 뉴스 {naver_count}건, "
            f"총 {total_count}건의 경쟁사 뉴스를 "
            f"확인했습니다."
        )

    return success_answer(
        answer=answer,
        summary=tool_result.get(
            "summary",
            "",
        ),
        table_title="경쟁사 뉴스",
        table_columns=[
            "source",
            "news_date",
            "company",
            "category",
            "title",
            "impact_score",
            "impact_level",
            "product_group",
        ],
        table_data=data,
        chart_title="경쟁사별 뉴스 건수",
        tool_result=tool_result,
    )

def build_briefing_answer(
    tool_args: dict[str, Any],
    tool_result: dict[str, Any],
) -> dict[str, Any]:
    """브리핑 Tool 결과를 화면 공통 응답 구조로 바꾼다."""
    topic = tool_args.get("topic", "브리핑")
    data = tool_result.get("data", [])

    answer = f"'{topic}' 브리핑 초안을 {len(data)}개 섹션으로 생성했습니다."

    return success_answer(
        answer=answer,
        summary=tool_result.get("summary", ""),
        table_title="브리핑 섹션",
        table_columns=["order", "section", "key_message"],
        table_data=data,
        chart_title="브리핑 구성",
        tool_result=tool_result,
    )

def success_answer(
    *,
    answer: str,
    summary: Any,
    table_title: str,
    table_columns: list[str],
    table_data: list[dict[str, Any]],
    chart_title: str,
    tool_result: dict[str, Any],
) -> dict[str, Any]:
    """Tool 결과를 Spring Boot와 Vue가 쓰는 공통 성공 응답으로 만든다."""
    return {
        "status": "success",
        "message": "요청이 정상 처리되었습니다.",
        "data": {
            "answer": answer,
            "summary": as_list(summary),
            "tables": [table(table_title, table_columns, table_data)],
            "charts": charts_from_tool_result(tool_result, chart_title),
            "insights": tool_result.get("insights", []),
            "risk_signals": tool_result.get("risk_signals", []),
            "actions": tool_result.get("actions", []),
        },
        "error": None,
    }


def unsupported_answer(question: str) -> dict[str, Any]:
    """지원하지 않는 질문이 들어왔을 때 안내 응답을 만든다."""
    return {
        "status": "success",
        "message": "요청이 정상 처리되었습니다.",
        "data": {
            "answer": (
                "현재 PoC에서는 판매 동향, 수주 현황, 재고 리스크, 고객 프로필, 경쟁사 뉴스, 브리핑 질문을 지원합니다. "
                "예: 최근 6개월 OLED 판매 동향 분석해줘"
            ),
            "summary": [
                "지원 질문 유형: sales_trend, order_status, inventory_risk, customer_profile, competitor_news, briefing_report",
                f"입력 질문: {question}",
            ],
            "tables": [],
            "charts": [],
            "insights": [],
            "risk_signals": [],
            "actions": [
                "판매, 수주, 재고, 고객, 경쟁사, 뉴스, 브리핑 키워드를 포함해 다시 질문해보세요."
            ],
        },
        "error": None,
    }


def table(title: str, columns: list[str], data: list[dict[str, Any]]) -> dict[str, Any]:
    """딕셔너리 목록을 화면 표 형식으로 변환한다."""
    return {
        "title": title,
        "columns": columns,
        "rows": [[item.get(column) for column in columns] for item in data],
    }


def charts_from_tool_result(tool_result: dict[str, Any], title: str) -> list[dict[str, Any]]:
    """Tool의 chart_data를 화면 차트 형식으로 변환한다."""
    chart_data = tool_result.get("chart_data", {})
    if not chart_data:
        return []

    labels = chart_data.get("x") or chart_data.get("categories", [])

    return [
        {
            "type": chart_data.get("type"),
            "title": title,
            "labels": labels,
            "datasets": [
                {
                    "label": series.get("name"),
                    "data": series.get("data", []),
                }
                for series in chart_data.get("series", [])
            ],
        }
    ]


def as_list(value: Any) -> list[Any]:
    """문자열이나 단일 값을 리스트 형태로 맞춘다."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def parse_agent_response(content: Any) -> dict[str, Any]:
    """Agent 마지막 메시지를 FastAPI가 반환할 dict로 변환한다."""
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        return json.loads(content)
    raise ValueError("Agent 응답을 JSON으로 변환할 수 없습니다.")


def last_user_question(messages: list[BaseMessage]) -> str:
    """메시지 목록에서 가장 최근 사용자 질문을 찾는다."""
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def last_tool_message(messages: list[BaseMessage]) -> ToolMessage | None:
    """Tool 실행 결과 메시지가 있으면 가장 최근 값을 반환한다."""
    for message in reversed(messages):
        if isinstance(message, ToolMessage):
            return message
    return None


def chat_result(message: AIMessage) -> ChatResult:
    """LangChain ChatModel이 요구하는 ChatResult 객체를 만든다."""
    return ChatResult(generations=[ChatGeneration(message=message)])


