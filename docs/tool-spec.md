# Display Market Intelligence Agent Tool 공통 규격서

## 1. 문서 개요

| 항목 | 내용 |
| --- | --- |
| 문서명 | MCP Tool 또는 MCP 스타일 Python Tool 개발 공통 규격서 |
| 프로젝트 | Display Market Intelligence Agent |
| 대상 환경 | Python 3.12, FastAPI, LangGraph, PostgreSQL, Spring Boot 2.1.18, Vue 2.6.10 |
| 대상 Tool | `get_sales_trend`, `get_order_status`, `get_inventory_risk`, `get_customer_brief`, `search_competitor_news`, `create_briefing_report` |
| 데이터 원칙 | 실제 업무 데이터 미사용, Synthetic Data만 사용 |

이 문서는 Display Market Intelligence Agent에서 사용하는 MCP Tool 또는 MCP 스타일 Python Tool의 입력, 출력, 오류, 차트, 리스크, 액션 작성 규칙을 정의한다.

각 담당자는 이 문서를 기준으로 Tool을 구현하며, Tool 응답은 LangGraph Agent, FastAPI API, Spring Boot 중계 API, Vue 화면에서 일관되게 사용할 수 있어야 한다.

## 2. Tool 개발 목적

Tool Layer는 LangGraph Agent가 자연어 질문을 업무 데이터 조회 및 분석 작업으로 분해했을 때 실제 데이터를 조회하고, Agent가 해석하기 쉬운 구조화 JSON을 반환하는 계층이다.

| 목적 | 설명 |
| --- | --- |
| 업무 데이터 조회 표준화 | 판매, 수주, 재고, 고객사, 경쟁사 뉴스 데이터를 동일한 호출 방식으로 조회 |
| Agent 응답 품질 향상 | LLM이 임의로 수치를 만들지 않도록 Tool에서 근거 데이터를 구조화하여 제공 |
| 화면 렌더링 지원 | Vue 화면에서 표, 차트, 리스크, 권장 조치를 별도 가공 없이 표시할 수 있도록 표준 필드 제공 |
| 백엔드 연동 단순화 | Spring Boot와 FastAPI 사이의 응답 구조를 고정하여 중계 API 구현 부담 감소 |
| 테스트 용이성 확보 | Tool 단위 테스트에서 입력, 출력, 오류 포맷을 명확히 검증 |

## 3. Tool 구현 원칙

| 원칙 | 기준 |
| --- | --- |
| 순수 함수형 구현 | 동일 입력과 동일 DB 상태에서는 동일 결과를 반환해야 한다. |
| Synthetic Data 사용 | PoC 범위에서는 실제 고객사, 가격, 계약, 뉴스 데이터를 사용하지 않는다. |
| SQL 파라미터 바인딩 | PostgreSQL 조회 시 문자열 결합 SQL을 사용하지 않고 파라미터 바인딩을 사용한다. |
| 예외 캡처 | Tool 내부 예외는 공통 오류 JSON으로 변환해 반환한다. |
| 빈 결과 허용 | 조회 결과가 없어도 `status`는 `success`로 반환하고, `summary`에 조회 결과가 없음을 명시한다. |
| 화면 독립성 | Tool은 Vue 화면 문구나 HTML을 반환하지 않는다. JSON 데이터만 반환한다. |
| LLM 비의존 | Tool은 핵심 수치 계산과 필터링을 직접 수행한다. LLM은 요약 문장 생성 보조에만 사용한다. |

## 4. 공통 입력 필드

모든 Tool은 아래 공통 입력 필드를 받을 수 있어야 한다. Tool별 필수 여부는 각 Tool 섹션에서 별도로 정의한다.

| 필드 | 타입 | 필수 | 설명 | 예시 |
| --- | --- | --- | --- | --- |
| `request_id` | String | 권장 | 호출 추적용 ID. FastAPI 또는 LangGraph 실행 단위에서 생성한다. | `req-20260824-0001` |
| `user_id` | String | 선택 | 요청 사용자 ID. PoC에서는 권한 검증보다 로그 추적 목적이다. | `demo.user` |
| `locale` | String | 선택 | 응답 언어 및 숫자 표현 기준. 기본값은 `ko-KR`이다. | `ko-KR` |
| `timezone` | String | 선택 | 기간 계산 기준 타임존. 기본값은 `Asia/Seoul`이다. | `Asia/Seoul` |
| `start_date` | String | 조건부 | 조회 시작일. ISO 날짜 형식 `YYYY-MM-DD`를 사용한다. | `2026-01-01` |
| `end_date` | String | 조건부 | 조회 종료일. ISO 날짜 형식 `YYYY-MM-DD`를 사용한다. | `2026-03-31` |
| `period` | String | 선택 | 사전 정의 기간. `start_date`, `end_date`가 있으면 해당 값이 우선한다. | `last_3_months` |
| `customer_id` | String | 조건부 | 고객사 식별자. 고객사 단위 조회 시 사용한다. | `CUST-SAM-001` |
| `customer_name` | String | 선택 | 사용자 표시용 고객사명 또는 검색 조건. | `Samsung Display` |
| `region` | String | 선택 | 지역 필터. | `KR`, `CN`, `US`, `EU`, `ALL` |
| `product_family` | String | 선택 | 제품군 필터. | `OLED`, `LCD`, `MicroLED`, `ALL` |
| `metric` | String | 선택 | 분석 지표. | `revenue`, `quantity`, `order_amount`, `inventory_qty` |
| `group_by` | String | 선택 | 집계 기준. | `month`, `region`, `customer`, `product_family` |
| `limit` | Integer | 선택 | 최대 반환 건수. 기본값은 Tool별로 정의한다. | `10` |
| `include_chart` | Boolean | 선택 | `chart_data` 포함 여부. 기본값은 `true`이다. | `true` |
| `include_actions` | Boolean | 선택 | `actions` 포함 여부. 기본값은 `true`이다. | `true` |

### 4.1 기간 필드 기준

