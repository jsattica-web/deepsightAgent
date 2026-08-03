# Display Market Intelligence Agent PoC API 명세서

## 1. 문서 개요

| 항목 | 내용 |
| --- | --- |
| 문서명 | Display Market Intelligence Agent PoC API 명세서 |
| 대상 시스템 | Vue 2.6.10, Spring Boot 2.1.18.RELEASE, Java 8, Python 3.12 FastAPI, PostgreSQL |
| 데이터 원칙 | 실제 업무 데이터 미사용, Synthetic Data만 사용 |
| 주요 흐름 | Vue 화면 -> Spring Boot API -> Python FastAPI Agent -> PostgreSQL / MCP Tool -> LLM API -> 응답 반환 |

## 2. 공통 응답 포맷

### 2.1 성공 응답

```json
{
  "status": "success",
  "message": "요청이 정상 처리되었습니다.",
  "data": {
    "answer": "",
    "summary": [],
    "tables": [],
    "charts": [],
    "insights": [],
    "risk_signals": [],
    "actions": []
  },
  "error": null
}
```

### 2.2 오류 응답

```json
{
  "status": "error",
  "message": "처리 중 오류가 발생했습니다.",
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "상세 오류 메시지"
  }
}
```

### 2.3 공통 필드 설명

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `status` | String | 처리 상태. `success` 또는 `error` |
| `message` | String | 사용자 표시용 처리 메시지 |
| `data` | Object | 성공 시 업무 응답 데이터 |
| `data.answer` | String | 자연어 답변 본문 |
| `data.summary` | Array | 요약 항목 목록 |
| `data.tables` | Array | 표 형태 데이터 목록 |
| `data.charts` | Array | 차트 렌더링용 데이터 목록 |
| `data.insights` | Array | 주요 인사이트 목록 |
| `data.risk_signals` | Array | 리스크 신호 목록 |
| `data.actions` | Array | 권장 후속 조치 목록 |
| `error` | Object | 오류 상세. 성공 시 `null` |
| `error.code` | String | 오류 코드 |
| `error.message` | String | 오류 상세 메시지 |

## 3. 공통 오류 코드

| 코드 | HTTP Status | 설명 |
| --- | --- | --- |
| `INVALID_REQUEST` | 400 | 요청 필드 또는 파라미터가 올바르지 않음 |
| `NOT_FOUND` | 404 | 고객사, 데이터, 리소스를 찾을 수 없음 |
| `AGENT_SERVER_ERROR` | 502 | Spring Boot에서 Python Agent 호출 실패 |
| `TOOL_EXECUTION_ERROR` | 500 | Python Tool 또는 MCP 스타일 Tool 실행 실패 |
| `LLM_API_ERROR` | 502 | LLM API 호출 실패 |
| `DATABASE_ERROR` | 500 | PostgreSQL 조회 또는 연결 실패 |
| `INTERNAL_ERROR` | 500 | 기타 서버 내부 오류 |

## 4. Spring Boot API

Spring Boot API는 Vue 화면의 요청을 받고, 필요한 경우 Python FastAPI Agent 또는 Tool API를 호출한 뒤 공통 응답 포맷으로 반환한다. Java 8 및 Spring Boot 2.1.18.RELEASE 기준으로 구현한다.

### 4.1 POST /api/agent/chat

| 항목 | 내용 |
| --- | --- |
| 목적 | 사용자의 자연어 질문을 Python Agent로 중계하고 최종 답변을 반환 |
| 요청 Method | `POST` |
| URL | `/api/agent/chat` |
| Python 연계 API | `POST /agent/chat` |

#### Request JSON 예시

```json
{
  "sessionId": "SYN-SESSION-001",
  "userId": "demo-user",
  "message": "2026년 2분기 OLED 패널 판매 실적을 지역별로 요약해줘.",
  "context": {
    "periodStart": "2026-04-01",
    "periodEnd": "2026-06-30",
    "locale": "ko-KR"
  }
}
```

#### Response JSON 예시

```json
{
  "status": "success",
  "message": "요청이 정상 처리되었습니다.",
  "data": {
    "answer": "2026년 2분기 OLED 패널 판매는 북미와 유럽 중심으로 증가했습니다.",
    "summary": [
      "전체 매출은 전분기 대비 8.4% 증가했습니다.",
      "북미 지역 매출 증가율이 가장 높았습니다."
    ],
    "tables": [
      {
        "title": "지역별 판매 추이",
        "columns": ["region", "revenue", "growthRate"],
        "rows": [
          ["North America", 1250000, 12.5],
          ["Europe", 980000, 9.1]
        ]
      }
    ],
    "charts": [
      {
        "type": "bar",
        "title": "지역별 매출",
        "labels": ["North America", "Europe"],
        "datasets": [
          {
            "label": "Revenue",
            "data": [1250000, 980000]
          }
        ]
      }
    ],
    "insights": [
      "프리미엄 OLED 제품군의 판매 비중이 상승했습니다."
    ],
    "risk_signals": [
      "아시아 지역 판매 성장률은 상대적으로 둔화되었습니다."
    ],
    "actions": [
      "북미 주요 고객사 대상 추가 수주 가능성을 점검합니다."
    ]
  },
  "error": null
}
```

