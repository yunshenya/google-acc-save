import asyncio
import random
from collections import defaultdict
from enum import IntEnum
from typing import Any
from loguru import logger

from app.dependencies.utils import get_cloud_file_task_info, get_app_install_info, open_root, reboot, install_app, \
    replace_pad
from app.config import clash_install_url, script_install_url, temple_id_list, pkg_name, global_timeout_minute, \
    check_task_timeout_minute


class InstallTaskStatus(IntEnum):
    ALL_FAILED = -1
    SOME_FAILED = -2
    CANCEL= -3
    TIMEOUT = -4
    PENDING = 1
    RUNNING = 2
    COMPLETED = 3    # 完成

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
                task.cancel()
                del self._operations[pad_code]

    async def get_task(self, pad_code: str) -> asyncio.Task:
        async with self._lock:
            return self._operations.get(pad_code)

    @staticmethod
    async def handle_install_result(result, task_type) -> bool:
        script_md5 = script_install_url.split("/")[-1].replace(".apk", "")
        clash_md5 = clash_install_url.split("/")[-1].replace(".apk", "")
        pad_code = result["data"][0]["padCode"]
        if task_type.lower() == "script":
            logger.info(f'{task_type}安装成功')
            app_install_result : Any = await get_app_install_info([pad_code], "Clash for Android")
            if len(app_install_result["data"][0]["apps"]) == 2:
                logger.success(f"{pad_code}: 安装成功")
                await open_root(pad_code_list=[pad_code], pkg_name=pkg_name)
                logger.info(f"{pad_code}: 开始重启")
                await reboot(pad_code_list=[pad_code])
                return True

            elif len(app_install_result["data"][0]["apps"]) == 0:
                logger.warning(f"{pad_code}: 重新安装")
                await install_app(pad_code_list=[pad_code],
                                                 app_url=clash_install_url, md5=clash_md5)
                await install_app(pad_code_list=[pad_code],
                                                  app_url=script_install_url, md5=script_md5)
                await asyncio.sleep(10)
                return False

            elif len(app_install_result["data"][0]["apps"]) == 1:
                app_result = app_install_result["data"][0]["apps"]
                logger.warning(f"安装成功一个:{app_result[0]['appName']}")
                await install_app(pad_code_list=[pad_code],app_url=clash_install_url, md5=clash_md5)
                await asyncio.sleep(10)
                return False


        elif task_type.lower() == "clash":
            logger.info(f"{task_type}安装成功")
            app_install_result = await get_app_install_info([pad_code], "Clash for Android")
            if len(app_install_result["data"][0]["apps"]) == 2:
                return True
            elif len(app_install_result["data"][0]["apps"]) == 0:
                logger.warning(f"{pad_code}: 重新安装")
                await install_app(pad_code_list=[pad_code],
                                                 app_url=clash_install_url,  md5=clash_md5)

                await install_app(pad_code_list=[pad_code],
                                                  app_url=script_install_url, md5=script_md5)
                await asyncio.sleep(10)
                return False

            elif len(app_install_result["data"][0]["apps"]) == 1:
                app_result = app_install_result["data"][0]["apps"]
                logger.info(f"安装成功一个:{app_result[0]['appName']}")
                await install_app(pad_code_list=[pad_code],app_url=script_install_url, md5=script_md5)
                await asyncio.sleep(10)
                return False
        return False


    async def check_task_status(self, task_id, task_type, timeout_seconds: int = (check_task_timeout_minute * 60), retry_interval: int = 5):
        app_url = clash_install_url if task_type.lower() == "clash" else script_install_url
        app_mod5 = app_url.split("/")[-1].replace(".apk", "")
        try:
            async with asyncio.timeout(timeout_seconds):
                while True:
                    try:
                        result: Any = await get_cloud_file_task_info([str(task_id)])
                        error_message: Any = result["data"][0]["errorMsg"]
                        if error_message:
                            logger.info(f"{task_type} 安装任务: {error_message}")

                        task_status = result["data"][0]["taskStatus"]
                        pad_code = result["data"][0]["padCode"]
                        match InstallTaskStatus(task_status):
                            case InstallTaskStatus.PENDING:
                                logger.info(f"{pad_code}:{task_type}等待安装中")
                                message = result["data"][0]["errorMsg"]
                                if message:
                                    logger.warning(f"{pad_code}: {message}")

                            case InstallTaskStatus.RUNNING:
                                logger.info(f"{pad_code}:{task_type}安装中")
                                message = result["data"][0]["errorMsg"]
                                if message:
                                    logger.warning(f"{pad_code}: {message}")

                            case InstallTaskStatus.TIMEOUT:
                                logger.info(f"{pad_code}:{task_type}安装超时")
                                message = result["data"][0]["errorMsg"]
                                if message:
                                    logger.warning(f"{pad_code}: {message}")

                            case InstallTaskStatus.SOME_FAILED:
                                logger.warning(f"{task_type}下载失败")
                                logger.warning(result["data"][0]["errorMsg"])
                                result = await install_app(pad_code_list=[pad_code], app_url=app_url, md5=app_mod5)
                                logger.info(result["data"][0]["errorMsg"])

                            case InstallTaskStatus.ALL_FAILED:
                                message = result["data"][0]["errorMsg"]
                                if message:
                                    logger.warning(f"{pad_code}: {message}")

                            case InstallTaskStatus.COMPLETED:
                                if await self.handle_install_result(result, task_type):
                                    break

                            case InstallTaskStatus.TIMEOUT:
                                logger.warning("设备离线，停止安装")
                                break
                        await asyncio.sleep(retry_interval)
                    except Exception as e:
                        logger.error(f"检查任务状态失败: {e}, 任务ID: {task_id}")
                        await asyncio.sleep(retry_interval)

        except asyncio.TimeoutError:
            logger.info(f"{task_type} task {task_id}: 安装超时后 {timeout_seconds} seconds")
            if 'result' not in locals():
                logger.warning(f"任务 {task_id} 在首次检查前超时")
                return
            try:
                pad_code = result["data"][0]["padCode"]
                await self.remove_task(pad_code)
                temple_id = random.choice(temple_id_list)
                replace_result = await replace_pad([pad_code], template_id=temple_id)
                logger.info(f"{pad_code}：正在一键新机，使用的模板为: {temple_id}")
                logger.warning("因为长时间安装不上，已移除任务")
            except (KeyError, IndexError) as e:
                logger.error(f"无法处理超时：{e}，任务ID：{task_id}")

    async def handle_timeout(self, pad_code_str: str, timeout_seconds: int = (global_timeout_minute * 60)):
        try:
            await asyncio.sleep(timeout_seconds)
            if await self.get_task(pad_code_str) is None:
                logger.info(f"标识符 {pad_code_str} 的任务已不存在，无需替换")
                return
            logger.warning(f"标识符超时: {pad_code_str}")
            temple_id = random.choice(temple_id_list)
            result = await replace_pad([pad_code_str], template_id=temple_id)
            logger.info(f"{pad_code_str}：正在一键新机，使用的模板为: {temple_id},运行结果为: {result['msg']}")
            await self.remove_task(pad_code_str)
        except asyncio.CancelledError:
            logger.info(f"标识符的超时任务: {pad_code_str} 被取消了.")