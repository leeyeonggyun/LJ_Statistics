from sqlalchemy import Column, String, BigInteger, Text, DateTime, Date, Integer, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class SearchResult(Base):
    __tablename__ = "search_results"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    search_query = Column(String(255), nullable=False, index=True)
    search_date = Column(Date, nullable=False, index=True)
    max_results = Column(Integer, nullable=False)
    result_count = Column(Integer, nullable=False)
    channels_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
