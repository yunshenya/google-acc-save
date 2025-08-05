from pydantic import BaseModel


class ProxyCountry(BaseModel):
    country: str
    code: str
    proxy_url: str
    time_zone: str
    language: str
    latitude: float
    longitude: float

class ProxyResponse(BaseModel):
    proxy: str
    country: str
    code: str
    time_zone: str
    language: str
    latitude: float
    longitude: float

class ProxyRequest(BaseModel):
    country_code: str

