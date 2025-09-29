from datetime import datetime

from pydantic import BaseModel


class AccountCreate(BaseModel):
    account: str
    password: str
    pad_code: str | None = None


class AndroidPadCodeRequest(BaseModel):
    pad_code: str
    type: int | None = None


class AccountUpdate(BaseModel):
    account: str
    password: str
    type: int | None = None
    status: int | None = None
    code: str | None = None


class AccountResponse(BaseModel):
    id: int
    account: str
    password: str
    for_email: str | None
    for_password: str | None
    type: int
    status: int
    code: str | None
    created_at: datetime
    is_boned_secondary_email: bool
    proxy_platform: str | None


class ForwardRequest(BaseModel):
    account: str
    pad_code: str
    for_email: str
    for_password: str
    image_base64: str


class SecondaryEmail(BaseModel):
    account: str
    pad_code: str
    for_email: str
    for_password: str
    is_boned_secondary_email: bool

