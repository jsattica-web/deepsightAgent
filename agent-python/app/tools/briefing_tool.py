import logging
from typing import Any

from app.schemas.common import ErrorResponse
from app.schemas.tool_schema import BriefingRequest, BriefingResponse, BriefingSection

logger = logging.getLogger(__name__)

SECTION_TITLES = {
    "sales": "판매 실적 요약",
    "orders": "수주 및 출하 현황",
    "inventory": "재고 리스크",
    "competitor_news": "경쟁사 동향",
    "recommended_actions": "권고 액션",
}


def _result_summary(value: Any) -> str:
    if value is None:
        return "분석 결과가 아직 제공되지 않았습니다."
    if hasattr(value, "summary"):
        return str(value.summary)
    if isinstance(value, dict):
        summary = value.get("summary")
        if isinstance(summary, list):
            return " / ".join(str(item) for item in summary)
        if summary:
            return str(summary)
    return "분석 결과가 제공됐으나 요약 문구가 없습니다."


def _collect_list(tool_results: dict[str, Any], field: str) -> list[str]:
    collected: list[str] = []
    for result in tool_results.values():
        if hasattr(result, field):
            values = getattr(result, field)
        elif isinstance(result, dict):
            values = result.get(field, [])
        else:
            values = []
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, str):
                collected.append(value)
            elif isinstance(value, dict):
                message = value.get("message")
                if message:
                    collected.append(str(message))
    return collected


def create_briefing_report(
    request: BriefingRequest,
) -> BriefingResponse | ErrorResponse:
    try:
        sections: list[BriefingSection] = []
        for index, section_key in enumerate(request.sections, start=1):
            title = SECTION_TITLES.get(section_key, section_key)
            if section_key == "recommended_actions":
                actions = _collect_list(request.tool_results, "actions")
                key_message = actions[0] if actions else "권고 액션을 정리할 분석 결과가 없습니다."
            else:
                key_message = _result_summary(request.tool_results.get(section_key))
            sections.append(
                BriefingSection(
                    order=index,
                    section=title,
                    key_message=key_message,
                )
            )

        insights = _collect_list(request.tool_results, "insights")
        risk_signals = _collect_list(request.tool_results, "risk_signals")
        actions = _collect_list(request.tool_results, "actions")

        if not insights:
            insights = ["각 Tool의 분석 결과를 연결하면 핵심 인사이트가 자동 취합됩니다."]
        if not actions:
            actions = ["판매·수주·재고·경쟁사 Tool 결과를 연결해 권고 액션을 구체화하세요."]

        target = request.customer_id or "전체 고객"
        return BriefingResponse(
            tool_name="create_briefing_report",
            status="success",
            summary=(
                f"{target} 대상 '{request.topic}' 브리프북 초안을 "
                f"{len(sections)}개 섹션으로 생성했습니다."
            ),
            data=sections,
            insights=insights[:10],
            risk_signals=risk_signals[:10],
            chart_data={},
            actions=actions[:10],
        )
    except Exception:
        logger.exception("Failed to execute create_briefing_report")
        return ErrorResponse(
            status="error",
            message="브리프북 초안을 생성하는 중 오류가 발생했습니다.",
        )
