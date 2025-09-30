import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException

from app.services.websocket_manager import ws_manager
from app.services.logger import ws_logger

router = APIRouter()


def get_client_ip(websocket: WebSocket) -> str:
    """安全地获取客户端IP地址"""
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


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点"""
    client_ip = None
    connection_accepted = False

    try:
        # 先获取客户端IP（在accept之前）
        client_ip = get_client_ip(websocket)

        # 建立连接
        await ws_manager.connect(websocket)
        connection_accepted = True
        ws_logger.info(f"WebSocket连接建立成功，客户端: {client_ip}")

        # 消息循环
        while True:
            try:
                # 设置接收超时，避免长时间阻塞
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=300.0,  # 5分钟超时
                )
                ws_logger.debug(f"收到客户端消息 ({client_ip}): {data[:100]}...")

                try:
                    message = json.loads(data)
                    await ws_manager.handle_client_message(websocket, message)
                except json.JSONDecodeError as e:
                    ws_logger.warning(f"客户端发送的消息格式无效 ({client_ip}): {e}")
                    # 只有在连接有效时才发送错误消息
                    if connection_accepted:
                        try:
                            await websocket.send_text(
                                json.dumps({"type": "error", "message": "消息格式无效"})
                            )
                        except Exception as e:
                            ws_logger.debug(
                                f"无法发送错误消息，连接可能已断开: {client_ip}， 错误为{e}"
                            )
                            break

            except asyncio.TimeoutError:
                ws_logger.debug(f"WebSocket接收超时 ({client_ip})，继续等待...")
                # 检查连接是否仍然有效
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception as e:
                    ws_logger.info(f"连接已断开 ({client_ip})，退出接收循环, 错误为{e}")
                    break
                continue

            except WebSocketDisconnect:
                ws_logger.info(f"客户端主动断开连接: {client_ip}")
                break

            except Exception as e:
                ws_logger.error(f"处理WebSocket消息时出错 ({client_ip}): {e}")
                # 尝试发送错误消息，但如果失败就断开连接
                if connection_accepted:
                    try:
                        await websocket.send_text(
                            json.dumps(
                                {"type": "error", "message": "服务器处理消息时出错"}
                            )
                        )
                    except Exception as send_error:
                        ws_logger.warning(
                            f"向客户端发送错误消息失败，连接可能已断开 ({client_ip}): {send_error}"
                        )
                        break
                else:
                    # 如果连接还没接受就出错，直接断开
                    break

    except WebSocketDisconnect:
        ws_logger.info(f"WebSocket连接断开: {client_ip or 'unknown'}")
    except WebSocketException as e:
        ws_logger.warning(f"WebSocket协议错误 ({client_ip or 'unknown'}): {e}")
    except Exception as e:
        ws_logger.error(f"WebSocket连接异常 ({client_ip or 'unknown'}): {e}")
    finally:
        # 清理连接
        if connection_accepted:
            ws_manager.disconnect(websocket)
            ws_logger.debug(f"WebSocket连接清理完成: {client_ip or 'unknown'}")


@router.get("/ws/stats")
async def get_websocket_stats():
    """获取WebSocket连接统计信息（调试用）"""
    try:
        stats = ws_manager.get_connection_stats()
        ws_logger.info(
            f"WebSocket统计信息查询: {stats['active_connections']} 个活跃连接"
        )
        return {
            "status": "success",
            "data": stats,
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        ws_logger.error(f"获取WebSocket统计信息失败: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": asyncio.get_event_loop().time(),
        }
