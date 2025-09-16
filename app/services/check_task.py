import asyncio
import random
from enum import IntEnum
from typing import Any, Dict, Set
from loguru import logger

from app.config import clash_install_url, script_install_url, temple_id_list, pkg_name, global_timeout_minute, \
    check_task_timeout_minute
from app.curd.status import get_proxy_status, update_cloud_status
from app.dependencies.utils import get_cloud_file_task_info, get_app_install_info, open_root, install_app, \
    replace_pad, update_language, update_time_zone, gps_in_ject_info
from app.models.proxy import ProxyResponse
from app.services.every_task import start_app_state


class InstallTaskStatus(IntEnum):
    ALL_FAILED = -1
    SOME_FAILED = -2
    CANCEL = -3
    TIMEOUT = -4
    PENDING = 1
    RUNNING = 2
    COMPLETED = 3


def _cancel_task_simple(task: asyncio.Task) -> None:
    """简单取消任务，不等待"""
    if not task.done():
        task.cancel()


class TaskManager:
    def __init__(self):
        # 只存储主任务和超时任务
        self._operations: Dict[str, asyncio.Task] = {}
        self._timeout_tasks: Dict[str, asyncio.Task] = {}
        # 正在清理的任务，防止重复清理
        self._cleaning: Set[str] = set()
        self._lock = asyncio.Lock()

    async def add_task(self, pad_code: str, task: asyncio.Task) -> None:
        """添加主任务"""
        async with self._lock:
            # 先清理现有任务
            await self._clean_existing_tasks(pad_code)
            self._operations[pad_code] = task

    async def add_timeout_task(self, pad_code: str, timeout_task: asyncio.Task) -> None:
        """添加超时任务"""
        async with self._lock:
            # 取消之前的超时任务
            if pad_code in self._timeout_tasks:
                old_task = self._timeout_tasks[pad_code]
                _cancel_task_simple(old_task)

            self._timeout_tasks[pad_code] = timeout_task

    async def _clean_existing_tasks(self, pad_code: str) -> None:
        """清理现有任务"""
        if pad_code in self._cleaning:
            return

        self._cleaning.add(pad_code)

        try:
            # 取消主任务
            if pad_code in self._operations:
                task = self._operations[pad_code]
                _cancel_task_simple(task)
                del self._operations[pad_code]

            # 取消超时任务
            if pad_code in self._timeout_tasks:
                timeout_task = self._timeout_tasks[pad_code]
                _cancel_task_simple(timeout_task)
                del self._timeout_tasks[pad_code]
        finally:
            self._cleaning.discard(pad_code)

    async def remove_task(self, pad_code: str) -> None:
        """移除任务"""
        async with self._lock:
            await self._clean_existing_tasks(pad_code)

    async def has_task(self, pad_code: str) -> bool:
        """检查是否存在活跃任务"""
        async with self._lock:
            if pad_code in self._operations:
                task = self._operations[pad_code]
                return not task.done()
            return False

    async def start_task_with_timeout(self, pad_code: str, main_task_coro, timeout_seconds: int = None) -> None:
        """启动带超时的任务"""
        if timeout_seconds is None:
            timeout_seconds = global_timeout_minute * 60

        if await self.has_task(pad_code):
            raise ValueError(f"标识符 {pad_code} 已在使用")

        # 创建主任务
        main_task = asyncio.create_task(main_task_coro)
        await self.add_task(pad_code, main_task)

        # 创建超时任务
        timeout_task = asyncio.create_task(self._handle_timeout_internal(pad_code, timeout_seconds))
        await self.add_timeout_task(pad_code, timeout_task)

        logger.info(f"已启动任务 {pad_code}，超时时间: {timeout_seconds}秒")

    async def _handle_timeout_internal(self, pad_code: str, timeout_seconds: int):
        """内部超时处理"""
        try:
            await asyncio.sleep(timeout_seconds)

            # 检查超时任务是否还应该继续（可能被 /status 接口取消了）
            async with self._lock:
                if pad_code not in self._timeout_tasks:
                    logger.info(f"超时任务已被取消: {pad_code}")
                    return

            logger.warning(f"任务超时: {pad_code}")

            # 执行替换逻辑
            temple_id = random.choice(temple_id_list)
            await replace_pad([pad_code], template_id=temple_id)
            await update_cloud_status(
                pad_code=pad_code,
                current_status="任务超时，正在一键新机中",
                temple_id=temple_id,
                number_of_run=1
            )
            logger.info(f"{pad_code}: 超时处理完成，模板: {temple_id}")

            # 超时后清理所有任务
            await self.remove_task(pad_code)

        except asyncio.CancelledError:
            logger.debug(f"超时任务被取消: {pad_code}")
        except Exception as e:
            logger.error(f"超时处理异常 {pad_code}: {e}")

    async def cancel_timeout_task_only(self, pad_code: str) -> None:
        """只取消超时任务（由 /status 接口调用）"""
        async with self._lock:
            if pad_code in self._timeout_tasks:
                timeout_task = self._timeout_tasks[pad_code]
                _cancel_task_simple(timeout_task)
                del self._timeout_tasks[pad_code]
                logger.info(f"已取消超时任务: {pad_code}")
            else:
                logger.warning(f"未找到超时任务: {pad_code}")

    async def complete_main_task(self, pad_code: str) -> None:
        """标记主任务完成，但保留超时任务"""
        logger.info(f"主任务完成: {pad_code}")
        async with self._lock:
            # 只清理主任务，保留超时任务
            if pad_code in self._operations:
                task = self._operations[pad_code]
                _cancel_task_simple(task)
                del self._operations[pad_code]
        """标记主任务完成，但保留超时任务"""
        logger.info(f"主任务完成: {pad_code}")
        async with self._lock:
            # 只清理主任务，保留超时任务
            if pad_code in self._operations:
                task = self._operations[pad_code]
                _cancel_task_simple(task)
                del self._operations[pad_code]

    async def handle_install_result(self, result, task_type, task_manager) -> bool:
        """处理安装结果"""
        script_md5_list: Any = script_install_url.split("/")
        script_md5 = script_md5_list[-1].replace(".apk", "")
        clash_md5_list: Any = clash_install_url.split("/")
        clash_md5 = clash_md5_list[-1].replace(".apk", "")
        pad_code = result["data"][0]["padCode"]

        # 检查任务是否仍然存在
        if not await self.has_task(pad_code):
            logger.warning(f"{pad_code}: 任务已不存在")
            return False

        try:
            if task_type.lower() == "script":
                app_install_result: Any = await get_app_install_info([pad_code])
                app_count = len(app_install_result["data"][0]["apps"])

                if app_count == 2:
                    # 检查安装完成状态
                    while await self.has_task(pad_code):
                        if await self.app_install_all_done(pad_code):
                            logger.success(f"{pad_code}: 安装成功")
                            await update_cloud_status(pad_code=pad_code, current_status="安装成功")

                            # 设置root权限
                            await open_root(pad_code_list=[pad_code], pkg_name=pkg_name)

                            # 获取代理信息并设置
                            current_proxy: ProxyResponse = await get_proxy_status(pad_code)
                            status_msg = f"设置语言、时区和GPS信息（使用代理国家: {current_proxy.country})"
                            await update_cloud_status(pad_code=pad_code, current_status=status_msg)

                            # 设置语言
                            await update_language("en", country=current_proxy.code, pad_code_list=[pad_code])
                            # 设置时区
                            await update_time_zone(pad_code_list=[pad_code], time_zone=current_proxy.time_zone)
                            # 设置GPS
                            await gps_in_ject_info(pad_code_list=[pad_code],
                                                   latitude=current_proxy.latitude,
                                                   longitude=current_proxy.longitude)

                            await asyncio.sleep(10)
                            await update_cloud_status(pad_code=pad_code, current_status="开始重启")
                            await start_app_state(package_name=pkg_name, pad_code=pad_code, task_manager=task_manager)

                            # 只完成主任务，保留超时任务等待 /status 接口调用
                            await self.complete_main_task(pad_code)
                            return True
                        else:
                            await asyncio.sleep(10)

                elif app_count == 0:
                    logger.warning(f"{pad_code}: 重新上传")
                    await update_cloud_status(pad_code=pad_code, current_status=f"{task_type}重新安装")
                    await install_app(pad_code_list=[pad_code], app_url=clash_install_url, md5=clash_md5)
                    await install_app(pad_code_list=[pad_code], app_url=script_install_url, md5=script_md5)

                elif app_count == 1:
                    app_result = app_install_result["data"][0]["apps"]
                    logger.warning(f"安装成功一个: {app_result[0]['appName']}")
                    await update_cloud_status(pad_code=pad_code, current_status=f"安装成功一个: {app_result[0]['appName']}")
                    await install_app(pad_code_list=[pad_code], app_url=clash_install_url, md5=clash_md5)

            elif task_type.lower() == "clash":
                app_install_result = await get_app_install_info([pad_code])
                app_count = len(app_install_result["data"][0]["apps"])

                if app_count == 2:
                    return True
                elif app_count == 0:
                    logger.warning(f"{pad_code}: 重新上传")
                    await update_cloud_status(pad_code=pad_code, current_status="上传失败，重新上传")
                    await install_app(pad_code_list=[pad_code], app_url=clash_install_url, md5=clash_md5)
                    await install_app(pad_code_list=[pad_code], app_url=script_install_url, md5=script_md5)
                elif app_count == 1:
                    app_result = app_install_result["data"][0]["apps"]
                    logger.info(f"安装成功一个: {app_result[0]['appName']}")
                    await update_cloud_status(pad_code=pad_code, current_status=f"安装成功一个: {app_result[0]['appName']}")
                    await install_app(pad_code_list=[pad_code], app_url=script_install_url, md5=script_md5)

        except Exception as e:
            logger.error(f"处理安装结果时出错 {pad_code}: {e}")
            return False

        return False

    async def check_task_status(self, task_id, task_type, task_manager,
                                timeout_seconds: int = None, retry_interval: int = 10):
        """检查任务状态"""
        if timeout_seconds is None:
            timeout_seconds = check_task_timeout_minute * 60

        app_url = clash_install_url if task_type.lower() == "clash" else script_install_url
        app_md5_list: Any = app_url.split("/")
        app_md5 = app_md5_list[-1].replace(".apk", "")

        end_time = asyncio.get_event_loop().time() + timeout_seconds

        try:
            while asyncio.get_event_loop().time() < end_time:
                try:
                    result: Any = await get_cloud_file_task_info([str(task_id)])
                    error_message = result["data"][0]["errorMsg"]
                    task_status = result["data"][0]["taskStatus"]
                    pad_code = result["data"][0]["padCode"]

                    # 检查主任务是否还存在
                    if not await self.has_task(pad_code):
                        logger.info(f"{pad_code}: 主任务已不存在，停止检查")
                        break

                    match InstallTaskStatus(task_status):
                        case InstallTaskStatus.PENDING:
                            logger.info(f"{pad_code}: {task_type} 等待安装中")
                            await update_cloud_status(pad_code=pad_code, current_status=f"{task_type}等待安装中")

                        case InstallTaskStatus.RUNNING:
                            logger.info(f"{pad_code}: {task_type} 安装中")
                            await update_cloud_status(pad_code=pad_code, current_status=f"{task_type}安装中")

                        case InstallTaskStatus.SOME_FAILED:
                            logger.warning(f"{pad_code}: {task_type} 下载失败，重试")
                            await update_cloud_status(pad_code=pad_code, current_status=f"{task_type}下载失败")
                            await install_app(pad_code_list=[pad_code], app_url=app_url, md5=app_md5)

                        case InstallTaskStatus.ALL_FAILED:
                            logger.error(f"{pad_code}: {task_type} 全部失败")
                            if error_message:
                                await update_cloud_status(pad_code=pad_code, current_status=f"安装失败: {error_message}")
                            return False

                        case InstallTaskStatus.COMPLETED:
                            if await self.handle_install_result(result, task_type, task_manager=task_manager):
                                return True

                        case InstallTaskStatus.TIMEOUT | InstallTaskStatus.CANCEL:
                            logger.warning(f"{pad_code}: {task_type} 任务超时或取消")
                            return False

                    if error_message:
                        logger.warning(f"{pad_code}: {error_message}")

                    await asyncio.sleep(retry_interval)

                except (KeyError, IndexError, TypeError) as e:
                    logger.error(f"获取任务 {task_id} 状态失败: {e}")
                    await asyncio.sleep(retry_interval)

        except asyncio.CancelledError:
            logger.info(f"任务状态检查被取消: {task_id}")
        except Exception as e:
            logger.error(f"检查任务状态异常 {task_id}: {e}")

        # 超时处理
        logger.warning(f"{task_type} 任务 {task_id} 检查超时")
        result: Any = await get_cloud_file_task_info([str(task_id)])
        pad_code = result["data"][0]["padCode"]
        if 'pad_code' in locals():
            if await self.has_task(pad_code):
                temple_id = random.choice(temple_id_list)
                await replace_pad([pad_code], template_id=temple_id)
                await update_cloud_status(
                    pad_code=pad_code,
                    current_status="安装超时，正在一键新机",
                    temple_id=temple_id,
                    number_of_run=1
                )
                await self.remove_task(pad_code)

        return False

    @staticmethod
    async def app_install_all_done(pad_code_str: str) -> bool:
        """检查应用是否全部安装完成"""
        try:
            app_install_result: Any = await get_app_install_info([pad_code_str])
            apps_list = app_install_result["data"][0]["apps"]

            install_done_count = 0
            for app in apps_list:
                if app["appState"] == 0:  # 安装完成
                    install_done_count += 1
                else:
                    logger.info(f"{app['appName']} 状态: {app['appState']}")

            return install_done_count == 2
        except Exception as e:
            logger.error(f"检查安装状态失败 {pad_code_str}: {e}")
            return False