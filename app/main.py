import logging
import random
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import config
from app.curd.status import add_cloud_status, remove_cloud_status, set_proxy_status
from app.dependencies.countries import load_proxy_countries
from app.dependencies.countries import manager
from app.dependencies.utils import replace_pad
from app.routers import accounts, proxy, server, status, auth, statistics, proxy_collection
from app.routers import pad_code as pad_code_router
from app.routers import config as config_router
from app.routers import websocket as websocket_router
from app.services.database import engine, Base
# 导入日志配置
from app.services.logger import get_logger, task_logger

# 获取主应用logger
logger = get_logger("main")


# 日志拦截器 - 将其他库的日志重定向到loguru
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # 获取对应的loguru级别
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 获取调用者信息
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


# noinspection PyShadowingNames
@asynccontextmanager
async def startup_event(app: FastAPI):
    """应用启动事件"""
    logger.info("=== 应用启动开始 ===")

    try:
        # 配置日志拦截器
        logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
        logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]
        logging.getLogger("uvicorn.error").propagate = False
        logging.getLogger("uvicorn").propagate = False
        logging.getLogger("fastapi").propagate = False

        logger.info("日志系统初始化完成")

        # 加载代理国家列表
        load_proxy_countries()
        logger.info("代理国家列表加载完成")

        # 挂载静态文件和路由
        app.mount("/static", StaticFiles(directory="static"), name="static")
        app.include_router(auth.router, prefix="/auth", tags=["认证"])
        app.include_router(statistics.router, prefix="/api", tags=["统计"])
        app.include_router(proxy_collection.router, prefix="", tags=["代理集合"])
        app.include_router(websocket_router.router, tags=["WebSocket"])
        app.include_router(config_router.router, prefix="/api", tags=["配置管理"])
        app.include_router(pad_code_router.router, prefix="", tags=["设备代码管理"])
        app.include_router(accounts.router, prefix="")
        app.include_router(proxy.router, prefix="")
        app.include_router(server.router, prefix="")
        app.include_router(status.router, prefix="")

        logger.info("路由注册完成")

        # 创建数据库表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库表创建/检查完成")

        # 初始化云机状态
        logger.info(f"开始初始化 {len(config.PAD_CODES)} 台云机")

        for i, pad_code in enumerate(config.PAD_CODES):
            try:
                template_id = random.choice(config.TEMPLE_IDS)
                await add_cloud_status(pad_code, template_id)

                default_proxy: Any = manager.get_proxy_countries()
                selected_proxy = random.choice(default_proxy)
                await set_proxy_status(pad_code, selected_proxy, number_of_run=1)

                if not config.DEBUG:
                    result = await replace_pad([pad_code], template_id=template_id)
                    task_logger.info(f"云机启动完成: {pad_code}, 模板: {template_id}, 结果: {result.get('msg', '未知')}")
                else:
                    task_logger.info(f"调试模式 - 云机模拟启动: {pad_code}, 模板: {template_id}")

                logger.info(f"云机初始化进度: {i+1}/{len(config.PAD_CODES)} ({pad_code})")

            except Exception as e:
                logger.error(f"初始化云机 {pad_code} 失败: {e}")
                continue

        logger.success("=== 应用启动完成 ===")

    except Exception as e:
        logger.error(f"应用启动过程中出错: {e}")
        raise

    yield

    # 应用关闭时的清理工作
    logger.info("=== 应用开始关闭 ===")

    try:
        # 清理云机状态
        for pad_code in config.PAD_CODES:
            try:
                await remove_cloud_status(pad_code)
            except Exception as e:
                logger.warning(f"清理云机状态失败 {pad_code}: {e}")

        logger.info("云机状态清理完成")

    except Exception as e:
        logger.error(f"应用关闭时出错: {e}")

    logger.info("=== 应用关闭完成 ===")


app = FastAPI(
    title="Google账号管理系统",
    lifespan=startup_event,
    description="云机管理和账号自动化系统",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("FastAPI应用创建完成")