import asyncio
import random
from typing import Dict, Set

from loguru import logger

from app.config import config
from app.curd.status import update_cloud_status
from app.dependencies.utils import replace_pad


def _cancel_task_simple(task: asyncio.Task) -> None:
    """简单取消任务，不等待"""
    if not task.done():
        task.cancel()


class TaskManager:
    def __init__(self):
        self._operations: Dict[str, asyncio.Task] = {}
        self._timeout_tasks: Dict[str, asyncio.Task] = {}
        self._cleaning: Set[str] = set()
        self._lock = asyncio.Lock()
        self._global_timeout_minute = config.get_timeout("global")
        self._temple_id_list = config.TEMPLE_IDS

    async def add_task(self, pad_code: str, task: asyncio.Task) -> None:
        """添加主任务"""
        async with self._lock:
            await self._clean_existing_tasks(pad_code)
            self._operations[pad_code] = task

    async def add_timeout_task(self, pad_code: str, timeout_task: asyncio.Task) -> None:
        """添加超时任务"""
        async with self._lock:
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
            if pad_code in self._operations:
                task = self._operations[pad_code]
                _cancel_task_simple(task)
                del self._operations[pad_code]

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

    async def start_task_with_timeout(
            self, pad_code: str, main_task_coro, timeout_seconds: int = None
    ) -> None:
        """启动带超时的任务"""
        if timeout_seconds is None:
            timeout_seconds = self._global_timeout_minute * 60

        if await self.has_task(pad_code):
            raise ValueError(f"标识符 {pad_code} 已在使用")

        main_task = asyncio.create_task(main_task_coro)
        await self.add_task(pad_code, main_task)

        timeout_task = asyncio.create_task(
            self._handle_timeout_internal(pad_code, timeout_seconds)
        )
        await self.add_timeout_task(pad_code, timeout_task)

        logger.info(f"已启动任务 {pad_code}，超时时间: {timeout_seconds}秒")

    async def _handle_timeout_internal(self, pad_code: str, timeout_seconds: int):
        """内部超时处理"""
        try:
            await asyncio.sleep(timeout_seconds)

            async with self._lock:
                if pad_code not in self._timeout_tasks:
                    logger.info(f"超时任务已被取消: {pad_code}")
                    return

            logger.warning(f"任务超时: {pad_code}")

            if pad_code in config.PAD_CODES:
                temple_id = random.choice(self._temple_id_list)
                await replace_pad([pad_code], template_id=temple_id)
                await update_cloud_status(
                    pad_code=pad_code,
                    current_status="任务超时，正在一键新机中",
                    temple_id=temple_id,
                    number_of_run=1,
                    num_other_error=1,
                )
                logger.info(f"{pad_code}: 超时处理完成，模板: {temple_id}")

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
                logger.info(f"还未启动超时任务: {pad_code}")

    async def complete_main_task(self, pad_code: str) -> None:
        """标记主任务完成，但保留超时任务"""
        logger.info(f"主任务完成: {pad_code}")
        async with self._lock:
            if pad_code in self._operations:
                task = self._operations[pad_code]
                _cancel_task_simple(task)
                del self._operations[pad_code]