import binascii
import datetime
import hashlib
import hmac
import json

import aiohttp
from loguru import logger


class VmosUtil(object):
    def __init__(self, url, data):
        self._url = url
        self._data = data
        self._ak = "nx9xwcQ5KEap2nUqrJZTBoxJK7G61uvj"
        self._sk = "7xf9Q8D9VRBhzjWhgzwHx2AB"
        self._x_date = datetime.datetime.now().strftime("%Y%m%dT%H%M%SZ")
        self._content_type = "application/json;charset=UTF-8"
        self._signed_headers = "content-type;host;x-content-sha256;x-date"
        self._host = "api.vmoscloud.com"

    def _get_signature(self):
        json_string = json.dumps(self._data, separators=(',', ':'), ensure_ascii=False)
        logger.info(json_string)

        # 计算SHA-256哈希值
        hash_object = hashlib.sha256(json_string.encode())
        x_content_sha256 = hash_object.hexdigest()

        # 使用f-string构建canonicalStringBuilder
        canonical_string_builder = (
            f"host:{self._host}\n"
            f"x-date:{self._x_date}\n"
            f"content-type:{self._content_type}\n"
            f"signedHeaders:{self._signed_headers}\n"
            f"x-content-sha256:{x_content_sha256}"
        )
        # 假设这些变量已经被赋值
        # short_x_date = datetime.datetime.now().strftime("%Y%m%d")  # 短请求时间，例如："20240101"
        short_x_date = self._x_date[:8]  # 短请求时间，例如："20240101"
        service = "armcloud-paas"  # 服务名

        # 构建credentialScope
        credential_scope = "{}/{}/request".format(short_x_date, service)

        # 假设这些变量已经被赋值
        algorithm = "HMAC-SHA256"

        # 计算canonicalStringBuilder的SHA-256哈希值
        hash_sha256 = hashlib.sha256(canonical_string_builder.encode()).hexdigest()
        # 构建StringToSign
        string_to_sign = (
                algorithm + '\n' +
                self._x_date + '\n' +
                credential_scope + '\n' +
                hash_sha256
        )

        # 假设这些变量已经被赋值
        service = "armcloud-paas"  # 服务名

        # 第一次hmacSHA256
        first_hmac = hmac.new(self._sk.encode(), digestmod=hashlib.sha256)
        first_hmac.update(short_x_date.encode())
        first_hmac_result = first_hmac.digest()

        # 第二次hmacSHA256
        second_hmac = hmac.new(first_hmac_result, digestmod=hashlib.sha256)
        second_hmac.update(service.encode())
        second_hmac_result = second_hmac.digest()

        # 第三次hmacSHA256
        signing_key = hmac.new(second_hmac_result, b'request', digestmod=hashlib.sha256).digest()

        # 使用signing_key和string_to_sign计算HMAC-SHA256
        signature_bytes = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).digest()

        # 将HMAC-SHA256的结果转换为十六进制编码的字符串
        signature = binascii.hexlify(signature_bytes).decode()

        return signature


    # def _paas_url_util(self):
    #     ShortDate = self._x_date[:8]
    #     host = "openapi-hk.armcloud.net"
    #     # 获取signature
    #     signature = self._get_signature()
    #     url = f"http://openapi-hk.armcloud.net{self._url}"
    #     payload = json.dumps(self._data)
    #     headers = {
    #         'Content-Type': self._content_type,
    #         'x-date': self._x_date,
    #         'x-host': host,
    #         'authorization': f"HMAC-SHA256 Credential={self._ak}/{ShortDate}/armcloud-paas/request, SignedHeaders=content-type;host;x-content-sha256;x-date, Signature={signature}"
    #     }
    #     response = requests.request("POST", url, headers=headers, data=payload)
    #     return response.json()


    async def send(self):
        signature = self._get_signature()
        url = f"https://api.vmoscloud.com{self._url}"
        payload = json.dumps(self._data, ensure_ascii=False)
        headers = {
            'content-type': "application/json;charset=UTF-8",
            'x-date': self._x_date,
            'x-host': "api.vmoscloud.com",
            'authorization': f"HMAC-SHA256 Credential={self._ak}, SignedHeaders=content-type;host;x-content-sha256;x-date, Signature={signature}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=payload) as response:
                return await response.json()


