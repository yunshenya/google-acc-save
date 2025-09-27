import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


@dataclass
class ProxyConfig:
    """代理配置数据结构"""
    country: str
    code: str
    proxy: str
    time_zone: str
    language: str
    latitude: float
    longitude: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "country": self.country,
            "code": self.code,
            "proxy": self.proxy,
            "time_zone": self.time_zone,
            "language": self.language,
            "latitude": self.latitude,
            "longitude": self.longitude
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProxyConfig':
        return cls(**data)

    @classmethod
    def from_env(cls) -> 'ProxyConfig':
        config_data = json.loads(os.getenv('PROXY_CONFIG'))
        return cls.from_dict(config_data)


@dataclass
class AppUrls:
    """应用程序下载链接"""
    clash: str
    script: str
    script2: str
    chrome: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppUrls':
        return cls(**data)

    @classmethod
    def from_env(cls, env_var: str = 'APP_URLS') -> Optional['AppUrls']:
        """从环境变量加载应用URLs"""
        urls_str = os.getenv(env_var)
        if not urls_str:
            return None

        try:
            urls_data = json.loads(urls_str)
            return cls.from_dict(urls_data)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Error parsing {env_var}: {e}")
            return None


@dataclass
class TimeoutConfig:
    """超时配置（单位：分钟）"""
    global_timeout: int
    check_task_timeout: int


