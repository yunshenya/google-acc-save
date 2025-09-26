from datetime import datetime

from pydantic import BaseModel


class AccountCreate(BaseModel):
    account: str
    password: str
    type: int = 0
    code: str | None = None
    for_email: str | None = None
    for_password: str | None = None
    pad_code: str | None = None


class AndroidPadCodeRequest(BaseModel):
    pad_code: str


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


class ForwardRequest(BaseModel):
    account: str
    pad_code: str
    for_email: str | None
    for_password: str | None


class SecondaryEmail(BaseModel):
    account: str
    pad_code: str
    for_email: str
    for_password: str
    is_boned_secondary_email: bool