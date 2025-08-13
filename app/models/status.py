from datetime import datetime

from pydantic import BaseModel


class StatusResponse(BaseModel):
    pad_code: str
    current_status: str | None = None
    number_of_run: int
    phone_number_counts: int
    country: str | None = None
    created_at: datetime


class StatusRequest(BaseModel):
    pad_code: str
    current_status: str

class GetOneCloudStatus(BaseModel):
    pad_code: str