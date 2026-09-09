from datetime import date
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import ToolResponse



# 목록 안의 각 문자열에도 길이 제한을 적용한다.
ProductGroup = Annotated[str, Field(min_length=1, max_length=50)]
CustomerId = Annotated[str, Field(min_length=1, max_length=30)]
OrderState = Literal["REQUESTED", "CONFIRMED", "DELAYED", "SHIPPED", "CANCELLED"]


def validate_month_range(start_month: str, end_month: str) -> None:
    """월 형식 검증 후 실제 달력과 조회 순서를 확인한다."""
    date.fromisoformat(f"{start_month}-01")
    date.fromisoformat(f"{end_month}-01")
    if start_month > end_month:
        raise ValueError("start_month는 end_month보다 늦을 수 없습니다.")


def validate_unique_items(values: list[str] | None) -> list[str] | None:
    """중복된 필터나 집계 항목을 허용하지 않는다."""
    if values is not None and len(values) != len(set(values)):
        raise ValueError("목록에 중복된 값이 있습니다.")
    return values


class SalesTrendRequest(BaseModel):
    """제품군과 고객 조건으로 월별 판매 실적을 조회한다."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "start_month": "2026-01",
                "end_month": "2026-06",
                "product_group": "Mobile OLED",
                "customer_id": None,
                "group_by_customer": False,
            }
        },
    )

    start_month: str = Field(pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$")
    end_month: str = Field(pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$")
    product_group: ProductGroup | None = Field(
        default=None, description="제품군 조건이 없으면 null. ALL은 사용하지 않는다."
    )
    customer_id: CustomerId | None = None
    group_by_customer: bool = False

    @model_validator(mode="after")
    def validate_request(self) -> "SalesTrendRequest":
        validate_month_range(self.start_month, self.end_month)
        return self


class SalesTrendPoint(BaseModel):
    """선택한 집계 기준과 지표를 담는 판매 결과 행이다."""

    # 집계하지 않은 차원과 선택하지 않은 지표는 None으로 구분한다.
    month: str | None = None
    product_group: str | None = None
    customer_id: str | None = None
    customer_name: str | None = None
    qty: int | None = None
    revenue: float | None = None
    asp: float | None = None


class SalesTrendResponse(ToolResponse):
    """판매 동향 Tool의 성공 응답이다."""

    data: list[SalesTrendPoint]
    chart_data: dict[str, Any]
    aggregates: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class OrderStatusRequest(BaseModel):
    """제품군·고객·상태 조건과 고객별·제품군별 집계를 받는 수주 요청이다."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "start_date": "2026-01-01",
                "end_date": "2026-06-30",
                "product_group": "Mobile OLED",
                "customer_id": None,
                "status": None,
                "group_by_customer": False,
                "group_by_product_group": True,
            }
        },
    )

    start_date: date
    end_date: date
    product_group: ProductGroup | None = Field(
        default=None, description="제품군 조건이 없으면 null. ALL은 사용하지 않는다."
    )
    customer_id: CustomerId | None = None
    status: OrderState | None = None
    group_by_customer: bool = False
    group_by_product_group: bool = True

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value):
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @model_validator(mode="after")
    def validate_request(self) -> "OrderStatusRequest":
        if self.start_date > self.end_date:
            raise ValueError("start_date는 end_date보다 늦을 수 없습니다.")
        return self


class OrderStatusPoint(BaseModel):
    """수주 현황 차트와 표에 표시할 월별 집계 데이터이다."""

    product_group: str | None = None
    customer_id: str | None = None
    customer_name: str | None = None
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
    aggregates: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class InventoryRiskRequest(BaseModel):
    """시작 월부터 종료 월까지 제품군별 재고를 조회하는 요청이다."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "start_month": "2026-04",
                "end_month": "2026-06",
                "product_group": "TV OLED",
                "customer_id": None,
                "group_by_customer": False,
            }
        },
    )

    start_month: str = Field(pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$")
    end_month: str = Field(pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$")
    product_group: ProductGroup | None = Field(
        default=None,
        min_length=1,
        description="제품군 조건이 없으면 null. ALL은 사용하지 않는다.",
    )

    customer_id: CustomerId | None = None
    group_by_customer: bool = False
    group_by_product_group: bool = True

    @model_validator(mode="after")
    def validate_request(self) -> "InventoryRiskRequest":
        validate_month_range(self.start_month, self.end_month)
        return self


class InventoryTrendPoint(BaseModel):
    """재고 리스크 차트와 표에 표시할 월별 재고 데이터이다."""

    customer_id: str | None = None
    customer_name: str | None = None
    product_group: str | None = None
    month: str
    ending_stock: int
    safety_stock: int
    production_qty: int
    sales_qty: int
    # 미계산 상태를 0으로 표시하지 않는다. 계산은 조회 계층에서 수행한다.
    shortage_qty: int | None = Field(default=None, ge=0)
    excess_qty: int | None = Field(default=None, ge=0)


class InventoryRiskSignal(BaseModel):
    """재고 Tool이 감지한 개별 리스크 신호이다."""

    customer_id: str | None = None
    customer_name: str | None = None
    product_group: str | None = None
    month: str | None = None
    level: Literal["HIGH", "MEDIUM", "LOW"]
    type: str
    message: str


class InventoryRiskResponse(ToolResponse):
    """재고 리스크 Tool의 성공 응답이다."""

    data: list[InventoryTrendPoint]
    risk_signals: list[InventoryRiskSignal]
    chart_data: dict[str, Any]
    aggregates: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


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


