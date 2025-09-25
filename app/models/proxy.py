from pydantic import BaseModel


class ProxyResponse(BaseModel):
    proxy: str
    country: str
    code: str
    time_zone: str
    language: str
    latitude: float
    longitude: float
    temple_id: int


class ProxyRequest(BaseModel):
    country_code: str


class DbProxyRequest(BaseModel):
    pad_code: str
    country_code: str
