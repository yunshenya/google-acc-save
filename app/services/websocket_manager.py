import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import Set, Dict, Optional, Any

from anyio import Semaphore

from app.config import config
from app.curd.proxy import get_proxies_by_country_code
from app.dependencies.utils import replace_pad
from app.curd.status import update_cloud_status, set_proxy_status, remove_cloud_status, get_one_pade_status
from app.dependencies.countries import manager
from fastapi import WebSocket
from sqlalchemy import select

from app.routers.server import task_manager
from app.services.database import SessionLocal, Status
from app.services.logger import ws_logger


def get_websocket_client_ip(websocket: WebSocket) -> str:
    """安全地获取WebSocket客户端IP地址"""
    try:
        # 尝试多种方式获取客户端IP
        if hasattr(websocket, "client") and websocket.client:
            # websocket.client 是一个 Address 对象 (host, port)
            if hasattr(websocket.client, "host"):
                return websocket.client.host
            # 如果是元组形式
            elif (
                isinstance(websocket.client, (tuple, list))
                and len(websocket.client) > 0
            ):
                return str(websocket.client[0])

        # 尝试从headers获取
        if hasattr(websocket, "headers"):
            # 检查X-Forwarded-For头（代理情况）
            x_forwarded_for = websocket.headers.get("x-forwarded-for")
            if x_forwarded_for:
                return x_forwarded_for.split(",")[0].strip()

            # 检查X-Real-IP头
            x_real_ip = websocket.headers.get("x-real-ip")
            if x_real_ip:
                return x_real_ip.strip()

        # 尝试从scope获取
        if hasattr(websocket, "scope") and "client" in websocket.scope:
            client = websocket.scope["client"]
            if isinstance(client, (tuple, list)) and len(client) > 0:
                return str(client[0])

        return "unknown"
    except Exception as e:
        ws_logger.warning(f"获取客户端IP失败: {e}")
        return "unknown"


class WebSocketManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.connection_info: Dict[WebSocket, Dict] = {}
        self._lock = asyncio.Lock()
        self.heartbeat_interval = 30  # 心跳间隔（秒）
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.timeout_check_minutes = config.get_timeout("global")
        self._timeout_semaphore = Semaphore(5)

    async def connect(self, websocket: WebSocket):
        """建立WebSocket连接"""
        try:
            await websocket.accept()

            # 获取客户端IP
            client_ip = get_websocket_client_ip(websocket)

            async with self._lock:
                self.active_connections.add(websocket)
                self.connection_info[websocket] = {
                    "connected_at": datetime.now(),
                    "last_ping": datetime.now(),
                    "client_ip": client_ip,
                }

            ws_logger.info(
                f"WebSocket连接已建立，客户端IP: {client_ip}, 当前连接数: {len(self.active_connections)}"
            )

            # 启动心跳任务（如果还没有启动）
            if not self.heartbeat_task or self.heartbeat_task.done():
                self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                ws_logger.info("启动WebSocket心跳任务")

            # 立即发送当前状态
            await self.send_status_update(websocket)

        except Exception as e:
            ws_logger.error(f"建立WebSocket连接失败: {e}")
            raise

    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""

        async def _disconnect():
            try:
                async with self._lock:
                    if websocket in self.active_connections:
                        self.active_connections.remove(websocket)
                        client_info = self.connection_info.pop(websocket, {})
                        client_ip = client_info.get("client_ip", "unknown")
                        ws_logger.info(
                            f"WebSocket连接已断开，客户端IP: {client_ip}, 当前连接数: {len(self.active_connections)}"
                        )

                # 如果没有活跃连接，停止心跳任务
                if (
                    not self.active_connections
                    and self.heartbeat_task
                    and not self.heartbeat_task.done()
                ):
                    self.heartbeat_task.cancel()
                    ws_logger.info("停止心跳任务，无活跃连接")

            except Exception as e:
                ws_logger.error(f"断开WebSocket连接时出错: {e}")

        # 如果在事件循环中，直接执行；否则创建任务
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_disconnect())
        except RuntimeError:
            # 没有运行中的事件循环
            asyncio.create_task(_disconnect())

    async def broadcast(self, message: dict, exclude_websocket: WebSocket = None):
        """向所有连接的客户端广播消息"""
        if not self.active_connections:
            ws_logger.debug("没有活跃连接，跳过广播")
            return

        message["timestamp"] = datetime.now().isoformat()
        message_str = json.dumps(message, ensure_ascii=False)

        disconnected = set()
        sent_count = 0

        # 获取连接副本避免在迭代时修改
        async with self._lock:
            connections = self.active_connections.copy()

        for connection in connections:
            if connection == exclude_websocket:
                continue

            try:
                # 再次检查连接是否仍在活跃列表中
                if connection not in self.active_connections:
                    continue

                await connection.send_text(message_str)
                sent_count += 1
            except Exception as e:
                client_ip = self.connection_info.get(connection, {}).get(
                    "client_ip", "unknown"
                )
                ws_logger.warning(f"发送WebSocket消息失败 (客户端: {client_ip}): {e}")
                disconnected.add(connection)

        # 清理断开的连接
        if disconnected:
            async with self._lock:
                for conn in disconnected:
                    self.active_connections.discard(conn)
                    self.connection_info.pop(conn, None)
            ws_logger.info(f"清理了 {len(disconnected)} 个断开的连接")

        ws_logger.debug(
            f"广播消息成功发送给 {sent_count} 个客户端，消息类型: {message.get('type', 'unknown')}"
        )

    async def _handle_timeout_device(self, pad_code: str):
        """处理超时设备 - 执行一键新机"""
        try:
            await task_manager.cancel_timeout_task_only(pad_code)
            # 选择随机模板
            temple_id = random.choice(config.TEMPLE_IDS)
            pade_status = await get_one_pade_status(pade_code=pad_code)
            # 选择随机代理
            if pade_status.is_random_proxy:
                default_proxy: Any = manager.get_proxy_countries()
                selected_proxy = random.choice(default_proxy)
            else:
                selected_proxy = get_proxies_by_country_code(country_code=pade_status.code)

            ws_logger.warning(
                f"{pad_code}: 检测到超时（超过{self.timeout_check_minutes}分钟未更新），开始执行一键新机"
            )

            if pad_code in config.PAD_CODES:
                # 设置代理
                await set_proxy_status(pad_code, selected_proxy, number_of_run=1)

                # 更新状态
                await update_cloud_status(
                    pad_code=pad_code,
                    current_status=f"超时检测触发一键新机（超过{self.timeout_check_minutes}分钟未更新）",
                    temple_id=temple_id,
                )

                if not config.DEBUG and pad_code in config.PAD_CODES:
                    result = await replace_pad([pad_code], template_id=temple_id)
                    await update_cloud_status(
                        pad_code=pad_code,
                        current_status="开始新机",
                        temple_id=temple_id,
                        num_other_error=1,
                    )
                    ws_logger.info(
                        f"{pad_code}: 超时触发一键新机结果 - {result.get('msg', '未知结果')}"
                    )
            else:
                await remove_cloud_status(pad_code=pad_code)

        except Exception as e:
            ws_logger.error(f"{pad_code}: 处理超时设备失败 - {e}")

    async def send_status_update(self, websocket: WebSocket = None):
        """发送状态更新"""
        try:
            # 获取最新状态数据
            async with SessionLocal() as db:
                result = await db.execute(
                    select(Status).order_by(Status.updated_at.desc())
                )
                statuses = result.scalars().all()

                # 当前时间
                now = datetime.now()
                timeout_threshold = now - timedelta(minutes=self.timeout_check_minutes)

                # 转换为字典格式，并检测超时
                status_data = []
                timeout_devices = []
                for status in statuses:
                    if status.updated_at and status.updated_at < timeout_threshold:
                        timeout_devices.append(
                            {
                                "pad_code": status.pad_code,
                                "pad_name": status.pad_name,
                                "updated_at": status.updated_at,
                            }
                        )
                        ws_logger.warning(
                            f"设备超时检测: {status.pad_name} (pad_code: {status.pad_code}), "
                            f"最后更新时间: {status.updated_at}, "
                            f"当前状态: {status.current_status}"
                        )

                    status_dict = {
                        "pad_code": status.pad_code,
                        "pad_name": status.pad_name,
                        "current_status": status.current_status,
                        "number_of_run": status.number_of_run,
                        "num_of_success": status.num_of_success,
                        "temple_id": status.temple_id,
                        "phone_number_counts": status.phone_number_counts,
                        "forward_num": status.forward_num,
                        "secondary_email_num": status.secondary_email_num,
                        "country": status.country,
                        "updated_at": status.updated_at.isoformat()
                        if status.updated_at
                        else None,
                        "created_at": status.created_at.isoformat()
                        if status.created_at
                        else None,
                        "code": status.code,
                        "latitude": status.latitude,
                        "longitude": status.longitude,
                        "language": status.language,
                        "time_zone": status.time_zone,
                        "proxy": status.proxy,
                        "num_of_error": status.num_of_error,
                        "num_other_error": status.num_other_error,
                        "is_secondary_email": bool(status.is_secondary_email) if status.is_secondary_email is not None else False,
                        "is_random_proxy": bool(status.is_random_proxy) if status.is_secondary_email is not None else False,
                        "android_version" : status.android_version,
                    }
                    status_data.append(status_dict)

                if timeout_devices:
                    ws_logger.warning(
                        f"检测到 {len(timeout_devices)} 台设备超时，开始处理"
                    )
                    asyncio.create_task(
                        self._handle_timeout_devices_batch(timeout_devices)
                    )

            message = {
                "type": "status_update",
                "data": status_data,
                "total_count": len(status_data),
                "timeout_count": len(timeout_devices) if timeout_devices else 0,
            }

            if websocket:
                # 发送给特定客户端
                try:
                    # 检查连接是否在活跃连接列表中
                    if websocket not in self.active_connections:
                        ws_logger.warning("尝试向未连接的WebSocket发送消息")
                        return

                    await websocket.send_text(json.dumps(message, ensure_ascii=False))
                    client_ip = self.connection_info.get(websocket, {}).get(
                        "client_ip", "unknown"
                    )
                    ws_logger.debug(
                        f"状态更新发送给特定客户端 ({client_ip})，数据条数: {len(status_data)}"
                    )
                except Exception as e:
                    client_ip = self.connection_info.get(websocket, {}).get(
                        "client_ip", "unknown"
                    )
                    ws_logger.error(f"发送状态更新给特定客户端失败 ({client_ip}): {e}")
                    # 从活跃连接中移除
                    self.disconnect(websocket)
            else:
                # 广播给所有客户端
                await self.broadcast(message)

        except Exception as e:
            ws_logger.error(f"发送状态更新失败: {e}")

    async def notify_status_change(self, pad_code: str, status: str):
        """通知特定设备状态变化"""
        try:
            message = {
                "type": "single_status_update",
                "data": {"pad_code": pad_code, "current_status": status},
            }
            await self.broadcast(message)
            ws_logger.debug(f"设备状态变化通知: {pad_code} -> {status}")
        except Exception as e:
            ws_logger.error(f"通知状态变化失败: {e}")

    async def _heartbeat_loop(self):
        """心跳循环，保持连接活跃"""
        ws_logger.info("启动WebSocket心跳任务")

        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)

                if not self.active_connections:
                    ws_logger.info("无活跃连接，停止心跳任务")
                    break

                # 发送心跳消息
                ping_message = {
                    "type": "ping",
                    "server_time": datetime.now().isoformat(),
                }

                await self.broadcast(ping_message)
                ws_logger.debug(
                    f"发送心跳消息给 {len(self.active_connections)} 个客户端"
                )

        except asyncio.CancelledError:
            ws_logger.info("心跳任务被取消")
        except Exception as e:
            ws_logger.error(f"心跳任务出错: {e}")

    async def _handle_timeout_devices_batch(self, timeout_devices: list):
        tasks = []
        for device in timeout_devices:
            task = self._handle_timeout_device_with_semaphore(device["pad_code"])
            tasks.append(task)
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _handle_timeout_device_with_semaphore(self, pad_code: str):
        async with self._timeout_semaphore:  # 限制并发数
            try:
                await self._handle_timeout_device(pad_code)
            except Exception as e:
                ws_logger.error(f"{pad_code}: 超时处理失败 - {e}")

    async def handle_client_message(self, websocket: WebSocket, message: dict):
        """处理客户端消息"""
        try:
            message_type = message.get("type")
            client_ip = self.connection_info.get(websocket, {}).get(
                "client_ip", "unknown"
            )

            if message_type == "pong":
                # 更新最后ping时间
                if websocket in self.connection_info:
                    self.connection_info[websocket]["last_ping"] = datetime.now()
                    ws_logger.debug(f"客户端心跳响应: {client_ip}")

            elif message_type == "subscribe_status":
                # 客户端订阅状态更新
                await self.send_status_update(websocket)
                ws_logger.debug(f"客户端订阅状态更新: {client_ip}")

            elif message_type == "request_full_update":
                # 客户端请求完整更新
                await self.send_status_update(websocket)
                ws_logger.debug(f"客户端请求完整状态更新: {client_ip}")

            else:
                ws_logger.warning(
                    f"收到未知消息类型: {message_type} (客户端: {client_ip})"
                )

        except Exception as e:
            client_ip = self.connection_info.get(websocket, {}).get(
                "client_ip", "unknown"
            )
            ws_logger.error(f"处理客户端消息失败 ({client_ip}): {e}")

    def get_connection_stats(self) -> Dict:
        """获取连接统计信息"""
        return {
            "active_connections": len(self.active_connections),
            "heartbeat_running": self.heartbeat_task and not self.heartbeat_task.done(),
            "timeout_check_minutes": self.timeout_check_minutes,
            "connection_details": [
                {
                    "client_ip": info.get("client_ip", "unknown"),
                    "connected_at": info.get("connected_at").isoformat()
                    if info.get("connected_at")
                    else None,
                    "last_ping": info.get("last_ping").isoformat()
                    if info.get("last_ping")
                    else None,
                }
                for info in self.connection_info.values()
            ],
        }


ws_manager = WebSocketManager()