| 조건 | 처리 기준 |
| --- | --- |
| `start_date`, `end_date` 모두 있음 | 두 날짜를 포함하여 조회한다. |
| `start_date`만 있음 | `start_date`부터 현재 기준일 또는 데이터 최대일까지 조회한다. |
| `end_date`만 있음 | Tool별 기본 조회 시작일부터 `end_date`까지 조회한다. |
| 둘 다 없고 `period` 있음 | `period`를 날짜 범위로 변환해 조회한다. |
| 둘 다 없고 `period` 없음 | Tool별 기본 기간을 사용한다. 일반 조회는 최근 3개월, 뉴스는 최근 30일을 기본으로 한다. |

### 4.2 공통 입력 예시

```json
{
  "request_id": "req-20260824-0001",
  "user_id": "demo.user",
  "locale": "ko-KR",
  "timezone": "Asia/Seoul",
  "start_date": "2026-01-01",
  "end_date": "2026-03-31",
  "customer_id": "CUST-SAM-001",
  "region": "KR",
  "product_family": "OLED",
  "include_chart": true,
  "include_actions": true
}
```

## 5. 공통 출력 JSON 포맷

모든 Tool은 성공 시 반드시 아래 구조를 반환한다. 사용하지 않는 필드도 생략하지 않고 빈 배열 또는 빈 객체로 반환한다.

```json
{
  "tool_name": "",
  "status": "success",
  "summary": "",
  "data": [],
  "insights": [],
  "risk_signals": [],
  "chart_data": {},
  "actions": []
}
```

### 5.1 출력 필드 설명

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `tool_name` | String | 필수 | 실행된 Tool 이름. 요청 Tool명과 동일해야 한다. |
| `status` | String | 필수 | 성공 시 `success`를 반환한다. |
| `summary` | String | 필수 | Tool 결과를 한두 문장으로 요약한다. |
| `data` | Array | 필수 | 원천 조회 또는 집계 결과 목록. 표 렌더링 가능한 JSON 배열이다. |
| `insights` | Array | 필수 | 데이터에서 도출한 주요 해석 목록. |
| `risk_signals` | Array | 필수 | 리스크 신호 목록. 없으면 빈 배열이다. |
| `chart_data` | Object | 필수 | 차트 렌더링 표준 구조. 차트가 없으면 빈 객체이다. |
| `actions` | Array | 필수 | 권장 후속 조치 목록. 없으면 빈 배열이다. |

## 6. 공통 오류 JSON 포맷

모든 Tool은 오류 발생 시 예외를 그대로 노출하지 않고 아래 구조를 반환한다.

```json
{
  "tool_name": "",
  "status": "error",
  "summary": "처리 중 오류가 발생했습니다.",
  "error": {
    "code": "",
    "message": ""
  },
  "data": [],
  "insights": [],
  "risk_signals": [],
  "chart_data": {},
  "actions": []
}
```

### 6.1 오류 코드 기준

| 코드 | 설명 | 사용 예 |
| --- | --- | --- |
| `INVALID_REQUEST` | 필수 입력 누락 또는 형식 오류 | `start_date`가 `YYYY-MM-DD` 형식이 아님 |
| `INVALID_DATE_RANGE` | 기간 조건 오류 | `start_date`가 `end_date`보다 늦음 |
| `UNKNOWN_FILTER` | 지원하지 않는 필터 값 | `product_family`가 정의되지 않은 값 |
| `NOT_FOUND` | 요청 대상 없음 | 존재하지 않는 `customer_id` |
| `DATABASE_ERROR` | PostgreSQL 연결 또는 쿼리 실패 | DB timeout, SQL 오류 |
| `TOOL_EXECUTION_ERROR` | Tool 내부 처리 실패 | 집계 계산 중 예외 |
| `EXTERNAL_SOURCE_ERROR` | 외부 소스 또는 뉴스 조회 실패 | 경쟁사 뉴스 API 호출 실패. PoC에서는 모의 데이터 조회 실패 |
| `REPORT_GENERATION_ERROR` | 보고서 생성 실패 | briefing report 구성 중 템플릿 오류 |

### 6.2 오류 응답 예시

```json
{
  "tool_name": "get_sales_trend",
  "status": "error",
  "summary": "처리 중 오류가 발생했습니다.",
  "error": {
    "code": "INVALID_DATE_RANGE",
    "message": "start_date는 end_date보다 늦을 수 없습니다."
  },
  "data": [],
  "insights": [],
  "risk_signals": [],
  "chart_data": {},
  "actions": []
}
```

## 7. chart_data 표준 구조

`chart_data`는 Vue 2.6.10 화면과 Agent 응답 생성에서 공통으로 사용할 수 있는 차트 데이터이다. Tool은 가능한 한 이 구조를 따른다.

```json
{
  "type": "line",
  "title": "월별 매출 추이",
  "x_axis": {
    "label": "월",
    "categories": ["2026-01", "2026-02", "2026-03"]
  },
  "y_axis": {
    "label": "매출",
    "unit": "KRW"
  },
  "series": [
    {
      "name": "OLED",
      "data": [1200000000, 1350000000, 1280000000]
    }
  ],
  "metadata": {
    "currency": "KRW",
    "source": "synthetic_postgresql",
    "generated_at": "2026-08-24T09:00:00+09:00"
  }
}
```

### 7.1 chart_data 필드 설명

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `type` | String | 필수 | 차트 유형. `line`, `bar`, `stacked_bar`, `pie`, `table` 중 하나를 권장한다. |
| `title` | String | 필수 | 차트 제목. 화면에 그대로 표시 가능해야 한다. |
| `x_axis.label` | String | 조건부 | X축 라벨. `pie` 차트에서는 생략 가능하다. |
| `x_axis.categories` | Array | 조건부 | X축 카테고리 목록. |
| `y_axis.label` | String | 조건부 | Y축 라벨. |
| `y_axis.unit` | String | 조건부 | 단위. `KRW`, `USD`, `EA`, `%`, `days`, `count` 등을 사용한다. |
| `series` | Array | 필수 | 차트 시리즈 목록. |
| `series[].name` | String | 필수 | 시리즈명. |
| `series[].data` | Array | 필수 | 데이터 배열. `x_axis.categories` 순서와 일치해야 한다. |
| `metadata` | Object | 선택 | 데이터 출처, 통화, 생성 시각 등 보조 정보. |

