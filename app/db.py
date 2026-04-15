# Database — SQLAlchemy models and functions for price insight records.
import logging
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, text
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


# --- Route Insight model ---

class RouteInsight(Base):
    __tablename__ = "route_insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    departure = Column(String(10), nullable=False)
    arrival = Column(String(10), nullable=False)
    outbound_date = Column(String(20), nullable=False)
    return_date = Column(String(20), nullable=False)
    lowest_price = Column(Float, nullable=True)
    price_level = Column(String(20), nullable=True)
    typical_low = Column(Float, nullable=True)
    typical_high = Column(Float, nullable=True)
    checked_at = Column(DateTime, default=datetime.now)


def save_route_insight(insight: dict):
    session = SessionLocal()
    try:
        record = RouteInsight(
            departure=insight["departure"],
            arrival=insight["arrival"],
            outbound_date=insight["outbound_date"],
            return_date=insight["return_date"],
            lowest_price=insight.get("lowest_price"),
            price_level=insight.get("price_level"),
            typical_low=insight.get("typical_low"),
            typical_high=insight.get("typical_high"),
        )
        session.add(record)
        session.commit()
        logger.info(
            "Saved route insight for %s → %s on %s: $%s (%s).",
            insight["departure"],
            insight["arrival"],
            insight["outbound_date"],
            insight.get("lowest_price"),
            insight.get("price_level"),
        )
    except Exception:
        logger.error("Failed to save route insight. Rolling back.")
        session.rollback()
        raise
    finally:
        session.close()


def get_latest_route_insight(
    departure: str, arrival: str, outbound_date: str, return_date: str
) -> RouteInsight | None:
    session = SessionLocal()
    try:
        return (
            session.query(RouteInsight)
            .filter_by(
                departure=departure,
                arrival=arrival,
                outbound_date=outbound_date,
                return_date=return_date,
            )
            .order_by(RouteInsight.checked_at.desc())
            .first()
        )
    finally:
        session.close()


# --- API call log ---

class ApiCallLog(Base):
    __tablename__ = "api_call_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint = Column(String(100), nullable=False)
    route = Column(String(20), nullable=False)
    called_at = Column(DateTime, default=datetime.now)


def log_api_call(endpoint: str, route: str):
    session = SessionLocal()
    try:
        session.add(ApiCallLog(endpoint=endpoint, route=route))
        session.commit()
    finally:
        session.close()


# --- Database setup ---

def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized — tables created.")


def check_db_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection check passed.")
        return True
    except Exception:
        logger.error("Database connection check failed.")
        return False
