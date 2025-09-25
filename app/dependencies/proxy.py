import threading
from typing import List, Dict, Union

from app.config import default_proxy
from app.models.proxy import ProxyResponse


class ProxyManager:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._proxy_countries: List[ProxyResponse] = []
        self._current_proxy: ProxyResponse = ProxyResponse(
            proxy=default_proxy["proxy"],
            country=default_proxy["country"],
            code=default_proxy["code"],
            time_zone=default_proxy["time_zone"],
            language=default_proxy["language"],
            latitude=default_proxy["latitude"],
            longitude=default_proxy["longitude"]
        )

    def __new__(cls):
        # 实现单例模式
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ProxyManager, cls).__new__(cls)
                    cls._instance.__init__()
        return cls._instance

    def get_proxy_countries(self) -> List[ProxyResponse]:
        with self._lock:
            return self._proxy_countries.copy()  # 返回副本以防止外部修改

    def set_proxy_countries(self, countries: List[ProxyResponse]) -> None:
        with self._lock:
            self._proxy_countries = countries.copy()  # 存储副本以防止外部修改

    def add_proxy_country(self, country: Dict[str, Union[str, float]]) -> None:
        with self._lock:
            try:
                proxy_country = ProxyResponse(**country)
                self._proxy_countries.append(proxy_country)
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid proxy country data: {e}")

    def set_current_proxy(self, proxy: ProxyResponse) -> None:
        with self._lock:
            self._current_proxy = {
                "country": proxy.country,
                "code": proxy.code,
                "proxy": proxy.proxy,
                "time_zone": proxy.time_zone,
                "language": proxy.language,
                "latitude": proxy.latitude,
                "longitude": proxy.longitude,
            }

    def get_current_proxy(self) -> ProxyResponse:
        with self._lock:
            return self._current_proxy.model_copy()
