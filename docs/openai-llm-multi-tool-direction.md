OpenAI LLM 기반 다중 툴 호출 구현 방향
========================================

1. 목표
-------

현재의 "질문 -> 툴 하나 선택" 구조를 다음 구조로 변경한다.

사용자 질문
  -> OpenAI LLM이 질문 분석 및 실행 계획 생성
  -> 필요한 데이터 툴을 복수 선택
  -> 서버가 선택된 툴을 병렬 실행
  -> 툴 결과를 공통 형식으로 정규화
  -> OpenAI LLM이 결과를 교차분석
  -> 답변, 표, 차트, 브리핑 형태로 반환


2. 현재 구조의 한계
-------------------

현재 agent.py의 RuleBasedChatModel과 choose_tool_name()은 키워드 우선순위에 따라
툴 이름 하나만 반환한다.

예를 들어 다음 질문에는 판매와 재고 키워드가 모두 포함되어 있다.

"TV OLED의 판매 감소가 재고 과잉으로 이어지고 있는지 월별 데이터를 기준으로 분석해줘."

하지만 현재 구조에서는 재고 조건이 판매 조건보다 먼저 검사되므로
inventory_risk_tool 하나만 선택된다.

따라서 2개 이상의 업무 영역을 비교하는 질문에는 현재 구조가 적합하지 않다.


3. 권장 API 및 기본 구조
------------------------

OpenAI Responses API와 Function Calling을 사용한다.

- LLM이 질문의 의미를 분석해 필요한 커스텀 툴을 선택한다.
- 하나의 질문에서 여러 툴을 호출할 수 있도록 한다.
- 서로 의존하지 않는 툴은 병렬로 실행한다.
- 툴 실행 결과를 모델에 다시 전달해 최종 답변을 생성한다.
- 실행 계획과 최종 응답은 Structured Outputs로 구조를 강제한다.

권장 처리 흐름:

QuestionParser
  -> QueryPlanner
  -> ParallelToolExecutor
  -> ResultNormalizer
  -> CrossDomainAnalyzer
  -> ResponseComposer


4. RuleBasedChatModel 교체
-------------------------

현재 LangChain create_agent() 구조를 유지하면서 RuleBasedChatModel을
OpenAI ChatModel로 교체할 수 있다.

개념 예시:

model = ChatOpenAI(
    model="사용할 OpenAI 모델",
    reasoning_effort="low",
)

단, 모델만 교체해서는 충분하지 않다. 각 툴의 입력 스키마와 설명을 명확하게
정의하고 여러 툴의 결과를 종합하는 단계도 구현해야 한다.


5. 툴 입력을 구조화된 인자로 변경
-----------------------------------

현재 툴은 질문 전체를 문자열 하나로 받는다.

예시:

def sales_trend_tool(question: str)

LLM Function Calling에서는 다음처럼 명확한 업무 인자를 받는 형태가 적합하다.

판매 툴 예시:

def sales_trend_tool(
    start_month: str,
    end_month: str,
    product_groups: list[str],
    customer_ids: list[str] | None,
    group_by_customer: bool,
)

수주 툴 예시:

def order_status_tool(
    start_date: str,
    end_date: str,
    product_groups: list[str],
    customer_ids: list[str] | None,
    statuses: list[str] | None,
    group_by_customer: bool,
)

각 툴의 인자는 JSON Schema로 엄격히 정의한다.


6. 실행 계획 스키마
-------------------

LLM이 바로 툴을 실행하게 할 수도 있지만, 먼저 실행 계획을 Structured Output으로
생성하게 하면 정확성, 테스트 가능성, 관찰 가능성이 좋아진다.

개념 예시:

class QueryPlan(BaseModel):
    tools: list[
        Literal[
            "sales",
            "orders",
            "inventory",
            "customer",
            "news",
        ]
    ]
    product_groups: list[str]
    customer_ids: list[str]
    start_month: str | None
    end_month: str | None
    group_by_customer: bool
    output_mode: Literal["analysis", "comparison", "briefing"]

질문 예시:

"TV OLED의 판매 감소가 재고 과잉으로 이어지고 있는지 월별 데이터를 기준으로 분석해줘."

예상 실행 계획:

