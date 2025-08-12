from fastapi import APIRouter

from app.curd.status import update_cloud_status
from app.models.status import StatusResponse, StatusRequest

router = APIRouter()

@router.put("/status_update", response_model=StatusRequest)
async def update_status_server(status_response: StatusResponse):
     await update_cloud_status(status_response.pad_code, status_response.current_status)


@router.get(path="/cloud_status", response_model=dict)
async def get_cloud_status():
    return {'msg': "ok", "data": "ok"}