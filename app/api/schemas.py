# API schemas — Pydantic models defining the shape of API request/response JSON.
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FlightRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    airline: str
    flight_number: str | None
    departure: str
    arrival: str
    outbound_date: str
    departure_time: str | None
    arrival_time: str | None
    stops: int | None
    total_duration: int | None
    price: float | None
    checked_at: datetime | None


class RouteResponse(BaseModel):
    departure: str
    arrival: str
