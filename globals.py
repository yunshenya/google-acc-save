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
        self._proxy_url: str = self._current_proxy["proxy_url"]
        self._time_zone: str = self._current_proxy["time_zone"]
        self._latitude: float = float(self._current_proxy["latitude"])
        self._longitude: float = float(self._current_proxy["longitude"])

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

    def set_time_zone(self, time_zone: str) -> None:
        with self._lock:
            if not isinstance(time_zone, str) or not time_zone:
                raise ValueError("Invalid time zone")
            self._time_zone = time_zone
            self._current_proxy["time_zone"] = time_zone

    def set_latitude(self, latitude: float) -> None:
        with self._lock:
            if not -90 <= latitude <= 90:
                raise ValueError("Latitude must be between -90 and 90")
            self._latitude = latitude
            self._current_proxy["latitude"] = latitude

    def set_longitude(self, longitude: float) -> None:
        with self._lock:
            if not -180 <= longitude <= 180:
                raise ValueError("Longitude must be between -180 and 180")
            self._longitude = longitude
            self._current_proxy["longitude"] = longitude

    def set_proxy_url(self, proxy_url: str) -> None:
        with self._lock:
            if not isinstance(proxy_url, str) or not proxy_url.startswith("http"):
                raise ValueError("Invalid proxy URL")
            self._proxy_url = proxy_url
            self._current_proxy["proxy_url"] = proxy_url

    def set_current_proxy(self, proxy: ProxyCountry) -> None:
        with self._lock:
            required_keys = {"proxy_url", "time_zone", "latitude", "longitude"}
            if not all(key in proxy for key in required_keys):
                raise ValueError("Proxy dictionary missing required keys")
            self._current_proxy = proxy.model_copy()
            self._proxy_url = proxy["proxy_url"]
            self._time_zone = proxy["time_zone"]
            self._latitude = float(proxy["latitude"])
            self._longitude = float(proxy["longitude"])

    def get_current_proxy(self) -> Dict[str, Union[str, float]]:
        with self._lock:
            return self._current_proxy.copy()

    def get_proxy_url(self):
        with self._lock:
            return self._proxy_url