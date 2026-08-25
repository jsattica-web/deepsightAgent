from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import ToolResponse


class SalesTrendRequest(BaseModel):
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
        if self.start_month > self.end_month:
            raise ValueError("start_month는 end_month보다 늦을 수 없습니다.")
        return self


class SalesTrendPoint(BaseModel):
    month: str
    qty: int
    revenue: float
    asp: float


class SalesTrendResponse(ToolResponse):
    data: list[SalesTrendPoint]
    chart_data: dict[str, Any]


class OrderStatusRequest(BaseModel):
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
    data: list[OrderStatusPoint]
    chart_data: dict[str, Any]


class InventoryRiskRequest(BaseModel):
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
    month: str
    ending_stock: int
    safety_stock: int
    production_qty: int
    sales_qty: int


class InventoryRiskSignal(BaseModel):
    level: Literal["HIGH", "MEDIUM", "LOW"]
    type: str
    message: str


class InventoryRiskResponse(ToolResponse):
    data: list[InventoryTrendPoint]
    risk_signals: list[InventoryRiskSignal]
    chart_data: dict[str, Any]


class CompetitorNewsRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start_date": "2026-04-01",
                "end_date": "2026-06-30",
                "companies": ["BOE", "CSOT", "LGD"],
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
        if self.start_date > self.end_date:
            raise ValueError("start_date는 end_date보다 늦을 수 없습니다.")
        if self.companies is not None:
            cleaned = [company.strip() for company in self.companies if company.strip()]
            self.companies = cleaned or None
        return self


class CompetitorNewsPoint(BaseModel):
    news_date: date
    company: str
    category: str
    title: str
    summary: str
    impact_score: float
    impact_level: Literal["HIGH", "MEDIUM", "LOW"]
    product_group: str


class CompetitorNewsResponse(ToolResponse):
    data: list[CompetitorNewsPoint]
    chart_data: dict[str, Any]


class BriefingRequest(BaseModel):
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
        if self.start_date > self.end_date:
            raise ValueError("start_date는 end_date보다 늦을 수 없습니다.")
        if not self.sections:
            raise ValueError("sections는 한 개 이상 지정해야 합니다.")
        return self


class BriefingSection(BaseModel):
    order: int
    section: str
    key_message: str


class BriefingResponse(ToolResponse):
    data: list[BriefingSection]
    chart_data: dict[str, Any]


class CustomerProfileRequest(BaseModel):
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
        if self.start_month > self.end_month:
            raise ValueError("start_month는 end_month보다 늦을 수 없습니다.")
        return self


class CustomerProfilePoint(BaseModel):
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
    data: list[CustomerProfilePoint]
    chart_data: dict[str, Any]
