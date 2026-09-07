sales_trend_tool AS-IS / TO-BE
==============================

1. 목적
-------

현재 sales_trend_tool은 사용자 질문 문자열을 직접 분석하여 판매 조회 조건을
만드는 구조이다. TO-BE에서는 OpenAI LLM이 질문을 해석하고 구조화된 인자를
생성하며, sales_trend_tool은 전달받은 조건으로 판매 데이터만 정확하게 조회한다.


2. 전체 비교
-------------

[AS-IS]

사용자 질문
  -> 키워드 기반 choose_tool_name()
  -> sales_trend_tool(question: str)
  -> Tool 내부에서 기간, 제품군, 고객별 집계 여부 추출
  -> get_sales_trend()
  -> 화면용 답변까지 생성

[TO-BE]

사용자 질문
  -> OpenAI LLM이 질문 분석 및 QueryPlan 생성
  -> 필요한 툴 목록과 구조화 인자 결정
  -> sales_trend_tool(structured arguments)
  -> 판매 원천 데이터와 계산 결과 반환
  -> 다른 툴 결과와 함께 LLM이 교차분석
  -> 최종 답변, 표, 차트 생성


3. AS-IS 함수
--------------

현재 위치:

agent-python/app/agent/agent.py

현재 형태:

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
    return build_sales_answer(
        request.model_dump(mode="json"),
        result.model_dump(mode="json"),
    )


4. AS-IS 동작
--------------

4.1 입력

사용자의 전체 질문을 question 문자열 하나로 받는다.

예시:

"최근 6개월 Mobile OLED 판매 매출 추이를 고객별로 분석해줘."


4.2 기간

질문에 포함된 기간을 실제로 해석하지 않고 고정값을 사용한다.

start_month = "2026-01"
end_month = "2026-06"

따라서 "최근 3개월", "2025년", "2분기"라고 질문해도 동일한 기간이 조회될
가능성이 있다.


4.3 제품군

extract_product_group(question)이 키워드로 제품군 하나를 선택한다.

- TV + OLED -> TV OLED
- IT + OLED -> IT OLED
- tablet 또는 태블릿 -> Tablet OLED
- LCD 또는 monitor -> LCD Monitor
- automotive 또는 차량 -> Automotive Display
- 해당 키워드가 없으면 Mobile OLED

복수 제품군이나 전체 제품군 비교는 지원하지 않는다.


4.4 고객 조건

sales_trend_tool에서는 customer_id를 항상 None으로 전달한다.

customer_id=None

따라서 질문에 CUST_A가 포함되어도 현재 Wrapper 수준에서는 특정 고객 필터가
적용되지 않는다.


4.5 고객별 집계

다음 문자열이 포함되면 group_by_customer=true가 된다.

- 고객별
- 고객사별
- customer by
- by customer

표현이 조금 달라지면 고객별 집계 의도를 놓칠 수 있다.


4.6 결과 생성

get_sales_trend()가 DB 조회, 증감률, 인사이트, 위험 신호, 차트 데이터를 만든다.
이후 build_sales_answer()가 화면용 답변 구조까지 생성한다.

즉, 현재 Tool은 다음 책임을 모두 가진다.

- 자연어 질문 해석
- 조회 조건 생성
- DB 조회
- 데이터 분석
- 화면용 답변 생성


5. AS-IS 한계
---------------

1) 키워드 기반 라우터가 툴 하나만 선택한다.

판매와 재고가 함께 언급되면 우선순위가 높은 하나의 툴만 호출될 수 있다.


2) 질문의 기간이 적용되지 않는다.

"최근 6개월"을 질문해도 DEFAULT_START_MONTH와 DEFAULT_END_MONTH를 사용한다.


3) 특정 고객 필터가 적용되지 않는다.

sales_trend_tool이 customer_id=None을 고정으로 전달한다.


4) 제품군 하나만 조회할 수 있다.

복수 제품군 비교 또는 전체 제품군 탐색 질문을 처리하기 어렵다.


5) 표현 방식에 의존한다.

"거래처 기준", "고객 단위", "계정별"과 같은 유사 표현을 고객별 집계로
인식하지 못할 수 있다.


6) 조회와 최종 답변 생성 책임이 섞여 있다.

다른 툴 결과와 교차분석하려면 판매 결과를 다시 분해해야 한다.


6. TO-BE 역할
--------------

TO-BE sales_trend_tool의 역할은 다음으로 제한한다.

- 구조화된 판매 조회 조건 검증
- 판매 데이터 조회
- 판매 도메인 내부 계산
- 구조화된 판매 결과 반환

