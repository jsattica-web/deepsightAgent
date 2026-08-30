from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import ToolResponse


class SalesTrendRequest(BaseModel):
    """판매 동향 Tool 요청값이다."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start_month": "2026-01",
                "end_month": "2026-06",
                "product_group": "Mobile OLED",
                "customer_id": None,
            }
        }
    )

    start_month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", examples=["2026-01"])
    end_month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", examples=["2026-06"])
    product_group: str = Field(min_length=1, max_length=50, examples=["Mobile OLED"])
    customer_id: str | None = Field(default=None, max_length=30)

    @model_validator(mode="after")
    def validate_month_range(self) -> "SalesTrendRequest":
        """판매 조회 시작 월이 종료 월보다 늦지 않은지 검증한다."""
        if self.start_month > self.end_month:
            raise ValueError("start_month는 end_month보다 늦을 수 없습니다.")
        return self


class SalesTrendPoint(BaseModel):
    """판매 동향 차트와 표에 표시할 월별 집계 데이터이다."""

    month: str
    qty: int
    revenue: float
    asp: float


class SalesTrendResponse(ToolResponse):
    """판매 동향 Tool의 성공 응답이다."""

    data: list[SalesTrendPoint]
    chart_data: dict[str, Any]


class OrderStatusRequest(BaseModel):
    """수주 현황 Tool 요청값이다."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start_date": "2026-01-01",
                "end_date": "2026-06-30",
                "customer_id": None,
                "product_group": "Mobile OLED",
                "status": None,
            }
        }
    )

    start_date: date
    end_date: date
    customer_id: str | None = Field(default=None, max_length=30)
    product_group: str = Field(
        min_length=1, max_length=50, examples=["Mobile OLED"]
    )
    status: str | None = Field(default=None, examples=["CONFIRMED"])

    @model_validator(mode="after")
    def validate_request(self) -> "OrderStatusRequest":
        """수주 조회 기간과 주문 상태 코드가 허용 범위 안에 있는지 검증한다."""
        if self.start_date > self.end_date:
            raise ValueError("start_date는 end_date보다 늦을 수 없습니다.")
        if self.status:
            self.status = self.status.upper()
            allowed_statuses = {
                "REQUESTED",
                "CONFIRMED",
                "DELAYED",
                "SHIPPED",
                "CANCELLED",
            }
            if self.status not in allowed_statuses:
                raise ValueError(
                    "status는 REQUESTED, CONFIRMED, DELAYED, "
                    "SHIPPED, CANCELLED 중 하나여야 합니다."
                )
        return self


class OrderStatusPoint(BaseModel):
    """수주 현황 차트와 표에 표시할 월별 집계 데이터이다."""

    month: str
    total_orders: int
    total_order_qty: int
    confirmed_count: int
    pending_count: int
    delayed_count: int
    cancelled_count: int
    shipped_count: int
    risk_order_count: int


class OrderStatusResponse(ToolResponse):
    """수주 현황 Tool의 성공 응답이다."""

    data: list[OrderStatusPoint]
    chart_data: dict[str, Any]


class InventoryRiskRequest(BaseModel):
    """재고 리스크 Tool 요청값이다."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "inventory_month": "2026-06",
                "product_group": "TV OLED",
            }
        }
    )

    inventory_month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    product_group: str = Field(min_length=1, max_length=50)


class InventoryTrendPoint(BaseModel):
    """재고 리스크 차트와 표에 표시할 월별 재고 데이터이다."""

    month: str
    ending_stock: int
    safety_stock: int
    production_qty: int
    sales_qty: int


class InventoryRiskSignal(BaseModel):
    """재고 Tool이 감지한 개별 리스크 신호이다."""

    level: Literal["HIGH", "MEDIUM", "LOW"]
    type: str
    message: str


class InventoryRiskResponse(ToolResponse):
    """재고 리스크 Tool의 성공 응답이다."""

    data: list[InventoryTrendPoint]
    risk_signals: list[InventoryRiskSignal]
    chart_data: dict[str, Any]


class CustomerProfileRequest(BaseModel):
    """13번 Customer Profile Tool 요청값이다."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer_id": "CUST_A",
                "start_month": "2026-01",
                "end_month": "2026-06",
            }
        }
    )

    customer_id: str = Field(min_length=1, max_length=30)
    start_month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    end_month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")

    @model_validator(mode="after")
    def validate_month_range(self) -> "CustomerProfileRequest":
        """고객사 조회 시작 월이 종료 월보다 늦지 않은지 검증한다."""
        if self.start_month > self.end_month:
            raise ValueError("start_month는 end_month보다 늦을 수 없습니다.")
        return self