{
  "tools": ["sales", "inventory"],
  "product_groups": ["TV OLED"],
  "customer_ids": [],
  "start_month": null,
  "end_month": null,
  "group_by_customer": false,
  "output_mode": "comparison"
}


7. 고객 툴과 고객별 집계 구분
-----------------------------

"고객"이라는 단어가 포함되었다고 항상 고객 프로필 툴을 호출하면 안 된다.

"고객별 판매 추이"
  -> 판매 툴 호출
  -> group_by_customer=true
  -> 고객 프로필 툴은 호출하지 않음

"CUST_A의 프로필과 판매 추이"
  -> 고객 프로필 툴 호출
  -> 판매 툴 호출
  -> customer_ids=["CUST_A"]

고객 ID가 질문에 없을 때 임의로 CUST_A를 기본값으로 사용하는 동작도 제거하고
None 또는 빈 목록을 반환하도록 변경하는 것이 안전하다.


8. 툴별 변경 방향
------------------

[판매 툴]
- 월별, 고객별, 제품별 그룹화 지원
- 복수 고객 및 복수 제품군 지원
- 질문에서 추출된 실제 기간 사용
- 판매량, 매출, ASP 및 증감률 반환

[수주 툴]
- 고객별 및 제품별 그룹화 지원
- 복수 고객 지원
- 확정, 지연, 취소, 출하 등 복수 상태 필터 지원
- 월별 주문량과 상태별 건수 반환

[재고 툴]
- 특정 월 하나가 아니라 월별 기간 조회 지원
- 복수 제품군 및 전체 제품군 비교 지원
- 기말재고, 안전재고, 생산량, 부족량, 과잉량 반환
- 고객 전용 재고 데이터가 없다면 고객 재고라고 표현하지 않음
- 고객 주문량과 제품 단위 재고를 비교하는 방식으로 처리

[고객 툴]
- 고객 ID, 고객명, 등급, 지역 등 프로필 정보가 필요할 때만 호출
- 단순한 "고객별 판매" 표현에는 호출하지 않음
- 명시된 복수 고객 조회 지원

[경쟁사 뉴스 툴]
- 복수 경쟁사 지원
- 제품군, 가격, 수요, 공급, 생산능력 조건 지원
- 뉴스 발생일, 출처, 영향도와 근거 반환

[브리핑]
- 별도의 데이터 조회 툴보다 결과 표현 방식으로 처리
- output_mode="briefing"일 때 선택된 데이터 툴 결과를 브리핑 형식으로 작성
- 항상 모든 데이터 툴을 고정 호출하지 않음


9. 툴 설명 작성 원칙
--------------------

LLM이 정확한 툴을 선택하려면 각 툴 설명에 호출 조건과 비호출 조건을 함께 적는다.

get_sales_trend
- 판매량, 매출, ASP, 판매 증감 질문에 사용한다.
- "고객별 판매"는 group_by_customer=true로 처리한다.
- 고객 프로필이 필요하지 않으면 customer_profile을 호출하지 않는다.

get_customer_profile
- 고객명, 지역, 등급, 담당자 등 고객 마스터 정보가 필요할 때 사용한다.
- 단순히 "고객별 판매"라는 표현에는 사용하지 않는다.

get_inventory_risk
- 기말재고, 안전재고, 과잉재고, 부족재고 분석에 사용한다.

get_order_status
- 주문량, 수주량, 납기, 지연, 취소, 출하 상태 분석에 사용한다.

get_competitor_news
- 경쟁사, 시장, 가격, 수요, 공급, 생산능력 관련 외부 동향에 사용한다.


10. 병렬 툴 실행
----------------

판매, 수주, 재고, 고객, 뉴스 조회는 대부분 서로 의존하지 않으므로 병렬로 실행한다.

예시:

판매 툴 -----\
수주 툴 ------+--> 결과 정규화 --> LLM 교차분석
재고 툴 -----/

툴 하나가 실패해도 전체 요청을 실패시키지 않고 부분 결과를 제공한다.

예시:

"판매와 수주 분석은 완료했습니다. 재고 조회는 실패하여 공급 위험 계산에서
제외했습니다."


11. 공통 결과 형식
------------------

서로 다른 툴의 결과를 비교하려면 공통 차원을 가져야 한다.

