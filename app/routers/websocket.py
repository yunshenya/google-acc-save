import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.websocket_manager import ws_manager
from app.services.logger import ws_logger

router = APIRouter()


def get_client_ip(websocket: WebSocket) -> str:
    """安全地获取客户端IP地址"""
    try:
        # 尝试多种方式获取客户端IP
        if hasattr(websocket, 'client') and websocket.client:
            # websocket.client 是一个 Address 对象 (host, port)
            if hasattr(websocket.client, 'host'):
                return websocket.client.host
            # 如果是元组形式
            elif isinstance(websocket.client, (tuple, list)) and len(websocket.client) > 0:
                return str(websocket.client[0])

        # 尝试从headers获取
        if hasattr(websocket, 'headers'):
            # 检查X-Forwarded-For头（代理情况）
            x_forwarded_for = websocket.headers.get('x-forwarded-for')
            if x_forwarded_for:
                return x_forwarded_for.split(',')[0].strip()

            # 检查X-Real-IP头
            x_real_ip = websocket.headers.get('x-real-ip')
            if x_real_ip:
                return x_real_ip.strip()

        # 尝试从scope获取
        if hasattr(websocket, 'scope') and 'client' in websocket.scope:
            client = websocket.scope['client']
            if isinstance(client, (tuple, list)) and len(client) > 0:
                return str(client[0])

        return 'unknown'
    except Exception as e:
        ws_logger.warning(f"获取客户端IP失败: {e}")
        return 'unknown'


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点"""
    client_ip = get_client_ip(websocket)

    try:
        # 建立连接
        await ws_manager.connect(websocket)
        ws_logger.info(f"WebSocket连接建立成功，客户端: {client_ip}")

        while True:
            try:
                # 监听客户端消息
                data = await websocket.receive_text()
                ws_logger.debug(f"收到客户端消息: {data[:100]}...")  # 只记录前100个字符

                try:
                    message = json.loads(data)
                    await ws_manager.handle_client_message(websocket, message)
                except json.JSONDecodeError as e:
                    ws_logger.warning(f"客户端发送的消息格式无效: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "消息格式无效"
                    }))

            except WebSocketDisconnect:
                ws_logger.info(f"客户端主动断开连接: {client_ip}")
                break
            except Exception as e:
                ws_logger.error(f"处理WebSocket消息时出错: {e}")
                # 发送错误消息给客户端
                try:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "服务器处理消息时出错"
                    }))
                except Exception as e:
                    # 如果发送失败，说明连接已经断开
                    ws_logger.warning(f"向客户端发送错误消息失败，连接可能已断开: {client_ip}: {e}")
                    break

    except WebSocketDisconnect:
        ws_logger.info(f"WebSocket连接断开: {client_ip}")
    except Exception as e:
        ws_logger.error(f"WebSocket连接异常: {e}")
    finally:
        # 清理连接
        ws_manager.disconnect(websocket)
        ws_logger.debug(f"WebSocket连接清理完成: {client_ip}")


@router.get("/ws/stats")
async def get_websocket_stats():
    """获取WebSocket连接统计信息（调试用）"""
    try:
        stats = ws_manager.get_connection_stats()
        ws_logger.info(f"WebSocket统计信息查询: {stats['active_connections']} 个活跃连接")
        return {
            "status": "success",
            "data": stats,
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        ws_logger.error(f"获取WebSocket统计信息失败: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": asyncio.get_event_loop().time()
        }


@router.post("/ws/broadcast")
async def broadcast_message(message: dict):
    """手动广播消息（调试用）"""
    try:
        await ws_manager.broadcast({
            "type": "manual_broadcast",
            "data": message
        })
        ws_logger.info(f"手动广播消息成功: {message}")
        return {
            "status": "success",
            "message": "广播成功",
            "data": message
        }
    except Exception as e:
        ws_logger.error(f"手动广播消息失败: {e}")
        return {
            "status": "error",
            "message": f"广播失败: {str(e)}"
        }


@router.post("/ws/send-status-update")
async def trigger_status_update():
    """手动触发状态更新（调试用）"""
    try:
        await ws_manager.send_status_update()
        ws_logger.info("手动触发状态更新成功")
        return {
            "status": "success",
            "message": "状态更新触发成功"
        }
    except Exception as e:
        ws_logger.error(f"手动触发状态更新失败: {e}")
        return {
            "status": "error",
            "message": f"状态更新失败: {str(e)}"
        }