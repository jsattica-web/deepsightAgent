from datetime import date
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ToolResponse


class SalesTrendRequest(BaseModel):
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
    sales_month: date
    total_qty: int
    total_revenue: float
    avg_asp: float


class SalesTrendResponse(ToolResponse):
    data: list[SalesTrendPoint]
    chart_data: dict[str, Any]
