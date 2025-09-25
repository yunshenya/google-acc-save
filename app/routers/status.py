from sqlite3 import IntegrityError
from typing import List, cast

from fastapi import APIRouter, HTTPException
from sqlalchemy import ColumnElement

from app.curd.status import update_cloud_status
from app.models.status import StatusResponse, StatusRequest, GetOneCloudStatus
from app.services.database import SessionLocal, Status

router = APIRouter()


@router.post("/status_update", response_model=StatusResponse)
async def update_status_server(status_request: StatusRequest) -> StatusResponse:
    status_response = await update_cloud_status(status_request.pad_code, status_request.current_status,
                                                phone_number_counts=status_request.phone_number_counts,
                                                forward_num=status_request.forward_num,
                                                secondary_email_num=status_request.secondary_email_num)
    return status_response


@router.get("/cloud_status", response_model=List[StatusResponse])
async def get_status_server() -> List[StatusResponse]:
    async with SessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(select(Status).order_by(cast(ColumnElement[bool], Status.id)))
        status = result.scalars().all()
        return status


@router.post("/cloud_status", response_model=StatusResponse)
async def get_one_cloud_status(one_cloud_status_request: GetOneCloudStatus) -> StatusRequest:
    async with SessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(
            select(Status).filter(cast(ColumnElement[bool], Status.pad_code == one_cloud_status_request.pad_code)))
        status = result.scalars().first()
        if status is None:
            raise HTTPException(status_code=404, detail="云机不存在")
        return status

@router.post("/add_cloud_status", response_model=dict[str, str])
async def add_cloud_status(status: StatusRequest) -> dict[str, str]:
    async with SessionLocal() as db:
        try:
            db_account = Status(
                pad_code=status.pad_code,
                current_status=status.current_status
            )
            db.add(db_account)
            await db.commit()
            await db.refresh(db_account)
            return {"msg": f"{status.pad_code}成功"}
        except IntegrityError:
            await db.rollback()
            return {"msg": f"云机已存在: {status.pad_code}"}