### 7.2 차트 작성 기준

| 상황 | 권장 차트 |
| --- | --- |
| 월별 또는 주별 추이 | `line` |
| 지역, 고객사, 제품군 비교 | `bar` |
| 구성비 비교 | `pie` |
| 지역별 제품군 누적 비교 | `stacked_bar` |
| 차트보다 행 단위 확인이 중요한 경우 | `table` |

## 8. risk_signals 표준 구조

`risk_signals`는 업무 리스크를 Agent와 화면이 동일하게 해석할 수 있도록 표준화한다.

```json
{
  "risk_id": "risk-inv-001",
  "severity": "high",
  "category": "inventory",
  "title": "OLED 패널 재고 과다",
  "description": "OLED 55인치 재고가 최근 4주 평균 출고량 대비 9.2주 수준입니다.",
  "metric": "weeks_of_supply",
  "value": 9.2,
  "threshold": 8.0,
  "related_entities": {
    "customer_id": "CUST-SAM-001",
    "product_family": "OLED",
    "region": "KR"
  }
}
```

### 8.1 risk_signals 필드 설명

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `risk_id` | String | 필수 | Tool 실행 내 고유 리스크 ID. |
| `severity` | String | 필수 | `low`, `medium`, `high`, `critical` 중 하나. |
| `category` | String | 필수 | `sales`, `order`, `inventory`, `customer`, `competitor`, `report` 중 하나. |
| `title` | String | 필수 | 리스크 제목. |
| `description` | String | 필수 | 수치 근거를 포함한 설명. |
| `metric` | String | 선택 | 리스크 판단에 사용한 지표명. |
| `value` | Number/String | 선택 | 현재 값. |
| `threshold` | Number/String | 선택 | 판단 기준값. |
| `related_entities` | Object | 선택 | 고객사, 제품군, 지역, 주문 등 관련 객체. |

### 8.2 severity 기준

| severity | 기준 |
| --- | --- |
| `low` | 참고 수준. 단기 조치 없이 모니터링 가능 |
| `medium` | 담당자 확인 필요. 추세가 지속되면 업무 영향 가능 |
| `high` | 단기 대응 필요. 매출, 공급, 고객 대응에 직접 영향 가능 |
| `critical` | 즉시 대응 필요. 주요 고객, 대형 수주, 공급 중단 수준의 영향 가능 |

## 9. actions 작성 기준

`actions`는 Tool 결과를 기반으로 담당자가 다음에 무엇을 해야 하는지 표현한다. 단순 설명이 아니라 실행 가능한 조치여야 한다.

```json
{
  "action_id": "act-001",
  "priority": "high",
  "owner_role": "sales_manager",
  "title": "고객사별 OLED 수주 전환 가능성 확인",
  "description": "3월 수주 금액이 전월 대비 감소한 고객사를 대상으로 영업 담당자가 전환 지연 사유를 확인합니다.",
  "due_hint": "이번 주 내",
  "related_tool": "get_order_status",
  "related_entities": {
    "customer_id": "CUST-SAM-001",
    "product_family": "OLED"
  }
}
```

### 9.1 actions 필드 설명

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `action_id` | String | 필수 | Tool 실행 내 고유 액션 ID. |
| `priority` | String | 필수 | `low`, `medium`, `high`, `urgent` 중 하나. |
| `owner_role` | String | 선택 | 권장 담당 역할. 예: `sales_manager`, `supply_planner`, `account_owner` |
| `title` | String | 필수 | 실행할 조치 제목. |
| `description` | String | 필수 | 구체적인 실행 내용. |
| `due_hint` | String | 선택 | 권장 기한. 예: `오늘`, `이번 주 내`, `다음 S&OP 회의 전` |
| `related_tool` | String | 선택 | 액션을 생성한 Tool 이름. |
| `related_entities` | Object | 선택 | 고객사, 제품군, 지역, 주문 등 관련 객체. |

### 9.2 actions 작성 규칙

| 규칙 | 설명 |
| --- | --- |
| 동사로 작성 | `확인`, `공유`, `조정`, `검토`, `재계산`, `후속 미팅 설정`처럼 실행 동사를 포함한다. |
| 근거 연결 | 어떤 수치나 리스크 때문에 필요한 조치인지 `description`에 포함한다. |
| 담당 역할 명시 | 가능한 경우 `owner_role`을 지정한다. |
| 과도한 단정 금지 | Synthetic Data 기반 PoC이므로 실제 계약 변경, 가격 변경을 확정 표현하지 않는다. |
| 화면 표시 가능 문장 | Vue 화면에 그대로 노출되어도 자연스럽고 짧은 문장으로 작성한다. |

## 10. Tool별 역할 및 Request/Response 예시

## 10.1 get_sales_trend

### 역할

판매 실적 추이를 기간, 지역, 고객사, 제품군 기준으로 집계한다. 매출, 판매 수량, 전월 대비 증감률, 주요 하락 또는 상승 구간을 반환한다.

| 항목 | 기준 |
| --- | --- |
| 주요 데이터 | 판매 실적, 제품군, 고객사, 지역, 월별 집계 |
| 기본 기간 | 최근 3개월 |
| 권장 차트 | `line`, `bar` |
| 주요 리스크 | 매출 급감, 특정 고객사 의존도 증가, 제품군별 역성장 |

### Request 예시

```json
{
  "request_id": "req-sales-001",
  "start_date": "2026-01-01",
  "end_date": "2026-03-31",
  "region": "KR",
  "product_family": "OLED",
  "metric": "revenue",
  "group_by": "month",
  "include_chart": true
}
```

### Response 예시

