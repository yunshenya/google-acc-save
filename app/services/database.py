import datetime
from typing import Any

from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DATABASE_URL

Base = declarative_base()
engine: Any = create_async_engine(DATABASE_URL)
SessionLocal = sessionmaker(class_=AsyncSession, bind=engine, autoflush=False, autocommit=False)



class Account(Base):
    __tablename__ = "google_account"
    id = Column(Integer, primary_key=True, index=True)
    account = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    type = Column(Integer, default=0, nullable=False)
    status = Column(Integer, default=0, nullable=False)
    code = Column(String(32), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now(), nullable=False)



class Status(Base):
    __tablename__ = "cloud_status"
    id = Column(Integer, primary_key=True, index=True)
    pad_code = Column(String(100), nullable=True, unique=True)
    country = Column(String(100), nullable=False)
    temple_id = Column(Integer, nullable=True)
    current_status = Column(String(200), default=0, nullable=False)
    number_of_run = Column(Integer, default=0, nullable=False)
    phone_number_counts = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now(), nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.now(), nullable=False)
    proxy = Column(String(100), nullable=False)
    code = Column(String(100), nullable=False)
    time_zone = Column(String(100), nullable=False)
    language = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)