#### 주요 필드 설명

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `sessionId` | String | Y | 화면 또는 대화 세션 식별자 |
| `userId` | String | Y | PoC 사용자 식별자 |
| `message` | String | Y | 사용자 자연어 질문 |
| `context` | Object | N | 기간, 언어 등 보조 조건 |
| `context.periodStart` | String | N | 조회 시작일. `YYYY-MM-DD` |
| `context.periodEnd` | String | N | 조회 종료일. `YYYY-MM-DD` |
| `context.locale` | String | N | 응답 언어 및 지역 |

#### 오류 응답 예시

```json
{
  "status": "error",
  "message": "처리 중 오류가 발생했습니다.",
  "data": null,
  "error": {
    "code": "AGENT_SERVER_ERROR",
    "message": "Python Agent 서버 호출에 실패했습니다."
  }
}
```

### 4.2 GET /api/sales/trend

| 항목 | 내용 |
| --- | --- |
| 목적 | 판매 추이 데이터를 조회하고 요약 결과를 반환 |
| 요청 Method | `GET` |
| URL | `/api/sales/trend` |
| Python 연계 API | `POST /tools/sales-trend` |

#### Request 예시

```http
GET /api/sales/trend?periodStart=2026-04-01&periodEnd=2026-06-30&region=North%20America&productFamily=OLED
```

```json
{
  "periodStart": "2026-04-01",
  "periodEnd": "2026-06-30",
  "region": "North America",
  "productFamily": "OLED"
}
```

#### Response JSON 예시

```json
{
  "status": "success",
  "message": "요청이 정상 처리되었습니다.",
  "data": {
    "answer": "OLED 제품군의 북미 판매는 기간 내 안정적인 증가세를 보였습니다.",
    "summary": [
      "총 매출은 1,250,000달러입니다.",
      "월별 매출은 4월 대비 6월에 11.2% 증가했습니다."
    ],
    "tables": [
      {
        "title": "월별 판매 추이",
        "columns": ["month", "quantity", "revenue"],
        "rows": [
          ["2026-04", 4200, 380000],
          ["2026-05", 4600, 410000],
          ["2026-06", 5000, 460000]
        ]
      }
    ],
    "charts": [
      {
        "type": "line",
        "title": "월별 매출 추이",
        "labels": ["2026-04", "2026-05", "2026-06"],
        "datasets": [
          {
            "label": "Revenue",
            "data": [380000, 410000, 460000]
          }
        ]
      }
    ],
    "insights": [
      "6월 대형 OLED 제품 출하 증가가 매출 상승에 기여했습니다."
    ],
    "risk_signals": [],
    "actions": [
      "고성장 지역의 수주 전환율을 추가 확인합니다."
    ]
  },
  "error": null
}
```

#### 주요 필드 설명

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `periodStart` | String | Y | 조회 시작일 |
| `periodEnd` | String | Y | 조회 종료일 |
| `region` | String | N | 지역 필터 |
| `productFamily` | String | N | 제품군 필터 |
| `customerId` | String | N | 고객사 필터 |

#### 오류 응답 예시

```json
{
  "status": "error",
  "message": "처리 중 오류가 발생했습니다.",
  "data": null,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "periodStart와 periodEnd는 필수입니다."
  }
}
```

### 4.3 GET /api/orders/status

| 항목 | 내용 |
| --- | --- |
| 목적 | 수주 현황과 단계별 상태를 조회 |
| 요청 Method | `GET` |
| URL | `/api/orders/status` |
| Python 연계 API | `POST /tools/order-status` |

#### Request 예시

```http
GET /api/orders/status?periodStart=2026-04-01&periodEnd=2026-06-30&customerId=CUST-A&orderStatus=CONFIRMED
```

```json
{
  "periodStart": "2026-04-01",
  "periodEnd": "2026-06-30",
  "customerId": "CUST-A",
  "orderStatus": "CONFIRMED"
}
```

#### Response JSON 예시