```json
{
  "tool_name": "get_sales_trend",
  "status": "success",
  "summary": "2026년 1분기 KR 지역 OLED 매출은 2월에 상승한 뒤 3월에 소폭 하락했습니다.",
  "data": [
    {
      "period": "2026-01",
      "region": "KR",
      "product_family": "OLED",
      "revenue": 1200000000,
      "quantity": 4800,
      "mom_change_rate": null
    },
    {
      "period": "2026-02",
      "region": "KR",
      "product_family": "OLED",
      "revenue": 1350000000,
      "quantity": 5100,
      "mom_change_rate": 12.5
    },
    {
      "period": "2026-03",
      "region": "KR",
      "product_family": "OLED",
      "revenue": 1280000000,
      "quantity": 4950,
      "mom_change_rate": -5.2
    }
  ],
  "insights": [
    "2월 매출은 전월 대비 12.5% 증가했습니다.",
    "3월 매출은 전월 대비 5.2% 감소했지만 1월 대비로는 높은 수준입니다."
  ],
  "risk_signals": [
    {
      "risk_id": "risk-sales-001",
      "severity": "medium",
      "category": "sales",
      "title": "3월 매출 감소",
      "description": "3월 OLED 매출이 전월 대비 5.2% 감소했습니다.",
      "metric": "mom_change_rate",
      "value": -5.2,
      "threshold": -5.0,
      "related_entities": {
        "region": "KR",
        "product_family": "OLED"
      }
    }
  ],
  "chart_data": {
    "type": "line",
    "title": "KR 지역 OLED 월별 매출 추이",
    "x_axis": {
      "label": "월",
      "categories": ["2026-01", "2026-02", "2026-03"]
    },
    "y_axis": {
      "label": "매출",
      "unit": "KRW"
    },
    "series": [
      {
        "name": "OLED",
        "data": [1200000000, 1350000000, 1280000000]
      }
    ],
    "metadata": {
      "currency": "KRW",
      "source": "synthetic_postgresql"
    }
  },
  "actions": [
    {
      "action_id": "act-sales-001",
      "priority": "medium",
      "owner_role": "sales_manager",
      "title": "3월 매출 감소 원인 확인",
      "description": "KR 지역 OLED 매출 감소가 특정 고객사 또는 제품 모델에 집중되어 있는지 확인합니다.",
      "due_hint": "이번 주 내",
      "related_tool": "get_sales_trend",
      "related_entities": {
        "region": "KR",
        "product_family": "OLED"
      }
    }
  ]
}
```

## 10.2 get_order_status

### 역할

수주 현황을 고객사, 제품군, 지역, 진행 단계 기준으로 조회한다. 수주 금액, 예상 납기, 단계별 병목, 지연 가능성을 반환한다.

| 항목 | 기준 |
| --- | --- |
| 주요 데이터 | 주문, 수주 금액, 주문 상태, 예상 납기, 고객사 |
| 기본 기간 | 최근 3개월 |
| 권장 차트 | `bar`, `stacked_bar` |
| 주요 리스크 | 납기 지연, 특정 단계 정체, 대형 주문 지연 |

### Request 예시

```json
{
  "request_id": "req-order-001",
  "customer_id": "CUST-SAM-001",
  "start_date": "2026-01-01",
  "end_date": "2026-03-31",
  "product_family": "OLED",
  "group_by": "status",
  "include_chart": true
}
```

### Response 예시

```json
{
  "tool_name": "get_order_status",
  "status": "success",
  "summary": "CUST-SAM-001의 OLED 수주는 총 3건이며, 1건은 생산 단계에서 지연 가능성이 있습니다.",
  "data": [
    {
      "order_id": "ORD-2026-001",
      "customer_id": "CUST-SAM-001",
      "product_family": "OLED",
      "order_amount": 820000000,
      "status": "confirmed",
      "expected_delivery_date": "2026-04-15",
      "delay_days": 0
    },
    {
      "order_id": "ORD-2026-002",
      "customer_id": "CUST-SAM-001",
      "product_family": "OLED",
      "order_amount": 610000000,
      "status": "production",
      "expected_delivery_date": "2026-04-30",
      "delay_days": 5
    }
  ],
  "insights": [
    "생산 단계 주문 1건에서 예상 납기 대비 5일 지연 가능성이 있습니다.",
    "확정 수주 금액 기준 OLED 비중이 가장 높습니다."
  ],
  "risk_signals": [
    {
      "risk_id": "risk-order-001",
      "severity": "high",
      "category": "order",
      "title": "생산 단계 납기 지연 가능성",
      "description": "ORD-2026-002 주문의 예상 지연일이 5일로 확인되었습니다.",
      "metric": "delay_days",
      "value": 5,
      "threshold": 3,
      "related_entities": {
        "order_id": "ORD-2026-002",
        "customer_id": "CUST-SAM-001"
      }
    }
  ],
  "chart_data": {
    "type": "bar",
    "title": "수주 상태별 금액",
    "x_axis": {
      "label": "상태",
      "categories": ["confirmed", "production"]
    },
    "y_axis": {
      "label": "수주 금액",
      "unit": "KRW"
    },
    "series": [
      {
        "name": "order_amount",
        "data": [820000000, 610000000]
      }
    ],
    "metadata": {
      "currency": "KRW",
      "source": "synthetic_postgresql"
    }
  },
  "actions": [
    {
      "action_id": "act-order-001",
      "priority": "high",
      "owner_role": "supply_planner",
      "title": "ORD-2026-002 생산 일정 확인",
      "description": "예상 지연일이 5일인 주문의 생산 병목 공정과 대체 납기 가능성을 확인합니다.",
      "due_hint": "오늘",
      "related_tool": "get_order_status",
      "related_entities": {
        "order_id": "ORD-2026-002"
      }
    }
  ]
}
```

## 10.3 get_inventory_risk

### 역할

재고 수준과 출고 추이를 기반으로 과다 재고, 부족 재고, 장기 체류 재고 리스크를 분석한다.