권장 공통 필드:

- month 또는 date
- product_group
- customer_id
- customer_name
- metric
- value
- unit
- source_tool

판매가 월별인데 재고는 한 달만 반환하거나 수주 결과에 고객 정보가 없다면
교차분석이 제한되므로 각 데이터 툴의 조회 단위를 맞춰야 한다.


12. 교차분석 규칙
-----------------

판매 + 수주
- 고객별 매출 증감률과 수주 증감률 비교
- 판매 대비 수주 부족 구간 탐지

판매 + 재고
- 판매 감소와 재고 증가가 동시에 발생한 월 탐지
- 판매 속도 대비 재고 과잉 여부 분석

수주 + 재고
- 확정 주문량 대비 가용 재고 계산
- 공급 부족 가능성 분석

판매 + 수주 + 재고
- 실적, 수요, 공급을 결합한 위험 분석

뉴스 + 내부 데이터
- 뉴스 발생 시점과 판매, ASP, 수주 변화 시점 비교
- 확인된 사실과 추정 가능한 영향을 구분


13. 인과관계 표현 주의
----------------------

질문에 "원인", "영향", "이탈 가능성"이 포함되어도 데이터만으로 인과관계를
확정해서는 안 된다.

최종 답변에서 다음을 구분한다.

- 데이터로 확인된 사실
- 관찰된 상관관계
- 추정 가능한 원인
- 추가로 필요한 데이터

뉴스 시점과 매출 감소 시점이 일치한다는 이유만으로 해당 뉴스가 매출 감소의
직접 원인이라고 단정하지 않는다.


14. 최종 응답 구조
------------------

최종 LLM 응답도 Structured Output을 사용해 프론트엔드 형식과 일치시킨다.

권장 필드:

{
  "answer": "분석 결과 설명",
  "summary": [],
  "tables": [],
  "charts": [],
  "insights": [],
  "risk_signals": [],
  "actions": [],
  "tools_used": [],
  "limitations": []
}

tools_used에는 실제 실행에 성공한 툴만 넣는다.


15. 테스트 방향
---------------

30개 복합 질문 각각에 대해 다음 항목을 검증한다.

1) LLM이 생성한 실행 계획의 툴 목록
2) 추출된 기간, 제품, 고객, 경쟁사, 주문 상태
3) 각 툴에 전달된 구조화 인자
4) 계획에 포함된 모든 툴의 실제 호출 여부
5) 툴 결과가 최종 교차분석에 포함됐는지
6) 고객별 집계와 고객 프로필 조회가 올바르게 구분되는지
7) 일부 툴 실패 시 부분 답변이 생성되는지
8) 사실, 상관관계, 추정이 구분되는지
9) 최종 JSON이 프론트엔드 스키마와 일치하는지

LLM 출력은 매번 표현이 달라질 수 있으므로 문장 전체를 비교하기보다
툴 목록, 인자, 응답 스키마, 핵심 수치와 같은 구조적 결과를 검증한다.


16. 최종 권장안
---------------

LLM에게 모든 실행을 완전히 맡기는 구조보다 다음 하이브리드 구조를 권장한다.

- OpenAI LLM: 질문 해석, 실행 계획 생성, 결과 교차분석, 답변 작성
- 애플리케이션 서버: 계획 검증, 툴 실행, 병렬 처리, 오류 처리, 권한 통제
- 데이터 툴: 구조화된 원천 데이터와 계산 결과 제공
- Structured Outputs: 실행 계획과 최종 응답 형식 보장

최종 구조:

OpenAI LLM
  -> QueryPlan 생성
  -> 서버가 선택된 툴을 검증하고 병렬 실행
  -> 결과를 공통 형식으로 정규화
  -> OpenAI LLM이 교차분석
  -> 프론트엔드용 구조화 JSON 반환

30개 질문 조합마다 별도의 복합 툴을 만드는 대신 범용 오케스트레이터 하나를
구축하는 것이 유지보수성과 확장성 측면에서 적합하다.


17. 공식 OpenAI 문서
--------------------

Responses API:
https://developers.openai.com/api/reference/cli/resources/responses/methods/create

모델 및 툴 호출 가이드:
https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.5
