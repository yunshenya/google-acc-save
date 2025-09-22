import os
from dotenv import load_dotenv
load_dotenv()

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

DATABASE_URL = "postgresql+asyncpg://postgres:1332@localhost:5432/google-manager"

pad_code_list =  ["AC32010800443","AC32010590813","AC32010780162","AC32011030882","AC32010790283"]

pkg_name = "com.gasegom.grni"

default_proxy = {
    "country": "摩洛哥",
    "code": "ma",
    "proxy": "https://raw.githubusercontent.com/heisiyyds999/clash-conf/refs/heads/master/proxys/ma.yaml",
    "time_zone": "Africa/Casablanca",
    "language": "English",
    "latitude": 35.7758,
    "longitude": -5.7909
}

temple_id_list = [473]

clash_install_url = "https://file.vmoscloud.com/userFile/b250a566f01210cb6783cf4e5d82313f.apk"

script_install_url = "https://file.vmoscloud.com/userFile/69e2efa91dba04abc11d8c04cf3aaf0d.apk"

global_timeout_minute = 10

check_task_timeout_minute = 5