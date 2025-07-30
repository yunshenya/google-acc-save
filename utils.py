from auth import VmosUtil


def replace_pad(pad_code:list[str], template_id:int) -> dict[str, str]:
    pad_infos_url = '/vcpcloud/api/padApi/replacePad'

    replace_pad_body = {
        "realPhoneTemplateId": template_id,
        "padCodes": pad_code
    }

    return VmosUtil(pad_infos_url, replace_pad_body).send()


def update_language(language:str, country,pad_code_list:list[str]) -> dict[str, str]:
    change_lang_url = "/vcpcloud/api/padApi/updateLanguage"

    set_lang_body = {
        "language": language,
        "country": country,
        "padCodes": pad_code_list
    }

    return VmosUtil(change_lang_url, set_lang_body).send()


def install_app(pad_code_list:list[str], app_url: str) -> dict[str, str]:
    install_app_url = "/vcpcloud/api/padApi/uploadFileV3"
    body = {
        "padCodes": pad_code_list,
        "autoInstall" : 1,
        "url": app_url,
        "isAuthorization": True
    }

    return VmosUtil(install_app_url, body).send()


def start_app(pad_code_list:list, pkg_name: str) -> list:
    start_app_url = "/vcpcloud/api/padApi/startApp"

    body = {
        "padCodes": pad_code_list,
        "pkgName": pkg_name
    }

    return VmosUtil(start_app_url, body).send()


def replacement(pad_code:str) -> dict[str, str]:
    replace_ment_url = "/vcpcloud/api/padApi/replacement"

    body = {
        "padCode": pad_code
    }

    return VmosUtil(replace_ment_url, body).send()


def update_time_zone(pad_code_list: list[str], time_zone: str) -> dict[str, str]:
    update_timezone_url = "/vcpcloud/api/padApi/updateTimeZone"

    body = {
        "timeZone": time_zone,
        "padCodes": pad_code_list
    }

    return VmosUtil(update_timezone_url, body).send()


def gps_in_ject_info(pad_code_list:list[str], longitude:float, latitude:float) -> dict[str, str]:
    set_local_url = "/vcpcloud/api/padApi/gpsInjectInfo"

    body = {
        "longitude" : 	longitude,
        "latitude" : latitude,
        "padCodes" : pad_code_list
    }

    return VmosUtil(set_local_url, body).send()


def get_cloud_task_info(tasks_list: list[str]):
    file_task = "/vcpcloud/api/padApi/fileTaskDetail"
    body = {
        "taskIds": tasks_list
    }
    return VmosUtil(file_task, body).send()



def get_cloud_file_task_info(tasks_list: list[str]):
    file_task = "/vcpcloud/api/padApi/padTaskDetail"
    body = {
        "taskIds": tasks_list
    }

    return VmosUtil(file_task, body).send()

def get_app_install_info(pad_code_list: list[str], app_name: str) -> dict[str, str]:
    url  ="/vcpcloud/api/padApi/listInstalledApp"
    body = {
        "padCodes" : pad_code_list,
        "appName" : app_name
    }

    return VmosUtil(url, body).send()