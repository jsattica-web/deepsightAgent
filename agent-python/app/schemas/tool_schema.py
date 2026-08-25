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
