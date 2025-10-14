from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import IntEnum
import asyncio
from loguru import logger

from app.dependencies.utils import install_app, exe_cmd, open_root
from app.curd.status import update_cloud_status


class InstallTaskStatus(IntEnum):
    ALL_FAILED = -1
    SOME_FAILED = -2
    CANCEL = -3
    TIMEOUT = -4
    PENDING = 1
    RUNNING = 2
    COMPLETED = 3


@dataclass
class AppConfig:
    """应用配置"""
    name: str
    package_name: str
    download_url: str
    md5: str
    needs_root: bool = False
    install_order: int = 0


class AppInstaller(ABC):
    """应用安装器基类"""

    def __init__(self, app_config: AppConfig):
        self.config = app_config

    @abstractmethod
    async def pre_install(self, pad_code: str) -> bool:
        """安装前的准备工作"""
        pass

    @abstractmethod
    async def post_install(self, pad_code: str) -> bool:
        """安装后的处理工作"""
        pass

    async def is_installed(self, pad_code: str) -> bool:
        """检查应用是否已安装"""
        try:
            result: Any = await exe_cmd(pad_code=pad_code, cmd="pm list packages")
            system_app_str = result["data"][0]["errorMsg"]
            packages = [
                item.replace("package:", "")
                for item in system_app_str.split()
                if item.startswith("package:")
            ]
            return self.config.package_name in packages
        except Exception as e:
            logger.error(f"{pad_code}: 检查{self.config.name}安装状态失败 - {e}")
            return False

    async def install(self, pad_code: str) -> Dict[str, Any]:
        """执行安装"""
        try:
            if await self.is_installed(pad_code):
                logger.info(f"{pad_code}: {self.config.name}已安装，跳过")
                return {"code": 200, "msg": "already_installed"}

            await update_cloud_status(
                pad_code=pad_code,
                current_status=f"正在安装{self.config.name}"
            )

            if not await self.pre_install(pad_code):
                return {"code": 500, "msg": "pre_install_failed"}

            result = await install_app(
                pad_code_list=[pad_code],
                app_url=self.config.download_url,
                md5=self.config.md5
            )

            if not await self.post_install(pad_code):
                return {"code": 500, "msg": "post_install_failed"}

            return result
        except Exception as e:
            logger.error(f"{pad_code}: 安装{self.config.name}失败 - {e}")
            return {"code": 500, "msg": str(e)}


class DefaultAppInstaller(AppInstaller):
    """默认应用安装器"""

    async def pre_install(self, pad_code: str) -> bool:
        return True

    async def post_install(self, pad_code: str) -> bool:
        if self.config.needs_root:
            await open_root(
                pad_code_list=[pad_code],
                pkg_name=self.config.package_name
            )
            await update_cloud_status(
                pad_code=pad_code,
                current_status=f"{self.config.package_name}获取root成功"
            )
            logger.success(f"{self.config.package_name}获取root成功")
            await asyncio.sleep(2)
        return True


class ScriptAppInstaller(DefaultAppInstaller):
    """脚本应用安装器（特殊处理）"""

    async def post_install(self, pad_code: str) -> bool:
        await super().post_install(pad_code)
        await update_cloud_status(
            pad_code=pad_code,
            current_status=f"{self.config.name}安装完成"
        )
        return True


class AppInstallManager:
    """应用安装管理器"""

    def __init__(self):
        self._installers: Dict[str, AppInstaller] = {}
        self._install_order: List[str] = []

    def register_app(self, app_config: AppConfig, installer_class=DefaultAppInstaller):
        """注册应用"""
        installer = installer_class(app_config)
        self._installers[app_config.name] = installer
        self._install_order.append(app_config.name)
        self._install_order.sort(
            key=lambda name: self._installers[name].config.install_order
        )
        logger.info(f"注册应用: {app_config.name}")

    def get_installer(self, app_name: str) -> Optional[AppInstaller]:
        """获取安装器"""
        return self._installers.get(app_name)

    async def install_app(self, pad_code: str, app_name: str) -> Dict[str, Any]:
        """安装指定应用"""
        installer = self.get_installer(app_name)
        if not installer:
            return {"code": 404, "msg": f"app_not_found: {app_name}"}

        return await installer.install(pad_code)

    async def install_all(self, pad_code: str) -> Dict[str, Any]:
        """安装所有应用"""
        results = {}
        for app_name in self._install_order:
            result = await self.install_app(pad_code, app_name)
            results[app_name] = result
        return results

    async def check_all_installed(self, pad_code: str) -> bool:
        """检查所有应用是否已安装"""
        for installer in self._installers.values():
            if not await installer.is_installed(pad_code):
                return False
        return True

    def get_app_list(self) -> List[str]:
        """获取应用列表"""
        return self._install_order.copy()



def init_app_manager(config) -> AppInstallManager:
    """初始化应用管理器"""
    manager = AppInstallManager()

    # 从配置中获取MD5
    clash_md5 = config.get_app_url("clash").split("/")[-1].replace(".apk", "")
    script_md5 = config.get_app_url("script").split("/")[-1].replace(".apk", "")
    script2_md5 = config.get_app_url("script2").split("/")[-1].replace(".apk", "")
    chrome_md5 = config.get_app_url("chrome").split("/")[-1].replace(".apk", "")

    # 注册Clash
    manager.register_app(AppConfig(
        name="clash",
        package_name=config.get_package_name("clash") or "com.github.kr328.clash",
        download_url=config.get_app_url("clash"),
        md5=clash_md5,
        needs_root=False,
        install_order=1
    ))

    # 注册Chrome
    manager.register_app(AppConfig(
        name="chrome",
        package_name=config.get_package_name("chrome") or "com.android.chrome",
        download_url=config.get_app_url("chrome"),
        md5=chrome_md5,
        needs_root=False,
        install_order=2
    ))

    # 注册Script2
    manager.register_app(AppConfig(
        name="script2",
        package_name=config.get_package_name("secondary"),
        download_url=config.get_app_url("script2"),
        md5=script2_md5,
        needs_root=True,
        install_order=3
    ))

    # 注册Script（主脚本，最后安装）
    manager.register_app(
        AppConfig(
            name="script",
            package_name=config.get_package_name("primary"),
            download_url=config.get_app_url("script"),
            md5=script_md5,
            needs_root=True,
            install_order=4
        ),
        installer_class=ScriptAppInstaller
    )

    return manager