| 항목 | 기준 |
| --- | --- |
| 주요 데이터 | 재고 수량, 안전 재고, 평균 출고량, 보유 주수, 창고, 제품군 |
| 기본 기간 | 현재 기준 재고와 최근 4주 출고 |
| 권장 차트 | `bar`, `table` |
| 주요 리스크 | 재고 부족, 재고 과다, 장기 체류 |

### Request 예시

```json
{
  "request_id": "req-inventory-001",
  "region": "KR",
  "product_family": "OLED",
  "limit": 5,
  "include_chart": true
}
```

### Response 예시

```json
{
  "tool_name": "get_inventory_risk",
  "status": "success",
  "summary": "KR 지역 OLED 재고 중 55인치 모델은 과다 재고, 65인치 모델은 부족 가능성이 있습니다.",
  "data": [
    {
      "sku": "OLED-55-A",
      "region": "KR",
      "inventory_qty": 9200,
      "safety_stock_qty": 4000,
      "avg_weekly_shipments": 1000,
      "weeks_of_supply": 9.2,
      "risk_type": "overstock"
    },
    {
      "sku": "OLED-65-B",
      "region": "KR",
      "inventory_qty": 1100,
      "safety_stock_qty": 1800,
      "avg_weekly_shipments": 900,
      "weeks_of_supply": 1.2,
      "risk_type": "shortage"
    }
  ],
  "insights": [
    "OLED-55-A는 9.2주치 재고로 과다 재고 기준을 초과했습니다.",
    "OLED-65-B는 안전 재고보다 700대 낮아 공급 부족 가능성이 있습니다."
  ],
  "risk_signals": [
    {
      "risk_id": "risk-inv-001",
      "severity": "high",
      "category": "inventory",
      "title": "OLED-55-A 과다 재고",
      "description": "OLED-55-A 재고가 최근 4주 평균 출고량 대비 9.2주 수준입니다.",
      "metric": "weeks_of_supply",
      "value": 9.2,
      "threshold": 8.0,
      "related_entities": {
        "sku": "OLED-55-A",
        "region": "KR"
      }
    },
    {
      "risk_id": "risk-inv-002",
      "severity": "high",
      "category": "inventory",
      "title": "OLED-65-B 부족 가능성",
      "description": "OLED-65-B 재고가 안전 재고보다 700대 부족합니다.",
      "metric": "inventory_gap",
      "value": -700,
      "threshold": 0,
      "related_entities": {
        "sku": "OLED-65-B",
        "region": "KR"
      }
    }
  ],
  "chart_data": {
    "type": "bar",
    "title": "SKU별 재고 보유 주수",
    "x_axis": {
      "label": "SKU",
      "categories": ["OLED-55-A", "OLED-65-B"]
    },
    "y_axis": {
      "label": "보유 주수",
      "unit": "weeks"
    },
    "series": [
      {
        "name": "weeks_of_supply",
        "data": [9.2, 1.2]
      }
    ],
    "metadata": {
      "source": "synthetic_postgresql"
    }
  },
  "actions": [
    {
      "action_id": "act-inv-001",
      "priority": "high",
      "owner_role": "supply_planner",
      "title": "OLED-55-A 출하 촉진 계획 검토",
      "description": "과다 재고 SKU에 대해 고객사별 단기 출하 가능성과 생산 조정 필요성을 확인합니다.",
      "due_hint": "이번 주 내",
      "related_tool": "get_inventory_risk",
      "related_entities": {
        "sku": "OLED-55-A"
      }
    }
  ]
}
```

## 10.4 get_customer_brief

### 역할

특정 고객사의 판매, 수주, 재고, 주요 이슈를 회의 준비용으로 요약한다. 단일 고객사 조회를 기본으로 한다.

| 항목 | 기준 |
| --- | --- |
| 주요 데이터 | 고객사 프로필, 판매 추이, 수주 현황, 재고 이슈, 담당 액션 |
| 필수 입력 | `customer_id` 또는 `customer_name` |
| 권장 차트 | `line`, `bar`, `table` |
| 주요 리스크 | 매출 감소, 수주 지연, 재고 불균형, 고객 이슈 |

### Request 예시

```json
{
  "request_id": "req-customer-001",
  "customer_id": "CUST-SAM-001",
  "start_date": "2026-01-01",
  "end_date": "2026-03-31",
  "include_chart": true,
  "include_actions": true
}
```

### Response 예시

```json
{
  "tool_name": "get_customer_brief",
  "status": "success",
  "summary": "CUST-SAM-001은 OLED 매출 비중이 높고, 1건의 생산 단계 지연 가능성과 1건의 과다 재고 이슈가 있습니다.",
  "data": [
    {
      "customer_id": "CUST-SAM-001",
      "customer_name": "Samsung Display",
      "primary_region": "KR",
      "top_product_family": "OLED",
      "quarter_revenue": 3830000000,
      "open_order_amount": 1430000000,
      "inventory_risk_count": 2,
      "last_contact_date": "2026-03-20"
    }
  ],
  "insights": [
    "1분기 매출은 38.3억원이며 OLED 비중이 가장 높습니다.",
    "생산 단계 주문 1건에서 납기 지연 가능성이 있습니다.",
    "OLED-55-A 과다 재고가 고객사 협의 안건으로 적합합니다."
  ],
  "risk_signals": [
    {
      "risk_id": "risk-cust-001",
      "severity": "high",
      "category": "customer",
      "title": "주요 고객 납기 이슈",
      "description": "CUST-SAM-001 관련 생산 단계 주문에서 5일 지연 가능성이 있습니다.",
      "metric": "delay_days",
      "value": 5,
      "threshold": 3,
      "related_entities": {
        "customer_id": "CUST-SAM-001"
      }
    }
  ],
  "chart_data": {
    "type": "line",
    "title": "Samsung Display 월별 매출",
    "x_axis": {
      "label": "월",
      "categories": ["2026-01", "2026-02", "2026-03"]
    },
    "y_axis": {
      "label": "매출",
      "unit": "KRW"
    },
    "series": [
      {
        "name": "revenue",
        "data": [1200000000, 1350000000, 1280000000]
      }
    ],
    "metadata": {
      "currency": "KRW",
      "source": "synthetic_postgresql"
    }
  },
  "actions": [
    {
      "action_id": "act-cust-001",
      "priority": "high",
      "owner_role": "account_owner",
      "title": "고객 미팅 안건에 납기 이슈 포함",
      "description": "생산 단계 지연 가능성이 있는 주문의 대체 납기와 대응 메시지를 사전에 준비합니다.",
      "due_hint": "다음 고객 미팅 전",
      "related_tool": "get_customer_brief",
      "related_entities": {
        "customer_id": "CUST-SAM-001"
      }
    }
  ]
}
```

