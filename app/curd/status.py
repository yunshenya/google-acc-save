import asyncio
import datetime
from typing import cast, Any

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import ColumnElement
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import IntegrityError

from app.dependencies.utils import get_pad_info
from app.models.proxy import ProxyResponse
from app.models.status import StatusResponse, OnePadeAllStatus
from app.services.database import SessionLocal, Status
from app.services.logger import task_logger


async def add_cloud_status(
    pad_code: str, temple_id: int, current_status: str = "新机中"
):
    """添加云机状态"""
    async with SessionLocal() as db:
        try:
            pad_info: Any = await get_pad_info(pad_code)
            data = pad_info.get("data", None)
            pad_name = data.get("padName", None)
            db_account = Status(
                pad_code=pad_code,
                current_status=current_status,
                temple_id=temple_id,
                is_secondary_email=False,
                proxy_platform="ipmars",
                pad_name=pad_name,
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


async def remove_cloud_status(pad_code: str):
    """删除云机状态"""
    async with SessionLocal() as db:
        try:
            from sqlalchemy import select, delete

            stmt = select(Status).filter(
                cast(ColumnElement[bool], cast(object, Status.pad_code == pad_code))
            )
            result = await db.execute(stmt)
            status = result.scalars().first()
            if status is None:
                raise HTTPException(status_code=404, detail="云机不存在")

            if status.pad_name != "调试用机":
                await db.execute(
                    delete(Status).filter(
                        cast(ColumnElement[bool], cast(object, Status.pad_code == pad_code))
                    )
                )
            else:
                status.updated_at = datetime.datetime.now()
            await db.commit()
            await db.refresh(status)
            task_logger.success(f"云机数据 {pad_code} : 删除成功")
        except IntegrityError:
            await db.rollback()


async def all_cloud_status():
    # 清理云机状态
    async with SessionLocal() as db:
        try:
            from sqlalchemy import select, delete

            # 查询所有状态
            result = await db.execute(select(Status))
            all_statuses = result.scalars().all()

            for status in all_statuses:
                try:
                    # 跳过调试用机
                    if status.pad_name == "调试用机":
                        logger.info(f"保留调试用机: {status.pad_code}")
                        continue

                    # 删除其他云机状态
                    await db.execute(
                        delete(Status).filter(
                            cast(ColumnElement[bool], cast(object, Status.pad_code == status.pad_code))
                        )
                    )
                    logger.info(f"已删除云机状态: {status.pad_code}")

                except Exception as e:
                    logger.warning(f"清理云机状态失败 {status.pad_code}: {e}")

            await db.commit()
            logger.info("云机状态清理完成")

        except Exception as e:
            logger.error(f"清理云机状态时出错: {e}")
            await db.rollback()

async def update_cloud_status(
    pad_code: str,
    current_status: str = None,
    number_of_run: int = None,
    temple_id: int = None,
    phone_number_counts: int = None,
    secondary_email_num: int = None,
    forward_num: int = None,
    num_of_success: int = None,
    num_of_error: int = None,
    num_other_error: int = None,
    max_retries: Any = 3,  # 重试次数
) -> StatusResponse:
    last_error = None

    for attempt in range(max_retries):
        try:
            async with SessionLocal() as db:
                from sqlalchemy import select

                stmt = select(Status).filter(
                    cast(ColumnElement[bool], cast(object, Status.pad_code == pad_code))
                )
                result = await db.execute(stmt)
                db_status = result.scalars().first()

                if db_status is None:
                    raise HTTPException(status_code=404, detail="云机状态不存在")

                # 记录更新前的状态用于比较
                old_status = db_status.current_status
                status_changed = False

                if (
                    current_status is not None
                    and db_status.current_status != current_status
                ):
                    db_status.current_status = current_status
                    status_changed = True
                    task_logger.info(
                        f"{pad_code}: 状态更新 {old_status} -> {current_status}"
                    )

                if number_of_run is not None:
                    old_run = db_status.number_of_run
                    db_status.number_of_run += number_of_run
                    task_logger.debug(
                        f"{pad_code}: 运行次数更新 {old_run} -> {db_status.number_of_run}"
                    )

                if phone_number_counts is not None:
                    old_phone = db_status.phone_number_counts
                    db_status.phone_number_counts += phone_number_counts
                    task_logger.debug(
                        f"{pad_code}: 手机号数量更新 {old_phone} -> {db_status.phone_number_counts}"
                    )

                if temple_id is not None:
                    db_status.temple_id = temple_id
                    task_logger.debug(f"{pad_code}: 模板ID更新为 {temple_id}")

                if secondary_email_num is not None:
                    old_secondary = db_status.secondary_email_num
                    db_status.secondary_email_num += secondary_email_num
                    task_logger.debug(
                        f"{pad_code}: 辅助邮箱数量更新 {old_secondary} -> {db_status.secondary_email_num}"
                    )

                if forward_num is not None:
                    old_forward = db_status.forward_num
                    db_status.forward_num += forward_num
                    task_logger.debug(
                        f"{pad_code}: 转发邮箱数量更新 {old_forward} -> {db_status.forward_num}"
                    )

                if num_of_success is not None:
                    old_num_success = db_status.num_of_success
                    db_status.num_of_success += num_of_success
                    task_logger.debug(
                        f"{pad_code}: 注册成功数量更新 {old_num_success} -> {db_status.num_of_success}"
                    )

                if num_of_error is not None:
                    old_num_error = db_status.num_of_error
                    db_status.num_of_error += num_of_error
                    task_logger.debug(
                        f"{pad_code}: 注册失败数量更新 {old_num_error} -> {db_status.num_of_error}"
                    )

                if num_other_error is not None:
                    old_num_other_error = db_status.num_other_error
                    db_status.num_other_error += num_other_error
                    task_logger.debug(
                        f"{pad_code}: 其他错误数量更新 {old_num_other_error} -> {db_status.num_other_error}"
                    )

                await db.commit()
                await db.refresh(db_status)

                # 延迟导入避免循环依赖
                from app.services.websocket_manager import ws_manager

                # 如果状态发生变化或有重要更新，通知WebSocket客户端
                if (
                    status_changed
                    or number_of_run
                    or phone_number_counts
                    or secondary_email_num
                    or forward_num
                    or num_of_success
                    or num_of_error
                    or temple_id
                ):
                    if status_changed:
                        await ws_manager.notify_status_change(pad_code, current_status)
                    else:
                        await ws_manager.send_status_update()

                return db_status

        except (DBAPIError, IntegrityError) as e:
            last_error = e
            task_logger.warning(
                f"{pad_code}: 数据库操作失败 (尝试 {attempt + 1}/{max_retries}): {e}"
            )

            if attempt < max_retries - 1:
                # 等待一段时间后重试，使用指数退避
                await asyncio.sleep(0.5 * (2**attempt))
                continue
            else:
                task_logger.error(f"{pad_code}: 数据库操作最终失败: {e}")
                raise HTTPException(
                    status_code=500, detail=f"更新云机状态失败: {str(e)}"
                )
        except HTTPException:
            raise
        except Exception as e:
            task_logger.error(f"{pad_code}: 更新云机状态异常: {e}")
            raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

    # 如果所有重试都失败
    raise HTTPException(
        status_code=500,
        detail=f"更新云机状态失败，已重试{max_retries}次: {str(last_error)}",
    )


async def set_proxy_status(
    pad_code: str, proxy_response: ProxyResponse, number_of_run: int = None
) -> StatusResponse:
    """设置代理状态"""
    async with SessionLocal() as db:
        try:
            from sqlalchemy import select

            stmt = select(Status).filter(
                cast(ColumnElement[bool], cast(object, Status.pad_code == pad_code))
            )
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
            if number_of_run is not None:
                db_status.number_of_run += number_of_run

            await db.commit()
            await db.refresh(db_status)

            task_logger.info(
                f"{pad_code}: 代理更新 {old_country} -> {proxy_response.country}"
            )

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
            select(Status).filter(
                cast(ColumnElement[bool], cast(object, Status.pad_code == pad_code))
            )
        )
        status = result.scalars().first()
        if status is None:
            task_logger.error(f"云机不存在: {pad_code}")
            raise HTTPException(status_code=404, detail="云机不存在")
        return status


async def get_one_pade_status(pade_code: str) -> OnePadeAllStatus:
    async with SessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(
            select(Status).filter(
                cast(
                    ColumnElement[bool],
                    cast(object, Status.pad_code == pade_code),
                )
            )
        )
        status = result.scalars().first()
        if status is None:
            raise HTTPException(status_code=404, detail="云机不存在")
        return status