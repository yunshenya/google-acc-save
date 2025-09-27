import asyncio
import random
from enum import IntEnum
from typing import Any

from app.config import config
from app.curd.status import update_cloud_status, set_proxy_status
from app.dependencies.countries import manager
from app.dependencies.utils import get_cloud_file_task_info, replace_pad
from app.services.every_task import start_app_state, install_app_task
from app.services.logger import task_logger


class TaskStatus(IntEnum):
    ALL_FAILED = -1  # 全失败
    CANCELLED = -3  # 取消
    TIMEOUT = -4  # 超时
    PENDING = 1  # 待执行
    RUNNING = 2  # 执行中
    COMPLETED = 3  # 完成


async def fileUpdate_task_status(data):
    """文件更新任务状态处理"""
    pad_code = data.get("padCode")
    task_id = data.get("taskId")
    task_logger.info(f"{pad_code}: 文件更新任务状态回调，任务ID: {task_id}")

    try:
        result = await get_cloud_file_task_info([task_id])
        error_message: Any = result["data"][0]["errorMsg"]
        if error_message:
            task_logger.info(f"{pad_code}: 文件更新任务消息 - {error_message}")
    except Exception as e:
        task_logger.error(f"{pad_code}: 获取文件更新任务信息失败 - {e}")


def app_start_task_status(data):
    """应用启动任务状态处理"""
    task_status = data.get("taskStatus")
    pad_code = data.get("padCode")

    try:
        match TaskStatus(task_status):
            case TaskStatus.COMPLETED:
                task_logger.success(f"{pad_code}: 应用启动成功回调")

            case TaskStatus.RUNNING:
                task_logger.info(f"{pad_code}: 应用启动中")

            case TaskStatus.PENDING:
                task_logger.info(f"{pad_code}: 应用启动等待中")

            case TaskStatus.CANCELLED:
                task_logger.warning(f"{pad_code}: 应用启动任务被取消")

            case TaskStatus.TIMEOUT:
                task_logger.warning(f"{pad_code}: 应用启动超时")

            case TaskStatus.ALL_FAILED:
                task_logger.error(f"{pad_code}: 应用启动失败")

            case _:
                task_logger.warning(f"{pad_code}: 应用启动未知状态 - {task_status}")
    except ValueError:
        task_logger.error(f"{pad_code}: 应用启动无效状态值 - {task_status}")


def app_install_task_status(data):
    """应用安装任务状态处理"""
    task_status = data.get("taskStatus")
    pad_code = data["apps"]["padCode"]
    app_name = data["apps"].get("appName", "未知应用")

    try:
        match TaskStatus(task_status):
            case TaskStatus.COMPLETED:
                task_logger.success(f'{pad_code}: 应用 {app_name} 安装成功')

            case TaskStatus.RUNNING:
                task_logger.info(f"{pad_code}: 应用 {app_name} 安装中")

            case TaskStatus.PENDING:
                task_logger.info(f"{pad_code}: 应用 {app_name} 准备安装")

            case TaskStatus.ALL_FAILED:
                task_logger.error(f"{pad_code}: 应用 {app_name} 安装失败")

            case TaskStatus.TIMEOUT:
                task_logger.warning(f"{pad_code}: 应用 {app_name} 安装超时")

            case TaskStatus.CANCELLED:
                task_logger.warning(f"{pad_code}: 应用 {app_name} 安装任务取消")

            case _:
                task_logger.warning(f"{pad_code}: 应用 {app_name} 安装未知状态 - {task_status}")
    except ValueError:
        task_logger.error(f"{pad_code}: 应用 {app_name} 安装无效状态值 - {task_status}")


