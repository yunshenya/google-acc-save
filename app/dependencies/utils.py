from dataclasses import dataclass
from enum import Enum
from typing import Optional

from loguru import logger

from app.dependencies.auth import VmosUtil


async def replace_pad(pad_code: list[str], template_id: int) -> dict[str, str]:
    pad_infos_url = '/vcpcloud/api/padApi/replacePad'

    replace_pad_body = {
        "realPhoneTemplateId": template_id,
        "padCodes": pad_code
    }

    return await VmosUtil(pad_infos_url, replace_pad_body).send()


async def update_language(language: str, country, pad_code_list: list[str]) -> dict[str, str]:
    change_lang_url = "/vcpcloud/api/padApi/updateLanguage"

    set_lang_body = {
        "language": language,
        "country": country,
        "padCodes": pad_code_list
    }

    return await VmosUtil(change_lang_url, set_lang_body).send()


async def install_app(pad_code_list: list[str], app_url: str, md5: str) -> dict[str, str]:
    install_app_url = "/vcpcloud/api/padApi/uploadFileV3"
    body = {
        "padCodes": pad_code_list,
        "autoInstall": 1,
        "url": app_url,
        "isAuthorization": True,
        "md5": md5
    }

    return await VmosUtil(install_app_url, body).send()


async def start_app(pad_code_list: list, pkg_name: str) -> list:
    start_app_url = "/vcpcloud/api/padApi/startApp"

    body = {
        "padCodes": pad_code_list,
        "pkgName": pkg_name
    }

    return await VmosUtil(start_app_url, body).send()


class ActionType(Enum):
    press = 0
    lift = 1
    touching = 2


@dataclass
class Position:
    action_type: ActionType
    x: int
    y: int
    next_position_wait_time: Optional[int] = None

    def __init__(self, action_type: ActionType, x: int, y: int, next_position_wait_time: Optional[int] = None):
        self.action_type = action_type
        self.x = x
        self.y = y
        self.next_position_wait_time = next_position_wait_time

    def to_dict(self) -> dict:
        result = {
            "actionType": self.action_type.value,
            "x": self.x,
            "y": self.y
        }
        if self.next_position_wait_time is not None:
            result["nextPositionWaitTime"] = self.next_position_wait_time
        return result


async def click(pad_code_list: list[str], positions: list,
                width: int = 1080,
                height: int = 2160) -> str:
    click_url = "/vcpcloud/api/padApi/simulateTouch"
    body = {
        "padCodes": pad_code_list,
        "width": width,
        "height": height,
        "positions": positions
    }

    return await VmosUtil(click_url, body).send()


async def replacement(pad_code: str) -> dict[str, str]:
    replace_ment_url = "/vcpcloud/api/padApi/replacement"

    body = {
        "padCode": pad_code
    }

    return await VmosUtil(replace_ment_url, body).send()


async def update_time_zone(pad_code_list: list[str], time_zone: str) -> dict[str, str]:
    update_timezone_url = "/vcpcloud/api/padApi/updateTimeZone"

    body = {
        "timeZone": time_zone,
        "padCodes": pad_code_list
    }

    return await VmosUtil(update_timezone_url, body).send()


async def gps_in_ject_info(pad_code_list: list[str], longitude: float, latitude: float) -> dict[str, str]:
    set_local_url = "/vcpcloud/api/padApi/gpsInjectInfo"

    body = {
        "longitude": longitude,
        "latitude": latitude,
        "padCodes": pad_code_list
    }

    return await VmosUtil(set_local_url, body).send()


async def get_cloud_file_task_info(tasks_list: list[str]):
    file_task = "/vcpcloud/api/padApi/padTaskDetail"
    body = {
        "taskIds": tasks_list
    }

    return await VmosUtil(file_task, body).send()


async def get_app_install_info(pad_code_list: list[str]) -> dict[str, str]:
    url = "/vcpcloud/api/padApi/listInstalledApp"
    body = {
        "padCodes": pad_code_list
    }

    return await VmosUtil(url, body).send()


async def open_root(pad_code_list: list[str], pkg_name: str) -> dict[str, str]:
    root_url = "/vcpcloud/api/padApi/switchRoot"
    body = {
        "padCodes": pad_code_list,
        "packageName": pkg_name,
        "rootStatus": 1,
        "globalRoot": False
    }
    return await VmosUtil(root_url, body).send()


async def reboot(pad_code_list: list[str]):
    reboot_url = "/vcpcloud/api/padApi/restart"
    body = {
        "padCodes": pad_code_list
    }

    return await VmosUtil(reboot_url, body).send()


async def get_cloud_phone_info(pad_code: str):
    url = "/vcpcloud/api/padApi/padInfo"
    body = {
        "padCode": pad_code
    }

    return await VmosUtil(url, body).send()

async def get_phone_list() -> dict[str, str]:
    list_url = "/vcpcloud/api/padApi/userPadList"
    return await VmosUtil(list_url).send()

async def check_padTaskDetail(tasks_list: list[str]) -> int:
    try:
        result = await get_cloud_file_task_info(tasks_list)
        task_status = result["data"][0]["taskStatus"]
        padCode = result["data"][0]["padCode"]
        errorMsg = result["data"][0]["errorMsg"]
        match task_status:
            case -1:
                if errorMsg:
                    logger.error(f"{task_status}: {padCode}：{errorMsg}")
                return -1

            case -2:
                if errorMsg:
                    logger.warning(f"{task_status}： {padCode}：{errorMsg}")
                return -1

            case -3:
                if errorMsg:
                    logger.warning(f"{task_status}: {padCode}：{errorMsg}")
                return -1

            case -4:
                if errorMsg:
                    logger.warning(f"{task_status}: {padCode}：{errorMsg}")
                return -1

            case 1:
                if errorMsg:
                    logger.info(f"{task_status}: {padCode}：{errorMsg}")
                return 0

            case 2:
                if errorMsg:
                    logger.info(f"{task_status}: {padCode}：{errorMsg}")
                return 0

            case 3:
                if errorMsg:
                    logger.success(f"{task_status}: {padCode}：{errorMsg}")
                return 1

        return 0

    except IndexError:
        return 0