## 10.5 search_competitor_news

### 역할

Synthetic 경쟁사 뉴스 또는 사전 적재된 시장 동향 데이터를 검색하고, 내부 판매/수주/재고 관점에서 해석 가능한 시그널을 반환한다.

| 항목 | 기준 |
| --- | --- |
| 주요 데이터 | 경쟁사명, 뉴스 제목, 게시일, 요약, 관련 제품군, 시장 영향 |
| 기본 기간 | 최근 30일 |
| 권장 차트 | `table`, `bar` |
| 주요 리스크 | 가격 경쟁, 신제품 출시, 공급 확대, 고객 전환 가능성 |

### Request 예시

```json
{
  "request_id": "req-news-001",
  "start_date": "2026-03-01",
  "end_date": "2026-03-31",
  "product_family": "OLED",
  "region": "KR",
  "limit": 5
}
```

### Response 예시

```json
{
  "tool_name": "search_competitor_news",
  "status": "success",
  "summary": "최근 OLED 관련 경쟁사 뉴스 2건이 검색되었으며, 가격 경쟁과 증설 시그널이 확인되었습니다.",
  "data": [
    {
      "news_id": "NEWS-2026-0310-001",
      "published_date": "2026-03-10",
      "competitor": "Competitor A",
      "title": "Competitor A expands OLED module capacity",
      "summary": "Competitor A가 OLED 모듈 생산 능력 확대 계획을 발표했습니다.",
      "region": "KR",
      "product_family": "OLED",
      "impact_type": "capacity_expansion",
      "impact_score": 0.78
    },
    {
      "news_id": "NEWS-2026-0322-001",
      "published_date": "2026-03-22",
      "competitor": "Competitor B",
      "title": "Competitor B signals aggressive pricing for premium panels",
      "summary": "Competitor B가 프리미엄 패널 가격 경쟁 가능성을 시사했습니다.",
      "region": "KR",
      "product_family": "OLED",
      "impact_type": "pricing_pressure",
      "impact_score": 0.84
    }
  ],
  "insights": [
    "경쟁사 증설 뉴스는 중기 공급 경쟁 심화 가능성을 시사합니다.",
    "가격 경쟁 시그널은 주요 고객사 협상 전 검토가 필요합니다."
  ],
  "risk_signals": [
    {
      "risk_id": "risk-news-001",
      "severity": "medium",
      "category": "competitor",
      "title": "OLED 가격 경쟁 가능성",
      "description": "Competitor B 뉴스의 impact_score가 0.84로 가격 압박 기준을 초과했습니다.",
      "metric": "impact_score",
      "value": 0.84,
      "threshold": 0.75,
      "related_entities": {
        "competitor": "Competitor B",
        "product_family": "OLED"
      }
    }
  ],
  "chart_data": {
    "type": "bar",
    "title": "경쟁사 뉴스 영향 점수",
    "x_axis": {
      "label": "뉴스",
      "categories": ["NEWS-2026-0310-001", "NEWS-2026-0322-001"]
    },
    "y_axis": {
      "label": "영향 점수",
      "unit": "score"
    },
    "series": [
      {
        "name": "impact_score",
        "data": [0.78, 0.84]
      }
    ],
    "metadata": {
      "source": "synthetic_news_dataset"
    }
  },
  "actions": [
    {
      "action_id": "act-news-001",
      "priority": "medium",
      "owner_role": "sales_manager",
      "title": "주요 고객 가격 협상 리스크 검토",
      "description": "OLED 가격 경쟁 가능성이 있는 뉴스와 고객사별 최근 수주 단가 흐름을 함께 확인합니다.",
      "due_hint": "다음 영업 회의 전",
      "related_tool": "search_competitor_news",
      "related_entities": {
        "product_family": "OLED",
        "region": "KR"
      }
    }
  ]
}
```

## 10.6 create_briefing_report

### 역할

고객사 또는 주제 기준으로 회의용 브리핑 리포트 초안을 생성한다. 내부적으로 다른 Tool의 결과를 조합할 수 있으며, 최종 반환은 JSON 구조를 유지한다.

| 항목 | 기준 |
| --- | --- |
| 주요 데이터 | 고객사 브리프, 판매 추이, 수주 현황, 재고 리스크, 경쟁사 뉴스 |
| 필수 입력 | `report_type`, `customer_id` 또는 `topic` |
| 권장 차트 | 보고서 구성에 따라 복수 차트 가능. 공통 포맷에서는 대표 차트 1개를 `chart_data`에 넣는다. |
| 주요 리스크 | 보고서 근거 부족, 핵심 리스크 누락, 액션 불명확 |

### 추가 입력 필드

| 필드 | 타입 | 필수 | 설명 | 예시 |
| --- | --- | --- | --- | --- |
| `report_type` | String | 필수 | 리포트 유형. | `customer_meeting`, `weekly_market`, `risk_review` |
| `topic` | String | 조건부 | 주제형 리포트 제목 또는 키워드. | `OLED Q1 risk briefing` |
| `sections` | Array | 선택 | 포함할 섹션 목록. | `["sales", "orders", "inventory", "competitor_news"]` |

### Request 예시

```json
{
  "request_id": "req-report-001",
  "report_type": "customer_meeting",
  "customer_id": "CUST-SAM-001",
  "start_date": "2026-01-01",
  "end_date": "2026-03-31",
  "sections": ["sales", "orders", "inventory", "competitor_news"],
  "include_chart": true,
  "include_actions": true
}
```

