from typing import List, cast

from fastapi import APIRouter, HTTPException
from sqlalchemy import ColumnElement
from sqlalchemy.exc import IntegrityError

from app.curd.status import update_cloud_status
from app.dependencies.countries import manager, load_proxy_countries
from app.models.status import (
    StatusResponse,
    StatusRequest,
    GetOneCloudStatus,
    AddStatusRequest,
)
from app.services.database import SessionLocal, Status
from app.services.logger import task_logger
from app.models.status import StatusUpdateRequest

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
                    Status.pad_code == one_cloud_status_request.pad_code,
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

            stmt = select(Status).filter(
                cast(ColumnElement[bool], Status.pad_code == pad_code)
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

            await db.commit()
            await db.refresh(db_status)

            # 通知WebSocket客户端
            from app.services.websocket_manager import ws_manager

            await ws_manager.send_status_update()

            task_logger.success(f"{pad_code}: 配置更新成功")
            return db_status

        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            task_logger.error(f"{pad_code}: 配置更新失败 - {e}")
            raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


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
                        pad_name= "调试用机"
                    )
                    db.add(db_account)
                    await db.commit()
                    await db.refresh(db_account)
                    return {"msg": f"{status.pad_code}成功"}

            return {"msg": "未找到代理国家"}

        except IntegrityError:
            await db.rollback()
            return {"msg": f"云机已存在: {status.pad_code}"}
