from datetime import date
from typing import Any

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
