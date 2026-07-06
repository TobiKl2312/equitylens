from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    ChatRequest,
    CompanyOut,
    FilingOut,
    FundamentalOut,
    PriceOut,
    ScreenerRow,
)
from app.core.config import get_settings
from app.core.db import get_session
from app.models import Company
from app.rag.embeddings import VoyageClient
from app.services import companies as service
from app.services import rag

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/companies", response_model=list[CompanyOut])
async def list_companies(session: SessionDep):
    return await service.list_companies(session)


@router.get("/screener", response_model=list[ScreenerRow])
async def screener(session: SessionDep):
    return await service.get_screener(session)


async def _require_company(ticker: str, session: AsyncSession) -> Company:
    company = await service.get_company(session, ticker)
    if company is None:
        raise HTTPException(status_code=404, detail=f"Unknown ticker: {ticker}")
    return company


@router.get("/companies/{ticker}", response_model=CompanyOut)
async def get_company(ticker: str, session: SessionDep):
    return await _require_company(ticker, session)


@router.get("/companies/{ticker}/prices", response_model=list[PriceOut])
async def get_prices(
    ticker: str,
    session: SessionDep,
    start: date | None = None,
    end: date | None = None,
):
    company = await _require_company(ticker, session)
    return await service.get_prices(session, company.id, start, end)


@router.get("/companies/{ticker}/fundamentals", response_model=list[FundamentalOut])
async def get_fundamentals(
    ticker: str,
    session: SessionDep,
    metric: str | None = None,
):
    company = await _require_company(ticker, session)
    return await service.get_fundamentals(session, company.id, metric)


@router.get("/companies/{ticker}/filings", response_model=list[FilingOut])
async def get_filings(ticker: str, session: SessionDep):
    company = await _require_company(ticker, session)
    return await service.get_filings(session, company.id)


@router.post("/companies/{ticker}/chat")
async def chat(ticker: str, request: ChatRequest, session: SessionDep):
    """RAG chat over the company's filings, streamed as Server-Sent Events."""
    company = await _require_company(ticker, session)
    voyage = VoyageClient(api_key=get_settings().voyage_api_key)

    async def event_stream():
        try:
            async for event in rag.answer_question(
                session, voyage, company, request.question, request.session_id
            ):
                yield event
        finally:
            voyage.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
