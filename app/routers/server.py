import random
from typing import Any

from fastapi import APIRouter
from fastapi import Request
from fastapi.responses import FileResponse
from starlette.responses import HTMLResponse

from app.config import config
from app.curd.status import update_cloud_status, set_proxy_status
from app.dependencies.countries import manager
from app.dependencies.utils import replace_pad
from app.models.accounts import AndroidPadCodeRequest
from app.services.check_task import TaskManager
from app.services.logger import task_logger, get_logger
from app.services.task_status import (
    reboot_task_status, replace_pad_stak_status,
    app_install_task_status, app_start_task_status,
    app_uninstall_task_status, adb_call_task_status,
    fileUpdate_task_status, app_reboot_task_status
)

router = APIRouter()
task_manager = TaskManager()

# 创建专用logger
callback_logger = get_logger("callback")


@router.get("/login", response_class=HTMLResponse)
async def login_page():
    """登录页面"""
    with open("templates/login.html", "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)


@router.get("/", response_class=HTMLResponse)
async def index():
    """主页 - 需要认证"""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)


@router.get("/statistics", response_class=HTMLResponse)
async def statistics_page():
    """统计页面 - 需要认证"""
    with open("templates/statistics.html", "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

@router.get("/pad-code-management", response_class=HTMLResponse)
async def pad_code_management_page():
    """设备代码管理页面"""
    with open("templates/pade_code.html", "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

@router.get("/favicon.ico")
async def favicon() -> FileResponse:
    return FileResponse("static/img/favicon.ico")

@router.get("/config", response_class=HTMLResponse)
async def config_page():
    """配置管理页面"""
    with open("templates/config.html", "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

@router.post("/status")
async def status(android_code: AndroidPadCodeRequest):
    pad_code = android_code.pad_code
    print(android_code.type)
    match android_code.type:
        case 0:
            await update_cloud_status(pad_code, num_other_error=1)
        case 1:
            await update_cloud_status(pad_code=pad_code, num_of_error=1)
    try:
        if pad_code in config.PAD_CODES:
            # 取消超时任务
            await task_manager.cancel_timeout_task_only(pad_code)

            # 选择模板和代理
            template_id = random.choice(config.TEMPLE_IDS)
            default_proxy: Any = manager.get_proxy_countries()
            selected_proxy = random.choice(default_proxy)

            await set_proxy_status(pad_code, selected_proxy, number_of_run=1)
            await update_cloud_status(
                pad_code,
                temple_id=template_id,
                current_status="一键新机中"
            )

            task_logger.success(f"{pad_code}: 手动触发一键新机，模板: {template_id}, 代理: {selected_proxy.country}")
            # 执行一键新机
            if not config.DEBUG:
                result = await replace_pad([pad_code], template_id=template_id)
                callback_logger.info(f"{pad_code}: 一键新机结果 - {result.get('msg', '未知结果')}")
            else:
                callback_logger.info(f"{pad_code}: 调试模式 - 模拟一键新机完成")
            return {"message": "一键新机启动成功", "template_id": template_id, "country": selected_proxy.country}
        else:

            return {"message": "其他机器成功"}

    except Exception as e:
        callback_logger.error(f"{pad_code}: 手动一键新机失败 - {e}")
        return {"message": f"一键新机启动失败: {str(e)}", "error": True}


@router.get("/proxy-collection-page", response_class=HTMLResponse)
async def proxy_collection_page():
    """代理集合管理页面"""
    with open("templates/proxy_collection.html", "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)


@router.get("/ipinfo")
async def get_client_ip(request: Request):
    # 获取客户端IP地址
    client_ip = request.client.host
    return {"client_ip": client_ip}

@router.post("/callback", response_model=str)
async def callback(data: dict) -> str:
    """云机任务状态回调接口"""
    task_business_type = data.get("taskBusinessType")
    pad_code = data.get("padCode", "未知设备")
    task_id = data.get("taskId", "未知任务")

    callback_logger.info(f"收到回调: 设备={pad_code}, 类型={task_business_type}, 任务ID={task_id}")

    try:
        match int(task_business_type):
            case 1000:  # 重启任务
                callback_logger.info(f"{pad_code}: 处理重启任务回调")
                await reboot_task_status(data, config.get_package_name("primary"), task_manager)
                return "ok"

            case 1001:  # 未知类型1001
                callback_logger.info(f"{pad_code}: 1001接口回调")
                return "ok"

            case 1002:  # ADB调用任务
                callback_logger.info(f"{pad_code}: 处理ADB调用任务回调")
                await adb_call_task_status(data)
                return "ok"

            case 1003:  # 应用安装任务
                app_name = data.get("apps", {}).get("appName", "未知应用")
                callback_logger.info(f"{pad_code}: 处理应用安装任务回调 - {app_name}")
                app_install_task_status(data)
                return "ok"

            case 1004:  # 应用卸载任务
                app_name = data.get("apps", {}).get("appName", "未知应用")
                callback_logger.info(f"{pad_code}: 处理应用卸载任务回调 - {app_name}")
                app_uninstall_task_status(data)
                return "ok"

            case 1006:  # 应用重启任务
                callback_logger.info(f"{pad_code}: 处理应用重启任务回调")
                app_reboot_task_status(data)
                return "ok"

            case 1007:  # 应用启动任务
                callback_logger.info(f"{pad_code}: 处理应用启动任务回调")
                app_start_task_status(data)
                return "ok"

            case 1009:  # 文件更新任务
                callback_logger.info(f"{pad_code}: 处理文件更新任务回调")
                await fileUpdate_task_status(data)
                return "ok"

            case 1124:  # 一键新机任务
                callback_logger.info(f"{pad_code}: 处理一键新机任务回调")
                if (pad_code in config.PAD_CODES) and not config.DEBUG:
                    await replace_pad_stak_status(data, task_manager=task_manager)
                elif config.DEBUG:
                    callback_logger.info(f"{pad_code}: 调试模式 - 跳过一键新机处理")
                else:
                    callback_logger.warning(f"{pad_code}: 设备不在管理列表中")
                return "ok"

            case _:  # 其他未知类型
                callback_logger.info(f"{pad_code}: 其他类型回调 (类型: {task_business_type}): {data}")
                return "ok"

    except ValueError as e:
        callback_logger.error(f"回调数据格式错误: {e}, 数据: {data}")
        return "error: invalid task_business_type"
    except Exception as e:
        callback_logger.error(f"处理回调时出错: {e}, 数据: {data}")
        return "error: callback processing failed"