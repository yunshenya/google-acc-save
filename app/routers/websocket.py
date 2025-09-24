import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from app.services.websocket_manager import WebSocketManager

router = APIRouter()
ws_manager = WebSocketManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # 保持连接并监听客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)

            # 处理客户端请求
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": asyncio.get_event_loop().time()
                }))
            elif message.get("type") == "subscribe_status":
                # 客户端订阅状态更新
                await ws_manager.send_status_update(websocket)

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("WebSocket连接已断开")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        ws_manager.disconnect(websocket)