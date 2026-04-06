# API routes — FastAPI endpoint definitions for the dashboard to read price data.
import logging
from fastapi import APIRouter, Query

from app.config import ROUTES
from app.api.schemas import FlightRecordResponse, RouteResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/routes", response_model=list[RouteResponse])
def get_routes():
    return ROUTES


@router.get("/prices/latest", response_model=list[FlightRecordResponse])
def get_latest_prices():
    from app.db import SessionLocal, FlightRecord
    from sqlalchemy import func

    session = SessionLocal()
    try:
        subquery = (
            session.query(
                FlightRecord.airline,
                FlightRecord.departure,
                FlightRecord.arrival,
                FlightRecord.flight_number,
                FlightRecord.outbound_date,
                func.max(FlightRecord.checked_at).label("max_checked_at"),
            )
            .group_by(
                FlightRecord.airline,
                FlightRecord.departure,
                FlightRecord.arrival,
                FlightRecord.flight_number,
                FlightRecord.outbound_date,
            )
            .subquery()
        )

        results = (
            session.query(FlightRecord)
            .join(
                subquery,
                (FlightRecord.airline == subquery.c.airline)
                & (FlightRecord.departure == subquery.c.departure)
                & (FlightRecord.arrival == subquery.c.arrival)
                & (FlightRecord.flight_number == subquery.c.flight_number)
                & (FlightRecord.outbound_date == subquery.c.outbound_date)
                & (FlightRecord.checked_at == subquery.c.max_checked_at),
            )
            .all()
        )

        return [FlightRecordResponse.model_validate(r) for r in results]
    finally:
        session.close()


@router.get("/prices/{departure}/{arrival}", response_model=list[FlightRecordResponse])
def get_price_history(departure: str, arrival: str, days: int = Query(default=90)):
    from datetime import datetime, timedelta
    from app.db import SessionLocal, FlightRecord

    session = SessionLocal()
    try:
        cutoff = datetime.now() - timedelta(days=days)
        results = (
            session.query(FlightRecord)
            .filter(
                FlightRecord.departure == departure,
                FlightRecord.arrival == arrival,
                FlightRecord.checked_at >= cutoff,
            )
            .order_by(FlightRecord.checked_at.desc())
            .all()
        )

        return [FlightRecordResponse.model_validate(r) for r in results]
    finally:
        session.close()
