import asyncio
import random
from collections import defaultdict
from enum import Enum
from typing import Any

from loguru import logger

from app.dependencies.utils import get_cloud_file_task_info, get_app_install_info, open_root, reboot, install_app, \
    replace_pad
from config import clash_install_url, script_install_url, temple_id_list, pkg_name


class TaskStatus(Enum):
    SUCCESS = "应用安装成功"
    DOWNLOAD_FAILED = "文件下载失败 请求被中断，请重试"
    TIMEOUT_OFFLINE = "任务已超时，当前设备状态为离线状态。"

class TaskManager:
    def __init__(self):
        self._operations = defaultdict(lambda: Any)
        self._lock = asyncio.Lock()

    async def add_task(self, pad_code: str, task: asyncio.Task) -> None:
        async with self._lock:
            self._operations[pad_code] = task

    async def remove_task(self, pad_code: str) -> None:
        async with self._lock:
            task = self._operations.get(pad_code)
            if task is not None:
                logger.success("移除任务成功")
                task.cancel()
                del self._operations[pad_code]

    async def get_task(self, pad_code: str) -> asyncio.Task:
        async with self._lock:
            return self._operations.get(pad_code)

    @staticmethod
    async def handle_install_result(result, task_type) -> bool:
        if task_type.lower() == "script":
            logger.info(f'{task_type}安装成功')
            app_install_result : Any = await get_app_install_info([result["data"][0]["padCode"]], "Clash for Android")
            if len(app_install_result["data"][0]["apps"]) == 2:
                logger.success("真安装成功")
                root_result = await open_root(pad_code_list=[result["data"][0]["padCode"]], pkg_name=pkg_name)
                logger.info(root_result)
                logger.info("开始重启")
                reboot_result = await reboot(pad_code_list=[result["data"][0]["padCode"]])
                logger.info(reboot_result)
                return True

            elif len(app_install_result["data"][0]["apps"]) == 0:
                logger.error("假安装成功，重新安装")
                clash_result = await install_app(pad_code_list=[result["data"][0]["padCode"]],
                                                 app_url=clash_install_url)
                logger.info(clash_result)
                script_result = await install_app(pad_code_list=[result["data"][0]["padCode"]],
                                                  app_url=script_install_url)
                logger.info(script_result)
                await asyncio.sleep(10)
                return False

            elif len(app_install_result["data"][0]["apps"]) == 1:
                app_result = app_install_result["data"][0]["apps"]
                logger.error(f"安装成功一个:{app_result[0]}")
                await install_app(pad_code_list=[result["data"][0]["padCode"]],app_url=clash_install_url)
                await asyncio.sleep(10)
                return False


        elif task_type.lower() == "clash":
            logger.info(f"{task_type}安装成功")
            app_install_result = await get_app_install_info([result["data"][0]["padCode"]], "Clash for Android")
            if len(app_install_result["data"][0]["apps"]) == 2:
                logger.success("真安装成功")
                return True
            elif len(app_install_result["data"][0]["apps"]) == 0:
                logger.error("假安装成功，重新安装")
                clash_result = await install_app(pad_code_list=[result["data"][0]["padCode"]],
                                                 app_url=clash_install_url)
                logger.info(clash_result)
                script_result = await install_app(pad_code_list=[result["data"][0]["padCode"]],
                                                  app_url=script_install_url)
                logger.info(script_result)
                await asyncio.sleep(10)
                return False

            elif len(app_install_result["data"][0]["apps"]) == 1:
                app_result = app_install_result["data"][0]["apps"]
                logger.info(f"安装成功一个:{app_result[0]}")
                await install_app(pad_code_list=[result["data"][0]["padCode"]],app_url=script_install_url)
                await asyncio.sleep(10)
                return False

        return False

    async def check_task_status(self, task_id, task_type, timeout_seconds: int = 120, retry_interval: int = 10):
        app_url = clash_install_url if task_type.lower() == "clash" else script_install_url
        other_app_url = script_install_url if task_type.lower() == "clash" else clash_install_url
        try:
            async with asyncio.timeout(timeout_seconds):
                while True:
                    try:
                        result: Any = await get_cloud_file_task_info([str(task_id)])
                        logger.info(f"{task_type} task {task_id}: {result}")
                        error_msg = result["data"][0]["errorMsg"]
                        if error_msg == TaskStatus.SUCCESS.value:
                            if await self.handle_install_result(result, task_type):
                                break
                        elif error_msg == TaskStatus.DOWNLOAD_FAILED.value:
                            logger.error(f"{task_type}下载失败")
                            result = await install_app(pad_code_list=[result["data"][0]["padCode"]], app_url=app_url)
                            logger.info(result)
                        elif error_msg == TaskStatus.TIMEOUT_OFFLINE.value:
                            logger.error("设备离线，停止安装")
                            break
                        await asyncio.sleep(retry_interval)
                    except Exception as e:
                        logger.error(f"检查任务状态失败: {e}, 任务ID: {task_id}")
                        await asyncio.sleep(retry_interval)
        except asyncio.TimeoutError:
            logger.info(f"{task_type} task {task_id}: 安装超时后 {timeout_seconds} seconds")
            if 'result' not in locals():
                logger.error(f"任务 {task_id} 在首次检查前超时")
                return
            try:
                pad_code = result["data"][0]["padCode"]
                await self.remove_task(pad_code)
                replace_result = await replace_pad([pad_code], template_id=random.choice(temple_id_list))
                logger.error(replace_result)
                logger.error("因为长时间安装不上，已移除任务")
            except (KeyError, IndexError) as e:
                logger.error(f"无法处理超时：{e}，任务ID：{task_id}")

    async def handle_timeout(self, pad_code_str: str, timeout_seconds: int = 360):
        logger.success("全局超时任务开启成功")
        try:
            await asyncio.sleep(timeout_seconds)
            if await self.get_task(pad_code_str) is None:
                logger.info(f"标识符 {pad_code_str} 的任务已不存在，无需替换")
                return
            logger.info(f"标识符超时: {pad_code_str}")
            result = await replace_pad([pad_code_str], template_id=random.choice(temple_id_list))
            logger.info(f"正在一键新机: {result}")
            await self.remove_task(pad_code_str)
        except asyncio.CancelledError:
            logger.error(f"标识符的超时任务: {pad_code_str} 被取消了.")