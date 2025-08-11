# 定义任务状态枚举
from enum import IntEnum

from loguru import logger

from app.services.every_task import set_phone_state, install_app_task


class TaskStatus(IntEnum):
    ALL_FAILED = -1  # 全失败
    CANCELLED = -3   # 取消
    TIMEOUT = -4     # 超时
    PENDING = 1      # 待执行
    RUNNING = 2      # 执行中
    COMPLETED = 3    # 完成


def process_task_status(data):
    task_status = data.get("taskStatus")
    try:
        match TaskStatus(task_status):
            case TaskStatus.ALL_FAILED:
                logger.error("任务全失败")
            case TaskStatus.CANCELLED:
                logger.warning("任务取消")
            case TaskStatus.TIMEOUT:
                logger.warning("任务超时")
            case TaskStatus.PENDING:
                logger.warning("任务待执行")
            case TaskStatus.RUNNING:
                logger.info("任务执行中")
            case TaskStatus.COMPLETED:
                logger.info("任务执行完成")
            case _:
                logger.error(f"未知任务状态: {task_status}")
    except ValueError:
        logger.error(f"无效的任务状态值: {task_status}")


def app_start_task_status(data):
    task_status = data.get("taskStatus")
    match TaskStatus(task_status):
        case TaskStatus.COMPLETED:
            logger.success("应用启动成功回调")
            logger.warning(data)




def app_install_task_status(data):
    task_status = data.get("taskStatus")
    pad_code = data["apps"]["padCode"]
    match TaskStatus(task_status):
        case TaskStatus.COMPLETED:
            logger.success(f'安装成功接口回调 {pad_code}: 安装成功')


def app_uninstall_task_status(data):
    task_status = data.get("taskStatus")
    pad_code = data["apps"]["padCode"]
    match TaskStatus(task_status):
        case TaskStatus.COMPLETED:
            logger.success(f"{pad_code}: 卸载成功")


async def reboot_task_status(data, current_proxy, package_name):
    task_status = data.get("taskStatus")
    pad_code = data.get("padCode")
    try:
        match TaskStatus(task_status):
            case TaskStatus.ALL_FAILED:
                logger.error("任务全失败")
            case TaskStatus.CANCELLED:
                logger.warning("任务取消")
            case TaskStatus.TIMEOUT:
                logger.warning("任务超时")
            case TaskStatus.PENDING:
                logger.warning("任务待执行")
            case TaskStatus.RUNNING:
                logger.info("任务执行中")
            case TaskStatus.COMPLETED:
                logger.success(f"{pad_code}: 重启成功")
                await set_phone_state(current_proxy, package_name, pad_code)

            case _:
                logger.error(f"未知任务状态: {task_status}")

    except ValueError:
        logger.error(f"无效的任务状态值: {task_status}")



async def replace_pad_stak_status(data, task_manager):
    task_status = data.get("taskStatus")
    pad_code = data.get("padCode")
    match TaskStatus(task_status):
        case TaskStatus.COMPLETED:
            await install_app_task(pad_code_str=pad_code, task_manager=task_manager)

        case TaskStatus.RUNNING:
            logger.info(f"{pad_code}: 一键新机执行中")


        case TaskStatus.PENDING:
            logger.info(f"{pad_code}: 一键新机等待中")


        case TaskStatus.CANCELLED:
            logger.info(f"{pad_code}: 一键新机任务取消")


        case TaskStatus.TIMEOUT:
            logger.info(f"{pad_code}: 一键新机任务超时")


        case TaskStatus.ALL_FAILED:
            logger.info(f"{pad_code}: 一键新机任务失败")



def adb_call_task_status(data):
    task_status = data.get("taskStatus")
    pad_code = data.get("padCode")
    match TaskStatus(task_status):
        case TaskStatus.COMPLETED:
            logger.success(f"{pad_code}: 调用adb成功")

        case TaskStatus.RUNNING:
            logger.success(f"{pad_code}: 调用adb中")

        case TaskStatus.PENDING:
            logger.success(f"{pad_code}: 准备调用adb")

        case TaskStatus.CANCELLED:
            logger.success(f"{pad_code}: adb调用任务关闭")

        case TaskStatus.TIMEOUT:
            logger.warning(f"{pad_code}: adb调用超时")
