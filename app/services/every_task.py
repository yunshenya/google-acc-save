import asyncio
import random
from asyncio import sleep
from typing import Any

from fastapi import HTTPException
from loguru import logger

from app.config import clash_install_url, script_install_url, temple_id_list
from app.curd.status import update_cloud_status
from app.dependencies.utils import start_app, install_app, \
    check_padTaskDetail, replace_pad, click, Position, ActionType


async def start_app_state(package_name, pad_code, task_manager):
    logger.success(f"{pad_code}: 开始启动app")
    await update_cloud_status(pad_code=pad_code, current_status="开始启动脚本")
    total_try_count = 0
    try:
        while total_try_count < 6:
            app_result: Any = await start_app(pad_code_list=[pad_code], pkg_name=package_name)
            taskid= app_result["data"][0]["taskId"]
            match await check_padTaskDetail([taskid]):
                case -1:
                    logger.warning(f"{pad_code}: 启动任务正在一键新机")
                    if await task_manager.get_task(pad_code) is not None:
                        await task_manager.remove_task(pad_code)
                        template_id=random.choice(temple_id_list)
                        await update_cloud_status(pad_code, number_of_run=1, temple_id=template_id, current_status="正在一键新机中")
                        await replace_pad([pad_code], template_id=template_id)
                    break

                case 0:
                    logger.info(f"{pad_code}: 启动app中...")
                    await asyncio.sleep(2)

                case 1:
                    await sleep(10)
                    await click([pad_code], [
                        Position(
                            x=559,
                            y=2056,
                            action_type=ActionType.press,
                            next_position_wait_time=10
                        ).to_dict(),
                        Position(
                            x=559,
                            y=2056,
                            action_type=ActionType.lift,
                            next_position_wait_time=100
                        ).to_dict(),
                        Position(
                            x=1003,
                            y=671,
                            action_type=ActionType.press,
                            next_position_wait_time=10
                        ).to_dict(),
                        Position(
                            x=1003,
                            y=671,
                            action_type=ActionType.lift,
                            next_position_wait_time=100
                        ).to_dict(),
                        Position(
                            x=456,
                            y=674,
                            action_type=ActionType.press,
                            next_position_wait_time=10
                        ).to_dict(),
                        Position(
                            x=456,
                            y=674,
                            action_type=ActionType.lift
                        ).to_dict()
                    ])
                    await sleep(3)
                    await click([pad_code], [
                        Position(
                            x=1003,
                            y=671,
                            action_type=ActionType.press,
                            next_position_wait_time=10
                        ).to_dict(),
                        Position(
                            x=1003,
                            y=671,
                            action_type=ActionType.lift,
                            next_position_wait_time=200
                        ).to_dict(),
                        Position(
                            x=456,
                            y=674,
                            action_type=ActionType.press,
                            next_position_wait_time=10
                        ).to_dict(),
                        Position(
                            x=456,
                            y=674,
                            action_type=ActionType.lift
                        ).to_dict()
                    ])
                    logger.success(f"{pad_code}: 启动app成功")
                    break
            total_try_count += 1

    except IndexError:
        while total_try_count < 6:
            app_result: Any = await start_app(pad_code_list=[pad_code], pkg_name=package_name)
            taskid= app_result["data"][0]["taskId"]
            match await check_padTaskDetail([taskid]):
                case -1:
                    logger.warning(f"{pad_code}: 正在一键新机")
                    if await task_manager.get_task(pad_code) is not None:
                        await task_manager.remove_task(pad_code)
                        template_id=random.choice(temple_id_list)
                        await update_cloud_status(pad_code, number_of_run=1, temple_id=template_id, current_status="正在一键新机中")
                        await replace_pad([pad_code], template_id=template_id)
                    break
                case 0:
                    logger.info(f"{pad_code}: 启动app中...")
                    await asyncio.sleep(2)
                case 1:
                    logger.success(f"{pad_code}: 启动app成功")
                    break
            total_try_count += 1



async def install_app_task(pad_code_str, task_manager):
    script_md5_list: Any = script_install_url.split("/")
    script_md5 = script_md5_list[-1].replace(".apk", "")
    clash_md5_list: Any = clash_install_url.split("/")
    clash_md5 = clash_md5_list[-1].replace(".apk", "")
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