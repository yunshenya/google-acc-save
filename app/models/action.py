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



class SlideRequest(BaseModel):
    pade_code: str
    x1: int
    y1: int
    next_position_wait_time1 : int
    x2: int
    y2: int
    next_position_wait_time2 : int
    x3: int
    y3: int
    next_position_wait_time3 : int
    width: int
    height: int

