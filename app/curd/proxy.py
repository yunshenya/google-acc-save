from sqlite3 import IntegrityError
from typing import Any

from sqlalchemy import cast, ColumnElement

from app.curd.status import get_proxy_status
from app.dependencies.utils import get_cloud_phone_info
from app.models.proxy import ProxyResponse
from app.services.database import SessionLocal, ProxyCollection


async def update_proxies(pade_code: str):
    async with SessionLocal() as db:
        try:
            current_proxy: ProxyResponse = await get_proxy_status(pad_code=pade_code)
            cloud_phone_info: Any = await get_cloud_phone_info(pad_code=pade_code)
            phon_data = cloud_phone_info["data"]
            proxy = ProxyCollection(
                country = current_proxy.country,
                android_version = phon_data["androidVersion"],
                temple_id = current_proxy.temple_id,
                code = current_proxy.code,
                latitude = current_proxy.latitude,
                longitude = current_proxy.longitude,
                time_zone = current_proxy.time_zone,
                proxy = current_proxy.proxy,
                language = current_proxy.language
            )
            db.add(proxy)
            await db.commit()
            await db.refresh(proxy)
        except IntegrityError:
            await db.rollback()



async def get_proxies():
    async with SessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(select(ProxyCollection).order_by(cast(ColumnElement[bool], ProxyCollection.id)))
        status = result.scalars().all()
        return status

