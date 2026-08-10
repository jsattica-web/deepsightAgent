from typing import Any, Literal

from pydantic import BaseModel, Field


class CommonResponse(BaseModel):
    """Fields shared by every API response."""

    status: Literal["success", "error"]


class HealthResponse(CommonResponse):
    service: str
    database: str


class ErrorResponse(CommonResponse):
    message: str
    details: Any | None = None


class ToolResponse(CommonResponse):
    tool_name: str
    summary: str
    data: list[Any] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)
    risk_signals: list[str] = Field(default_factory=list)
    chart_data: dict[str, Any] = Field(default_factory=dict)
    actions: list[str] = Field(default_factory=list)