### Response 예시

```json
{
  "tool_name": "create_briefing_report",
  "status": "success",
  "summary": "Samsung Display 고객 미팅용 브리핑 초안이 생성되었습니다. 핵심 안건은 OLED 매출 추이, 납기 지연 가능성, 과다 재고 대응입니다.",
  "data": [
    {
      "report_id": "RPT-2026-0001",
      "report_type": "customer_meeting",
      "title": "Samsung Display OLED Business Briefing",
      "period": {
        "start_date": "2026-01-01",
        "end_date": "2026-03-31"
      },
      "sections": [
        {
          "section_id": "sales",
          "title": "판매 실적 요약",
          "content": "1분기 OLED 매출은 38.3억원이며 2월 상승 후 3월 소폭 하락했습니다."
        },
        {
          "section_id": "orders",
          "title": "수주 및 납기 현황",
          "content": "생산 단계 주문 1건에서 5일 지연 가능성이 있습니다."
        },
        {
          "section_id": "inventory",
          "title": "재고 리스크",
          "content": "OLED-55-A는 9.2주치 재고로 과다 재고 기준을 초과했습니다."
        },
        {
          "section_id": "competitor_news",
          "title": "경쟁사 동향",
          "content": "OLED 가격 경쟁과 생산능력 확대 관련 시그널이 확인되었습니다."
        }
      ]
    }
  ],
  "insights": [
    "고객 미팅에서는 납기 대응과 과다 재고 해소 방안을 함께 논의하는 것이 적합합니다.",
    "경쟁사 가격 압박 가능성이 있어 수주 조건 검토가 필요합니다."
  ],
  "risk_signals": [
    {
      "risk_id": "risk-report-001",
      "severity": "high",
      "category": "report",
      "title": "고객 미팅 핵심 리스크",
      "description": "납기 지연 가능성과 과다 재고 이슈가 동시에 존재합니다.",
      "metric": "combined_risk_count",
      "value": 2,
      "threshold": 1,
      "related_entities": {
        "customer_id": "CUST-SAM-001"
      }
    }
  ],
  "chart_data": {
    "type": "line",
    "title": "Samsung Display OLED 매출 추이",
    "x_axis": {
      "label": "월",
      "categories": ["2026-01", "2026-02", "2026-03"]
    },
    "y_axis": {
      "label": "매출",
      "unit": "KRW"
    },
    "series": [
      {
        "name": "revenue",
        "data": [1200000000, 1350000000, 1280000000]
      }
    ],
    "metadata": {
      "currency": "KRW",
      "source": "synthetic_postgresql"
    }
  },
  "actions": [
    {
      "action_id": "act-report-001",
      "priority": "high",
      "owner_role": "account_owner",
      "title": "고객 미팅용 대응 메시지 준비",
      "description": "납기 지연 가능성과 OLED-55-A 재고 해소 방안을 고객 미팅 전 내부 조율합니다.",
      "due_hint": "다음 고객 미팅 전",
      "related_tool": "create_briefing_report",
      "related_entities": {
        "customer_id": "CUST-SAM-001",
        "report_id": "RPT-2026-0001"
      }
    }
  ]
}
```

## 11. Tool별 필수 입력 요약

| Tool | 필수 입력 | 기본값 |
| --- | --- | --- |
| `get_sales_trend` | 없음. 단, 필터 미입력 시 전체 기준 조회 | 최근 3개월, `group_by=month`, `metric=revenue` |
| `get_order_status` | 없음. 고객사 미입력 시 전체 수주 조회 | 최근 3개월, `group_by=status` |
| `get_inventory_risk` | 없음. 필터 미입력 시 전체 재고 리스크 조회 | 현재 재고, 최근 4주 출고 기준 |
| `get_customer_brief` | `customer_id` 또는 `customer_name` | 최근 3개월 |
| `search_competitor_news` | 없음. 키워드 미입력 시 전체 경쟁사 뉴스 조회 | 최근 30일, `limit=10` |
| `create_briefing_report` | `report_type`, 그리고 `customer_id` 또는 `topic` | 최근 3개월, 전체 섹션 |

## 12. MCP 스타일 Python Tool 함수 기준

MCP 서버로 분리하기 전 PoC 단계에서는 Python 함수로 Tool을 구현할 수 있다. 함수 이름은 Tool 이름과 동일하게 유지한다.

```python
from typing import Any


async def get_sales_trend(request: dict[str, Any]) -> dict[str, Any]:
    """판매 추이 데이터를 조회하고 공통 Tool 응답 포맷으로 반환한다."""
    ...
```

### 12.1 함수 구현 기준

| 항목 | 기준 |
| --- | --- |
| 함수명 | Tool 이름과 동일한 snake_case |
| 입력 | `dict[str, Any]` 또는 Pydantic Request Model |
| 출력 | 공통 출력 JSON과 동일한 `dict[str, Any]` |
| 비동기 | DB I/O 또는 외부 API I/O가 있으면 `async` 사용 권장 |
| 검증 | Pydantic 또는 명시적 검증 함수 사용 |
| DB 접근 | 공통 DB 커넥션 유틸리티 사용 |
| 오류 처리 | 예외를 공통 오류 JSON으로 변환 |

## 13. FastAPI 연동 기준

FastAPI는 LangGraph Agent가 Tool을 직접 호출하는 경우에도, 디버깅과 단위 확인을 위해 Tool 테스트 엔드포인트를 제공할 수 있다.

| 엔드포인트 예시 | 설명 |
| --- | --- |
| `POST /tools/get-sales-trend` | 판매 추이 Tool 단독 실행 |
| `POST /tools/get-order-status` | 수주 현황 Tool 단독 실행 |
| `POST /tools/get-inventory-risk` | 재고 리스크 Tool 단독 실행 |
| `POST /tools/get-customer-brief` | 고객사 브리프 Tool 단독 실행 |
| `POST /tools/search-competitor-news` | 경쟁사 뉴스 검색 Tool 단독 실행 |
| `POST /tools/create-briefing-report` | 브리핑 리포트 생성 Tool 단독 실행 |

