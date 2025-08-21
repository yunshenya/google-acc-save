from typing import cast

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import ColumnElement
from sqlalchemy.exc import IntegrityError
from app.models.proxy import ProxyResponse
from app.models.status import StatusResponse
from app.services.database import SessionLocal, Status


async def add_cloud_status(pad_code: str, temple_id: int, current_status: str = "新机中"):
    async with SessionLocal() as db:
        try:
            db_account = Status(
                pad_code=pad_code,
                current_status=current_status,
                temple_id=temple_id,
            )
            db.add(db_account)
            await db.commit()
            await db.refresh(db_account)
            logger.success("云机状态上传成功")
        except IntegrityError:
            await db.rollback()
            await update_cloud_status(pad_code=pad_code, current_status="新机中", country="")
            logger.warning(f"云机已存在: {pad_code}")


async def remove_cloud_status(pad_code: str):
    async with SessionLocal() as db:
        from sqlalchemy import select, delete
        stmt = select(Status).filter(cast(ColumnElement[bool], Status.pad_code == pad_code))
        result = await db.execute(stmt)
        account = result.scalars().first()
        if account is None:
            raise HTTPException(status_code=404, detail="云机不存在")
        await db.execute(delete(Status).filter(cast(ColumnElement[bool], Status.pad_code == pad_code)))
        await db.commit()
        logger.success(f"云机数据 {pad_code} : 删除成功")


async def update_cloud_status(pad_code: str,
                              current_status: str = None,
                              country: str = None,
                              number_of_run: int = None,
                              temple_id: int = None,
                              phone_number_counts: int = None) -> StatusResponse:
    async with SessionLocal() as db:
        try:
            from sqlalchemy import select
            stmt = select(Status).filter(cast(ColumnElement[bool], Status.pad_code == pad_code))
            result = await db.execute(stmt)
            db_status = result.scalars().first()
            if db_status is None:
                raise HTTPException(status_code=404, detail="云机状态不存在")
            if current_status is not None:
                db_status.current_status = current_status
            if country is not None:
                db_status.country = country

            if number_of_run is not None:
                db_status.number_of_run += number_of_run

            if phone_number_counts is not None:
                db_status.phone_number_counts += phone_number_counts

            if temple_id is not None:
                db_status.temple_id = temple_id

            await db.commit()
            await db.refresh(db_status)
            return db_status
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=400, detail="云机状态已存在")


async def set_proxy_status(pad_code: str, proxy_response: ProxyResponse) -> StatusResponse:
    async with SessionLocal() as db:
        try:
            from sqlalchemy import select
            stmt = select(Status).filter(cast(ColumnElement[bool], Status.pad_code == pad_code))
            result = await db.execute(stmt)
            db_status = result.scalars().first()
            if db_status is None:
                raise HTTPException(status_code=404, detail="云机状态不存在")

            db_status.proxy = proxy_response.proxy
            db_status.country = proxy_response.country
            db_status.code  = proxy_response.code
            db_status.time_zone = proxy_response.time_zone
            db_status.latitude = proxy_response.latitude
            db_status.longitude = proxy_response.longitude
            db_status.language = proxy_response.language

            await db.commit()
            await db.refresh(db_status)
            return db_status
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=400, detail="设置代理失败")

async def get_proxy_status(pad_code: str) -> ProxyResponse:
    async with SessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(
            select(Status).filter(cast(ColumnElement[bool], Status.pad_code == pad_code)))
        status = result.scalars().first()
        if status is None:
            raise HTTPException(status_code=404, detail="云机不存在")
        return status