def app_uninstall_task_status(data):
    """应用卸载任务状态处理"""
    task_status = data.get("taskStatus")
    pad_code = data["apps"]["padCode"]
    app_name = data["apps"].get("appName", "未知应用")

    try:
        match TaskStatus(task_status):
            case TaskStatus.COMPLETED:
                task_logger.success(f"{pad_code}: 应用 {app_name} 卸载成功")

            case TaskStatus.RUNNING:
                task_logger.info(f"{pad_code}: 应用 {app_name} 卸载中")

            case TaskStatus.PENDING:
                task_logger.info(f"{pad_code}: 应用 {app_name} 准备卸载")

            case TaskStatus.ALL_FAILED:
                task_logger.error(f"{pad_code}: 应用 {app_name} 卸载失败")

            case TaskStatus.TIMEOUT:
                task_logger.warning(f"{pad_code}: 应用 {app_name} 卸载超时")

            case TaskStatus.CANCELLED:
                task_logger.warning(f"{pad_code}: 应用 {app_name} 卸载任务取消")

            case _:
                task_logger.warning(f"{pad_code}: 应用 {app_name} 卸载未知状态 - {task_status}")
    except ValueError:
        task_logger.error(f"{pad_code}: 应用 {app_name} 卸载无效状态值 - {task_status}")


async def reboot_task_status(data, package_name, task_manager):
    """重启任务状态处理"""
    task_status = data.get("taskStatus")
    pad_code = data.get("padCode")

    task_logger.info(f"{pad_code}: 重启任务状态回调 - 状态: {task_status}")

    try:
        match TaskStatus(task_status):
            case TaskStatus.ALL_FAILED:
                task_logger.error(f"{pad_code}: 重启任务全失败")
                await update_cloud_status(pad_code=pad_code, current_status="重启任务全失败")

            case TaskStatus.CANCELLED:
                task_logger.warning(f"{pad_code}: 重启任务取消")
                await update_cloud_status(pad_code=pad_code, current_status="重启任务取消")

            case TaskStatus.TIMEOUT:
                task_logger.warning(f"{pad_code}: 重启任务超时")
                await update_cloud_status(pad_code=pad_code, current_status="重启任务超时")

            case TaskStatus.PENDING:
                task_logger.info(f"{pad_code}: 重启任务待执行")
                await update_cloud_status(pad_code=pad_code, current_status="重启任务待执行")

            case TaskStatus.RUNNING:
                task_logger.info(f"{pad_code}: 重启任务执行中")
                await update_cloud_status(pad_code=pad_code, current_status="重启任务执行中")

            case TaskStatus.COMPLETED:
                task_logger.success(f"{pad_code}: 重启成功，等待15秒后启动应用")
                await update_cloud_status(pad_code=pad_code, current_status="重启成功，准备启动应用")
                await asyncio.sleep(15)
                await start_app_state(package_name, pad_code, task_manager)

            case _:
                task_logger.error(f"{pad_code}: 重启未知任务状态: {task_status}")

    except ValueError:
        task_logger.error(f"{pad_code}: 重启无效的任务状态值: {task_status}")
    except Exception as e:
        task_logger.error(f"{pad_code}: 处理重启任务状态时出错: {e}")


def app_reboot_task_status(data):
    """应用重启任务状态处理"""
    pad_code = data.get("padCode")
    task_status = data.get("taskStatus")

    try:
        match TaskStatus(task_status):
            case TaskStatus.COMPLETED:
                task_logger.success(f"{pad_code}: 应用重启成功")

            case TaskStatus.RUNNING:
                task_logger.info(f"{pad_code}: 应用重启中")

            case TaskStatus.PENDING:
                task_logger.info(f"{pad_code}: 应用重启等待中")

            case TaskStatus.ALL_FAILED:
                task_logger.error(f"{pad_code}: 应用重启失败")

            case TaskStatus.TIMEOUT:
                task_logger.warning(f"{pad_code}: 应用重启超时")

            case TaskStatus.CANCELLED:
                task_logger.warning(f"{pad_code}: 应用重启任务取消")

            case _:
                task_logger.warning(f"{pad_code}: 应用重启未知状态 - {task_status}")
    except ValueError:
        task_logger.error(f"{pad_code}: 应用重启无效状态值 - {task_status}")


