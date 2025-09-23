import asyncio
import random
from asyncio import sleep
from typing import Any

from loguru import logger

from app.config import clash_install_url, script_install_url, temple_id_list, global_timeout_minute, chrome_install_url, \
    script2_install_url
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
                    await update_cloud_status(pad_code=pad_code, current_status="启动任务正在一键新机")
                    await task_manager.cancel_timeout_task_only(pad_code)
                    template_id=random.choice(temple_id_list)
                    await update_cloud_status(pad_code, number_of_run=1, temple_id=template_id, current_status="正在一键新机中")
                    await replace_pad([pad_code], template_id=template_id)
                    break

                case 0:
                    logger.info(f"{pad_code}: 启动app中...")
                    await update_cloud_status(pad_code=pad_code, current_status="启动app中...")
                    await asyncio.sleep(2)

                case 1:
                    await sleep(5)
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
                    await sleep(5)
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
                            next_position_wait_time=2000
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
                    await update_cloud_status(pad_code=pad_code, current_status="启动app成功")
                    break
            total_try_count += 1

    except IndexError:
        while total_try_count < 6:
            app_result: Any = await start_app(pad_code_list=[pad_code], pkg_name=package_name)
            taskid= app_result["data"][0]["taskId"]
            match await check_padTaskDetail([taskid]):
                case -1:
                    logger.warning(f"{pad_code}: 正在一键新机")
                    await task_manager.cancel_timeout_task_only(pad_code)
                    template_id=random.choice(temple_id_list)
                    await update_cloud_status(pad_code, number_of_run=1, temple_id=template_id, current_status="正在一键新机中")
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


async def install_app_main_logic(pad_code_str: str, task_manager):
    """主要的应用安装逻辑"""
    script_md5_list: Any = script_install_url.split("/")
    script_md5 = script_md5_list[-1].replace(".apk", "")
    clash_md5_list: Any = clash_install_url.split("/")
    clash_md5 = clash_md5_list[-1].replace(".apk", "")
    chrome_md5_list: Any = chrome_install_url.split("/")
    chrome_md5 = chrome_md5_list[-1].replace(".apk", "")
    script2_md5_list: Any = script2_install_url.split("/")
    script2_md5 = script2_md5_list[-1].replace(".apk", "")

    logger.success(f'{pad_code_str}: 一键新机成功，开始安装应用')
    await update_cloud_status(pad_code=pad_code_str, current_status="一键新机成功，开始安装应用")

    # 开始安装
    clash_install_result: Any = await install_app(
        pad_code_list=[pad_code_str],
        app_url=clash_install_url,
        md5=clash_md5
    )
    logger.info(f"Clash 安装结果: {clash_install_result['msg']}")

    script_install_result: Any = await install_app(
        pad_code_list=[pad_code_str],
        app_url=script_install_url,
        md5=script_md5
    )
    logger.info(f"脚本安装结果: {script_install_result['msg']}")

    chrome_install_result: Any = await install_app(
        pad_code_list=[pad_code_str],
        app_url=chrome_install_url,
        md5=chrome_md5
    )


    script2_install_result: Any = await install_app(
        pad_code_list=[pad_code_str],
        app_url=script2_install_url,
        md5=script2_md5
    )

    # 创建检查任务
    clash_task = asyncio.create_task(
        task_manager.check_task_status(
            clash_install_result["data"][0]["taskId"],
            "Clash",
            task_manager=task_manager
        )
    )
    script_task = asyncio.create_task(
        task_manager.check_task_status(
            script_install_result["data"][0]["taskId"],
            "Script",
            task_manager=task_manager
        )
    )

    script2_task = asyncio.create_task(
        task_manager.check_task_status(
            script2_install_result["data"][0]["taskId"],
            "Script2",
            task_manager=task_manager
        )
    )

    chrome_task = asyncio.create_task(
        task_manager.check_task_status(
            chrome_install_result["data"][0]["taskId"],
            "Chrome",
            task_manager=task_manager
        )
    )

    try:
        await asyncio.gather(clash_task, script_task, chrome_task, script2_task)
        logger.success(f"{pad_code_str}: 所有应用安装完成")
    except asyncio.CancelledError:
        logger.info(f"安装任务被取消: {pad_code_str}")
        # 确保取消所有子任务
        if not clash_task.done():
            clash_task.cancel()
        if not script_task.done():
            script_task.cancel()
        if not chrome_task.done():
            chrome_task.cancel()
        if not script2_task.done():
            script2_task.cancel()
        raise


async def install_app_task(pad_code_str, task_manager):
    """启动带超时的安装任务"""
    logger.success(f'{pad_code_str}: 准备启动安装任务')

    # 使用新的带超时任务管理
    await task_manager.start_task_with_timeout(
        pad_code_str,
        install_app_main_logic(pad_code_str, task_manager),
        timeout_seconds=global_timeout_minute * 60
    )