class CustomerProfilePoint(BaseModel):
    """고객 프로필과 기간별 판매·수주 요약 데이터이다."""

    customer_id: str
    customer_name: str
    segment: str
    region: str
    tier: str
    main_application: str
    sales_qty: int
    sales_revenue: float
    order_count: int
    order_qty: int
    delayed_order_count: int


class CustomerProfileResponse(ToolResponse):
    """13번 Customer Profile Tool의 성공 응답이다."""

    data: list[CustomerProfilePoint]
    chart_data: dict[str, Any]


class CompetitorNewsRequest(BaseModel):
    """14번 Competitor News Tool 요청값이다."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start_date": "2026-04-01",
                "end_date": "2026-06-30",
                "companies": ["Samsung Display", "LG Display", "BOE"],
                "category": None,
                "impact_level": None,
                "keyword": "OLED",
                "product_group": None,
            }
        }
    )

    start_date: date
    end_date: date
    companies: list[str] | None = None
    category: str | None = Field(default=None, max_length=50)
    impact_level: Literal["HIGH", "MEDIUM", "LOW"] | None = None
    keyword: str | None = Field(default=None, max_length=100)
    product_group: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def validate_request(self) -> "CompetitorNewsRequest":
        """뉴스 조회 기간과 경쟁사 목록을 검증한다."""
        if self.start_date > self.end_date:
            raise ValueError("start_date는 end_date보다 늦을 수 없습니다.")
        if self.companies is not None:
            cleaned = [company.strip() for company in self.companies if company.strip()]
            self.companies = cleaned or None
        return self


class CompetitorNewsPoint(BaseModel):
    """경쟁사 뉴스 검색 결과의 개별 기사 데이터이다."""

    news_date: date
    company: str
    category: str
    title: str
    summary: str
    impact_score: float
    impact_level: Literal["HIGH", "MEDIUM", "LOW"]
    product_group: str

    # 같은 응답 안에서 DB 기사인지 NAVER 기사인지 구분합니다.
    source: Literal["DB", "NAVER"] | None = None


class CompetitorNewsResponse(ToolResponse):
    """14번 Competitor News Tool의 성공 응답이다."""

    data: list[CompetitorNewsPoint]
    chart_data: dict[str, Any]


class BriefingRequest(BaseModel):
    """15번 Briefing Report Tool 요청값이다."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "topic": "2026년 2분기 사업 리뷰",
                "customer_id": "CUST_A",
                "start_date": "2026-04-01",
                "end_date": "2026-06-30",
                "sections": [
                    "sales",
                    "orders",
                    "inventory",
                    "competitor_news",
                    "recommended_actions",
                ],
                "tool_results": {},
            }
        }
    )

    topic: str = Field(min_length=1, max_length=200)
    customer_id: str | None = Field(default=None, max_length=30)
    start_date: date
    end_date: date
    sections: list[str] = Field(
        default_factory=lambda: [
            "sales",
            "orders",
            "inventory",
            "competitor_news",
            "recommended_actions",
        ]
    )
    tool_results: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_request(self) -> "BriefingRequest":
        """브리핑 기간과 생성할 섹션 목록을 검증한다."""
        if self.start_date > self.end_date:
            raise ValueError("start_date는 end_date보다 늦을 수 없습니다.")
        if not self.sections:
            raise ValueError("sections는 한 개 이상 지정해야 합니다.")
        return self


class BriefingSection(BaseModel):
    """브리프북의 개별 섹션 데이터이다."""

    order: int
    section: str
    key_message: str


class BriefingResponse(ToolResponse):
    """15번 Briefing Report Tool의 성공 응답이다."""

    data: list[BriefingSection]
    chart_data: dict[str, Any]
