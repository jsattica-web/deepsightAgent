from typing import Any, Literal

from pydantic import BaseModel, Field


class CommonResponse(BaseModel):
    """모든 API 응답이 공통으로 가지는 최상위 상태값이다."""

    status: Literal["success", "error"]


class HealthResponse(CommonResponse):
    """헬스체크 API가 서버와 DB 상태를 알려줄 때 사용하는 응답이다."""

    service: str
    database: str


class ErrorResponse(CommonResponse):
    """API 또는 Tool 처리 중 오류가 났을 때 사용하는 공통 응답이다."""

    message: str
    details: Any | None = None


class ToolResponse(CommonResponse):
    """판매, 수주, 재고 Tool이 공통으로 반환하는 기본 응답 구조이다."""

    tool_name: str
    summary: str
    data: list[Any] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)
    risk_signals: list[str] = Field(default_factory=list)
    chart_data: dict[str, Any] = Field(default_factory=dict)
    actions: list[str] = Field(default_factory=list)
