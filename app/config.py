import os
from dataclasses import dataclass
from typing import Dict, List, Any

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


@dataclass
class AppUrls:
    """应用程序下载链接"""
    clash: str
    script: str
    script2: str
    chrome: str


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

    # Application Identifiers
    PAD_CODES: List[str] = ["AC32010800443","AC32010590813","AC32010780162","AC32011030882","AC32010790283","ACP250924ZG0VI6K","ACP250924STJP7UW","ACP250924LR2980N","ACP250924851YPGS","ACP2509245PR99BZ","ACP250922XZ4JZEP","ACP250920UMKGU2Z","ACP250423RNNLK3X","ACP2504175U3RVGE","AC32010590031"]


    PACKAGE_NAMES: Dict[str, str] = {
        "primary": "com.gasegom.grni",
        "secondary": "com.agyucmbsz.cc7c1ioku"
    }

    # Template Configuration
    TEMPLE_IDS: List[int] = [473]

    # Default Proxy Configuration
    DEFAULT_PROXY = ProxyConfig(
        country="摩洛哥",
        code="ma",
        proxy="https://raw.githubusercontent.com/heisiyyds999/clash-conf/refs/heads/master/proxys/ma.yaml",
        time_zone="Africa/Casablanca",
        language="English",
        latitude=35.7758,
        longitude=-5.7909
    )

    # Application URLs
    APP_URLS = AppUrls(
        clash="https://file.vmoscloud.com/userFile/b250a566f01210cb6783cf4e5d82313f.apk",
        script="https://file.vmoscloud.com/userFile/6ce1525577c00eb42fc514be7f4de94c.apk",
        script2="https://file.vmoscloud.com/userFile/fd336a6bd620c5f930635c4f49a6b23b.apk",
        chrome="https://file.vmoscloud.com/userFile/802e02a74ada323819f38ba5858a5fbf.apk"
    )

    # Timeout Configuration
    TIMEOUTS = TimeoutConfig(
        global_timeout=int(os.getenv("GLOBAL_TIMEOUT_MINUTES", "10")),
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