FastAPI 응답은 Tool 원본 응답을 유지해야 한다. Spring Boot API 공통 응답 포맷으로 감싸는 작업은 Spring Boot 중계 계층 또는 상위 Agent API에서 수행한다.

## 14. LangGraph 연동 기준

LangGraph Node에서 Tool을 호출할 때는 다음 기준을 따른다.

| 항목 | 기준 |
| --- | --- |
| Tool 선택 | 사용자 질문 의도에 따라 하나 이상의 Tool을 선택한다. |
| 상태 저장 | Tool 응답 원본을 LangGraph state에 저장한다. |
| 다중 Tool 호출 | `create_briefing_report`는 필요 시 판매, 수주, 재고, 뉴스 Tool 결과를 조합한다. |
| 실패 처리 | 특정 Tool이 실패해도 전체 Agent 응답에서 어떤 Tool이 실패했는지 명시한다. |
| 근거 유지 | 최종 LLM 응답 생성 시 `data`, `insights`, `risk_signals`, `actions`를 근거로 사용한다. |

## 15. Tool 개발 체크리스트

| 체크 | 항목 |
| --- | --- |
| [ ] | Tool 함수명이 문서의 Tool 이름과 동일하다. |
| [ ] | 공통 입력 필드를 수용하거나 무시 가능한 구조로 구현했다. |
| [ ] | Tool별 필수 입력 누락 시 `INVALID_REQUEST`를 반환한다. |
| [ ] | 날짜 형식과 날짜 범위를 검증한다. |
| [ ] | SQL은 파라미터 바인딩을 사용한다. |
| [ ] | 빈 조회 결과를 정상 응답으로 처리한다. |
| [ ] | 성공 응답에 `tool_name`, `status`, `summary`, `data`, `insights`, `risk_signals`, `chart_data`, `actions`가 모두 포함된다. |
| [ ] | 오류 응답에 `error.code`, `error.message`가 포함된다. |
| [ ] | `chart_data.series[].data` 길이가 `x_axis.categories` 길이와 일치한다. |
| [ ] | `risk_signals`는 severity, category, title, description을 포함한다. |
| [ ] | `actions`는 실제 후속 조치로 이해 가능한 문장이다. |
| [ ] | Synthetic Data만 사용하며 실제 고객 정보나 비밀번호가 포함되지 않는다. |
| [ ] | Tool 단위 테스트를 추가했다. |
| [ ] | FastAPI 단독 실행 또는 LangGraph 호출 경로에서 동작을 확인했다. |

## 16. Pull Request 전에 확인할 테스트 항목

| 구분 | 테스트 항목 | 기대 결과 |
| --- | --- | --- |
| 입력 검증 | 필수 입력 누락 | 공통 오류 JSON과 `INVALID_REQUEST` 반환 |
| 입력 검증 | 잘못된 날짜 형식 | 공통 오류 JSON과 `INVALID_REQUEST` 반환 |
| 입력 검증 | `start_date`가 `end_date`보다 늦음 | 공통 오류 JSON과 `INVALID_DATE_RANGE` 반환 |
| 정상 조회 | 기본 입력만 전달 | Tool별 기본 기간과 기본 필터로 `success` 반환 |
| 정상 조회 | 필터 조합 입력 | 필터 조건에 맞는 `data` 반환 |
| 빈 결과 | 존재하지 않는 고객사 또는 조건 | `success`, 빈 `data`, 조회 결과 없음 summary 반환 |
| 차트 | `include_chart=true` | 표준 `chart_data` 반환 |
| 차트 | `include_chart=false` | 빈 객체 `{}` 반환 |
| 리스크 | 리스크 기준 초과 데이터 | `risk_signals`에 severity와 근거 수치 포함 |
| 액션 | `include_actions=true` | 실행 가능한 `actions` 반환 |
| 오류 처리 | DB 예외 발생 | 공통 오류 JSON과 `DATABASE_ERROR` 반환 |
| LangGraph | Agent state에서 Tool 호출 | Tool 응답 원본이 state에 저장됨 |
| FastAPI | Tool 테스트 엔드포인트 호출 | HTTP 200과 Tool JSON 반환. Tool 내부 오류도 JSON `status=error`로 반환 |
| Spring Boot | Python Agent 응답 중계 | Vue 공통 응답 포맷으로 변환 가능 |
| 보안 | 응답 데이터 확인 | 실제 비밀번호, 토큰, 실고객 민감 정보 없음 |

## 17. 권장 테스트 케이스 파일

| Tool | 테스트 파일 예시 |
| --- | --- |
| `get_sales_trend` | `agent-python/tests/test_sales_tool.py` |
| `get_order_status` | `agent-python/tests/test_order_tool.py` |
| `get_inventory_risk` | `agent-python/tests/test_inventory_tool.py` |
| `get_customer_brief` | `agent-python/tests/test_customer_tool.py` |
| `search_competitor_news` | `agent-python/tests/test_competitor_news_tool.py` |
| `create_briefing_report` | `agent-python/tests/test_briefing_report_tool.py` |

## 18. 구현 완료 기준

Tool 구현은 다음 조건을 모두 만족할 때 완료로 본다.

| 조건 | 기준 |
| --- | --- |
| 기능 완료 | 정상 입력에 대해 업무적으로 의미 있는 `summary`, `data`, `insights`를 반환한다. |
| 오류 완료 | 검증 오류, DB 오류, 내부 오류를 공통 오류 JSON으로 반환한다. |
| 화면 연동 가능 | `chart_data`, `risk_signals`, `actions`가 Vue 화면에서 바로 사용할 수 있는 구조이다. |
| Agent 연동 가능 | LangGraph Node에서 Tool 호출 결과를 state에 저장하고 최종 답변 근거로 사용할 수 있다. |
| 테스트 완료 | Tool별 정상, 오류, 빈 결과 테스트가 통과한다. |
| 문서 일치 | Request/Response 필드명이 이 문서와 일치한다. |