class Config:
    """主配置类"""

    # 环境和调试设置
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:1332@localhost:5432/google-manager"
    )

    # 应用程序标识符
    PAD_CODES: List[str] = os.getenv('PADE_CODE_LIST').split(',')


    PACKAGE_NAMES: Dict[str, str] = json.loads(os.getenv('PACKAGE_NAMES'))

    # Template Configuration
    TEMPLE_IDS: List[int] = [459]

    # Default Proxy Configuration
    DEFAULT_PROXY = ProxyConfig.from_env()

    # Application URLs
    APP_URLS = AppUrls.from_env()

    # Timeout Configuration
    TIMEOUTS = TimeoutConfig(
        global_timeout=int(os.getenv("GLOBAL_TIMEOUT_MINUTES", "12")),
        check_task_timeout=int(os.getenv("CHECK_TASK_TIMEOUT_MINUTES", "5"))
    )

    @classmethod
    def get_package_name(cls, package_type: str = "primary") -> str:
        """Get package name by type"""
        return cls.PACKAGE_NAMES.get(package_type, cls.PACKAGE_NAMES["primary"])

    @classmethod
    def get_app_url(cls, app_name: str) -> str:
        """Get application download URL by name"""
        return getattr(cls.APP_URLS, app_name, "")

    @classmethod
    def is_debug_mode(cls) -> bool:
        """Check if debug mode is enabled"""
        return cls.DEBUG

    @classmethod
    def get_timeout(cls, timeout_type: str) -> int:
        """Get timeout value by type"""
        return getattr(cls.TIMEOUTS, f"{timeout_type}_timeout", 10)

    @classmethod
    def update_config(cls, updates: dict) -> None:
        """热更新配置"""
        from app.services.logger import get_logger
        logger = get_logger("config")

        updated_fields = []

        if "pad_codes" in updates:
            cls.PAD_CODES = updates["pad_codes"]
            # 更新全局变量
            global pad_code_list
            pad_code_list = cls.PAD_CODES
            updated_fields.append("PAD_CODES")

        if "package_names" in updates:
            cls.PACKAGE_NAMES.update(updates["package_names"])
            # 更新全局变量
            global pkg_name, pkg_name2
            pkg_name = cls.get_package_name("primary")
            pkg_name2 = cls.get_package_name("secondary")
            updated_fields.append("PACKAGE_NAMES")

        if "temple_ids" in updates:
            cls.TEMPLE_IDS = updates["temple_ids"]
            # 更新全局变量
            global temple_id_list
            temple_id_list = cls.TEMPLE_IDS
            updated_fields.append("TEMPLE_IDS")

        if "default_proxy" in updates:
            proxy_data = updates["default_proxy"]
            cls.DEFAULT_PROXY = ProxyConfig(**proxy_data)
            # 更新全局变量
            global default_proxy
            default_proxy = cls.DEFAULT_PROXY.to_dict()
            updated_fields.append("DEFAULT_PROXY")

        if "app_urls" in updates:
            url_data = updates["app_urls"]
            cls.APP_URLS = AppUrls(**url_data)
            # 更新全局变量
            global clash_install_url, script_install_url, script2_install_url, chrome_install_url
            clash_install_url = cls.get_app_url("clash")
            script_install_url = cls.get_app_url("script")
            script2_install_url = cls.get_app_url("script2")
            chrome_install_url = cls.get_app_url("chrome")
            updated_fields.append("APP_URLS")

        if "timeouts" in updates:
            timeout_data = updates["timeouts"]
            cls.TIMEOUTS = TimeoutConfig(**timeout_data)
            # 更新全局变量
            global global_timeout_minute, check_task_timeout_minute
            global_timeout_minute = cls.get_timeout("global")
            check_task_timeout_minute = cls.get_timeout("check_task")
            updated_fields.append("TIMEOUTS")

        if "debug" in updates:
            cls.DEBUG = updates["debug"]
            # 更新全局变量
            global DEBUG
            DEBUG = cls.DEBUG
            updated_fields.append("DEBUG")

        if updated_fields:
            logger.info(f"配置已更新: {', '.join(updated_fields)}")

    @classmethod
    def get_current_config(cls) -> dict:
        """获取当前配置"""
        return {
            "pad_codes": cls.PAD_CODES,
            "package_names": cls.PACKAGE_NAMES,
            "temple_ids": cls.TEMPLE_IDS,
            "default_proxy": cls.DEFAULT_PROXY.to_dict(),
            "app_urls": {
                "clash": cls.APP_URLS.clash,
                "script": cls.APP_URLS.script,
                "script2": cls.APP_URLS.script2,
                "chrome": cls.APP_URLS.chrome
            },
            "timeouts": {
                "global_timeout": cls.TIMEOUTS.global_timeout,
                "check_task_timeout": cls.TIMEOUTS.check_task_timeout
            },
            "debug": cls.DEBUG
        }

    @classmethod
    def reset_to_defaults(cls) -> None:
        """重置为默认配置"""
        # 重新加载环境变量
        load_dotenv()

        # 重置为初始值
        cls.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        cls.DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:1332@localhost:5432/google-manager"
        )

        # 重置其他配置为硬编码的默认值
        # 这里可以根据需要添加重置逻辑

        # 更新全局变量
        global DEBUG, DATABASE_URL, pad_code_list, pkg_name, pkg_name2
        global default_proxy, temple_id_list, clash_install_url, script_install_url
        global script2_install_url, chrome_install_url, global_timeout_minute, check_task_timeout_minute

        DEBUG = cls.DEBUG
        DATABASE_URL = cls.DATABASE_URL
        pad_code_list = cls.PAD_CODES
        pkg_name = cls.get_package_name("primary")
        pkg_name2 = cls.get_package_name("secondary")
        default_proxy = cls.DEFAULT_PROXY.to_dict()
        temple_id_list = cls.TEMPLE_IDS
        clash_install_url = cls.get_app_url("clash")
        script_install_url = cls.get_app_url("script")
        script2_install_url = cls.get_app_url("script2")
        chrome_install_url = cls.get_app_url("chrome")
        global_timeout_minute = cls.get_timeout("global")
        check_task_timeout_minute = cls.get_timeout("check_task")


# 创建全局配置实例以便于访问
config = Config()

# 向后兼容性 - 如果您需要保留原始变量名称
DEBUG = config.DEBUG
DATABASE_URL = config.DATABASE_URL
pad_code_list = config.PAD_CODES
pkg_name = config.get_package_name("primary")
pkg_name2 = config.get_package_name("secondary")
default_proxy = config.DEFAULT_PROXY.to_dict()
temple_id_list = config.TEMPLE_IDS
clash_install_url = config.get_app_url("clash")
script_install_url = config.get_app_url("script")
script2_install_url = config.get_app_url("script2")
chrome_install_url = config.get_app_url("chrome")
global_timeout_minute = config.get_timeout("global")
check_task_timeout_minute = config.get_timeout("check_task")
