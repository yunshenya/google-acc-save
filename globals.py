# 加载代理国家列表
from app.models.proxy import ProxyCountry
from config import default_proxy

# 初始化全局变量
proxy_countries = []

# 获取当前使用的代理信息
current_proxy = default_proxy.copy()

# 使用默认代理设置初始化变量
proxy_url = current_proxy["proxy_url"]
time_zone = current_proxy["time_zone"]
latitude = current_proxy["latitude"]
longitude = current_proxy["longitude"]


def get_proxy_countries():
    global proxy_countries
    return proxy_countries


def set_proxy_countries_list(countries: list[ProxyCountry]):
    global proxy_countries
    proxy_countries = countries


def set_proxy_countries(countries: dict[str, str | float]):
    global proxy_countries
    proxy_countries.append(countries)

def set_time_zone(time_zone_re: str):
    global time_zone
    time_zone = time_zone_re


def set_latitude(latitude_re: str):
    global latitude
    latitude = latitude_re

def set_longitude(longitude_re: str):
    global longitude
    longitude = longitude_re

def set_proxy_url(proxy_url_re: str):
    global proxy_url
    proxy_url = proxy_url_re


def set_current_proxy(current_proxy_re: dict):
    global current_proxy
    current_proxy = current_proxy_re


def get_current_proxy():
    global current_proxy
    return current_proxy