다음 책임은 OpenAI LLM 또는 상위 오케스트레이터가 담당한다.

- 자연어 질문 해석
- 필요한 툴 선택
- 기간 및 고객 조건 추출
- 판매, 수주, 재고, 뉴스 결과 비교
- 최종 자연어 답변 작성
- 브리핑 형식 결정


7. TO-BE 입력 스키마
---------------------

권장 형태:

class SalesTrendToolInput(BaseModel):
    start_month: str
    end_month: str
    product_groups: list[str]
    customer_ids: list[str] | None = None
    group_by: list[Literal["month", "customer", "product_group"]]
    metrics: list[Literal["qty", "revenue", "asp"]]


권장 Function Tool 형태:

@tool
def sales_trend_tool(
    start_month: str,
    end_month: str,
    product_groups: list[str],
    customer_ids: list[str] | None = None,
    group_by: list[str] = ["month"],
    metrics: list[str] = ["qty", "revenue", "asp"],
) -> dict[str, Any]:
    """구조화된 조건으로 판매량, 매출 및 ASP 추이를 조회한다."""

    request = SalesTrendRequest(
        start_month=start_month,
        end_month=end_month,
        product_groups=product_groups,
        customer_ids=customer_ids,
        group_by=group_by,
        metrics=metrics,
    )

    result = get_sales_trend(request)
    return result.model_dump(mode="json")


8. TO-BE 툴 설명
-----------------

LLM에 제공할 툴 설명에는 호출 조건과 비호출 조건을 함께 작성한다.

권장 설명:

"판매량, 매출, ASP, 판매 증감, 판매 순위 및 판매 추이를 조회한다.
고객별 판매, 고객사별 매출, 고객별 ASP 질문은 이 툴에서 customer 기준으로
group_by 한다. 고객의 회사 정보나 등급 같은 프로필 정보만 필요한 경우에는
customer_profile_tool을 사용한다. 판매와 수주 또는 재고를 비교하는 질문에서는
해당 툴들과 함께 호출한다."


9. AS-IS / TO-BE 요청 비교
---------------------------

질문:

"최근 6개월 Mobile OLED 판매 매출 추이를 고객별로 분석해줘."

[AS-IS]

{
  "question": "최근 6개월 Mobile OLED 판매 매출 추이를 고객별로 분석해줘."
}

Tool 내부에서 생성되는 조건:

{
  "start_month": "2026-01",
  "end_month": "2026-06",
  "product_group": "Mobile OLED",
  "customer_id": null,
  "group_by_customer": true
}

[TO-BE]

OpenAI LLM이 생성하는 구조화 인자:

{
  "start_month": "2026-04",
  "end_month": "2026-09",
  "product_groups": ["Mobile OLED"],
  "customer_ids": null,
  "group_by": ["month", "customer"],
  "metrics": ["qty", "revenue", "asp"]
}

기간은 예시이며 실제 서비스 기준일 또는 DB의 최신 데이터 월을 기준으로 계산한다.


10. 다중 툴 질문 처리
---------------------

질문:

"최근 6개월 Mobile OLED의 고객별 판매 추이와 수주 현황을 비교해서 매출 감소
위험이 큰 고객을 알려줘."

OpenAI LLM이 선택할 툴:

1) sales_trend_tool
2) order_status_tool

sales_trend_tool 인자 예시:

{
  "start_month": "2026-04",
  "end_month": "2026-09",
  "product_groups": ["Mobile OLED"],
  "customer_ids": null,
  "group_by": ["month", "customer"],
  "metrics": ["qty", "revenue", "asp"]
}

order_status_tool도 동일한 기간, 제품군, 고객 집계 단위로 호출한다.

두 툴의 실행 결과를 받은 LLM은 customer_id와 month를 기준으로 데이터를 비교한다.

- 고객별 판매 증감률
- 고객별 수주 증감률
- 판매 대비 수주 부족 여부
- 매출 감소 위험 고객
- 분석 한계와 추가 확인 데이터


11. TO-BE 반환 구조
--------------------

판매 툴은 최종 사용자 문장보다 다른 툴과 결합하기 쉬운 구조화 데이터를 반환한다.

권장 예시:

{
  "tool_name": "sales_trend_tool",
  "status": "success",
  "query": {
    "start_month": "2026-04",
    "end_month": "2026-09",
    "product_groups": ["Mobile OLED"],
    "customer_ids": null,
    "group_by": ["month", "customer"]
  },
  "data": [
    {
      "month": "2026-04",
      "product_group": "Mobile OLED",
      "customer_id": "CUST_A",
      "customer_name": "Customer A",
      "qty": 1000,
      "revenue": 250000.0,
      "asp": 250.0
    }
  ],
  "aggregates": {
    "total_qty": 1000,
    "total_revenue": 250000.0
  },
  "warnings": []
}