class InstallTaskChecker:
    """安装任务状态检查器"""

    def __init__(self, app_manager: AppInstallManager):
        self.app_manager = app_manager

    async def check_task_status(
            self,
            pad_code: str,
            task_id: str,
            app_name: str,
            timeout_seconds: int = 300,
            retry_interval: int = 10
    ) -> bool:
        """检查任务状态"""
        from app.dependencies.utils import get_cloud_file_task_info

        end_time = asyncio.get_event_loop().time() + timeout_seconds
        installer = self.app_manager.get_installer(app_name)

        if not installer:
            logger.error(f"{pad_code}: 未找到应用{app_name}的安装器")
            return False

        try:
            while asyncio.get_event_loop().time() < end_time:
                try:
                    result: Any = await get_cloud_file_task_info([str(task_id)])
                    task_status = result["data"][0]["taskStatus"]
                    error_message = result["data"][0]["errorMsg"]

                    match InstallTaskStatus(task_status):
                        case InstallTaskStatus.PENDING:
                            logger.info(f"{pad_code}: {app_name}等待安装中")
                            await update_cloud_status(
                                pad_code=pad_code,
                                current_status=f"{app_name}等待安装中"
                            )

                        case InstallTaskStatus.RUNNING:
                            logger.info(f"{pad_code}: {app_name}安装中")
                            await update_cloud_status(
                                pad_code=pad_code,
                                current_status=f"{app_name}安装中"
                            )

                        case InstallTaskStatus.SOME_FAILED:
                            logger.warning(f"{pad_code}: {app_name}下载失败，重试")
                            await installer.install(pad_code)

                        case InstallTaskStatus.ALL_FAILED:
                            logger.error(f"{pad_code}: {app_name}全部失败")
                            if error_message:
                                await update_cloud_status(
                                    pad_code=pad_code,
                                    current_status=f"{app_name}安装失败: {error_message}"
                                )
                            return False

                        case InstallTaskStatus.COMPLETED:
                            if await installer.is_installed(pad_code):
                                logger.success(f"{pad_code}: {app_name}安装成功")
                                return True

                        case InstallTaskStatus.TIMEOUT | InstallTaskStatus.CANCEL:
                            logger.warning(f"{pad_code}: {app_name}任务超时或取消")
                            return False

                    await asyncio.sleep(retry_interval)

                except (KeyError, IndexError, TypeError) as e:
                    logger.error(f"获取任务{task_id}状态失败: {e}")
                    await asyncio.sleep(retry_interval)

            logger.warning(f"{pad_code}: {app_name}检查超时")
            return False

        except asyncio.CancelledError:
            logger.info(f"{pad_code}: {app_name}任务检查被取消")
            return False
        except Exception as e:
            logger.error(f"{pad_code}: {app_name}检查任务状态异常 - {e}")
            return False


async def install_all_apps(pad_code: str, config, task_manager):
    """安装所有应用的入口函数"""
    app_manager = init_app_manager(config)
    checker = InstallTaskChecker(app_manager)

    logger.info(f"{pad_code}: 开始安装应用，共{len(app_manager.get_app_list())}个")

    install_results = await app_manager.install_all(pad_code)

    check_tasks = []
    for app_name, result in install_results.items():
        if result.get("code") == 200 and "taskId" in result.get("data", [{}])[0]:
            task_id = result["data"][0]["taskId"]
            task = checker.check_task_status(pad_code, task_id, app_name)
            check_tasks.append(task)

    results = await asyncio.gather(*check_tasks, return_exceptions=True)

    all_success = all(r is True for r in results if not isinstance(r, Exception))

    if all_success and await app_manager.check_all_installed(pad_code):
        logger.success(f"{pad_code}: 所有应用安装完成")
        await update_cloud_status(pad_code=pad_code, current_status="所有应用安装完成")

        from app.curd.status import get_proxy_status
        from app.dependencies.utils import update_language, update_time_zone, gps_in_ject_info
        from app.services.every_task import start_app_state

        current_proxy = await get_proxy_status(pad_code)
        await update_cloud_status(
            pad_code=pad_code,
            current_status=f"设置语言、时区和GPS信息（使用代理国家: {current_proxy.country}）"
        )

        await update_language("en", country=current_proxy.code, pad_code_list=[pad_code])
        await update_time_zone(pad_code_list=[pad_code], time_zone=current_proxy.time_zone)
        await gps_in_ject_info(
            pad_code_list=[pad_code],
            latitude=current_proxy.latitude,
            longitude=current_proxy.longitude
        )

        await open_root(
            pad_code_list=[pad_code],
            pkg_name=config.get_package_name("primary")
        )

        await asyncio.sleep(5)
        await update_cloud_status(pad_code=pad_code, current_status="开始启动应用")

        await start_app_state(
            package_name=config.get_package_name("primary"),
            pad_code=pad_code,
            task_manager=task_manager
        )

        await task_manager.complete_main_task(pad_code)

        return True
    else:
        logger.error(f"{pad_code}: 部分应用安装失败")
        await update_cloud_status(pad_code=pad_code, current_status="部分应用安装失败")
        return False