import random

from fastapi import APIRouter
from fastapi import Request
from fastapi.templating import Jinja2Templates
from loguru import logger

from app.dependencies.countries import manager
from app.dependencies.utils import replace_pad
from app.models.accounts import AndroidPadCodeRequest
from app.services.check_task import TaskManager
from app.services.task_status import process_task_status, reboot_task_status, replace_pad_stak_status
from config import pad_code_list, pkg_name, temple_id_list

router = APIRouter()
task_manager = TaskManager()


@router.get("/")
async def index(request: Request):
    templates = Jinja2Templates(directory="static")
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/status")
async def status(android_code: AndroidPadCodeRequest):
    await task_manager.remove_task(android_code.pad_code)
    logger.info("已在规定时间内完成， 超时任务已移除")
    result = await replace_pad([android_code.pad_code], template_id=random.choice(temple_id_list))
    logger.info(result)
    return {"message": "Task cancelled"}


@router.post("/callback", response_model= str)
async def callback(data: dict):
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
            logger.success("调用了adb")
            return "ok"

        case 1003:
            logger.success(f'安装成功接口回调 {data["apps"]["padCode"]}: 安装成功')
            process_task_status(data)
            return "ok"

        case 1004:
            logger.success(f"安装接口的回调{data}")
            process_task_status(data)
            return "ok"

        case 1006:
            process_task_status(data)
            return "ok"

        case 1007:
            logger.success("应用启动成功回调")
            process_task_status(data)
            return "ok"

        case 1009:
            process_task_status(data)
            return "ok"

        case 1124:
            if data.get("padCode") in pad_code_list:
                await replace_pad_stak_status(data, task_manager=task_manager)
            return "ok"

        case _:
            logger.success(f"其他接口回调: {data}")
            return "ok"