```json
{
  "status": "success",
  "message": "요청이 정상 처리되었습니다.",
  "data": {
    "answer": "CUST-A의 확정 수주는 2분기 중 안정적으로 유지되고 있습니다.",
    "summary": [
      "확정 수주 금액은 920,000달러입니다.",
      "출하 예정 물량은 7월에 집중되어 있습니다."
    ],
    "tables": [
      {
        "title": "수주 상태별 집계",
        "columns": ["orderStatus", "orderCount", "orderAmount"],
        "rows": [
          ["CONFIRMED", 12, 920000],
          ["NEGOTIATION", 5, 310000]
        ]
      }
    ],
    "charts": [
      {
        "type": "donut",
        "title": "수주 상태 비중",
        "labels": ["CONFIRMED", "NEGOTIATION"],
        "datasets": [
          {
            "label": "Order Amount",
            "data": [920000, 310000]
          }
        ]
      }
    ],
    "insights": [
      "확정 수주 비중이 높아 단기 매출 가시성이 양호합니다."
    ],
    "risk_signals": [
      "일부 수주는 납기 일정이 7월 첫째 주에 집중되어 있습니다."
    ],
    "actions": [
      "출하 가능 재고와 물류 일정을 함께 점검합니다."
    ]
  },
  "error": null
}
```

#### 주요 필드 설명

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `periodStart` | String | Y | 조회 시작일 |
| `periodEnd` | String | Y | 조회 종료일 |
| `customerId` | String | N | 고객사 ID |
| `productFamily` | String | N | 제품군 필터 |
| `orderStatus` | String | N | 수주 상태. 예: `LEAD`, `NEGOTIATION`, `CONFIRMED`, `CANCELLED` |

#### 오류 응답 예시

```json
{
  "status": "error",
  "message": "처리 중 오류가 발생했습니다.",
  "data": null,
  "error": {
    "code": "DATABASE_ERROR",
    "message": "수주 현황 조회 중 데이터베이스 오류가 발생했습니다."
  }
}
```

### 4.4 GET /api/inventory/risk

| 항목 | 내용 |
| --- | --- |
| 목적 | 재고 과다, 부족, 장기 보유 등 재고 리스크를 조회 |
| 요청 Method | `GET` |
| URL | `/api/inventory/risk` |
| Python 연계 API | `POST /tools/inventory-risk` |

#### Request 예시

```http
GET /api/inventory/risk?snapshotDate=2026-06-30&warehouseRegion=Asia&productFamily=LCD&riskLevel=HIGH
```

```json
{
  "snapshotDate": "2026-06-30",
  "warehouseRegion": "Asia",
  "productFamily": "LCD",
  "riskLevel": "HIGH"
}
```

#### Response JSON 예시

```json
{
  "status": "success",
  "message": "요청이 정상 처리되었습니다.",
  "data": {
    "answer": "Asia 지역 LCD 재고 중 고위험 항목은 3건입니다.",
    "summary": [
      "안전재고 대비 150% 이상 초과한 품목이 확인되었습니다.",
      "일부 모델은 60일 이상 장기 보유 상태입니다."
    ],
    "tables": [
      {
        "title": "재고 리스크 품목",
        "columns": ["productId", "stockQuantity", "safetyStock", "riskLevel", "reason"],
        "rows": [
          ["PROD-LCD-43", 7800, 4200, "HIGH", "OVER_STOCK"],
          ["PROD-LCD-55", 6400, 3000, "HIGH", "AGING_STOCK"]
        ]
      }
    ],
    "charts": [
      {
        "type": "bar",
        "title": "품목별 재고 수준",
        "labels": ["PROD-LCD-43", "PROD-LCD-55"],
        "datasets": [
          {
            "label": "Stock Quantity",
            "data": [7800, 6400]
          },
          {
            "label": "Safety Stock",
            "data": [4200, 3000]
          }
        ]
      }
    ],
    "insights": [
      "LCD 중형 제품군에서 재고 소진 속도가 둔화되었습니다."
    ],
    "risk_signals": [
      "고위험 재고가 특정 창고에 집중되어 있습니다."
    ],
    "actions": [
      "프로모션 또는 출하 우선순위 조정을 검토합니다."
    ]
  },
  "error": null
}
```

#### 주요 필드 설명

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `snapshotDate` | String | Y | 재고 기준일 |
| `warehouseRegion` | String | N | 창고 또는 권역 |
| `productFamily` | String | N | 제품군 필터 |
| `riskLevel` | String | N | 리스크 등급. 예: `LOW`, `MEDIUM`, `HIGH` |

#### 오류 응답 예시

```json
{
  "status": "error",
  "message": "처리 중 오류가 발생했습니다.",
  "data": null,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "snapshotDate 형식은 YYYY-MM-DD여야 합니다."
  }
}
```

### 4.5 GET /api/customers/{customerId}/brief

