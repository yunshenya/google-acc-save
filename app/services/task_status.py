# 定义任务状态枚举
import asyncio
from enum import IntEnum
from typing import Any

from loguru import logger

from app.curd.status import update_cloud_status
from app.dependencies.utils import get_cloud_file_task_info
from app.services.every_task import start_app_state, install_app_task


class TaskStatus(IntEnum):
    ALL_FAILED = -1  # 全失败
    CANCELLED = -3   # 取消
    TIMEOUT = -4     # 超时
    PENDING = 1      # 待执行
    RUNNING = 2      # 执行中
    COMPLETED = 3    # 完成


async def fileUpdate_task_status(data):
    pad_code = data.get("padCode")
    task_id = data.get("taskId")
    result = await get_cloud_file_task_info([task_id])
    error_message: Any = result["data"][0]["errorMsg"]
    if error_message:
        logger.info(f"{pad_code}: {error_message}")


def app_start_task_status(data):
    task_status = data.get("taskStatus")
    pad_code = data.get("padCode")
    match TaskStatus(task_status):
        case TaskStatus.COMPLETED:
            logger.success(f"{pad_code}: 应用启动成功回调")

        case _:
            logger.warning(data)




def app_install_task_status(data):
    task_status = data.get("taskStatus")
    pad_code = data["apps"]["padCode"]
    match TaskStatus(task_status):
        case TaskStatus.COMPLETED:
            logger.success(f'安装成功接口回调 {pad_code}: 安装成功')

        case TaskStatus.RUNNING:
            logger.info(f"{pad_code}: 安装中")

        case TaskStatus.PENDING:
            logger.info(f"{pad_code}: 正在准备安装")

        case TaskStatus.ALL_FAILED:
            logger.error(f"{pad_code}: 安装失败")

        case TaskStatus.TIMEOUT:
            logger.warning(f"{pad_code}: 安装超时")

        case TaskStatus.CANCELLED:
            logger.warning(f"{pad_code}: 安装任务关闭")


def app_uninstall_task_status(data):
    task_status = data.get("taskStatus")
    pad_code = data["apps"]["padCode"]
    match TaskStatus(task_status):
        case TaskStatus.COMPLETED:
            logger.success(f"{pad_code}: 卸载成功")


async def reboot_task_status(data, package_name, task_manager):
    task_status = data.get("taskStatus")
    pad_code = data.get("padCode")
    try:
        match TaskStatus(task_status):
            case TaskStatus.ALL_FAILED:
                logger.error(f"{pad_code}: 重启任务全失败")
                await update_cloud_status(pad_code=pad_code, current_status="重启任务全失败")

            case TaskStatus.CANCELLED:
                logger.warning(f"{pad_code}: 重启任务取消")
                await update_cloud_status(pad_code=pad_code, current_status="重启任务取消")

            case TaskStatus.TIMEOUT:
                logger.warning(f"{pad_code}: 重启任务超时")
                await update_cloud_status(pad_code=pad_code, current_status="重启任务超时")

            case TaskStatus.PENDING:
                logger.warning(f"{pad_code}: 重启任务待执行")
                await update_cloud_status(pad_code=pad_code, current_status="重启任务待执行")

            case TaskStatus.RUNNING:
                logger.info(f"{pad_code}: 重启任务执行中")
                await update_cloud_status(pad_code=pad_code, current_status="重启任务执行中")
            case TaskStatus.COMPLETED:
                logger.success(f"{pad_code}: 重启成功")
                await update_cloud_status(pad_code=pad_code, current_status="重启成功")
                await asyncio.sleep(10)
                await start_app_state(package_name, pad_code, task_manager)

            case _:
                logger.error(f"未知任务状态: {task_status}")

    except ValueError:
        logger.error(f"无效的任务状态值: {task_status}")


def app_reboot_task_status(data):
    pad_code = data.get("padCode")
    task_status = data.get("taskStatus")
    match TaskStatus(task_status):
        case TaskStatus.COMPLETED:
            logger.success("应用重启成功")

        case _:
            logger.warning(f"{pad_code}: 未知重启id {task_status}")


async def replace_pad_stak_status(data, task_manager):
    task_status = data.get("taskStatus")
    pad_code = data.get("padCode")
    match TaskStatus(task_status):
        case TaskStatus.COMPLETED:
            await update_cloud_status(pad_code=pad_code, current_status= "正在安装app")
            await install_app_task(pad_code_str=pad_code, task_manager=task_manager)
        case TaskStatus.RUNNING:
            await update_cloud_status(pad_code=pad_code, current_status= "一键新机执行中")
            logger.info(f"{pad_code}: 一键新机执行中")

        case TaskStatus.PENDING:
            await update_cloud_status(pad_code=pad_code, current_status= "一键新机等待中")
            logger.info(f"{pad_code}: 一键新机等待中")


        case TaskStatus.CANCELLED:
            await update_cloud_status(pad_code=pad_code, current_status= "一键新机任务取消")
            logger.info(f"{pad_code}: 一键新机任务取消")


        case TaskStatus.TIMEOUT:
            await update_cloud_status(pad_code=pad_code, current_status= "一键新机任务超时")
            logger.info(f"{pad_code}: 一键新机任务超时")


        case TaskStatus.ALL_FAILED:
            await update_cloud_status(pad_code=pad_code, current_status= "一键新机任务失败")
            logger.info(f"{pad_code}: 一键新机任务失败")



async def adb_call_task_status(data):
    task_status = data.get("taskStatus")
    pad_code = data.get("padCode")
    match TaskStatus(task_status):
        case TaskStatus.COMPLETED:
            await update_cloud_status(pad_code=pad_code, current_status= "获取root权限成功")
            logger.success(f"{pad_code}: 获取root权限成功")

        case TaskStatus.RUNNING:
            await update_cloud_status(pad_code=pad_code, current_status= "调用adb中")
            logger.success(f"{pad_code}: 调用adb中")

        case TaskStatus.PENDING:
            await update_cloud_status(pad_code=pad_code, current_status= "准备调用adb")
            logger.success(f"{pad_code}: 准备调用adb")

        case TaskStatus.CANCELLED:
            await update_cloud_status(pad_code=pad_code, current_status= "adb调用任务关闭")
            logger.success(f"{pad_code}: adb调用任务关闭")

        case TaskStatus.TIMEOUT:
            await update_cloud_status(pad_code=pad_code, current_status= "adb调用超时")
            logger.warning(f"{pad_code}: adb调用超时")

        case TaskStatus.ALL_FAILED:
            await update_cloud_status(pad_code=pad_code, current_status= "adb调用失败")
            logger.error(f"{pad_code}: adb调用失败")
