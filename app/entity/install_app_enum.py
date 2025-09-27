from typing import Any

from app.config import config


class InstallAppEnum:
    total_app_count: int = 4
    script_md5_list: Any = config.get_app_url("script").split("/")
    script_md5 = script_md5_list[-1].replace(".apk", "")
    clash_md5_list: Any = config.get_app_url("clash").split("/")
    clash_md5 = clash_md5_list[-1].replace(".apk", "")
    chrome_md5_list: Any = config.get_app_url("chrome").split("/")
    chrome_md5 = chrome_md5_list[-1].replace(".apk", "")
    script2_md5_list: Any = config.get_app_url("script2").split("/")
    script2_md5 = script2_md5_list[-1].replace(".apk", "")
