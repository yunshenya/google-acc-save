from datetime import datetime

from pydantic import BaseModel


class StatusResponse(BaseModel):
    pad_code: str
    current_status: str | None = None
    number_of_run: int
    temple_id: int
    phone_number_counts: int
    country: str | None = None
    updated_at: datetime
    created_at: datetime
    code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    language: str | None = None
    time_zone: str | None = None
    proxy: str | None = None
    is_secondary_email: bool | None = None


class StatusRequest(BaseModel):
    pad_code: str
    current_status: str | None = None
    phone_number_counts: int | None = None
    forward_num: int | None = None
    secondary_email_num: int | None = None


class GetOneCloudStatus(BaseModel):
    pad_code: str


class AddStatusRequest(BaseModel):
    pad_code: str
    country_code: str