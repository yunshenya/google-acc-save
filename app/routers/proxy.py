from typing import List

from fastapi import APIRouter, HTTPException

from app.dependencies.countries import load_proxy_countries, manager
from app.models.proxy import ProxyResponse, ProxyRequest, ProxyCountry

router = APIRouter()

@router.get("/proxy", response_model=ProxyResponse)
async def get_proxy():
    """获取当前使用的代理信息"""
    current_proxy = manager.get_current_proxy()
    return {
        "proxy": current_proxy["proxy_url"],
        "country": current_proxy["country"],
        "code": current_proxy["code"],
        "time_zone": current_proxy["time_zone"],
        "language": current_proxy["language"],
        "latitude": current_proxy["latitude"],
        "longitude": current_proxy["longitude"]
    }

@router.get("/proxy/countries", response_model=List[ProxyCountry])
async def get_proxy_countries():
    proxy_countries = manager.get_proxy_countries()
    """获取所有可用的代理国家列表"""
    # 如果代理国家列表为空，尝试加载
    if not proxy_countries:
        load_proxy_countries()
    return proxy_countries


@router.post("/proxy/set", response_model=ProxyResponse)
async def set_proxy(proxy_request: ProxyRequest):
    """根据国家代码设置代理"""
    proxy_countries = manager.get_proxy_countries()
    # 如果代理国家列表为空，尝试加载
    if not proxy_countries:
        load_proxy_countries()

    # 查找指定国家代码的代理信息
    found = False
    for country in proxy_countries:
        if country.code.lower() == proxy_request.country_code.lower():
            manager.set_current_proxy(country)
        found = True
        break

    if not found:
        return HTTPException(status_code=404, detail=f"未找到国家代码为 {proxy_request.country_code} 的代理信息")

    current_proxy = manager.get_current_proxy()
    return {
        "proxy": current_proxy["proxy_url"],
        "country": current_proxy["country"],
        "code": current_proxy["code"],
        "time_zone": current_proxy["time_zone"],
        "language": current_proxy["language"],
        "latitude": current_proxy["latitude"],
        "longitude": current_proxy["longitude"]
    }
