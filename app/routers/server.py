import random

from fastapi import APIRouter
from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from loguru import logger

from app.config import pad_code_list, pkg_name, temple_id_list
from app.curd.status import update_cloud_status
from app.dependencies.countries import manager
from app.dependencies.utils import replace_pad
from app.models.accounts import AndroidPadCodeRequest
from app.services.check_task import TaskManager
from app.services.task_status import reboot_task_status, replace_pad_stak_status, \
    app_install_task_status, app_start_task_status, app_uninstall_task_status, adb_call_task_status, \
    fileUpdate_task_status, app_reboot_task_status
from app.config import DEBUG

router = APIRouter()
task_manager = TaskManager()


@router.get("/")
async def index(request: Request):
    templates = Jinja2Templates(directory="templates")
    return templates.TemplateResponse("index.html", {"request": request, "debug": "true" if DEBUG else "false"})

@router.get("/favicon.ico")
async def favicon() -> FileResponse:
    return FileResponse("static/favicon.ico")


@router.post("/status")
async def status(android_code: AndroidPadCodeRequest):
    await task_manager.remove_task(android_code.pad_code)
    template_id=random.choice(temple_id_list)
    await update_cloud_status(android_code.pad_code, number_of_run=1, temple_id=template_id, current_status="任务已完成，正在一键新机中")
    await replace_pad([android_code.pad_code], template_id=template_id)
    return {"message": "Task cancelled"}


@router.post("/callback", response_model= str)
async def callback(data: dict) -> str:
    current_proxy = manager.get_current_proxy()
    task_business_type = data.get("taskBusinessType")
    match int(task_business_type):
        case 1000:
            await reboot_task_status(data, current_proxy, pkg_name)
            return "ok"

        case 1001:
            logger.success("1001接口回调")
            return "ok"

        case 1002:
            await adb_call_task_status(data)
            return "ok"

        case 1003:
            app_install_task_status(data)
            return "ok"

        case 1004:
            logger.success(f"应用卸载的接口回调：{data}")
            app_uninstall_task_status(data)
            return "ok"

        case 1006:
            app_reboot_task_status(data)
            return "ok"

        case 1007:
            app_start_task_status(data)
            return "ok"

        case 1009:
            await fileUpdate_task_status(data)
            return "ok"

        case 1124:
            if data.get("padCode") in pad_code_list:
                await replace_pad_stak_status(data, task_manager=task_manager)
            return "ok"

        case _:
            logger.success(f"其他接口回调: {data}")
            return "ok"