12. 데이터 조회 계층 변경 방향
-----------------------------

현재 SalesTrendRequest:

- product_group: str
- customer_id: str | None
- group_by_customer: bool

TO-BE SalesTrendRequest:

- product_groups: list[str]
- customer_ids: list[str] | None
- group_by: list["month" | "customer" | "product_group"]
- metrics: list["qty" | "revenue" | "asp"]

SQL도 선택된 group_by 값에 따라 허용된 고정 SQL 조각만 조합한다.
사용자가 입력한 컬럼명이나 SQL 문자열을 직접 쿼리에 연결해서는 안 된다.


13. 오류 처리
-------------

판매 툴에서 오류가 발생하면 자연어 답변으로 감추지 말고 구조화된 오류를 반환한다.

예시:

{
  "tool_name": "sales_trend_tool",
  "status": "error",
  "error_code": "SALES_QUERY_FAILED",
  "message": "판매 데이터를 조회하지 못했습니다.",
  "retryable": true
}

상위 오케스트레이터는 판매 툴 실패 여부를 확인한 뒤 다른 툴의 결과만으로 부분
답변을 만들거나 사용자에게 누락된 분석 범위를 알린다.


14. 테스트 방향
---------------

[입력 스키마 테스트]

- 시작 월이 종료 월보다 늦으면 실패
- 잘못된 YYYY-MM 형식이면 실패
- 허용되지 않은 group_by 값이면 실패
- 빈 제품군 목록 처리
- 복수 고객 및 복수 제품군 처리

[LLM 툴 선택 테스트]

- "고객별 판매" -> sales_trend_tool만 선택
- "CUST_A의 판매" -> sales_trend_tool에 CUST_A 전달
- "판매와 수주 비교" -> sales_trend_tool + order_status_tool
- "판매와 재고 비교" -> sales_trend_tool + inventory_risk_tool
- "고객 프로필과 판매" -> customer_profile_tool + sales_trend_tool

[결과 테스트]

- 월별 합계 정확성
- 고객별 합계 정확성
- 제품군별 합계 정확성
- ASP 계산 정확성
- 결과 정렬 순서
- 누락 월 처리
- 데이터가 없을 때 빈 결과 처리
- DB 오류 시 구조화 오류 반환


15. 단계별 전환 순서
--------------------

1단계
- SalesTrendRequest를 복수 제품군, 복수 고객, group_by 구조로 확장한다.

2단계
- get_sales_trend() SQL이 새 요청 구조를 처리하도록 변경한다.

3단계
- sales_trend_tool의 question: str 입력을 구조화 인자로 변경한다.

4단계
- OpenAI LLM에 명확한 Function Tool 스키마와 설명을 제공한다.

5단계
- 판매 툴이 화면용 최종 답변이 아니라 구조화된 판매 결과를 반환하게 한다.

6단계
- 상위 오케스트레이터에서 다른 툴 결과와 병렬 실행 및 교차분석한다.

7단계
- 기존 질문 및 복합 질문을 대상으로 툴 선택, 인자, 결과 스키마 테스트를 추가한다.


16. 최종 TO-BE 책임 분리
------------------------

[OpenAI LLM]

- 질문 의미 해석
- 기간, 제품, 고객, 집계 기준 추출
- 필요한 툴 복수 선택
- 툴 결과 교차분석
- 최종 답변 작성

[sales_trend_tool]

- 구조화된 입력 검증
- 판매 데이터 조회
- 판매 도메인 계산
- 구조화된 결과 반환

[애플리케이션 서버]

- LLM 실행 계획 검증
- 툴 병렬 실행
- 타임아웃 및 오류 처리
- 실행 이력과 tools_used 기록
- 최종 응답 스키마 검증


17. 핵심 결론
-------------

AS-IS sales_trend_tool은 질문 해석, 조회, 분석, 답변 생성을 한 번에 담당한다.

TO-BE에서는 OpenAI LLM이 질문 해석과 툴 선택을 담당하고 sales_trend_tool은
구조화된 판매 조회 기능에 집중해야 한다.

가장 중요한 변경은 다음 세 가지다.

1) question: str 입력을 구조화된 Function Tool 인자로 변경
2) 단일 제품 및 단일 고객 구조를 복수 조건과 동적 group_by 구조로 확장
3) 최종 답변 생성을 Tool 밖으로 이동하여 다른 툴 결과와 교차분석 가능하게 구성
