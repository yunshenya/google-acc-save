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

    # 应用程序标识符
    PAD_CODES: List[str] = ["AC32010800443","AC32010590813","AC32010780162","AC32011030882",
                            "AC32010790283","ACP250924ZG0VI6K","ACP250924STJP7UW",
                            "ACP250924LR2980N","ACP250924851YPGS","ACP2509245PR99BZ",
                            "ACP250922XZ4JZEP","ACP250920UMKGU2Z","ACP250423RNNLK3X",
                            "ACP2504175U3RVGE","AC32010590031","ACP250925YAMC4D4","ACP250925Y4VSIDE",
                            "ACP250925Y2BAPZK","ACP250921P28PPW2","ACP250425R3P1ST1","ATP250925XGTFG0B",
                            "ATP250925UBX0C3N","ATP250925FGPRF6T","ATP250925U9LA8YZ","ATP250925PDYEYP6",
                            "ATP250925X3FQMNR","ATP250925UGRCZLW","ACP250605CF6AISS","ACP250326XA2KRDK","ACP2504306ZXY0KU",
                            "AC32010961023","ACP250914XYMS4I6","ACP250401MXFDKDI","ACP250317B0L0MLT","ACP250925YATHR1V",
                            "ACP2509258F099QF","ACP250925KH1RFNF","ACP250924M8GLRSD"]


    PACKAGE_NAMES: Dict[str, str] = {
        "primary": "com.gasegom.grni",
        "secondary": "com.agyucmbsz.cc7c1ioku"
    }

    # Template Configuration
    TEMPLE_IDS: List[int] = [459]

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
        script="https://file.vmoscloud.com/userFile/4aa79fee6d19188613b11decc18ab895.apk",
        script2="https://file.vmoscloud.com/userFile/2a125188c61b3a69a0ac871891c956d2.apk",
        chrome="https://file.vmoscloud.com/userFile/802e02a74ada323819f38ba5858a5fbf.apk"
    )

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