| 항목 | 내용 |
| --- | --- |
| 목적 | 특정 고객사의 판매, 수주, 재고, 이슈 요약 정보를 조회 |
| 요청 Method | `GET` |
| URL | `/api/customers/{customerId}/brief` |
| Python 연계 API | `POST /tools/customer-brief` |

#### Request 예시

```http
GET /api/customers/CUST-A/brief?periodStart=2026-04-01&periodEnd=2026-06-30
```

```json
{
  "customerId": "CUST-A",
  "periodStart": "2026-04-01",
  "periodEnd": "2026-06-30"
}
```

#### Response JSON 예시

```json
{
  "status": "success",
  "message": "요청이 정상 처리되었습니다.",
  "data": {
    "answer": "CUST-A는 2분기 OLED 중심 판매가 증가했으며, 7월 출하 집중 리스크가 있습니다.",
    "summary": [
      "2분기 매출은 1,150,000달러입니다.",
      "확정 수주는 12건입니다.",
      "주요 재고 리스크는 OLED 65인치 출하 대기 물량입니다."
    ],
    "tables": [
      {
        "title": "고객사 브리프",
        "columns": ["category", "value", "note"],
        "rows": [
          ["Sales", "1,150,000", "Q2 revenue"],
          ["Orders", "12", "Confirmed orders"],
          ["Inventory Risk", "MEDIUM", "Shipment concentration"]
        ]
      }
    ],
    "charts": [],
    "insights": [
      "프리미엄 제품군 비중 상승으로 평균 판매 단가가 개선되었습니다."
    ],
    "risk_signals": [
      "7월 초 출하 물량 집중으로 납기 지연 가능성이 있습니다."
    ],
    "actions": [
      "회의 전 출하 일정과 재고 가용성을 확인합니다."
    ]
  },
  "error": null
}
```

#### 주요 필드 설명

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `customerId` | String | Y | Path Variable. 고객사 ID |
| `periodStart` | String | Y | 조회 시작일 |
| `periodEnd` | String | Y | 조회 종료일 |

#### 오류 응답 예시

```json
{
  "status": "error",
  "message": "처리 중 오류가 발생했습니다.",
  "data": null,
  "error": {
    "code": "NOT_FOUND",
    "message": "요청한 고객사 정보를 찾을 수 없습니다."
  }
}
```

### 4.6 POST /api/briefing/generate

| 항목 | 내용 |
| --- | --- |
| 목적 | 회의용 브리프북 초안 생성을 요청 |
| 요청 Method | `POST` |
| URL | `/api/briefing/generate` |
| Python 연계 API | `POST /agent/briefing` |

#### Request JSON 예시

```json
{
  "sessionId": "SYN-SESSION-001",
  "userId": "demo-user",
  "topic": "CUST-A 2026년 2분기 사업 리뷰",
  "customerId": "CUST-A",
  "periodStart": "2026-04-01",
  "periodEnd": "2026-06-30",
  "sections": [
    "sales",
    "orders",
    "inventory",
    "competitor_news",
    "recommended_actions"
  ]
}
```

#### Response JSON 예시

```json
{
  "status": "success",
  "message": "요청이 정상 처리되었습니다.",
  "data": {
    "answer": "CUST-A 2026년 2분기 사업 리뷰 브리프북 초안이 생성되었습니다.",
    "summary": [
      "판매는 OLED 중심으로 증가했습니다.",
      "수주는 안정적이나 7월 출하 집중 리스크가 있습니다.",
      "경쟁사 가격 프로모션 뉴스가 관찰되었습니다."
    ],
    "tables": [
      {
        "title": "브리프북 섹션",
        "columns": ["section", "title"],
        "rows": [
          ["sales", "판매 실적 요약"],
          ["orders", "수주 현황"],
          ["inventory", "재고 및 출하 리스크"],
          ["competitor_news", "경쟁사 동향"],
          ["recommended_actions", "권장 대응"]
        ]
      }
    ],
    "charts": [],
    "insights": [
      "고객사 미팅에서는 납기 안정성과 프리미엄 제품 공급 역량을 핵심 메시지로 제안합니다."
    ],
    "risk_signals": [
      "경쟁사 가격 인하 움직임으로 중형 LCD 제품군 마진 압박 가능성이 있습니다."
    ],
    "actions": [
      "OLED 공급 안정성 자료를 회의 부록으로 준비합니다.",
      "LCD 가격 대응 시나리오를 내부 검토합니다."
    ]
  },
  "error": null
}
```

#### 주요 필드 설명

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `sessionId` | String | Y | 화면 또는 대화 세션 식별자 |
| `userId` | String | Y | PoC 사용자 식별자 |
| `topic` | String | Y | 브리프북 주제 |
| `customerId` | String | N | 고객사 ID |
| `periodStart` | String | Y | 분석 시작일 |
| `periodEnd` | String | Y | 분석 종료일 |
| `sections` | Array | N | 포함할 브리프북 섹션 목록 |

