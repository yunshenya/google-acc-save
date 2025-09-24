from typing import Any

from app.config import script_install_url, clash_install_url, chrome_install_url, script2_install_url


class InstallAppEnum:
    total_app_count: int = 4
    script_md5_list: Any = script_install_url.split("/")
    script_md5 = script_md5_list[-1].replace(".apk", "")
    clash_md5_list: Any = clash_install_url.split("/")
    clash_md5 = clash_md5_list[-1].replace(".apk", "")
    chrome_md5_list: Any = chrome_install_url.split("/")
    chrome_md5 = chrome_md5_list[-1].replace(".apk", "")
    script2_md5_list: Any = script2_install_url.split("/")
    script2_md5 = script2_md5_list[-1].replace(".apk", "")