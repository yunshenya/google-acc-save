import csv
from typing import Any

from loguru import logger

from app.config import config
from app.dependencies.proxy import ProxyManager

manager = ProxyManager()


def load_proxy_countries():
    try:
        with open("default_proxy.csv", "r", encoding="utf-8") as f:
            reader: Any = csv.reader(f)
            for row in reader:
                if len(row) >= 9:
                    country_data = {
                        "country": row[0],
                        "code": row[1],
                        "proxy": row[2],
                        "time_zone": row[3],
                        "language": row[4],
                        "latitude": float(row[5]),
                        "longitude": float(row[6]),
                    }
                    manager.add_proxy_country(country_data)
            logger.info(f"已加载 {len(manager.get_proxy_countries())} 个代理国家信息")
    except Exception as e:
        logger.error(f"加载代理国家列表失败: {e}")
        manager.set_proxy_countries(config.DEFAULT_PROXY.to_dict())
