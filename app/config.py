import os
from dotenv import load_dotenv
load_dotenv()

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

DATABASE_URL = "postgresql+asyncpg://postgres:1332@localhost:5432/google-manager"

pad_code_list =  [] if DEBUG else ["ACP250605DG51WR4","ACP250417JIWWZSL","AC20250226GBVI6P","ACP250417FRB7H9K","ACP2504175KEOO32"]

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

temple_id_list = [744, 832, 808, 804, 714, 864,781, 807]

clash_install_url = "https://file.vmoscloud.com/userFile/b250a566f01210cb6783cf4e5d82313f.apk"

script_install_url = "https://file.vmoscloud.com/userFile/b3328e6cbd809fc38f4665c7269a68f9.apk"

global_timeout_minute = 10

check_task_timeout_minute = 5