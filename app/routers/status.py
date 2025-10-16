from typing import List, cast

from fastapi import APIRouter, HTTPException
from loguru import logger
from sqlalchemy import ColumnElement, func
from sqlalchemy.exc import IntegrityError

from app.config import Config
from app.curd.status import update_cloud_status, remove_cloud_status
from app.dependencies.countries import manager, load_proxy_countries
from app.models.status import (
    StatusResponse,
    StatusRequest,
    GetOneCloudStatus,
    AddStatusRequest,
)
from app.services.database import SessionLocal, Status
from app.services.logger import task_logger
from app.models.status import StatusUpdateRequest, BulkStatusUpdateRequest

router = APIRouter()


@router.post("/status_update", response_model=StatusResponse)
async def update_status_server(status_request: StatusRequest) -> StatusResponse:
    status_response = await update_cloud_status(
        status_request.pad_code,
        status_request.current_status,
        phone_number_counts=status_request.phone_number_counts,
        forward_num=status_request.forward_num,
        secondary_email_num=status_request.secondary_email_num,
    )
    return status_response


@router.get("/cloud_status", response_model=List[StatusResponse])
async def get_status_server() -> List[StatusResponse]:
    async with SessionLocal() as db:
        from sqlalchemy import select

        result = await db.execute(
            select(Status).order_by(cast(ColumnElement[bool], Status.id))
        )
        status = result.scalars().all()
        return status


@router.post("/cloud_status", response_model=StatusResponse)
async def get_one_cloud_status(
    one_cloud_status_request: GetOneCloudStatus,
) -> StatusRequest:
    async with SessionLocal() as db:
        from sqlalchemy import select

        result = await db.execute(
            select(Status).filter(
                cast(
                    ColumnElement[bool],
                    cast(object, Status.pad_code == one_cloud_status_request.pad_code),
                )
            )
        )
        status = result.scalars().first()
        if status is None:
            raise HTTPException(status_code=404, detail="云机不存在")
        return status


@router.put("/cloud_status/{pad_code}", response_model=StatusResponse)
async def update_single_cloud_status(
        pad_code: str, status_update: StatusUpdateRequest
) -> StatusResponse:
    """更新单个云机的配置信息"""
    async with SessionLocal() as db:
        try:
            from sqlalchemy import select

            normalized_code = (pad_code or "").strip()
            stmt = select(Status).filter(
                cast(
                    ColumnElement[bool],
                    cast(object, func.lower(Status.pad_code) == func.lower(normalized_code)),
                )
            )
            result = await db.execute(stmt)
            db_status = result.scalars().first()

            if db_status is None:
                raise HTTPException(status_code=404, detail="云机不存在")

            # 更新模板ID
            if status_update.temple_id is not None:
                db_status.temple_id = status_update.temple_id

            # 更新代理信息
            if status_update.proxy is not None:
                db_status.proxy = status_update.proxy
            if status_update.country is not None:
                db_status.country = status_update.country
            if status_update.code is not None:
                db_status.code = status_update.code
            if status_update.time_zone is not None:
                db_status.time_zone = status_update.time_zone
            if status_update.language is not None:
                db_status.language = status_update.language
            if status_update.latitude is not None:
                db_status.latitude = status_update.latitude
            if status_update.longitude is not None:
                db_status.longitude = status_update.longitude

            # 更新辅助邮箱状态
            if status_update.is_secondary_email is not None:
                db_status.is_secondary_email = status_update.is_secondary_email

            # 更新随机代理状态
            if status_update.is_random_proxy is not None:
                db_status.is_random_proxy = status_update.is_random_proxy

            await db.commit()
            await db.refresh(db_status)

            # 通知WebSocket客户端
            from app.services.websocket_manager import ws_manager

            await ws_manager.send_status_update()

            task_logger.success(f"{normalized_code}: 配置更新成功")
            return db_status

        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            task_logger.error(f"{pad_code}: 配置更新失败 - {e}")
            raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.put("/cloud_status/bulk", response_model=list[StatusResponse])
async def bulk_update_cloud_status(
        bulk_update: BulkStatusUpdateRequest,
) -> list[StatusResponse]:
    """批量更新多个云机的配置信息"""
    if not bulk_update.pad_codes:
        raise HTTPException(status_code=400, detail="pad_codes 不能为空")

    updated_statuses: list[StatusResponse] = []
    errors: list[str] = []

    for code in bulk_update.pad_codes:
        try:
            single = StatusUpdateRequest(
                temple_id=bulk_update.temple_id,
                proxy=bulk_update.proxy,
                country=bulk_update.country,
                code=bulk_update.code,
                time_zone=bulk_update.time_zone,
                language=bulk_update.language,
                latitude=bulk_update.latitude,
                longitude=bulk_update.longitude,
                is_secondary_email=bulk_update.is_secondary_email,
                is_random_proxy=bulk_update.is_random_proxy,
            )
            updated = await update_single_cloud_status(code, single)
            updated_statuses.append(updated)
        except HTTPException as e:
            errors.append(f"{code}:{e.detail}")
        except Exception as e:
            errors.append(f"{code}:{str(e)}")

    if not updated_statuses:
        raise HTTPException(status_code=400, detail=f"批量更新失败: {', '.join(errors[:5])}")

    # 广播一次即可
    try:
        from app.services.websocket_manager import ws_manager
        await ws_manager.send_status_update()
    except Exception:
        pass

    if errors:
        logger.warning(f"部分设备更新失败: {errors}")

    return updated_statuses

@router.post("/add_cloud_status", response_model=dict[str, str])
async def add_cloud_status(status: AddStatusRequest) -> dict[str, str]:
    async with SessionLocal() as db:
        try:
            proxy_countries = manager.get_proxy_countries()
            if not proxy_countries:
                load_proxy_countries()

            for country in proxy_countries:
                if country.code.lower() == status.country_code.lower():
                    db_account = Status(
                        pad_code=status.pad_code,
                        country=country.country,
                        current_status="调试用机",
                        proxy=country.proxy,
                        code=country.code,
                        time_zone=country.time_zone,
                        language=country.language,
                        latitude=country.latitude,
                        longitude=country.longitude,
                        proxy_platform= "ipmars",
                        pad_name= f"调试用机:{status.pad_code}",
                    )
                    db.add(db_account)
                    await db.commit()
                    await db.refresh(db_account)
                    return {"msg": f"{status.pad_code}成功"}

            return {"msg": "未找到代理国家"}

        except IntegrityError:
            await db.rollback()
            return {"msg": f"云机已存在: {status.pad_code}"}


@router.delete("/cloud_status/{pad_code}", response_model=dict)
async def delete_cloud_status(pad_code: str) -> dict:
    """删除指定的云机状态"""
    try:
        await remove_cloud_status(pad_code=pad_code)
        current_codes = set(Config.PAD_CODES)
        codes_to_remove = {pad_code}

        not_exists = codes_to_remove - current_codes
        if not_exists:
            logger.warning(f"以下代码不在当前配置中: {not_exists}")

        # 计算移除后的代码
        remaining_codes = current_codes - codes_to_remove

        # 更新配置
        Config.update_config({"pad_codes": list(remaining_codes)})

        # 通知WebSocket客户端
        from app.services.websocket_manager import ws_manager
        await ws_manager.send_status_update()

        return {"success": True, "message": f"云机 {pad_code} 已成功删除"}
    except HTTPException as e:
        raise e
    except Exception as e:
        task_logger.error(f"{pad_code}: 删除云机失败 - {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")