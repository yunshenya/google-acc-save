from sqlite3 import IntegrityError
from typing import cast

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import ColumnElement

from app.models.status import StatusRequest
from app.services.database import SessionLocal, Status


async def add_cloud_status(pad_code: str, current_status: str = "新机中"):
    async with SessionLocal() as db:
        try:
            db_account = Status(
                pad_code=pad_code,
                current_status =current_status
            )
            db.add(db_account)
            await db.commit()
            await db.refresh(db_account)
            logger.success("云机状态上传成功")
        except IntegrityError:
            await db.rollback()
            logger.warning("云机已存在")


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




async def update_cloud_status(pad_code: str, current_status: str) -> StatusRequest:
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
            await db.commit()
            await db.refresh(db_status)
            return StatusRequest(msg="ok", data=db_status)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=400, detail="云机状态已存在")