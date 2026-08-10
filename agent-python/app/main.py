import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.db import db
from app.schemas.common import ErrorResponse, HealthResponse
from app.schemas.tool_schema import SalesTrendRequest, SalesTrendResponse
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
def sales_trend(request: SalesTrendRequest) -> SalesTrendResponse:
    return get_sales_trend(request)
