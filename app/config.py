import os
from dotenv import load_dotenv
load_dotenv()

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

DATABASE_URL = "postgresql+asyncpg://postgres:1332@localhost:5432/google-manager"

pad_code_list =  [] if DEBUG else ["ACP250605DG51WR4","ACP250417JIWWZSL","AC20250226GBVI6P","ACP250417FRB7H9K","ACP2504175KEOO32"]

pkg_name = "com.aaee8h0kh.cejwrh616"

default_proxy = {
    "country": "新加坡",
    "code": "sg",
    "proxy_url": "https://raw.githubusercontent.com/heisiyyds999/clash-conf/refs/heads/master/proxys/sg.yaml",
    "time_zone": "Asia/Singapore",
    "language": "English",
    "latitude": 1.3248,
    "longitude": 103.8566
}

temple_id_list = [610]

clash_install_url = "https://file.vmoscloud.com/userFile/b250a566f01210cb6783cf4e5d82313f.apk"

script_install_url = "https://file.vmoscloud.com/userFile/3ccde428595e28284f8bb87feafc6c94.apk"

global_timeout_minute = 8

check_task_timeout_minute = 4