#### 오류 응답 예시

```json
{
  "status": "error",
  "message": "처리 중 오류가 발생했습니다.",
  "data": null,
  "error": {
    "code": "LLM_API_ERROR",
    "message": "브리프북 문장 생성 중 LLM API 호출에 실패했습니다."
  }
}
```

## 5. Python FastAPI

Python FastAPI는 Spring Boot에서 호출하는 내부 Agent 서버 API이다. LangGraph 실행, MCP 스타일 Tool 함수 호출, PostgreSQL 조회, LLM API 호출을 담당한다.

### 5.1 GET /health

| 항목 | 내용 |
| --- | --- |
| 목적 | Python Agent 서버 상태 확인 |
| 요청 Method | `GET` |
| URL | `/health` |

#### Request 예시

```http
GET /health
```

```json
{}
```

#### Response JSON 예시

```json
{
  "status": "success",
  "message": "요청이 정상 처리되었습니다.",
  "data": {
    "answer": "Agent server is healthy.",
    "summary": [
      "FastAPI server is running.",
      "PostgreSQL connection is available."
    ],
    "tables": [],
    "charts": [],
    "insights": [],
    "risk_signals": [],
    "actions": []
  },
  "error": null
}
```

#### 주요 필드 설명

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | 별도 요청 필드 없음 |

#### 오류 응답 예시

```json
{
  "status": "error",
  "message": "처리 중 오류가 발생했습니다.",
  "data": null,
  "error": {
    "code": "DATABASE_ERROR",
    "message": "PostgreSQL 연결 상태 확인에 실패했습니다."
  }
}
```

### 5.2 POST /agent/chat

| 항목 | 내용 |
| --- | --- |
| 목적 | LangGraph Agent를 실행하여 자연어 질문에 대한 분석 답변을 생성 |
| 요청 Method | `POST` |
| URL | `/agent/chat` |

#### Request JSON 예시

```json
{
  "requestId": "REQ-CHAT-001",
  "sessionId": "SYN-SESSION-001",
  "userId": "demo-user",
  "message": "최근 3개월 동안 매출이 가장 많이 증가한 제품군은 뭐야?",
  "context": {
    "periodStart": "2026-04-01",
    "periodEnd": "2026-06-30",
    "locale": "ko-KR"
  }
}
```

#### Response JSON 예시

```json
{
  "status": "success",
  "message": "요청이 정상 처리되었습니다.",
  "data": {
    "answer": "최근 3개월 동안 매출 증가율이 가장 높은 제품군은 OLED입니다.",
    "summary": [
      "OLED 매출은 4월 대비 6월에 14.8% 증가했습니다.",
      "LCD 매출은 같은 기간 3.2% 감소했습니다."
    ],
    "tables": [
      {
        "title": "제품군별 매출 증감",
        "columns": ["productFamily", "aprilRevenue", "juneRevenue", "growthRate"],
        "rows": [
          ["OLED", 880000, 1010000, 14.8],
          ["LCD", 620000, 600000, -3.2]
        ]
      }
    ],
    "charts": [],
    "insights": [
      "OLED 대형 제품군의 판매 확대가 전체 성장세를 견인했습니다."
    ],
    "risk_signals": [
      "LCD 수요 둔화가 지속될 경우 재고 부담이 커질 수 있습니다."
    ],
    "actions": [
      "OLED 고성장 고객사를 대상으로 추가 수주 기회를 점검합니다."
    ]
  },
  "error": null
}
```

#### 주요 필드 설명

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `requestId` | String | Y | Spring Boot에서 전달하는 요청 식별자 |
| `sessionId` | String | Y | 대화 세션 식별자 |
| `userId` | String | Y | PoC 사용자 식별자 |
| `message` | String | Y | 사용자 자연어 질문 |
| `context` | Object | N | 분석 조건 |

#### 오류 응답 예시

```json
{
  "status": "error",
  "message": "처리 중 오류가 발생했습니다.",
  "data": null,
  "error": {
    "code": "TOOL_EXECUTION_ERROR",
    "message": "질문 처리 중 sales-trend Tool 실행에 실패했습니다."
  }
}
```

### 5.3 POST /tools/sales-trend

| 항목 | 내용 |
| --- | --- |
| 목적 | 판매 추이 Tool을 실행하여 기간별 판매 데이터를 분석 |
| 요청 Method | `POST` |
| URL | `/tools/sales-trend` |

#### Request JSON 예시

```json
{
  "periodStart": "2026-04-01",
  "periodEnd": "2026-06-30",
  "region": "North America",
  "productFamily": "OLED",
  "customerId": null
}
```

