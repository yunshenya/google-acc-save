from typing import cast

from fastapi import HTTPException
from sqlalchemy import ColumnElement
from sqlalchemy.exc import IntegrityError

from app.models.proxy import ProxyResponse
from app.models.status import StatusResponse
from app.services.database import SessionLocal, Status
from app.services.logger import task_logger


async def add_cloud_status(pad_code: str, temple_id: int, current_status: str = "新机中"):
    """添加云机状态"""
    async with SessionLocal() as db:
        try:
            db_account = Status(
                pad_code=pad_code,
                current_status=current_status,
                temple_id=temple_id,
                is_secondary_email = True
            )
            db.add(db_account)
            await db.commit()
            await db.refresh(db_account)
            task_logger.success(f"{pad_code}: 云机状态上传成功")

            # 延迟导入避免循环依赖
            from app.services.websocket_manager import ws_manager
            # 通知WebSocket客户端
            await ws_manager.notify_status_change(pad_code, current_status)

        except IntegrityError:
            await db.rollback()
            await update_cloud_status(pad_code=pad_code, current_status="新机中")
            task_logger.warning(f"云机已存在: {pad_code}")


async def remove_cloud_status(pad_code: str):
    """删除云机状态"""
    async with SessionLocal() as db:
        from sqlalchemy import select, delete
        stmt = select(Status).filter(cast(ColumnElement[bool], Status.pad_code == pad_code))
        result = await db.execute(stmt)
        account = result.scalars().first()
        if account is None:
            raise HTTPException(status_code=404, detail="云机不存在")
        await db.execute(delete(Status).filter(cast(ColumnElement[bool], Status.pad_code == pad_code)))
        await db.commit()
        task_logger.success(f"云机数据 {pad_code} : 删除成功")


async def update_cloud_status(pad_code: str,
                              current_status: str = None,
                              number_of_run: int = None,
                              temple_id: int = None,
                              phone_number_counts: int = None,
                              secondary_email_num: int = None,
                              forward_num: int = None,
                              num_of_success: int = None
                              ) -> StatusResponse:
    """更新云机状态"""
    async with SessionLocal() as db:
        try:
            from sqlalchemy import select
            stmt = select(Status).filter(cast(ColumnElement[bool], Status.pad_code == pad_code))
            result = await db.execute(stmt)
            db_status = result.scalars().first()
            if db_status is None:
                raise HTTPException(status_code=404, detail="云机状态不存在")

            # 记录更新前的状态用于比较
            old_status = db_status.current_status
            status_changed = False

            if current_status is not None and db_status.current_status != current_status:
                db_status.current_status = current_status
                status_changed = True
                task_logger.info(f"{pad_code}: 状态更新 {old_status} -> {current_status}")

            if number_of_run is not None:
                old_run = db_status.number_of_run
                db_status.number_of_run += number_of_run
                task_logger.debug(f"{pad_code}: 运行次数更新 {old_run} -> {db_status.number_of_run}")

            if phone_number_counts is not None:
                old_phone = db_status.phone_number_counts
                db_status.phone_number_counts += phone_number_counts
                task_logger.debug(f"{pad_code}: 手机号数量更新 {old_phone} -> {db_status.phone_number_counts}")

            if temple_id is not None:
                db_status.temple_id = temple_id
                task_logger.debug(f"{pad_code}: 模板ID更新为 {temple_id}")

            if secondary_email_num is not None:
                old_secondary = db_status.secondary_email_num
                db_status.secondary_email_num += secondary_email_num
                task_logger.debug(f"{pad_code}: 辅助邮箱数量更新 {old_secondary} -> {db_status.secondary_email_num}")

            if forward_num is not None:
                old_forward = db_status.forward_num
                db_status.forward_num += forward_num
                task_logger.debug(f"{pad_code}: 转发邮箱数量更新 {old_forward} -> {db_status.forward_num}")


            if num_of_success is not None:
                old_num_success = db_status.num_of_success
                db_status.num_of_success += num_of_success
                task_logger.debug(f"{pad_code}: 注册成功数量更新 {old_num_success} -> {db_status.num_of_success}")

            await db.commit()
            await db.refresh(db_status)

            # 延迟导入避免循环依赖
            from app.services.websocket_manager import ws_manager

            # 如果状态发生变化或有重要更新，通知WebSocket客户端
            if status_changed or number_of_run or phone_number_counts or secondary_email_num or forward_num:
                if status_changed:
                    # 状态变化时发送单个状态更新
                    await ws_manager.notify_status_change(pad_code, current_status)
                else:
                    # 数据更新时发送完整状态更新
                    await ws_manager.send_status_update()

            return db_status
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=400, detail="云机状态已存在")


async def set_proxy_status(pad_code: str, proxy_response: ProxyResponse) -> StatusResponse:
    """设置代理状态"""
    async with SessionLocal() as db:
        try:
            from sqlalchemy import select
            stmt = select(Status).filter(cast(ColumnElement[bool], Status.pad_code == pad_code))
            result = await db.execute(stmt)
            db_status = result.scalars().first()
            if db_status is None:
                raise HTTPException(status_code=404, detail="云机状态不存在")

            # 记录代理更新
            old_country = db_status.country
            db_status.proxy = proxy_response.proxy
            db_status.country = proxy_response.country
            db_status.code = proxy_response.code
            db_status.time_zone = proxy_response.time_zone
            db_status.latitude = proxy_response.latitude
            db_status.longitude = proxy_response.longitude
            db_status.language = proxy_response.language

            await db.commit()
            await db.refresh(db_status)

            task_logger.info(f"{pad_code}: 代理更新 {old_country} -> {proxy_response.country}")

            # 延迟导入避免循环依赖
            from app.services.websocket_manager import ws_manager
            # 代理更新后发送完整状态更新
            await ws_manager.send_status_update()

            return db_status
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=400, detail="设置代理失败")


async def get_proxy_status(pad_code: str) -> ProxyResponse:
    """获取代理状态"""
    async with SessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(
            select(Status).filter(cast(ColumnElement[bool], Status.pad_code == pad_code)))
        status = result.scalars().first()
        if status is None:
            task_logger.error(f"云机不存在: {pad_code}")
            raise HTTPException(status_code=404, detail="云机不存在")
        return status