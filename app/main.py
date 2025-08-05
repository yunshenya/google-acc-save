import random
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from loguru import logger

from app.dependencies.countries import load_proxy_countries
from app.dependencies.utils import replace_pad
from app.routers import router
from app.services.database import engine, Base
from config import pad_code_list, temple_id_list


@asynccontextmanager
async def startup_event(app: FastAPI):
    # 加载代理国家列表
    load_proxy_countries()

    # 一键新机
    result = await replace_pad(pad_code_list, template_id=random.choice(temple_id_list))
    logger.info(result)

    # 创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    logger.info("application shutdown")


if __name__ == "__main__":
    app = FastAPI(title="google账号管理系统", lifespan=startup_event)
    app.include_router(router, prefix="")
    uvicorn.run("app.main:app", host="0.0.0.0", port=5000)


