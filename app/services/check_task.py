import asyncio
import random
from enum import IntEnum
from typing import Any, Dict

from loguru import logger

from app.config import clash_install_url, script_install_url, temple_id_list, pkg_name, global_timeout_minute, \
    check_task_timeout_minute
from app.curd.status import get_proxy_status
from app.curd.status import update_cloud_status
from app.dependencies.utils import get_cloud_file_task_info, get_app_install_info, open_root, install_app, \
    replace_pad, update_language, update_time_zone, gps_in_ject_info
from app.models.proxy import ProxyResponse
from app.services.every_task import start_app_state


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
        # 存储主任务
        self._operations: Dict[str, asyncio.Task] = {}
        # 存储超时任务
        self._timeout_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def add_task(self, pad_code: str, task: asyncio.Task) -> None:
        """添加主任务"""
        async with self._lock:
            # 如果已有任务，先清理
            await self._cleanup_existing_task(pad_code)
            self._operations[pad_code] = task

    async def add_timeout_task(self, pad_code: str, timeout_task: asyncio.Task) -> None:
        """添加超时任务"""
        async with self._lock:
            # 取消之前的超时任务
            if pad_code in self._timeout_tasks:
                old_timeout_task = self._timeout_tasks[pad_code]
                if not old_timeout_task.done():
                    old_timeout_task.cancel()
                    try:
                        await old_timeout_task
                    except asyncio.CancelledError:
                        pass

            self._timeout_tasks[pad_code] = timeout_task

    async def remove_task(self, pad_code: str) -> None:
        """移除任务（包括主任务和超时任务）"""
        async with self._lock:
            await self._cleanup_existing_task(pad_code)

    async def _cleanup_existing_task(self, pad_code: str) -> None:
        """清理指定pad_code的所有任务（内部方法，调用时应已持有锁）"""
        # 清理主任务
        if pad_code in self._operations:
            task = self._operations[pad_code]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self._operations[pad_code]

        # 清理超时任务
        if pad_code in self._timeout_tasks:
            timeout_task = self._timeout_tasks[pad_code]
            if not timeout_task.done():
                timeout_task.cancel()
                try:
                    await timeout_task
                except asyncio.CancelledError:
                    pass
            del self._timeout_tasks[pad_code]

    async def has_task(self, pad_code: str) -> bool:
        """检查是否存在任务"""
        async with self._lock:
            return pad_code in self._operations

    async def start_task_with_timeout(self, pad_code: str, main_task_coro, timeout_seconds: int = None) -> None:
        """启动带超时的任务"""
        if timeout_seconds is None:
            timeout_seconds = global_timeout_minute * 60

        # 检查是否已有任务
        if await self.has_task(pad_code):
            raise ValueError(f"标识符 {pad_code} 已在使用")

        # 创建主任务
        main_task = asyncio.create_task(main_task_coro)
        await self.add_task(pad_code, main_task)

        # 创建超时任务
        timeout_task = asyncio.create_task(self._handle_timeout_internal(pad_code, timeout_seconds))
        await self.add_timeout_task(pad_code, timeout_task)

        # 启动任务但不等待完成
        logger.info(f"已启动任务 {pad_code}，超时时间: {timeout_seconds}秒")

    async def _handle_timeout_internal(self, pad_code: str, timeout_seconds: int):
        """内部超时处理方法"""
        try:
            await asyncio.sleep(timeout_seconds)

            # 检查任务是否还存在
            async with self._lock:
                if pad_code not in self._operations:
                    logger.info(f"标识符 {pad_code} 的任务已不存在，无需替换")
                    return

                # 任务仍存在，执行超时处理
                logger.warning(f"标识符超时: {pad_code}")

                # 先移除任务（这会取消主任务）
                await self._cleanup_existing_task(pad_code)

            # 执行替换逻辑（在锁外执行，避免长时间持有锁）
            temple_id = random.choice(temple_id_list)
            result = await replace_pad([pad_code], template_id=temple_id)
            await update_cloud_status(
                pad_code=pad_code,
                current_status="任务超时，正在一键新机中",
                temple_id=temple_id,
                number_of_run=1
            )
            logger.info(f"{pad_code}：正在一键新机，使用的模板为: {temple_id}, 运行结果为: {result['msg']}")

        except asyncio.CancelledError:
            logger.info(f"标识符的超时任务: {pad_code} 被取消了.")
            raise

    async def complete_task(self, pad_code: str) -> None:
        """标记任务完成并清理"""
        logger.info(f"任务 {pad_code} 已完成，正在清理...")
        await self.remove_task(pad_code)

    # 原有方法保持不变，但需要适配新的任务管理方式
    async def handle_install_result(self, result, task_type, task_manager) -> bool:
        script_md5_list: Any = script_install_url.split("/")
        script_md5 = script_md5_list[-1].replace(".apk", "")
        clash_md5_list: Any = clash_install_url.split("/")
        clash_md5 = clash_md5_list[-1].replace(".apk", "")
        pad_code = result["data"][0]["padCode"]

        if task_type.lower() == "script":
            app_install_result : Any = await get_app_install_info([pad_code])
            if len(app_install_result["data"][0]["apps"]) == 2:
                while True:
                    # 检查任务是否仍然存在
                    if not await self.has_task(pad_code):
                        logger.warning(f"{pad_code}: 任务已被取消或超时")
                        return False

                    if await self.app_install_all_done(pad_code):
                        logger.success(f"{pad_code}: 安装成功")
                        await update_cloud_status(pad_code=pad_code, current_status="安装成功")
                        await open_root(pad_code_list=[pad_code], pkg_name=pkg_name)
                        current_proxy: ProxyResponse = await get_proxy_status(pad_code)
                        logger.info(
                            f"设置语言、时区和GPS信息（使用代理国家: {current_proxy.country} ({current_proxy.code}))")

                        await update_cloud_status(pad_code=pad_code,
                                                  current_status=f"设置语言、时区和GPS信息（使用代理国家: {current_proxy.country} ({current_proxy.code}))")
                        lang_result = await update_language("en", country=current_proxy.code,
                                                            pad_code_list=[pad_code])
                        logger.info(f"语言更新结果: {lang_result['msg']}")
                        # 设置时区
                        tz_result = await update_time_zone(pad_code_list=[pad_code],
                                                           time_zone=current_proxy.time_zone)
                        logger.info(f"时区更新结果: {tz_result['msg']}")
                        # 设置GPS信息
                        gps_result = await gps_in_ject_info(
                            pad_code_list=[pad_code],
                            latitude=current_proxy.latitude,
                            longitude=current_proxy.longitude
                        )
                        logger.info(f"GPS注入结果: {gps_result['msg']}")
                        await asyncio.sleep(10)
                        logger.info(f"{pad_code}: 开始重启")
                        await update_cloud_status(pad_code=pad_code, current_status="开始重启")
                        await start_app_state(package_name=pkg_name, pad_code=pad_code, task_manager=task_manager)

                        # 任务完成，清理
                        await self.complete_task(pad_code)
                        return True
                    else:
                        logger.info(f"{pad_code}: 安装中...")
                        await asyncio.sleep(10)

            elif len(app_install_result["data"][0]["apps"]) == 0:
                logger.warning(f"{pad_code}: 重新上传")
                await update_cloud_status(pad_code=pad_code, current_status=f"{task_type}重新安装")
                await install_app(pad_code_list=[pad_code],
                                  app_url=clash_install_url, md5=clash_md5)
                await install_app(pad_code_list=[pad_code],
                                  app_url=script_install_url, md5=script_md5)
                await asyncio.sleep(20)
                return False

            elif len(app_install_result["data"][0]["apps"]) == 1:
                app_result = app_install_result["data"][0]["apps"]
                logger.warning(f"上传成功一个:{app_result[0]['appName']}")
                await update_cloud_status(pad_code=pad_code, current_status=f"安装成功一个:{app_result[0]['appName']}")
                await install_app(pad_code_list=[pad_code],app_url=clash_install_url, md5=clash_md5)
                await asyncio.sleep(10)
                return False

        elif task_type.lower() == "clash":
            app_install_result = await get_app_install_info([pad_code])
            if len(app_install_result["data"][0]["apps"]) == 2:
                return True

            elif len(app_install_result["data"][0]["apps"]) == 0:
                logger.warning(f"{pad_code}: 重新上传")
                await update_cloud_status(pad_code=pad_code, current_status="上传失败，重新上传")
                await install_app(pad_code_list=[pad_code],
                                  app_url=clash_install_url,  md5=clash_md5)
                await install_app(pad_code_list=[pad_code],
                                  app_url=script_install_url, md5=script_md5)
                await asyncio.sleep(10)
                return False

            elif len(app_install_result["data"][0]["apps"]) == 1:
                app_result = app_install_result["data"][0]["apps"]
                logger.info(f"上传成功一个:{app_result[0]['appName']}")
                await update_cloud_status(pad_code=pad_code, current_status=f"上传成功一个:{app_result[0]['appName']}")
                await install_app(pad_code_list=[pad_code],app_url=script_install_url, md5=script_md5)
                await asyncio.sleep(10)
                return False
        return False

    async def check_task_status(self, task_id, task_type, task_manager, timeout_seconds: int = (check_task_timeout_minute * 60), retry_interval: int = 10):
        app_url = clash_install_url if task_type.lower() == "clash" else script_install_url
        app_mod5_list: Any = app_url.split("/")
        app_mod5 = app_mod5_list[-1].replace(".apk", "")

        try:
            async with asyncio.timeout(timeout_seconds):
                while True:
                    try:
                        result: Any = await get_cloud_file_task_info([str(task_id)])
                        error_message: Any = result["data"][0]["errorMsg"]
                        task_status = result["data"][0]["taskStatus"]
                        pad_code = result["data"][0]["padCode"]

                        # 检查任务是否仍然存在
                        if not await self.has_task(pad_code):
                            logger.info(f"{pad_code}: 主任务已不存在，停止检查任务状态")
                            break

                        match InstallTaskStatus(task_status):
                            case InstallTaskStatus.PENDING:
                                logger.info(f"{pad_code}:{task_type}: 等待上传中")
                                await update_cloud_status(pad_code=pad_code, current_status=f"{task_type}等待安装中")
                                if error_message:
                                    logger.warning(f"{pad_code}: {error_message}")
                                    await update_cloud_status(pad_code=pad_code, current_status=error_message)

                            case InstallTaskStatus.RUNNING:
                                logger.info(f"{pad_code}:{task_type}:上传中")
                                await update_cloud_status(pad_code=pad_code, current_status=f"{task_type}安装中")
                                if error_message:
                                    logger.warning(f"{pad_code}: {error_message}")
                                    await update_cloud_status(pad_code=pad_code, current_status=error_message)

                            case InstallTaskStatus.SOME_FAILED:
                                logger.warning(f"{task_type}: 下载失败")
                                await update_cloud_status(pad_code=pad_code, current_status=f"{task_type}下载失败")
                                if error_message:
                                    logger.warning(error_message)
                                    await update_cloud_status(pad_code=pad_code, current_status=error_message)
                                await install_app(pad_code_list=[pad_code], app_url=app_url, md5=app_mod5)

                            case InstallTaskStatus.ALL_FAILED:
                                if error_message and await self.has_task(pad_code):
                                    logger.error(f"全失败: {pad_code}: {error_message}")
                                    await update_cloud_status(pad_code=pad_code, current_status=f"全失败: {error_message}")
                                raise asyncio.TimeoutError("强制超时")

                            case InstallTaskStatus.COMPLETED:
                                if await self.handle_install_result(result, task_type, task_manager=task_manager):
                                    break

                            case InstallTaskStatus.TIMEOUT:
                                break

                        await asyncio.sleep(retry_interval)

                    except TypeError:
                        logger.error(f"{task_id}: 获取任务失败")
                        raise asyncio.TimeoutError("强制超时")

        except asyncio.TimeoutError:
            logger.info(f"{task_type} task {task_id}: 安装超时 {timeout_seconds} seconds")
            if 'result' not in locals():
                logger.warning(f"任务 {task_id} 在首次检查前超时")
                return

            try:
                pad_code = result["data"][0]["padCode"]
                if await self.has_task(pad_code):
                    temple_id = random.choice(temple_id_list)
                    replace_result = await replace_pad([pad_code], template_id=temple_id)
                    await update_cloud_status(pad_code=pad_code, current_status="由于长时间安装失败，正在一键新机", temple_id=temple_id, number_of_run=1)
                    logger.info(f"{pad_code}：正在一键新机，使用的模板为: {temple_id}")
                    logger.warning("因为长时间安装不上，已移除任务")
                    await self.remove_task(pad_code)
            except (KeyError, IndexError) as e:
                logger.error(f"无法处理超时：{e}，任务ID：{task_id}")

    # 废弃的方法，保留以兼容现有代码
    async def handle_timeout(self, pad_code_str: str, timeout_seconds: int = (global_timeout_minute * 60)):
        """已废弃：请使用 start_task_with_timeout"""
        logger.warning("handle_timeout 方法已废弃，请使用 start_task_with_timeout")
        return await self._handle_timeout_internal(pad_code_str, timeout_seconds)

    @staticmethod
    async def app_install_all_done(pad_code_str: str) -> bool:
        install_done_list = []
        app_install_result : Any = await get_app_install_info([pad_code_str])
        apps_list = app_install_result["data"][0]["apps"]
        for app in apps_list:
            match app["appState"]:
                case 0:
                    install_done_list.append(app["appName"])
                case 1:
                    logger.info(f"{app['appName']} 安装中")
                case 2:
                    logger.info(f"{app['appName']}下载中")

        if len(install_done_list) == 2:
            return True
        else:
            return False