#### Response JSON 예시

```json
{
  "status": "success",
  "message": "요청이 정상 처리되었습니다.",
  "data": {
    "answer": "판매 추이 조회가 완료되었습니다.",
    "summary": [
      "총 판매량은 13,800대입니다.",
      "총 매출은 1,250,000달러입니다."
    ],
    "tables": [
      {
        "title": "Sales Trend",
        "columns": ["month", "quantity", "revenue"],
        "rows": [
          ["2026-04", 4200, 380000],
          ["2026-05", 4600, 410000],
          ["2026-06", 5000, 460000]
        ]
      }
    ],
    "charts": [
      {
        "type": "line",
        "title": "Revenue Trend",
        "labels": ["2026-04", "2026-05", "2026-06"],
        "datasets": [
          {
            "label": "Revenue",
            "data": [380000, 410000, 460000]
          }
        ]
      }
    ],
    "insights": [
      "월별 판매량이 연속 증가했습니다."
    ],
    "risk_signals": [],
    "actions": []
  },
  "error": null
}
```

#### 주요 필드 설명

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `periodStart` | String | Y | 조회 시작일 |
| `periodEnd` | String | Y | 조회 종료일 |
| `region` | String | N | 지역 필터 |
| `productFamily` | String | N | 제품군 필터 |
| `customerId` | String | N | 고객사 ID |

#### 오류 응답 예시

```json
{
  "status": "error",
  "message": "처리 중 오류가 발생했습니다.",
  "data": null,
  "error": {
    "code": "DATABASE_ERROR",
    "message": "sales_records 조회 중 오류가 발생했습니다."
  }
}
```

### 5.4 POST /tools/order-status

| 항목 | 내용 |
| --- | --- |
| 목적 | 수주 상태 Tool을 실행하여 단계별 수주 현황을 분석 |
| 요청 Method | `POST` |
| URL | `/tools/order-status` |

#### Request JSON 예시

```json
{
  "periodStart": "2026-04-01",
  "periodEnd": "2026-06-30",
  "customerId": "CUST-A",
  "productFamily": "OLED",
  "orderStatus": null
}
```

#### Response JSON 예시

```json
{
  "status": "success",
  "message": "요청이 정상 처리되었습니다.",
  "data": {
    "answer": "수주 상태 조회가 완료되었습니다.",
    "summary": [
      "확정 수주 12건, 협의 중 수주 5건이 확인되었습니다."
    ],
    "tables": [
      {
        "title": "Order Status",
        "columns": ["orderStatus", "orderCount", "orderAmount"],
        "rows": [
          ["CONFIRMED", 12, 920000],
          ["NEGOTIATION", 5, 310000]
        ]
      }
    ],
    "charts": [],
    "insights": [
      "확정 수주 금액 비중이 74.8%입니다."
    ],
    "risk_signals": [
      "협의 중 수주 일부는 경쟁사 가격 제안 영향을 받을 수 있습니다."
    ],
    "actions": [
      "협의 중 수주의 가격 조건과 납기 조건을 재점검합니다."
    ]
  },
  "error": null
}
```

#### 주요 필드 설명

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `periodStart` | String | Y | 조회 시작일 |
| `periodEnd` | String | Y | 조회 종료일 |
| `customerId` | String | N | 고객사 ID |
| `productFamily` | String | N | 제품군 필터 |
| `orderStatus` | String | N | 수주 상태 |

#### 오류 응답 예시

```json
{
  "status": "error",
  "message": "처리 중 오류가 발생했습니다.",
  "data": null,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "periodStart는 periodEnd보다 이후일 수 없습니다."
  }
}
```

### 5.5 POST /tools/inventory-risk

| 항목 | 내용 |
| --- | --- |
| 목적 | 재고 리스크 Tool을 실행하여 과다, 부족, 장기 보유 재고를 분석 |
| 요청 Method | `POST` |
| URL | `/tools/inventory-risk` |

#### Request JSON 예시

```json
{
  "snapshotDate": "2026-06-30",
  "warehouseRegion": "Asia",
  "productFamily": "LCD",
  "riskLevel": "HIGH"
}
```

#### Response JSON 예시

```json
{
  "status": "success",
  "message": "요청이 정상 처리되었습니다.",
  "data": {
    "answer": "재고 리스크 조회가 완료되었습니다.",
    "summary": [
      "고위험 재고 2건이 확인되었습니다."
    ],
    "tables": [
      {
        "title": "Inventory Risk",
        "columns": ["productId", "stockQuantity", "safetyStock", "riskLevel", "reason"],
        "rows": [
          ["PROD-LCD-43", 7800, 4200, "HIGH", "OVER_STOCK"],
          ["PROD-LCD-55", 6400, 3000, "HIGH", "AGING_STOCK"]
        ]
      }
    ],
    "charts": [],
    "insights": [
      "안전재고 대비 초과 물량이 큰 품목이 있습니다."
    ],
    "risk_signals": [
      "장기 보유 재고가 증가하면 가격 할인 압박이 발생할 수 있습니다."
    ],
    "actions": [
      "출하 우선순위 조정과 재고 소진 계획 수립이 필요합니다."
    ]
  },
  "error": null
}
```

