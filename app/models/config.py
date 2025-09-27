from typing import List, Dict, Optional, Any
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


class AdminCredentialsModel(BaseModel):
    username: str
    password: str


class CustomEnvVarModel(BaseModel):
    key: str
    value: str
    description: Optional[str] = None


class ConfigUpdateRequest(BaseModel):
    pad_codes: Optional[List[str]] = None
    package_names: Optional[Dict[str, str]] = None
    temple_ids: Optional[List[int]] = None
    default_proxy: Optional[ProxyConfigModel] = None
    app_urls: Optional[AppUrlsModel] = None
    timeouts: Optional[TimeoutConfigModel] = None
    debug: Optional[bool] = None
    jwt_secret_key: Optional[str] = None
    admin_credentials: Optional[AdminCredentialsModel] = None
    database_url: Optional[str] = None
    custom_env_vars: Optional[List[CustomEnvVarModel]] = None


class ConfigResponse(BaseModel):
    pad_codes: List[str]
    package_names: Dict[str, str]
    temple_ids: List[int]
    default_proxy: ProxyConfigModel
    app_urls: AppUrlsModel
    timeouts: TimeoutConfigModel
    debug: bool
    jwt_secret_key: str
    admin_credentials: AdminCredentialsModel
    database_url: str
    custom_env_vars: List[Dict[str, Any]]


class EnvVarUpdateRequest(BaseModel):
    key: str
    value: str
    description: Optional[str] = None


class EnvVarDeleteRequest(BaseModel):
    key: str