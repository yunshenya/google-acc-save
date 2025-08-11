import csv

from loguru import logger

from config import default_proxy
from app.dependencies.proxy import ProxyManager

manager = ProxyManager() ## 全局代理管理

def load_proxy_countries():
    try:
        with open("代理国家列表 - IPIDEA.csv", "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 9:
                    # 读取所有字段，但只保留模型中需要的字段
                    country_data =  {
                        "country": row[0],  # 国家名称
                        "code": row[1],    # 国家代码
                        "proxy_url": row[2],  # 代理URL
                        "time_zone": row[3],  # 时区
                        "language": row[4],   # 语言
                        "latitude": float(row[5]),  # 纬度
                        "longitude": float(row[6]),  # 经度
                    }
                    # 仅用于内部过滤，不包含在API响应中
                    if row[7] == "是":  # 只添加可用的代理
                        manager.add_proxy_country(country_data)
            logger.info(f"已加载 {len(manager.get_proxy_countries())} 个代理国家信息")
    except Exception as e:
        logger.error(f"加载代理国家列表失败: {e}")
        # 如果加载失败，使用默认代理
        manager.set_proxy_countries(default_proxy)