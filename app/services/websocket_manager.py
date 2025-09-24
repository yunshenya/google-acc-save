import asyncio
import json
from typing import Set

from fastapi import WebSocket
from loguru import logger
from sqlalchemy import select

from app.services.database import SessionLocal, Status


class WebSocketManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"WebSocket连接已建立，当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        async def _disconnect():
            async with self._lock:
                self.active_connections.discard(websocket)
            logger.info(f"WebSocket连接已断开，当前连接数: {len(self.active_connections)}")

        # 如果在事件循环中，直接执行；否则创建任务
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_disconnect())
        except RuntimeError:
            # 没有运行中的事件循环
            pass

    async def broadcast(self, message: dict):
        """向所有连接的客户端广播消息"""
        if not self.active_connections:
            return

        disconnected = set()
        async with self._lock:
            connections = self.active_connections.copy()

        for connection in connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"发送WebSocket消息失败: {e}")
                disconnected.add(connection)

        # 清理断开的连接
        if disconnected:
            async with self._lock:
                self.active_connections -= disconnected

    async def send_status_update(self, websocket: WebSocket = None):
        """发送状态更新"""
        try:
            # 获取最新状态数据
            async with SessionLocal() as db:
                result = await db.execute(select(Status))
                statuses = result.scalars().all()

                # 转换为字典格式
                status_data = []
                for status in statuses:
                    status_dict = {
                        "pad_code": status.pad_code,
                        "current_status": status.current_status,
                        "number_of_run": status.number_of_run,
                        "temple_id": status.temple_id,
                        "phone_number_counts": status.phone_number_counts,
                        "country": status.country,
                        "updated_at": status.updated_at.isoformat() if status.updated_at else None,
                        "created_at": status.created_at.isoformat() if status.created_at else None,
                        "code": status.code,
                        "latitude": status.latitude,
                        "longitude": status.longitude,
                        "language": status.language,
                        "time_zone": status.time_zone,
                        "proxy": status.proxy
                    }
                    status_data.append(status_dict)

            message = {
                "type": "status_update",
                "data": status_data,
                "timestamp": asyncio.get_event_loop().time()
            }

            if websocket:
                # 发送给特定客户端
                await websocket.send_text(json.dumps(message))
            else:
                # 广播给所有客户端
                await self.broadcast(message)

        except Exception as e:
            logger.error(f"发送状态更新失败: {e}")

    async def notify_status_change(self, pad_code: str, status: str):
        """通知特定设备状态变化"""
        message = {
            "type": "single_status_update",
            "data": {
                "pad_code": pad_code,
                "current_status": status,
                "timestamp": asyncio.get_event_loop().time()
            }
        }
        await self.broadcast(message)

# 全局WebSocket管理器实例
ws_manager = WebSocketManager()