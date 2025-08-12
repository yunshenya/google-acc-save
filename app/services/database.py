import datetime
from typing import Any

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from config import DATABASE_URL

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

