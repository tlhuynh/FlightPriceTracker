# Database — SQLAlchemy models and functions to save/read flight price records.
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# Define the FlightRecord model
class FlightRecord(Base):
    __tablename__ = "flight_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    airline = Column(String(100), nullable=False)
    flight_number = Column(String(20), nullable=True)
    departure = Column(String(10), nullable=False)
    arrival = Column(String(10), nullable=False)
    outbound_date = Column(String(10), nullable=False)
    departure_time = Column(String(10), nullable=True)
    arrival_time = Column(String(10), nullable=True)
    stops = Column(Integer, nullable=True)
    total_duration = Column(Integer, nullable=True)
    price = Column(Float, nullable=True)
    checked_at = Column(DateTime, default=datetime.now)


# Function to save flight records to the database
def save_flight_prices(flights: list[dict]):
    session = SessionLocal()
    try:
        for flight in flights:
            record = FlightRecord(
                airline=flight["airline"],
                flight_number=flight.get("flight_number"),
                departure=flight["departure"],
                arrival=flight["arrival"],
                outbound_date=flight["outbound_date"],
                departure_time=flight.get("departure_time"),
                arrival_time=flight.get("arrival_time"),
                stops=flight.get("stops"),
                total_duration=flight.get("total_duration"),
                price=flight.get("price"),
            )
            session.add(record)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Function to get the latest record for a specific route and airline
def get_latest_price(departure: str, arrival: str, airline: str) -> FlightRecord | None:
    session = SessionLocal()
    try:
        return (
            session.query(FlightRecord)
            .filter_by(departure=departure, arrival=arrival, airline=airline)
            .order_by(FlightRecord.checked_at.desc())
            .first()
        )
    finally:
        session.close()


# Function to initialize the database (create tables)
def init_db():
    Base.metadata.create_all(bind=engine)
