import asyncio
import binascii
import datetime
import hashlib
import hmac
import json
from typing import Any, Optional

import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from loguru import logger


class VmosUtil(object):
    # Class-level session for connection reuse
    _session: Optional[ClientSession] = None
    _session_lock = asyncio.Lock()

    def __init__(self, url, data=None):
        if data is None:
            data = {}
        self._url = url
        self._data = data
        self._ak = "nx9xwcQ5KEap2nUqrJZTBoxJK7G61uvj"
        self._sk = "7xf9Q8D9VRBhzjWhgzwHx2AB"
        self._x_date = datetime.datetime.now().strftime("%Y%m%dT%H%M%SZ")
        self._content_type = "application/json;charset=UTF-8"
        self._signed_headers = "content-type;host;x-content-sha256;x-date"
        self._host = "api.vmoscloud.com"

    @classmethod
    async def get_session(cls) -> ClientSession:
        """Get or create a shared session with proper configuration"""
        async with cls._session_lock:
            if cls._session is None or cls._session.closed:
                # Configure connection pool and timeouts
                connector = TCPConnector(
                    limit=100,  # Total connection pool limit
                    limit_per_host=30,  # Per-host connection limit
                    ttl_dns_cache=300,  # DNS cache timeout
                    enable_cleanup_closed=True,  # Clean up closed connections
                    force_close=False,  # Don't force close connections
                    keepalive_timeout=30,  # Keep connections alive for 30 seconds
                )

                timeout = ClientTimeout(
                    total=60,  # Total timeout for the request
                    connect=10,  # Connection timeout
                    sock_connect=10,  # Socket connection timeout
                    sock_read=30,  # Socket read timeout
                )

                cls._session = ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={
                        'User-Agent': 'VmosClient/1.0',
                        'Accept': 'application/json',
                        'Connection': 'keep-alive',
                    }
                )
                logger.info("Created new aiohttp session for VmosUtil")

            return cls._session

    @classmethod
    async def close_session(cls):
        """Close the shared session"""
        async with cls._session_lock:
            if cls._session and not cls._session.closed:
                await cls._session.close()
                cls._session = None
                logger.info("Closed VmosUtil session")

    def _get_signature(self):
        json_string: Any = json.dumps(
            self._data, separators=(",", ":"), ensure_ascii=False
        )
        # 计算SHA-256哈希值
        hash_object = hashlib.sha256(json_string.encode())
        x_content_sha256 = hash_object.hexdigest()

        # 使用f-string构建canonicalStringBuilder
        canonical_string_builder: Any = (
            f"host:{self._host}\n"
            f"x-date:{self._x_date}\n"
            f"content-type:{self._content_type}\n"
            f"signedHeaders:{self._signed_headers}\n"
            f"x-content-sha256:{x_content_sha256}"
        )

        short_x_date = self._x_date[:8]
        service = "armcloud-paas"  # 服务名

        # 构建credentialScope
        credential_scope = "{}/{}/request".format(short_x_date, service)

        # 假设这些变量已经被赋值
        algorithm = "HMAC-SHA256"

        # 计算canonicalStringBuilder的SHA-256哈希值
        hash_sha256 = hashlib.sha256(canonical_string_builder.encode()).hexdigest()
        # 构建StringToSign
        string_to_sign = (
                algorithm
                + "\n"
                + self._x_date
                + "\n"
                + credential_scope
                + "\n"
                + hash_sha256
        )

        # 假设这些变量已经被赋值
        service = "armcloud-paas"  # 服务名

        # 第一次hmacSHA256
        first_hmac: Any = hmac.new(self._sk.encode(), digestmod=hashlib.sha256)
        first_hmac.update(short_x_date.encode())
        first_hmac_result = first_hmac.digest()

        # 第二次hmacSHA256
        second_hmac: Any = hmac.new(first_hmac_result, digestmod=hashlib.sha256)
        second_hmac.update(service.encode())
        second_hmac_result = second_hmac.digest()

        # 第三次hmacSHA256
        signing_key = hmac.new(
            second_hmac_result, b"request", digestmod=hashlib.sha256
        ).digest()

        # 使用signing_key和string_to_sign计算HMAC-SHA256
        signature_bytes: Any = hmac.new(
            signing_key, string_to_sign.encode(), hashlib.sha256
        ).digest()

        # 将HMAC-SHA256的结果转换为十六进制编码的字符串
        signature = binascii.hexlify(signature_bytes).decode()

        return signature

    async def send(self, max_retries: Any = 3, retry_delay: Any = 1.0) -> dict:
        signature = self._get_signature()
        url = f"https://api.vmoscloud.com{self._url}"
        payload = json.dumps(self._data, ensure_ascii=False)
        headers = {
            "content-type": "application/json;charset=UTF-8",
            "x-date": self._x_date,
            "x-host": "api.vmoscloud.com",
            "authorization": f"HMAC-SHA256 Credential={self._ak}, SignedHeaders=content-type;host;x-content-sha256;x-date, Signature={signature}",
        }

        last_exception = None

        for attempt in range(max_retries):
            try:
                session = await self.get_session()

                # Log the attempt
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries} for {self._url}")

                async with session.post(
                        url,
                        headers=headers,
                        data=payload,
                        timeout=ClientTimeout(total=30, connect=10, sock_read=20)
                ) as response:
                    # Check response status
                    if response.status == 200:
                        return await response.json()
                    elif response.status >= 500:
                        # Server error, retry
                        error_text = await response.text()
                        logger.warning(f"Server error {response.status}: {error_text}")
                        last_exception = aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=error_text,
                            headers=response.headers
                        )
                    else:
                        # Client error, don't retry
                        error_text = await response.text()
                        logger.error(f"Client error {response.status}: {error_text}")
                        return {
                            "code": response.status,
                            "msg": f"Request failed: {error_text}",
                            "data": None
                        }

            except aiohttp.ClientConnectorError as e:
                # Connection establishment error
                logger.warning(f"Connector error on attempt {attempt + 1}: {e}")
                last_exception = e
            except aiohttp.ClientOSError as e:
                # Connection reset or network error
                logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
                last_exception = e

                # Recreate session on connection errors
                await self.close_session()

            except asyncio.TimeoutError as e:
                # Timeout error
                logger.warning(f"Timeout error on attempt {attempt + 1}: {e}")
                last_exception = e

            except Exception as e:
                # Other unexpected errors
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                last_exception = e

            # If this wasn't the last attempt, wait before retrying
            if attempt < max_retries - 1:
                delay = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Waiting {delay:.1f} seconds before retry...")
                await asyncio.sleep(delay)

        # All retries exhausted
        logger.error(f"All {max_retries} attempts failed for {self._url}")

        # Return error response
        return {
            "code": 500,
            "msg": f"Request failed after {max_retries} attempts: {str(last_exception)}",
            "data": None
        }