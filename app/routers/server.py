import asyncio
import random
from typing import Any

from fastapi import HTTPException, APIRouter
from loguru import logger

from app.dependencies.countries import manager
from app.dependencies.utils import install_app, start_app, gps_in_ject_info, update_time_zone, update_language, \
    replace_pad
from app.models.accounts import AndroidPadCodeRequest
from app.services.check_task import TaskManager
from config import script_install_url, clash_install_url, pad_code_list, pkg_name, temple_id_list

router = APIRouter()
task_manager = TaskManager()

@router.post("/status")
async def status(android_code: AndroidPadCodeRequest):
    await task_manager.remove_task(android_code.pad_code)
    logger.info("已在规定时间内完成， 超时任务已移除")
    result = await replace_pad([android_code.pad_code], template_id=random.choice(temple_id_list))
    logger.info(result)
    return {"message": "Task cancelled"}


@router.post("/callback")
async def callback(data: dict):
    task_business_type = data.get("taskBusinessType")
    current_proxy = manager.get_current_proxy()
    match int(task_business_type):
        case 1000:
            if data["taskStatus"] == 3:
                _id = data.get("padCode")
                logger.success(f"{_id}: 重启成功")
                logger.info(f"设置语言、时区和GPS信息（使用代理国家: {current_proxy['country']} ({current_proxy['code']}))")
                # 设置语言
                lang_result = await update_language("en", country=current_proxy['code'], pad_code_list=[data["padCode"]])
                logger.info(f"语言更新结果: {lang_result}")
                # 设置时区
                tz_result = await update_time_zone(pad_code_list=[data["padCode"]], time_zone=current_proxy["time_zone"])
                logger.info(f"时区更新结果: {tz_result}")
                # 设置GPS信息
                gps_result = await gps_in_ject_info(
                    pad_code_list=[data["padCode"]],
                    latitude=current_proxy["latitude"],
                    longitude=current_proxy["longitude"]
                )
                logger.info(f"GPS注入结果: {gps_result}")
                await asyncio.sleep(2)
                logger.success(f"{_id}: 开始启动app")
                app_result = await start_app(pad_code_list=[data["padCode"]], pkg_name=pkg_name)
                logger.info(f"Start app result: {app_result}")
            return None

        case 1001:
            logger.success("1001接口回调")
            return None

        case 1002:
            logger.success("调用了adb")
            return None

        case 1003:
            logger.success(f'安装成功接口回调 {data["apps"]["padCode"]}: 安装成功')
            logger.success(data)
            return None


        case 1004:
            logger.success(f"安装接口的回调{data}")
            return None

        case 1006:
            logger.success("应用重启")
            return None

        case 1007:
            logger.success("应用启动成功回调")
            if data["taskStatus"] == 3:
                logger.success("启动成功")
                return None

            else:
                task = data["taskStatus"]
                logger.success(f"应用启动等待中: {task}")
                return None

        case 1009:
            logger.success("1009接口回调")
            return None

        case 1124:
            if data.get("padCode") in pad_code_list:
                if data["taskStatus"] == 3:
                    pad_code_str = data.get("padCode")
                    logger.info(f'{data["padCode"]}: 一键新机成功')
                    if await task_manager.get_task(pad_code_str) is not None:
                        return HTTPException(status_code=400, detail=f"Identifier {pad_code_str} is already in use")
                    task = asyncio.create_task(task_manager.handle_timeout(pad_code_str))
                    await task_manager.add_task(pad_code_str, task)
                    clash_install_result: Any = await install_app(pad_code_list=[data["padCode"]],
                                                                  app_url=clash_install_url)
                    logger.info(f"Clash 安装结果: {clash_install_result}")
                    script_install_result: Any = await install_app(pad_code_list=[data["padCode"]],
                                                                   app_url=script_install_url)
                    logger.info(f"脚本安装结果: {script_install_result}")
                    clash_task = asyncio.create_task(
                        task_manager.check_task_status(clash_install_result["data"][0]["taskId"], "Clash"))
                    script_task = asyncio.create_task(
                        task_manager.check_task_status(script_install_result["data"][0]["taskId"], "Script"))
                    try:
                        await asyncio.gather(clash_task, script_task)
                    except asyncio.CancelledError:
                        logger.info(f"任务被取消: {data['padCode']}")
                        # 确保取消所有子任务
                        if not clash_task.done():
                            clash_task.cancel()
                        if not script_task.done():
                            script_task.cancel()
                else:
                    logger.info(f'一键新机等待中 {data["taskStatus"]}')
            return None
        case _:
            logger.success(f"其他接口回调: {data}")
            return None


@router.get("/")
async def index():
    return {"status": "ok"}
