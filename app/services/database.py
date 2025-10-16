import datetime
from typing import Any

from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import config

Base = declarative_base()

engine: Any = create_async_engine(
    config.DATABASE_URL,
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 超出pool_size后最多创建的连接数
    pool_timeout=30,  # 获取连接的超时时间（秒）
    pool_recycle=3600,  # 1小时后回收连接
    pool_pre_ping=True,  # 使用连接前先测试
    echo=False,  # 生产环境关闭SQL日志
    connect_args={
        "server_settings": {
            "application_name": "google-manager",
            "jit": "off",  # 禁用JIT可以提高稳定性
        },
        "command_timeout": 60,  # 命令超时60秒
        "prepared_statement_cache_size": 0,  # 禁用预编译语句缓存
    }
    if "postgresql" in config.DATABASE_URL
    else {},
)

SessionLocal = sessionmaker(
    class_=AsyncSession,
    bind=engine,
    autocommit=False,  # 关闭自动提交
    expire_on_commit=False,  # 提交后不过期对象
)


class Account(Base):
    __tablename__ = "google_account"
    id = Column(Integer, primary_key=True, index=True)
    account = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    type = Column(Integer, default=0, nullable=False)
    status = Column(Integer, default=2, nullable=False)
    code = Column(String(32), nullable=True)
    for_email = Column(Text, nullable=True)
    for_password = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now(), nullable=False)
    is_boned_secondary_email = Column(Boolean, nullable=False, default=False)
    proxy_platform = Column(Text, nullable=True)
    is_forward_email = Column(Boolean, nullable=False, default=False)
    image_base64 = Column(Text, nullable=True)


class Status(Base):
    __tablename__ = "cloud_status"
    id = Column(Integer, primary_key=True, index=True)
    pad_code = Column(String(100), nullable=True, unique=True)
    country = Column(String(100), nullable=False)
    temple_id = Column(Integer, nullable=True)
    current_status = Column(Text, nullable=False)
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
    forward_num = Column(Integer, default=0, nullable=False)
    secondary_email_num = Column(Integer, default=0, nullable=False)
    is_secondary_email = Column(Boolean, nullable=False, default=False)
    num_of_success = Column(Integer, default=0, nullable=False)
    num_of_error = Column(Integer, nullable=False, default=0)
    num_other_error = Column(Integer, nullable=False, default=0)
    proxy_platform = Column(Text, nullable=True)
    pad_name = Column(Text, nullable=True)
    is_random_proxy = Column(Boolean, nullable=False, default=False)
    android_version = Column(Text, nullable=True)


class ProxyCollection(Base):
    __tablename__ = "proxy_collection"
    id = Column(Integer, primary_key=True, index=True)
    country = Column(Text, nullable=True)
    android_version = Column(Text, nullable=True)
    temple_id = Column(Integer, nullable=True)
    code = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    proxy = Column(Text, nullable=True)
    language = Column(Text, nullable=True)
    time_zone = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now(), nullable=False)
