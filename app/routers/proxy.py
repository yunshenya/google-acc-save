from typing import List

from fastapi import APIRouter, HTTPException

from app.curd.status import set_proxy_status, get_proxy_status
from app.dependencies.countries import load_proxy_countries, manager
from app.models.accounts import AndroidPadCodeRequest
from app.models.proxy import ProxyResponse, DbProxyRequest

router = APIRouter()

@router.post("/proxy", response_model=ProxyResponse)
async def get_proxy(android_pad_code: AndroidPadCodeRequest):
    """获取当前使用的代理信息"""
    current_proxy: ProxyResponse = await get_proxy_status(android_pad_code.pad_code)
    return current_proxy

@router.get("/proxy/countries", response_model=List[ProxyResponse])
async def get_proxy_countries() -> List[ProxyResponse]:
    proxy_countries = manager.get_proxy_countries()
    """获取所有可用的代理国家列表"""
    # 如果代理国家列表为空，尝试加载
    if not proxy_countries:
        load_proxy_countries()
    return proxy_countries


@router.post("/proxy/set", response_model=ProxyResponse)
async def set_database_proxy(proxy_request: DbProxyRequest) -> ProxyResponse:
    """根据国家代码设置数据库的代理"""
    proxy_countries = manager.get_proxy_countries()
    # 如果代理国家列表为空，尝试加载
    if not proxy_countries:
        load_proxy_countries()

    # 查找指定国家代码的代理信息
    found = False
    for country in proxy_countries:
        if country.code.lower() == proxy_request.country_code.lower():
            await set_proxy_status(proxy_request.pad_code, country)
            manager.set_current_proxy(country)
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail=f"未找到国家代码为 {proxy_request.country_code} 的代理信息")

    return await get_proxy_status(proxy_request.pad_code)