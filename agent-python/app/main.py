import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.db import db
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

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    db.close()


app = FastAPI(title="DeepSight Agent API", version="0.1.0", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    response = ErrorResponse(
        status="error",
        message="요청 값이 올바르지 않습니다.",
        details=jsonable_encoder(exc.errors()),
    )
    return JSONResponse(status_code=422, content=response.model_dump(mode="json"))


@app.exception_handler(Exception)
async def unexpected_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API error", exc_info=exc)
    response = ErrorResponse(status="error", message="요청 처리 중 오류가 발생했습니다.")
    return JSONResponse(status_code=500, content=response.model_dump(mode="json"))


@app.get(
    "/health",
    response_model=HealthResponse,
    responses={500: {"model": ErrorResponse}},
)
def health() -> HealthResponse:
    db.ping()
    return HealthResponse(status="success", service="agent-python", database="connected")


@app.post(
    "/tools/sales-trend",
    response_model=SalesTrendResponse,
    responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def sales_trend(request: SalesTrendRequest) -> SalesTrendResponse | JSONResponse:
    result = get_sales_trend(request)
    if isinstance(result, ErrorResponse):
        return JSONResponse(status_code=500, content=result.model_dump(mode="json"))
    return result


@app.post(
    "/tools/order-status",
    response_model=OrderStatusResponse,
    responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def order_status(request: OrderStatusRequest) -> OrderStatusResponse | JSONResponse:
    result = get_order_status(request)
    if isinstance(result, ErrorResponse):
        return JSONResponse(status_code=500, content=result.model_dump(mode="json"))
    return result


@app.post(
    "/tools/inventory-risk",
    response_model=InventoryRiskResponse,
    responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def inventory_risk(
    request: InventoryRiskRequest,
) -> InventoryRiskResponse | JSONResponse:
    result = get_inventory_risk(request)
    if isinstance(result, ErrorResponse):
        return JSONResponse(status_code=500, content=result.model_dump(mode="json"))
    return result


@app.post(
    "/tools/customer-brief",
    response_model=CustomerProfileResponse,
    responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def customer_brief(
    request: CustomerProfileRequest,
) -> CustomerProfileResponse | JSONResponse:
    result = get_customer_profile(request)
    if isinstance(result, ErrorResponse):
        return JSONResponse(status_code=500, content=result.model_dump(mode="json"))
    return result


@app.post(
    "/tools/competitor-news",
    response_model=CompetitorNewsResponse,
    responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def competitor_news(
    request: CompetitorNewsRequest,
) -> CompetitorNewsResponse | JSONResponse:
    result = search_competitor_news(request)
    if isinstance(result, ErrorResponse):
        return JSONResponse(status_code=500, content=result.model_dump(mode="json"))
    return result


@app.post(
    "/agent/briefing",
    response_model=BriefingResponse,
    responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def briefing(request: BriefingRequest) -> BriefingResponse | JSONResponse:
    result = create_briefing_report(request)
    if isinstance(result, ErrorResponse):
        return JSONResponse(status_code=500, content=result.model_dump(mode="json"))
    return result