async def replace_pad_stak_status(data, task_manager):
    """一键新机任务状态处理"""
    task_status = data.get("taskStatus")
    pad_code = data.get("padCode")

    task_logger.info(f"{pad_code}: 一键新机任务状态 - {task_status}")

    try:
        match TaskStatus(task_status):
            case TaskStatus.COMPLETED:
                task_logger.success(f"{pad_code}: 一键新机完成，开始安装应用")
                await update_cloud_status(pad_code=pad_code, current_status="一键新机完成，正在安装app")
                try:
                    await install_app_task(pad_code_str=pad_code, task_manager=task_manager)
                except Exception as e:
                    task_logger.error(f"{pad_code}: 启动安装任务失败: {e}")

            case TaskStatus.RUNNING:
                task_logger.info(f"{pad_code}: 一键新机执行中")
                await update_cloud_status(pad_code=pad_code, current_status="一键新机执行中")

            case TaskStatus.PENDING:
                task_logger.info(f"{pad_code}: 一键新机等待中")
                await update_cloud_status(pad_code=pad_code, current_status="一键新机等待中")

            case TaskStatus.CANCELLED:
                task_logger.warning(f"{pad_code}: 一键新机任务取消")
                await update_cloud_status(pad_code=pad_code, current_status="一键新机任务取消")

            case TaskStatus.TIMEOUT:
                task_logger.warning(f"{pad_code}: 一键新机任务超时")
                await update_cloud_status(pad_code=pad_code, current_status="一键新机任务超时")

            case TaskStatus.ALL_FAILED:
                task_logger.error(f"{pad_code}: 一键新机任务失败，准备重新一键新机")
                await update_cloud_status(pad_code=pad_code, current_status="一键新机任务失败，准备重试")

                # 一键新机失败时的处理逻辑
                template_id = random.choice(config.TEMPLE_IDS)
                default_proxy: Any = manager.get_proxy_countries()
                await set_proxy_status(pad_code, random.choice(default_proxy), number_of_run=1)
                await update_cloud_status(pad_code, temple_id=template_id,
                                          current_status="一键新机失败后重试中")
                await replace_pad([pad_code], template_id=template_id)

            case _:
                task_logger.warning(f"{pad_code}: 一键新机未知状态 - {task_status}")

    except ValueError:
        task_logger.error(f"{pad_code}: 一键新机无效状态值 - {task_status}")
    except Exception as e:
        task_logger.error(f"{pad_code}: 处理一键新机任务状态时出错: {e}")


async def adb_call_task_status(data):
    """ADB调用任务状态处理"""
    task_status = data.get("taskStatus")
    pad_code = data.get("padCode")

    task_logger.info(f"{pad_code}: ADB调用任务状态 - {task_status}")

    try:
        match TaskStatus(task_status):
            case TaskStatus.COMPLETED:
                task_logger.success(f"{pad_code}: 获取root权限成功")
                await update_cloud_status(pad_code=pad_code, current_status="获取root权限成功")

            case TaskStatus.RUNNING:
                task_logger.info(f"{pad_code}: 调用adb中")
                await update_cloud_status(pad_code=pad_code, current_status="调用adb中")

            case TaskStatus.PENDING:
                task_logger.info(f"{pad_code}: 准备调用adb")
                await update_cloud_status(pad_code=pad_code, current_status="准备调用adb")

            case TaskStatus.CANCELLED:
                task_logger.warning(f"{pad_code}: adb调用任务取消")
                await update_cloud_status(pad_code=pad_code, current_status="adb调用任务取消")

            case TaskStatus.TIMEOUT:
                task_logger.warning(f"{pad_code}: adb调用超时")
                await update_cloud_status(pad_code=pad_code, current_status="adb调用超时")

            case TaskStatus.ALL_FAILED:
                task_logger.error(f"{pad_code}: adb调用失败")
                await update_cloud_status(pad_code=pad_code, current_status="adb调用失败")

            case _:
                task_logger.warning(f"{pad_code}: ADB调用未知状态 - {task_status}")

    except ValueError:
        task_logger.error(f"{pad_code}: ADB调用无效状态值 - {task_status}")
    except Exception as e:
        task_logger.error(f"{pad_code}: 处理ADB调用任务状态时出错: {e}")