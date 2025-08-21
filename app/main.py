import logging
import random
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.config import pad_code_list, temple_id_list
from app.curd.status import add_cloud_status, remove_cloud_status
from app.dependencies.countries import load_proxy_countries
from app.dependencies.utils import replace_pad
from app.routers import accounts, proxy, server, status
from app.services.database import engine, Base


#日志拦截器
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # 获取 Loguru 对应的日志级别
        level = logger.level(record.levelname).name
        # 将日志记录传递给 Loguru
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())



# noinspection PyShadowingNames
@asynccontextmanager
async def startup_event(app: FastAPI):
    """

    :type app: FastAPI
    """
    # 将 Uvicorn 的日志处理器替换为我们的拦截器
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.error").propagate = False # 避免重复输出
    # 加载代理国家列表
    load_proxy_countries()
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.include_router(accounts.router, prefix="")
    app.include_router(proxy.router, prefix="")
    app.include_router(server.router, prefix="")
    app.include_router(status.router, prefix="")
    # 一键新机
    for pad_code in pad_code_list:
        template_id=random.choice(temple_id_list)
        await add_cloud_status(pad_code, template_id)
        result = await replace_pad(pad_code, template_id=template_id)
        logger.info(f"已启动: {pad_code}，执行结果为: {result['msg']}")

    # 创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    for pad_code in pad_code_list:
        await remove_cloud_status(pad_code)
    logger.info("application shutdown")



app = FastAPI(title="google账号管理系统", lifespan=startup_event)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

