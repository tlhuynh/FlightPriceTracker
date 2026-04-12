# Database — SQLAlchemy models and functions to save/read flight price records.
# NOTE: Models and database functions are kept in this single file for now.
# Consider splitting into models/ and repositories/ folders as the project grows.
# TODO: Refactor this file when more models and functions are added to keep things organized and maintainable.
import logging
from datetime import datetime

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Float,
    text,
    func,
)
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

logger = logging.getLogger(__name__)
connection_url = URL.create(
    "mssql+pyodbc",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    query={
        "driver": "ODBC Driver 18 for SQL Server",
        "TrustServerCertificate": "yes",
    },
)
engine = create_engine(connection_url)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# --- Flight Record model ---


# Define the FlightRecord model
class FlightRecord(Base):
    __tablename__ = "flight_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    airline = Column(String(100), nullable=False)
    flight_number = Column(String(20), nullable=True)
    departure = Column(String(10), nullable=False)
    arrival = Column(String(10), nullable=False)
    outbound_date = Column(String(20), nullable=False)
    return_date = Column(String(20), nullable=True)
    departure_time = Column(String(20), nullable=True)
    arrival_time = Column(String(20), nullable=True)
    stops = Column(Integer, nullable=True)
    total_duration = Column(Integer, nullable=True)
    price = Column(Float, nullable=True)
    checked_at = Column(DateTime, default=datetime.now)


# Function to save flight records to the database
def save_flight_records(flights: list[dict]):
    logger.info("Saving %d flight records to database.", len(flights))
    session = SessionLocal()
    try:
        for flight in flights:
            record = FlightRecord(
                airline=flight["airline"],
                flight_number=flight.get("flight_number"),
                departure=flight["departure"],
                arrival=flight["arrival"],
                outbound_date=flight["outbound_date"],
                return_date=flight.get("return_date"),
                departure_time=flight.get("departure_time"),
                arrival_time=flight.get("arrival_time"),
                stops=flight.get("stops"),
                total_duration=flight.get("total_duration"),
                price=flight.get("price"),
            )
            session.add(record)
        session.commit()
        logger.info("Successfully saved %d flight records.", len(flights))
    except Exception:
        logger.error("Failed to save flight records. Rolling back.")
        session.rollback()
        raise
    finally:
        session.close()


# Function to get the latest record for a specific route, airline, and trip (outbound + return date)
def get_latest_record(
    departure: str, arrival: str, airline: str, flight_number: str, outbound_date: str, return_date: str
) -> FlightRecord | None:
    session = SessionLocal()
    try:
        return (
            session.query(FlightRecord)
            .filter_by(
                departure=departure,
                arrival=arrival,
                airline=airline,
                flight_number=flight_number,
                outbound_date=outbound_date,
                return_date=return_date,
            )
            .order_by(FlightRecord.checked_at.desc())
            .first()
        )
    finally:
        session.close()


# Function to get the list of flight numbers for a specific route and trip from the most recent check
def get_previous_flight_numbers(
    departure: str, arrival: str, outbound_date: str, return_date: str
) -> list[dict]:
    session = SessionLocal()
    try:
        latest_check = (
            session.query(func.max(FlightRecord.checked_at))
            .filter_by(
                departure=departure, arrival=arrival, outbound_date=outbound_date, return_date=return_date
            )
            .scalar()
        )
        if not latest_check:
            return []

        records = (
            session.query(FlightRecord)
            .filter_by(
                departure=departure,
                arrival=arrival,
                outbound_date=outbound_date,
                return_date=return_date,
                checked_at=latest_check,
            )
            .all()
        )
        return [
            {"flight_number": r.flight_number, "airline": r.airline, "price": r.price}
            for r in records
            if r.flight_number is not None
        ]
    finally:
        session.close()


# --- SerpAPI call logs ---


# Define the ApiCallLog model to track API calls for monitoring and debugging purposes.
class ApiCallLog(Base):
    __tablename__ = "api_call_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint = Column(String(100), nullable=False)
    route = Column(String(20), nullable=False)
    called_at = Column(DateTime, default=datetime.now)


# Function to log API calls to the database for monitoring and debugging purposes.
def log_api_call(endpoint: str, route: str):
    session = SessionLocal()
    try:
        session.add(ApiCallLog(endpoint=endpoint, route=route))
        session.commit()
    finally:
        session.close()


# --- Database ---


# Function to initialize the database (create tables)
def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized — tables created.")


# Function to check database connection
def check_db_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection check passed.")
        return True
    except Exception:
        logger.error("Database connection check failed.")
        return False
