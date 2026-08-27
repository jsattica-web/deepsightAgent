from typing import Any, Literal, TypedDict


QuestionType = Literal["sales_trend", "order_status", "inventory_risk", "unsupported"]


class AgentState(TypedDict):
    """LangGraph의 각 단계가 함께 읽고 쓰는 작업 상태이다."""

    question: str
    question_type: QuestionType
    tool_args: dict[str, Any]
    tool_result: dict[str, Any]
    answer: dict[str, Any]
    error: str | None

