import os
from dotenv import load_dotenv
load_dotenv()

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

DATABASE_URL = "postgresql+asyncpg://postgres:1332@localhost:5432/google-manager"

pad_code_list =  ["AC32010810553"] if DEBUG else ["ACP250605DG51WR4","ACP250417JIWWZSL","AC20250226GBVI6P","ACP2504175KEOO32"]

pkg_name = "com.aaee8h0kh.cejwrh616"

default_proxy = {
    "country": "摩洛哥",
    "code": "ma",
    "proxy_url": "https://raw.githubusercontent.com/heisiyyds999/clash-conf/refs/heads/master/proxys/ma.yaml",
    "time_zone": "Africa/Casablanca",
    "language": "English",
    "latitude": 35.7758,
    "longitude": -5.7909
}

temple_id_list = [679]

clash_install_url = "https://file.vmoscloud.com/userFile/b250a566f01210cb6783cf4e5d82313f.apk"

script_install_url = "https://file.vmoscloud.com/userFile/a879d3ce5608dad0689d6cbb5879802f.apk"

global_timeout_minute = 8

check_task_timeout_minute = 4