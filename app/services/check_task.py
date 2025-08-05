import asyncio
import random
from asyncio import Task
from collections import defaultdict
from typing import Any

from loguru import logger

from app.dependencies.utils import get_cloud_file_task_info, get_app_install_info, open_root, reboot, install_app, \
    replace_pad
from config import clash_install_url, script_install_url, temple_id_list, pkg_name

operations = defaultdict(lambda: Task[None])
lock = asyncio.Lock()


async def check_task_status(task_id, task_type):
    TIMEOUT_SECONDS = 2 * 60
    try:
        async with asyncio.timeout(TIMEOUT_SECONDS):
            while True:
                result = await get_cloud_file_task_info([str(task_id)])
                logger.info(f"{task_type} task {task_id}: {result}")
                if result["data"][0]["errorMsg"] == "应用安装成功":
                    if task_type.lower() == "script":
                        logger.info(f'{task_type}安装成功')
                        app_install_result : Any = await get_app_install_info([result["data"][0]["padCode"]], "Clash for Android")
                        if len(app_install_result["data"][0]["apps"]) == 2:
                            logger.info("真安装成功")
                            root_result = await open_root(pad_code_list=[result["data"][0]["padCode"]], pkg_name=pkg_name)
                            logger.info(root_result)
                            logger.info("开始重启")
                            reboot_result = await reboot(pad_code_list=[result["data"][0]["padCode"]])
                            logger.info(reboot_result)
                            break

                        elif len(app_install_result["data"][0]["apps"]) == 0:
                            logger.error("假安装成功，重新安装")
                            clash_result = await install_app(pad_code_list=[result["data"][0]["padCode"]],
                                                             app_url=clash_install_url)
                            logger.info(clash_result)
                            script_result = await install_app(pad_code_list=[result["data"][0]["padCode"]],
                                                              app_url=script_install_url)
                            logger.info(script_result)
                            await asyncio.sleep(10)

                        elif len(app_install_result["data"][0]["apps"]) == 1:
                            app_result = app_install_result["data"][0]["apps"]
                            logger.error(f"安装成功一个:{app_result[0]}")
                            await install_app(pad_code_list=[result["data"][0]["padCode"]],app_url=clash_install_url)
                            await asyncio.sleep(10)




                    elif task_type.lower() == "clash":
                        logger.info(f"{task_type}安装成功")
                        app_install_result = await get_app_install_info([result["data"][0]["padCode"]], "Clash for Android")
                        if len(app_install_result["data"][0]["apps"]) == 2:
                            logger.success("真安装成功")
                            break
                        elif len(app_install_result["data"][0]["apps"]) == 0:
                            logger.error("假安装成功，重新安装")
                            clash_result = await install_app(pad_code_list=[result["data"][0]["padCode"]],
                                                             app_url=clash_install_url)
                            logger.info(clash_result)
                            script_result = await install_app(pad_code_list=[result["data"][0]["padCode"]],
                                                              app_url=script_install_url)
                            logger.info(script_result)
                            await asyncio.sleep(10)

                        elif len(app_install_result["data"][0]["apps"]) == 1:
                            app_result = app_install_result["data"][0]["apps"]
                            logger.info(f"安装成功一个:{app_result[0]}")
                            await install_app(pad_code_list=[result["data"][0]["padCode"]],app_url=script_install_url)
                            await asyncio.sleep(10)

                elif result["data"][0]["errorMsg"] == "文件下载失败 请求被中断，请重试":
                    if task_type.lower() == "clash":
                        logger.error("clash下载失败")
                        clash_result = await install_app(pad_code_list=[result["data"][0]["padCode"]],
                                                         app_url=clash_install_url)
                        logger.info(clash_result)
                    else:
                        logger.error("脚本下载失败")
                        script_result = await install_app(pad_code_list=[result["data"][0]["padCode"]],
                                                          app_url=script_install_url)
                        logger.info(script_result)
                    await asyncio.sleep(10)

                elif result["data"][0]["errorMsg"] == "任务已超时，当前设备状态为离线状态。":
                    print("设备离线，停止安装")
                    break
                await asyncio.sleep(1)

    except asyncio.TimeoutError:
        logger.info(f"{task_type} task {task_id}: 安装超时后 {TIMEOUT_SECONDS} seconds")
        try:
            pad_code = result["data"][0]["padCode"]
            async with lock:
                task: Any = operations.get(pad_code)
                if task is not None:
                    task.cancel()
                    del operations[pad_code]
            replace_result = await replace_pad([pad_code], template_id=random.choice(temple_id_list))
            logger.error(replace_result)
            logger.error("因为长时间安装不上，已移除任务")
        except (NameError, KeyError, IndexError) as e:
            logger.error(f"无法处理超时：{e}，任务ID：{task_id}")
        return


async def handle_timeout(pad_code_str: str):
    try:
        await asyncio.sleep(5 * 60)
        async with lock:
            if operations.get(pad_code_str) is not None:
                logger.info(f"标识符超时: {pad_code_str}")
                result = await replace_pad([pad_code_str], template_id=random.choice(temple_id_list))
                logger.info(f"正在一键新机: {result}")
                del operations[pad_code_str]
    except asyncio.CancelledError:
        logger.error(f"标识符的超时任务: {pad_code_str} 被取消了.")