from fastapi import APIRouter

from app.curd.status import update_cloud_status
from app.models.status import StatusResponse, StatusRequest

router = APIRouter()

@router.put("/status_update", response_model=StatusRequest)
async def update_status_server(status_response: StatusResponse) -> StatusRequest:
     status_request = await update_cloud_status(status_response.pad_code, status_response.current_status)
     return status_request


@router.get("/status", response_model=dict)
async def get_status_server() -> dict:
     return {"status": "ok"}