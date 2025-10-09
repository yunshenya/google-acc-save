from typing import Any

from pydantic import BaseModel


class ClickRequest(BaseModel):
    pade_code: str
    x: int
    y: int
    width: int
    height: int


class ClickResponse(BaseModel):
    msg: str
    code: int
    data : list[dict[str, Any]]




class InputRequest(BaseModel):
    pade_code: str
    text: str


class InputResponse(BaseModel):
    msg: str
    code: int
    ts : int
    data : list[dict[str, Any]]