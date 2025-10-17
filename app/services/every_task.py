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

    # 配置参数
    MAX_START_ATTEMPTS: Any = 3  # 最大启动尝试次数
    MAX_CHECK_ATTEMPTS = 6  # 最大检查尝试次数
    CHECK_INTERVAL = 2  # 检查间隔（秒）

    for attempt in range(MAX_START_ATTEMPTS):
        try:
            logger.info(f"{pad_code}: 第 {attempt + 1}/{MAX_START_ATTEMPTS} 次尝试启动")

            # 启动应用
            app_result = await asyncio.wait_for(
                start_app(pad_code_list=[pad_code], pkg_name=package_name),
                timeout=30  # 30秒超时
            )

            # 验证返回结果
            if not isinstance(app_result, dict):
                logger.error(f"{pad_code}: 启动返回结果格式错误: {type(app_result)}")
                await asyncio.sleep(5)
                continue

            if app_result.get("msg") != "success":
                error_msg = app_result.get("msg", "未知错误")
                logger.warning(f"{pad_code}: 启动失败 - {error_msg}")
                await update_cloud_status(pad_code=pad_code, current_status=f"启动失败: {error_msg}")
                await asyncio.sleep(5)
                continue

            # 获取任务ID
            data: Any = app_result.get("data")
            if not data or not isinstance(data, list) or len(data) == 0:
                logger.error(f"{pad_code}: 返回数据为空或格式错误")
                await asyncio.sleep(5)
                continue

            taskid = data[0].get("taskId")
            if not taskid:
                logger.error(f"{pad_code}: 未获取到taskId")
                await asyncio.sleep(5)
                continue

            logger.info(f"{pad_code}: 获取到任务ID: {taskid}")

            # 检查任务状态
            check_success = await _check_task_status(
                pad_code=pad_code,
                taskid=taskid,
                task_manager=task_manager,
                max_attempts=MAX_CHECK_ATTEMPTS,
                check_interval=CHECK_INTERVAL
            )

            if check_success:
                return True

            # 如果检查失败但不是一键新机的情况，继续重试
            logger.warning(f"{pad_code}: 任务检查未成功，准备重试")
            await asyncio.sleep(5)

        except asyncio.TimeoutError:
            logger.error(f"{pad_code}: 启动app超时 (第 {attempt + 1} 次)")
            await update_cloud_status(pad_code=pad_code, current_status="启动超时")
            await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"{pad_code}: 启动过程发生异常 (第 {attempt + 1} 次): {str(e)}")
            await update_cloud_status(pad_code=pad_code, current_status=f"启动异常: {str(e)}")
            await asyncio.sleep(5)

    # 所有尝试都失败
    logger.error(f"{pad_code}: 启动app失败，已达到最大重试次数")
    await update_cloud_status(pad_code=pad_code, current_status="启动失败（达到最大重试次数）")
    return False


async def _check_task_status(pad_code, taskid, task_manager, max_attempts, check_interval):
    for check_count in range(max_attempts):
        try:
            logger.info(f"{pad_code}: 第 {check_count + 1}/{max_attempts} 次检查任务状态")

            status = await asyncio.wait_for(
                check_padTaskDetail([taskid]),
                timeout=10  # 10秒超时
            )

            match status:
                case -1:
                    logger.warning(f"{pad_code}: 启动任务正在一键新机")
                    await update_cloud_status(pad_code=pad_code, current_status="启动任务正在一键新机")
                    await task_manager.cancel_timeout_task_only(pad_code)

                    if pad_code in config.PAD_CODES:
                        try:
                            template_id = random.choice(config.TEMPLE_IDS)
                            logger.info(f"{pad_code}: 选择模板ID: {template_id}")

                            await update_cloud_status(
                                pad_code,
                                number_of_run=1,
                                temple_id=template_id,
                                current_status="正在一键新机中",
                                num_other_error=1
                            )

                            await replace_pad([pad_code], template_id=template_id)
                            logger.info(f"{pad_code}: 一键新机操作已触发")
                        except Exception as e:
                            logger.error(f"{pad_code}: 一键新机操作失败: {str(e)}")

                    return False  # 需要一键新机，不算成功

                case 0:  # 进行中
                    logger.info(f"{pad_code}: 启动app中...")
                    await update_cloud_status(pad_code=pad_code, current_status="启动app中...")
                    await asyncio.sleep(check_interval)

                case 1:  # 成功
                    logger.success(f"{pad_code}: 启动app成功")
                    await update_cloud_status(pad_code=pad_code, current_status="app启动成功")
                    return True

                case _:  # 未知状态
                    logger.warning(f"{pad_code}: 未知任务状态: {status}")
                    await update_cloud_status(pad_code=pad_code, current_status=f"未知状态: {status}")
                    await asyncio.sleep(check_interval)

        except asyncio.TimeoutError:
            logger.warning(f"{pad_code}: 检查任务状态超时 (第 {check_count + 1} 次)")
            await asyncio.sleep(check_interval)

        except Exception as e:
            logger.error(f"{pad_code}: 检查任务状态异常 (第 {check_count + 1} 次): {str(e)}")
            await asyncio.sleep(check_interval)

    # 达到最大检查次数
    logger.warning(f"{pad_code}: 任务状态检查超时，已达到最大检查次数")
    await update_cloud_status(pad_code=pad_code, current_status="任务检查超时")
    return False


async def install_app_task(pad_code_str, task_manager):
    """启动带超时的安装任务"""
    from app.services.app_installer import install_all_apps

    logger.success(f"{pad_code_str}: 准备启动安装任务")

    await task_manager.start_task_with_timeout(
        pad_code_str,
        install_all_apps(pad_code_str, config, task_manager),
        timeout_seconds=config.get_timeout("global") * 60,
    )