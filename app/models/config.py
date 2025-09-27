from typing import List, Dict

from pydantic import BaseModel


class ProxyConfigModel(BaseModel):
    country: str
    code: str
    proxy: str
    time_zone: str
    language: str
    latitude: float
    longitude: float


class AppUrlsModel(BaseModel):
    clash: str
    script: str
    script2: str
    chrome: str


class TimeoutConfigModel(BaseModel):
    global_timeout: int
    check_task_timeout: int


class ConfigUpdateRequest(BaseModel):
    pad_codes: List[str] = None
    package_names: Dict[str, str] = None
    temple_ids: List[int] = None
    default_proxy: ProxyConfigModel = None
    app_urls: AppUrlsModel = None
    timeouts: TimeoutConfigModel = None
    debug: bool = None


class ConfigResponse(BaseModel):
    pad_codes: List[str]
    package_names: Dict[str, str]
    temple_ids: List[int]
    default_proxy: ProxyConfigModel
    app_urls: AppUrlsModel
    timeouts: TimeoutConfigModel
    debug: bool