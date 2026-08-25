import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.db import db
from app.graph.agent import run_agent
from app.schemas.common import ErrorResponse, HealthResponse
from app.schemas.tool_schema import (
    BriefingRequest,
    BriefingResponse,
    CompetitorNewsRequest,
    CompetitorNewsResponse,
    CustomerProfileRequest,
    CustomerProfileResponse,
    InventoryRiskRequest,
    InventoryRiskResponse,
    OrderStatusRequest,
    OrderStatusResponse,
    SalesTrendRequest,
    SalesTrendResponse,
)
from app.tools.briefing_tool import create_briefing_report
from app.tools.customer_tool import get_customer_profile
from app.tools.inventory_tool import get_inventory_risk
from app.tools.news_tool import search_competitor_news
from app.tools.order_tool import get_order_status
from app.tools.sales_tool import get_sales_trend
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Utf8JSONResponse(JSONResponse):
    """Windows PowerShell에서도 한글 JSON 응답을 UTF-8로 해석하게 한다."""

    media_type = "application/json; charset=utf-8"


@asynccontextmanager
async def lifespan(_: FastAPI):
    """FastAPI 앱이 종료될 때 DB 커넥션 풀을 정리한다."""
    yield
    db.close()


app = FastAPI(
    title="DeepSight Agent API",
    version="0.1.0",
    lifespan=lifespan,
    default_response_class=Utf8JSONResponse,
)


class AgentChatRequest(BaseModel):
    """사용자가 채팅창에 입력한 자연어 질문이다."""

    question: str = Field(min_length=1, examples=["최근 6개월 OLED 판매 동향 분석해줘"])


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    """요청 바디 검증 실패를 프로젝트 공통 오류 응답 형태로 변환한다."""
    response = ErrorResponse(
        status="error",
        message="요청 값이 올바르지 않습니다.",
        details=jsonable_encoder(exc.errors()),
    )
    return Utf8JSONResponse(status_code=422, content=response.model_dump(mode="json"))


@app.exception_handler(Exception)
async def unexpected_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """예상하지 못한 서버 오류를 로그로 남기고 공통 오류 응답을 반환한다."""
    logger.exception("Unhandled API error", exc_info=exc)
    response = ErrorResponse(status="error", message="요청 처리 중 오류가 발생했습니다.")
    return Utf8JSONResponse(status_code=500, content=response.model_dump(mode="json"))


@app.get(
    "/health",
    response_model=HealthResponse,
    responses={500: {"model": ErrorResponse}},
)
def health() -> HealthResponse:
    """서버와 PostgreSQL 연결이 정상인지 확인하는 헬스체크 API이다."""
    db.ping()
    return HealthResponse(status="success", service="agent-python", database="connected")


@app.post("/agent/chat")
def agent_chat(request: AgentChatRequest) -> dict:
    """사용자 자연어 질문을 Display Market Intelligence Agent로 전달한다."""
    return run_agent(request.question)


@app.post(
    "/tools/sales-trend",
    response_model=SalesTrendResponse,
    responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def sales_trend(request: SalesTrendRequest) -> SalesTrendResponse | JSONResponse:
    """판매 동향 Tool을 단독 실행하고 Tool 오류를 HTTP 오류 응답으로 변환한다."""
    # /agent/chat을 거치지 않고 Tool만 따로 확인할 때 사용하는 테스트용 API이다.
    result = get_sales_trend(request)
    if isinstance(result, ErrorResponse):
        return Utf8JSONResponse(status_code=500, content=result.model_dump(mode="json"))
    return result


@app.post(
    "/tools/order-status",
    response_model=OrderStatusResponse,
    responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def order_status(request: OrderStatusRequest) -> OrderStatusResponse | JSONResponse:
    """수주 현황 Tool을 단독 실행하고 Tool 오류를 HTTP 오류 응답으로 변환한다."""
    # Tool 함수가 ErrorResponse를 돌려주면 FastAPI 응답 코드도 500으로 맞춘다.
    result = get_order_status(request)
    if isinstance(result, ErrorResponse):
        return Utf8JSONResponse(status_code=500, content=result.model_dump(mode="json"))
    return result


@app.post(
    "/tools/inventory-risk",
    response_model=InventoryRiskResponse,
    responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def inventory_risk(
    request: InventoryRiskRequest,
) -> InventoryRiskResponse | JSONResponse:
    """재고 리스크 Tool을 단독 실행하고 Tool 오류를 HTTP 오류 응답으로 변환한다."""
    # 정상 결과는 Pydantic response_model을 통해 JSON으로 자동 변환된다.
    result = get_inventory_risk(request)
    if isinstance(result, ErrorResponse):
        return Utf8JSONResponse(status_code=500, content=result.model_dump(mode="json"))
    return result


@app.post(
    "/tools/customer-brief",
    response_model=CustomerProfileResponse,
    responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def customer_brief(
    request: CustomerProfileRequest,
) -> CustomerProfileResponse | JSONResponse:
    """13번 Customer Profile Tool을 단독 실행하고 Tool 오류를 HTTP 오류 응답으로 변환한다."""
    result = get_customer_profile(request)
    if isinstance(result, ErrorResponse):
        return Utf8JSONResponse(status_code=500, content=result.model_dump(mode="json"))
    return result


@app.post(
    "/tools/competitor-news",
    response_model=CompetitorNewsResponse,
    responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def competitor_news(
    request: CompetitorNewsRequest,
) -> CompetitorNewsResponse | JSONResponse:
    """14번 Competitor News Tool을 단독 실행하고 Tool 오류를 HTTP 오류 응답으로 변환한다."""
    result = search_competitor_news(request)
    if isinstance(result, ErrorResponse):
        return Utf8JSONResponse(status_code=500, content=result.model_dump(mode="json"))
    return result


@app.post(
    "/agent/briefing",
    response_model=BriefingResponse,
    responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def briefing(request: BriefingRequest) -> BriefingResponse | JSONResponse:
    """15번 Briefing Report Tool을 실행하고 Tool 오류를 HTTP 오류 응답으로 변환한다."""
    result = create_briefing_report(request)
    if isinstance(result, ErrorResponse):
        return Utf8JSONResponse(status_code=500, content=result.model_dump(mode="json"))
    return result