#### 주요 필드 설명

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `snapshotDate` | String | Y | 재고 기준일 |
| `warehouseRegion` | String | N | 창고 권역 |
| `productFamily` | String | N | 제품군 필터 |
| `riskLevel` | String | N | 리스크 등급 |

#### 오류 응답 예시

```json
{
  "status": "error",
  "message": "처리 중 오류가 발생했습니다.",
  "data": null,
  "error": {
    "code": "DATABASE_ERROR",
    "message": "inventory_records 조회 중 오류가 발생했습니다."
  }
}
```

### 5.6 POST /tools/customer-brief

| 항목 | 내용 |
| --- | --- |
| 목적 | 고객사 단위 판매, 수주, 재고 요약 Tool을 실행 |
| 요청 Method | `POST` |
| URL | `/tools/customer-brief` |

#### Request JSON 예시

```json
{
  "customerId": "CUST-A",
  "periodStart": "2026-04-01",
  "periodEnd": "2026-06-30",
  "includeInventory": true,
  "includeOrders": true
}
```

#### Response JSON 예시

```json
{
  "status": "success",
  "message": "요청이 정상 처리되었습니다.",
  "data": {
    "answer": "고객사 브리프 조회가 완료되었습니다.",
    "summary": [
      "CUST-A는 프리미엄 OLED 판매 비중이 높습니다.",
      "수주는 확정 단계 중심으로 구성되어 있습니다."
    ],
    "tables": [
      {
        "title": "Customer Brief",
        "columns": ["metric", "value", "note"],
        "rows": [
          ["Revenue", 1150000, "Q2 total"],
          ["Confirmed Orders", 12, "Q2 confirmed"],
          ["Inventory Risk", "MEDIUM", "Shipment concentration"]
        ]
      }
    ],
    "charts": [],
    "insights": [
      "고객사 관계는 안정적이며 추가 수주 여지가 있습니다."
    ],
    "risk_signals": [
      "출하 일정 집중 리스크가 있습니다."
    ],
    "actions": [
      "납기 리스크 완화 방안을 회의 안건에 포함합니다."
    ]
  },
  "error": null
}
```

#### 주요 필드 설명

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `customerId` | String | Y | 고객사 ID |
| `periodStart` | String | Y | 조회 시작일 |
| `periodEnd` | String | Y | 조회 종료일 |
| `includeInventory` | Boolean | N | 재고 정보 포함 여부 |
| `includeOrders` | Boolean | N | 수주 정보 포함 여부 |

#### 오류 응답 예시

```json
{
  "status": "error",
  "message": "처리 중 오류가 발생했습니다.",
  "data": null,
  "error": {
    "code": "NOT_FOUND",
    "message": "customerId에 해당하는 Synthetic 고객사를 찾을 수 없습니다."
  }
}
```

### 5.7 POST /tools/competitor-news

| 항목 | 내용 |
| --- | --- |
| 목적 | Synthetic 경쟁사 뉴스 데이터를 조회하고 시장 영향 요약을 생성 |
| 요청 Method | `POST` |
| URL | `/tools/competitor-news` |

#### Request JSON 예시

```json
{
  "periodStart": "2026-04-01",
  "periodEnd": "2026-06-30",
  "competitorName": "Competitor-X",
  "impactLevel": "HIGH",
  "keyword": "OLED"
}
```

#### Response JSON 예시

```json
{
  "status": "success",
  "message": "요청이 정상 처리되었습니다.",
  "data": {
    "answer": "경쟁사 뉴스 요약이 완료되었습니다.",
    "summary": [
      "Competitor-X는 OLED 신제품 출시와 가격 프로모션을 발표했습니다."
    ],
    "tables": [
      {
        "title": "Competitor News",
        "columns": ["newsDate", "competitorName", "title", "impactLevel"],
        "rows": [
          ["2026-05-12", "Competitor-X", "OLED premium line expansion", "HIGH"],
          ["2026-06-08", "Competitor-X", "Regional price promotion", "MEDIUM"]
        ]
      }
    ],
    "charts": [],
    "insights": [
      "프리미엄 OLED 영역에서 경쟁 강도가 높아질 가능성이 있습니다."
    ],
    "risk_signals": [
      "가격 프로모션으로 일부 고객사의 단가 협상 압박이 예상됩니다."
    ],
    "actions": [
      "주요 고객사별 가격 민감도와 대체 공급 가능성을 점검합니다."
    ]
  },
  "error": null
}
```

