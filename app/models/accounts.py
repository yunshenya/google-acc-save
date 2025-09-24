from datetime import datetime

from pydantic import BaseModel


class AccountCreate(BaseModel):
    account: str
    password: str
    type: int = 0
    code: str | None = None


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
    type: int
    status: int
    code: str | None
    created_at: datetime
