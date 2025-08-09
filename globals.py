from typing import List, Dict, Union
from app.models.proxy import ProxyCountry
from config import default_proxy
import threading

class ProxyManager:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._proxy_countries: List[ProxyCountry] = []
        self._current_proxy: Dict[str, Union[str, float]] = default_proxy.copy()

    def __new__(cls):
        # 实现单例模式
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ProxyManager, cls).__new__(cls)
                    cls._instance.__init__()
        return cls._instance

    def get_proxy_countries(self) -> List[ProxyCountry]:
        with self._lock:
            return self._proxy_countries.copy()  # 返回副本以防止外部修改

    def set_proxy_countries(self, countries: List[ProxyCountry]) -> None:
        with self._lock:
            self._proxy_countries = countries.copy()  # 存储副本以防止外部修改

    def add_proxy_country(self, country: Dict[str, Union[str, float]]) -> None:
        with self._lock:
            try:
                proxy_country = ProxyCountry(**country)
                self._proxy_countries.append(proxy_country)
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid proxy country data: {e}")

    def set_current_proxy(self, proxy: ProxyCountry) -> None:
        with self._lock:
            self._current_proxy =  {
                "country": proxy.country,
                "code": proxy.code,
                "proxy_url": proxy.proxy_url,
                "time_zone": proxy.time_zone,
                "language": proxy.language,
                "latitude": proxy.latitude,
                "longitude": proxy.longitude,
            }

    def get_current_proxy(self) -> Dict[str, Union[str, float]]:
        with self._lock:
            return self._current_proxy.copy()
