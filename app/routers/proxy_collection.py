from typing import List

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.services.database import SessionLocal, ProxyCollection

router = APIRouter()


@router.get("/proxy-collection", response_model=List[dict])
async def get_proxy_collection():
    """获取所有代理收集数据"""
    async with SessionLocal() as db:
        try:
            result = await db.execute(
                select(ProxyCollection).order_by(ProxyCollection.id.desc())
            )
            proxy_collections = result.scalars().all()

            # 转换为字典格式
            proxy_data = []
            for proxy in proxy_collections:
                proxy_dict = {
                    "id": proxy.id,
                    "country": proxy.country,
                    "android_version": proxy.android_version,
                    "temple_id": proxy.temple_id,
                    "code": proxy.code,
                    "latitude": proxy.latitude,
                    "longitude": proxy.longitude,
                    "proxy": proxy.proxy,
                    "language": proxy.language,
                    "time_zone": proxy.time_zone,
                    "created_at": proxy.created_at.isoformat() if proxy.created_at else None
                }
                proxy_data.append(proxy_dict)

            return proxy_data

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取代理数据失败: {str(e)}")


@router.delete("/proxy-collection/{proxy_id}")
async def delete_proxy_collection(proxy_id: int):
    """删除指定的代理数据"""
    async with SessionLocal() as db:
        try:
            result = await db.execute(
                select(ProxyCollection).filter(proxy_id == ProxyCollection.id))
            proxy = result.scalars().first()

            if not proxy:
                raise HTTPException(status_code=404, detail="代理记录不存在")

            # 删除记录
            await db.delete(proxy)
            await db.commit()

            return {"message": f"代理记录 {proxy_id} 删除成功"}

        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"删除代理记录失败: {str(e)}")