#### 주요 필드 설명

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `periodStart` | String | Y | 조회 시작일 |
| `periodEnd` | String | Y | 조회 종료일 |
| `competitorName` | String | N | Synthetic 경쟁사명 |
| `impactLevel` | String | N | 시장 영향 등급 |
| `keyword` | String | N | 검색 키워드 |

#### 오류 응답 예시

```json
{
  "status": "error",
  "message": "처리 중 오류가 발생했습니다.",
  "data": null,
  "error": {
    "code": "DATABASE_ERROR",
    "message": "competitor_news 조회 중 오류가 발생했습니다."
  }
}
```

### 5.8 POST /agent/briefing

| 항목 | 내용 |
| --- | --- |
| 목적 | LangGraph와 Tool 결과, LLM API를 사용하여 회의용 브리프북 초안을 생성 |
| 요청 Method | `POST` |
| URL | `/agent/briefing` |

#### Request JSON 예시

```json
{
  "requestId": "REQ-BRIEF-001",
  "sessionId": "SYN-SESSION-001",
  "userId": "demo-user",
  "topic": "CUST-A 2026년 2분기 사업 리뷰",
  "customerId": "CUST-A",
  "periodStart": "2026-04-01",
  "periodEnd": "2026-06-30",
  "sections": [
    "sales",
    "orders",
    "inventory",
    "competitor_news",
    "recommended_actions"
  ]
}
```

#### Response JSON 예시

```json
{
  "status": "success",
  "message": "요청이 정상 처리되었습니다.",
  "data": {
    "answer": "브리프북 초안 생성이 완료되었습니다.",
    "summary": [
      "1. 고객사 개요",
      "2. 판매 실적 요약",
      "3. 수주 및 출하 현황",
      "4. 재고 리스크",
      "5. 경쟁사 동향",
      "6. 회의 핵심 메시지"
    ],
    "tables": [
      {
        "title": "Briefing Outline",
        "columns": ["order", "section", "keyMessage"],
        "rows": [
          [1, "고객사 개요", "프리미엄 OLED 중심 고객사"],
          [2, "판매 실적 요약", "2분기 매출 증가"],
          [3, "재고 리스크", "7월 출하 집중 관리 필요"]
        ]
      }
    ],
    "charts": [],
    "insights": [
      "미팅의 핵심 메시지는 OLED 공급 안정성과 장기 협력 확대입니다."
    ],
    "risk_signals": [
      "경쟁사 가격 프로모션에 따른 단가 협상 리스크가 있습니다."
    ],
    "actions": [
      "납기 대응 계획을 첫 번째 안건으로 준비합니다.",
      "가격 방어 논리를 제품 품질과 공급 안정성 중심으로 구성합니다."
    ]
  },
  "error": null
}
```

#### 주요 필드 설명

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `requestId` | String | Y | Spring Boot에서 전달하는 요청 식별자 |
| `sessionId` | String | Y | 대화 세션 식별자 |
| `userId` | String | Y | PoC 사용자 식별자 |
| `topic` | String | Y | 브리프북 주제 |
| `customerId` | String | N | 고객사 ID |
| `periodStart` | String | Y | 분석 시작일 |
| `periodEnd` | String | Y | 분석 종료일 |
| `sections` | Array | N | 포함할 브리프북 섹션 목록 |

#### 오류 응답 예시

```json
{
  "status": "error",
  "message": "처리 중 오류가 발생했습니다.",
  "data": null,
  "error": {
    "code": "LLM_API_ERROR",
    "message": "LLM API 응답 생성에 실패했습니다."
  }
}
```

## 6. 구현 참고 사항

| 구분 | 기준 |
| --- | --- |
| Spring Boot 구현 | Java 8 문법과 Spring Boot 2.1.18.RELEASE 호환 API 사용 |
| Vue 구현 | Vue 2.6.10 Options API 기준으로 호출 |
| Secret 관리 | LLM API Key, DB Password는 코드 하드코딩 금지. 환경변수 또는 설정 파일 분리 |
| 데이터 사용 | 모든 예시는 Synthetic Data 기준 |
| 날짜 형식 | `YYYY-MM-DD` |
| 금액 단위 | PoC에서는 기본 `USD` 또는 응답 내 명시값 사용 |
| 오류 처리 | Spring Boot는 Python Agent 오류를 공통 오류 응답 포맷으로 변환 |
| 내부 API | Python FastAPI는 PoC 내부망 또는 로컬 개발 환경에서 Spring Boot가 호출하는 구조로 가정 |

