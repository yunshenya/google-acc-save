from pydantic import BaseModel


class StatusResponse(BaseModel):
    pad_code: str
    current_status: str


class StatusRequest(BaseModel):
    msg: str
    data: StatusResponse