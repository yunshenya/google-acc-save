import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv, set_key

# 加载环境变量
load_dotenv()

# 环境变量文件路径
ENV_FILE = Path(".env")


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


class ConfigManager:
    """配置管理器 - 负责环境变量的持久化"""

    @staticmethod
    def update_env_var(key: str, value: Any) -> None:
        """更新单个环境变量到 .env 文件"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        elif isinstance(value, bool):
            value = str(value).lower()
        else:
            value = str(value)

        # 更新 .env 文件
        set_key(ENV_FILE, key, value)
        # 同时更新当前进程的环境变量
        os.environ[key] = value

    @staticmethod
    def update_multiple_env_vars(updates: Dict[str, Any]) -> None:
        """批量更新环境变量"""
        for key, value in updates.items():
            ConfigManager.update_env_var(key, value)

    @staticmethod
    def get_env_var(key: str, default: Any = None) -> Any:
        """获取环境变量"""
        return os.getenv(key, default)

    @staticmethod
    def reload_env() -> None:
        """重新加载环境变量文件"""
        load_dotenv(override=True)
import ast
import json
from typing import List


def safe_parse_int_list(env_value: str, default: List[int] = None) -> List[int]:
    """安全解析环境变量为整数列表"""
    if not env_value:
        return default or []

    # 处理中文逗号
    env_value = env_value.replace('，', ',')

    # 尝试作为JSON解析
    try:
        result = json.loads(env_value)
        if isinstance(result, list):
            return [int(item) for item in result]
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    # 尝试作为Python字面量解析
    try:
        result = ast.literal_eval(env_value)
        if isinstance(result, (list, tuple)):
            return [int(item) for item in result]
    except (ValueError, SyntaxError):
        pass

    # 作为逗号分隔的字符串处理
    try:
        return [int(item.strip()) for item in env_value.split(',') if item.strip()]
    except ValueError:
        print(f"Warning: Cannot parse TEMPLE_IDS value: {env_value}")
        return default or []

def safe_parse_str_list(env_value: str, default: List[str] = None) -> List[str]:
    """安全解析环境变量为字符串列表"""
    if not env_value:
        return default or []

    # 处理中文逗号
    env_value = env_value.replace('，', ',')

    # 尝试作为JSON解析
    try:
        result = json.loads(env_value)
        if isinstance(result, list):
            return [str(item) for item in result]
    except (json.JSONDecodeError, TypeError):
        pass

    # 尝试作为Python字面量解析
    try:
        result = ast.literal_eval(env_value)
        if isinstance(result, (list, tuple)):
            return [str(item) for item in result]
    except (ValueError, SyntaxError):
        pass

    # 作为逗号分隔的字符串处理
    return [item.strip() for item in env_value.split(',') if item.strip()]


class Config:
    """主配置类"""

    # 环境和调试设置
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:1332@localhost:5432/google-manager"
    )

    # JWT 配置
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", '+H~I52e."@bM5BC"?-5mpKUnr\}{+nh,>>SrV4Sx@qfthW/_D9')

    # 管理员账户配置
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")

    # 应用程序标识符
    PAD_CODES: List[str] = os.getenv('PADE_CODE_LIST', '').split(',') if os.getenv('PADE_CODE_LIST') else []

    PACKAGE_NAMES: Dict[str, str] = json.loads(os.getenv('PACKAGE_NAMES', '{}'))

    TEMPLE_IDS = safe_parse_int_list(os.getenv('TEMPLE_IDS'), [459])

# Default Proxy Configuration
    DEFAULT_PROXY = ProxyConfig.from_env() if os.getenv('PROXY_CONFIG') else None

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
        return cls.PACKAGE_NAMES.get(package_type, cls.PACKAGE_NAMES.get("primary", ""))

    @classmethod
    def get_app_url(cls, app_name: str) -> str:
        """Get application download URL by name"""
        if cls.APP_URLS:
            return getattr(cls.APP_URLS, app_name, "")
        return ""

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
        """热更新配置并持久化到 .env 文件"""
        from app.services.logger import get_logger
        logger = get_logger("config")

        updated_fields = []
        env_updates = {}

        # PAD_CODES 更新
        if "pad_codes" in updates:
            cls.PAD_CODES = updates["pad_codes"]
            env_updates["PADE_CODE_LIST"] = ",".join(cls.PAD_CODES)
            updated_fields.append("PAD_CODES")

        # PACKAGE_NAMES 更新
        if "package_names" in updates:
            cls.PACKAGE_NAMES.update(updates["package_names"])
            env_updates["PACKAGE_NAMES"] = cls.PACKAGE_NAMES

            updated_fields.append("PACKAGE_NAMES")

        # TEMPLE_IDS 更新
        if "temple_ids" in updates:
            cls.TEMPLE_IDS = updates["temple_ids"]
            env_updates["TEMPLE_IDS"] = cls.TEMPLE_IDS
            updated_fields.append("TEMPLE_IDS")

        # DEFAULT_PROXY 更新
        if "default_proxy" in updates:
            proxy_data = updates["default_proxy"]
            cls.DEFAULT_PROXY = ProxyConfig(**proxy_data)
            env_updates["PROXY_CONFIG"] = cls.DEFAULT_PROXY.to_dict()
            updated_fields.append("DEFAULT_PROXY")

        # APP_URLS 更新
        if "app_urls" in updates:
            url_data = updates["app_urls"]
            cls.APP_URLS = AppUrls(**url_data)
            env_updates["APP_URLS"] = cls.APP_URLS.to_dict()
            updated_fields.append("APP_URLS")

        # TIMEOUTS 更新
        if "timeouts" in updates:
            timeout_data = updates["timeouts"]
            cls.TIMEOUTS = TimeoutConfig(**timeout_data)
            env_updates["GLOBAL_TIMEOUT_MINUTES"] = cls.TIMEOUTS.global_timeout
            env_updates["CHECK_TASK_TIMEOUT_MINUTES"] = cls.TIMEOUTS.check_task_timeout
            updated_fields.append("TIMEOUTS")

        # DEBUG 更新
        if "debug" in updates:
            cls.DEBUG = updates["debug"]
            env_updates["DEBUG"] = cls.DEBUG
            updated_fields.append("DEBUG")

        # JWT_SECRET_KEY 更新
        if "jwt_secret_key" in updates:
            cls.JWT_SECRET_KEY = updates["jwt_secret_key"]
            env_updates["JWT_SECRET_KEY"] = cls.JWT_SECRET_KEY
            updated_fields.append("JWT_SECRET_KEY")

        # ADMIN 凭据更新
        if "admin_credentials" in updates:
            admin_data = updates["admin_credentials"]
            if "username" in admin_data:
                cls.ADMIN_USERNAME = admin_data["username"]
                env_updates["ADMIN_USERNAME"] = cls.ADMIN_USERNAME
            if "password" in admin_data:
                cls.ADMIN_PASSWORD = admin_data["password"]
                env_updates["ADMIN_PASSWORD"] = cls.ADMIN_PASSWORD
            updated_fields.append("ADMIN_CREDENTIALS")

        # DATABASE_URL 更新
        if "database_url" in updates:
            cls.DATABASE_URL = updates["database_url"]
            env_updates["DATABASE_URL"] = cls.DATABASE_URL
            updated_fields.append("DATABASE_URL")

        # 批量更新环境变量到 .env 文件
        if env_updates:
            ConfigManager.update_multiple_env_vars(env_updates)

        if updated_fields:
            logger.info(f"配置已更新并持久化: {', '.join(updated_fields)}")

    @classmethod
    def get_current_config(cls) -> dict:
        """获取当前配置"""
        return {
            "pad_codes": cls.PAD_CODES,
            "package_names": cls.PACKAGE_NAMES,
            "temple_ids": cls.TEMPLE_IDS,
            "default_proxy": cls.DEFAULT_PROXY.to_dict() if cls.DEFAULT_PROXY else {},
            "app_urls": cls.APP_URLS.to_dict() if cls.APP_URLS else {},
            "timeouts": {
                "global_timeout": cls.TIMEOUTS.global_timeout,
                "check_task_timeout": cls.TIMEOUTS.check_task_timeout
            },
            "debug": cls.DEBUG,
            "jwt_secret_key": cls.JWT_SECRET_KEY,
            "admin_credentials": {
                "username": cls.ADMIN_USERNAME,
                "password": cls.ADMIN_PASSWORD
            },
            "database_url": cls.DATABASE_URL
        }

    @classmethod
    def reset_to_defaults(cls) -> None:
        """重置为默认配置并持久化"""
        # 重新加载环境变量
        ConfigManager.reload_env()

        # 重置为初始值
        cls.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        cls.DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:1332@localhost:5432/google-manager"
        )
        cls.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", '+H~I52e."@bM5BC"?-5mpKUnr\}{+nh,>>SrV4Sx@qfthW/_D9')
        cls.ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
        cls.ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

        # 重新解析其他配置
        cls.PAD_CODES = os.getenv('PADE_CODE_LIST', '').split(',') if os.getenv('PADE_CODE_LIST') else []
        cls.PACKAGE_NAMES = json.loads(os.getenv('PACKAGE_NAMES', '{}'))
        cls.TEMPLE_IDS = json.loads(os.getenv('TEMPLE_IDS', '[459]'))

        if os.getenv('PROXY_CONFIG'):
            cls.DEFAULT_PROXY = ProxyConfig.from_env()

        if os.getenv('APP_URLS'):
            cls.APP_URLS = AppUrls.from_env()

        cls.TIMEOUTS = TimeoutConfig(
            global_timeout=int(os.getenv("GLOBAL_TIMEOUT_MINUTES", "12")),
            check_task_timeout=int(os.getenv("CHECK_TASK_TIMEOUT_MINUTES", "5"))
        )

    @classmethod
    def add_custom_env_var(cls, key: str, value: Any) -> None:
        """添加自定义环境变量"""
        ConfigManager.update_env_var(key, value)

    @classmethod
    def get_custom_env_var(cls, key: str, default: Any = None) -> Any:
        """获取自定义环境变量"""
        return ConfigManager.get_env_var(key, default)

    @classmethod
    def remove_env_var(cls, key: str) -> None:
        """删除环境变量（从 .env 文件和当前进程）"""
        # 从当前进程删除
        if key in os.environ:
            del os.environ[key]

        # 从 .env 文件删除（通过重写文件）
        if ENV_FILE.exists():
            lines = []
            with open(ENV_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip().startswith(f"{key}="):
                        lines.append(line)

            with open(ENV_FILE, 'w', encoding='utf-8') as f:
                f.writelines(lines)


# 创建全局配置实例以便于访问
config = Config()