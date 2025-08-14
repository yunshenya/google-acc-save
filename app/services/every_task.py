import asyncio
from typing import Any

from fastapi import HTTPException
from loguru import logger

from app.curd.status import update_cloud_status
from app.dependencies.utils import update_language, update_time_zone, gps_in_ject_info, start_app, install_app
from app.config import clash_install_url, script_install_url


async def set_phone_state(current_proxy, package_name, pad_code):
    logger.info(
        f"设置语言、时区和GPS信息（使用代理国家: {current_proxy['country']} ({current_proxy['code']}))")
    # 设置语言
    await update_cloud_status(pad_code=pad_code,
                              current_status=f"设置语言、时区和GPS信息（使用代理国家: {current_proxy['country']} ({current_proxy['code']}))",
                              country=current_proxy["country"])
    lang_result = await update_language("en", country=current_proxy['code'],
                                        pad_code_list=[pad_code])
    logger.info(f"语言更新结果: {lang_result['msg']}")
    # 设置时区
    tz_result = await update_time_zone(pad_code_list=[pad_code],
                                       time_zone=current_proxy["time_zone"])
    logger.info(f"时区更新结果: {tz_result['msg']}")
    # 设置GPS信息
    gps_result = await gps_in_ject_info(
        pad_code_list=[pad_code],
        latitude=current_proxy["latitude"],
        longitude=current_proxy["longitude"]
    )
    logger.info(f"GPS注入结果: {gps_result['msg']}")
    await asyncio.sleep(2)
    logger.success(f"{pad_code}: 开始启动app")
    await update_cloud_status(pad_code=pad_code, current_status="开始启动脚本")
    app_result: Any = await start_app(pad_code_list=[pad_code], pkg_name=package_name)
    logger.info(f"Start app result: {app_result['msg']}")


async def install_app_task(pad_code_str, task_manager):
    script_md5 = script_install_url.split("/")[-1].replace(".apk", "")
    clash_md5 = clash_install_url.split("/")[-1].replace(".apk", "")
    logger.success(f'{pad_code_str}: 一键新机成功')
    await update_cloud_status(pad_code=pad_code_str,current_status="一键新机成功")
    if await task_manager.get_task(pad_code_str) is not None:
        raise HTTPException(status_code=400, detail=f"标识符 {pad_code_str} 已在使用")
    task = asyncio.create_task(task_manager.handle_timeout(pad_code_str))
    await task_manager.add_task(pad_code_str, task)
    clash_install_result: Any = await install_app(pad_code_list=[pad_code_str],
                                                  app_url=clash_install_url, md5=clash_md5)
    logger.info(f"Clash 安装结果: {clash_install_result['msg']}")
    script_install_result: Any = await install_app(pad_code_list=[pad_code_str],
                                                   app_url=script_install_url, md5=script_md5)
    logger.info(f"脚本安装结果: {script_install_result['msg']}")
    clash_task = asyncio.create_task(
        task_manager.check_task_status(clash_install_result["data"][0]["taskId"], "Clash"))
    script_task = asyncio.create_task(
        task_manager.check_task_status(script_install_result["data"][0]["taskId"], "Script"))
    try:
        await asyncio.gather(clash_task, script_task)
    except asyncio.CancelledError:
        logger.info(f"任务被取消: {pad_code_str}")
        # 确保取消所有子任务
        if not clash_task.done():
            clash_task.cancel()
        if not script_task.done():
            script_task.cancel()