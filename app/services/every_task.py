import asyncio
import random
from typing import Any

from loguru import logger

from app.config import config
from app.curd.status import update_cloud_status
from app.dependencies.utils import start_app, check_padTaskDetail, replace_pad


async def start_app_state(package_name, pad_code, task_manager):
    logger.success(f"{pad_code}: 开始启动app")
    await update_cloud_status(pad_code=pad_code, current_status="开始启动脚本")
    total_try_count = 0
    try:
        app_result: Any = await start_app(pad_code_list=[pad_code], pkg_name=package_name)
        while total_try_count < 6:
            taskid = app_result["data"][0]["taskId"]
            match await check_padTaskDetail([taskid]):
                case -1:
                    logger.warning(f"{pad_code}: 启动任务正在一键新机")
                    await update_cloud_status(pad_code=pad_code, current_status="启动任务正在一键新机")
                    await task_manager.cancel_timeout_task_only(pad_code)
                    if pad_code in config.PAD_CODES:
                        template_id = random.choice(config.TEMPLE_IDS)
                        await update_cloud_status(
                            pad_code, number_of_run=1, temple_id=template_id,
                            current_status="正在一键新机中", num_other_error=1
                        )
                        await replace_pad([pad_code], template_id=template_id)
                    break
                case 0:
                    logger.info(f"{pad_code}: 启动app中...")
                    await update_cloud_status(pad_code=pad_code, current_status="启动app中...")
                    await asyncio.sleep(2)
                case 1:
                    # await update_cloud_status(pad_code=pad_code, current_status="开始点击脚本")
                    # await sleep(5)
                    # await click(
                    #     [pad_code],
                    #     [
                    #         Position(x=559, y=2056, action_type=ActionType.press, next_position_wait_time=10).to_dict(),
                    #         Position(x=559, y=2056, action_type=ActionType.lift, next_position_wait_time=100).to_dict(),
                    #         Position(x=1003, y=671, action_type=ActionType.press, next_position_wait_time=10).to_dict(),
                    #         Position(x=1003, y=671, action_type=ActionType.lift, next_position_wait_time=100).to_dict(),
                    #         Position(x=456, y=674, action_type=ActionType.press, next_position_wait_time=10).to_dict(),
                    #         Position(x=456, y=674, action_type=ActionType.lift).to_dict(),
                    #     ],
                    # )
                    # await sleep(5)
                    # await click(
                    #     [pad_code],
                    #     [
                    #         Position(x=1003, y=671, action_type=ActionType.press, next_position_wait_time=10).to_dict(),
                    #         Position(x=1003, y=671, action_type=ActionType.lift, next_position_wait_time=2000).to_dict(),
                    #         Position(x=456, y=674, action_type=ActionType.press, next_position_wait_time=10).to_dict(),
                    #         Position(x=456, y=674, action_type=ActionType.lift).to_dict(),
                    #     ],
                    # )
                    logger.success(f"{pad_code}: 启动app成功")
                    await update_cloud_status(pad_code=pad_code, current_status="app启动成功")
                    break
            total_try_count += 1
    except IndexError:
        app_result: Any = await start_app(pad_code_list=[pad_code], pkg_name=package_name)
        while total_try_count < 6:
            taskid = app_result["data"][0]["taskId"]
            match await check_padTaskDetail([taskid]):
                case -1:
                    logger.warning(f"{pad_code}: 正在一键新机")
                    await task_manager.cancel_timeout_task_only(pad_code)
                    template_id = random.choice(config.TEMPLE_IDS)
                    await update_cloud_status(
                        pad_code, number_of_run=1, temple_id=template_id,
                        current_status="正在一键新机中", num_other_error=1
                    )
                    await replace_pad([pad_code], template_id=template_id)
                    break
                case 0:
                    logger.info(f"{pad_code}: 启动app中...")
                    await update_cloud_status(pad_code=pad_code, current_status="启动app中...")
                    await asyncio.sleep(2)
                case 1:
                    logger.success(f"{pad_code}: 启动app成功")
                    await update_cloud_status(pad_code=pad_code, current_status="启动app成功")
                    break
            total_try_count += 1


async def install_app_task(pad_code_str, task_manager):
    """启动带超时的安装任务"""
    from app.services.app_installer import install_all_apps

    logger.success(f"{pad_code_str}: 准备启动安装任务")

    await task_manager.start_task_with_timeout(
        pad_code_str,
        install_all_apps(pad_code_str, config, task_manager),
        timeout_seconds=config.get_timeout("global") * 60,
    )