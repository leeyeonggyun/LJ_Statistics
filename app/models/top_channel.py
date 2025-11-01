
from sqlalchemy import Column, String, BigInteger, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class TopChannel(Base):
    __tablename__ = "top_channels"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    country_code = Column(String(2), nullable=False, index=True)  # KR, JP, US
    channel_id = Column(String(255), nullable=False, unique=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    subscriber_count = Column(BigInteger, nullable=False)
    video_count = Column(BigInteger, nullable=False)
    view_count = Column(BigInteger, nullable=False)
    custom_url = Column(String(255), nullable=True)
    published_at = Column(String(50), nullable=True)
    rank = Column(BigInteger, nullable=False)  # 1-5
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
