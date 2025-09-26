import os
import sys
from pathlib import Path
from loguru import logger

# 创建日志目录
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 移除默认的控制台处理器
logger.remove()

# 添加控制台输出（带颜色）
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

# 添加文件输出（所有日志）
logger.add(
    LOG_DIR / "app_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="00:00",  # 每天午夜轮转
    retention="30 days",  # 保留30天
    compression="zip",  # 压缩旧日志
    encoding="utf-8"
)

# 添加错误日志文件
logger.add(
    LOG_DIR / "error_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
    rotation="00:00",
    retention="90 days",
    compression="zip",
    encoding="utf-8"
)

# 添加WebSocket专用日志
logger.add(
    LOG_DIR / "websocket_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | WebSocket - {message}",
    level="DEBUG",
    rotation="00:00",
    retention="7 days",
    filter=lambda record: "websocket" in record["name"].lower() or "ws" in record.get("extra", {}),
    encoding="utf-8"
)

# 添加任务状态专用日志
logger.add(
    LOG_DIR / "task_status_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | Task - {message}",
    level="DEBUG",
    rotation="00:00",
    retention="15 days",
    filter=lambda record: "task" in record["name"].lower() or record.get("extra", {}).get("category") == "task",
    encoding="utf-8"
)

# 导出配置好的logger
def get_logger(name: str = None):
    """获取配置好的logger实例"""
    if name:
        return logger.bind(name=name)
    return logger

# 为WebSocket创建专用logger
ws_logger = logger.bind(name="websocket", ws=True)

# 为任务状态创建专用logger
task_logger = logger.bind(name="task", category="task")