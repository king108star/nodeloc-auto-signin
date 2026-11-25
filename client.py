# -*- coding: utf-8 -*-
"""NodeLoc 新站签到 API 客户端。"""

from __future__ import annotations

import hashlib
import logging
import re
import time
import uuid
from dataclasses import dataclass
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

BASE_URL = "https://www.nodeloc.com"
CHECKIN_PATH = "/api/v1/checkin"
POINTS_PATH = "/api/v1/points"
ME_PATH = "/api/v1/me"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/138.0.0.0 Safari/537.36"
)

_COOKIE_HEADER = re.compile(r"^\s*cookie\s*:\s*", re.IGNORECASE)
_CURL_COOKIE = re.compile(
    r"(?:-H|--header)\s+(['\"])cookie\s*:\s*(.*?)\1",
    re.IGNORECASE | re.DOTALL,
)


class NodelocError(RuntimeError):
    """NodeLoc 接口或网络错误。"""

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status

    def __str__(self) -> str:
        return self.message


class ConfigError(NodelocError):
    """本地配置错误。"""


class SessionExpiredError(NodelocError):
    """Cookie 缺失、失效或账号未登录。"""


@dataclass(frozen=True)
class CheckinOutcome:
    account_id: str
    username: str
    already_checked_in: bool
    points: int | None
    balance: int | None
    verified: bool
    note: str = ""


def _strip_matching_quotes(text: str) -> str:
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1].strip()
    return text


def normalize_cookie(raw: str) -> str:
    """接受 Cookie 值、`Cookie: ...` 请求头或 Chrome 的 cURL 片段。"""
    text = raw.strip().lstrip("\ufeff")
    if not text:
        return ""

    if text.lower().startswith("curl "):
        match = _CURL_COOKIE.search(text)
        if not match:
            raise ConfigError("看起来是 cURL 命令，但没有找到 cookie 请求头")
        text = match.group(2).strip()

    text = _COOKIE_HEADER.sub("", text, count=1)
    text = re.sub(r"\r?\n\s*", "", text).strip()
    return _strip_matching_quotes(text)


def parse_cookie_accounts(raw: str) -> list[str]:
    """一行一个账号；支持空行、`#` 注释和整段 cURL。"""
    text = raw.strip().lstrip("\ufeff")
    if not text:
        return []

    if text.lower().startswith("curl "):
        cookie = normalize_cookie(text)
        return [cookie] if cookie else []

    accounts: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if " #" in line:
            line = line.split(" #", 1)[0].rstrip()
        cookie = normalize_cookie(line)
        if not cookie:
            continue
        if "=" not in cookie:
            raise ConfigError(
                f"第 {number} 行不是有效的 Cookie（应形如 name=value; name2=value2）"
            )
        accounts.append(cookie)
    return accounts


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _error_code(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if isinstance(error, dict):
        code = error.get("code")
        return code if isinstance(code, str) else None
    code = payload.get("code")
    return code if isinstance(code, str) else None


def _error_message(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        return message if isinstance(message, str) and message.strip() else None
    if isinstance(error, str) and error.strip():
        return error
    message = payload.get("message")
    return message if isinstance(message, str) and message.strip() else None


class NodelocClient:
    def __init__(
        self,
        cookie: str,
        *,
        timeout: float = 30.0,
        retries: int = 3,
    ) -> None:
        self.cookie = normalize_cookie(cookie)
        if not self.cookie or "=" not in self.cookie:
            raise ConfigError("Cookie 为空或格式不正确")

        self.account_id = hashlib.sha256(
            self.cookie.encode("utf-8")
        ).hexdigest()[:8]
        self.timeout = float(timeout)

        retry = Retry(
            total=retries,
            connect=retries,
            read=retries,
            status=retries,
            backoff_factor=0.8,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET", "POST"}),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        self.session = requests.Session()
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Cookie": self.cookie,
                "Referer": BASE_URL + "/",
            }
        )

    def close(self) -> None:
        self.session.close()

    def _request(self, method: str, path: str) -> dict[str, Any]:
        url = BASE_URL + path
        headers: dict[str, str] = {}
        if method != "GET":
            headers.update(
                {
                    "Accept": "application/json, text/plain, */*",
                    "Origin": BASE_URL,
                    "Idempotency-Key": str(uuid.uuid4()),
                    "Sec-Fetch-Site": "same-origin",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Dest": "empty",
                }
            )

        try:
            response = self.session.request(
                method,
                url,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise NodelocError(f"请求超时：{method} {path}") from exc
        except requests.RequestException as exc:
            raise NodelocError(f"网络请求失败：{exc}") from exc

        return self._decode_response(response, method, path)

    def _decode_response(
        self,
        response: requests.Response,
        method: str,
        path: str,
    ) -> dict[str, Any]:
        data: Any = None
        if response.content:
            try:
                data = response.json()
            except ValueError:
                data = None

        code = _error_code(data)
        if response.status_code == 401 or (
            response.status_code == 403 and code == "unauthorized"
        ):
            message = _error_message(data) or "登录状态已失效"
            raise SessionExpiredError(
                f"Cookie 已失效或未登录（{message}）",
                code=code,
                status=response.status_code,
            )

        if response.status_code >= 400:
            message = _error_message(data)
            if message is None:
                message = f"HTTP {response.status_code}"
            if data is None:
                snippet = response.text[:160].replace("\n", " ").strip()
                if snippet:
                    message = f"{message}：{snippet}"
            raise NodelocError(
                f"{method} {path} 失败：{message}",
                code=code,
                status=response.status_code,
            )

        if response.status_code == 204 or not response.content:
            return {}
        if data is None:
            raise NodelocError(
                f"{method} {path} 返回了非 JSON 内容，可能 Cookie 已失效或站点有风控",
                status=response.status_code,
            )
        if not isinstance(data, dict):
            raise NodelocError(
                f"{method} {path} 返回格式异常：预期 JSON 对象",
                status=response.status_code,
            )
        if data.get("error"):
            message = _error_message(data) or "接口返回错误"
            raise NodelocError(
                message,
                code=_error_code(data),
                status=response.status_code,
            )
        return data

    def get_checkin_status(self) -> tuple[bool, dict[str, Any]]:
        data = self._request("GET", CHECKIN_PATH)
        value = data.get("checked_in_today")
        if value is None:
            value = data.get("checked_in")
        if value is None:
            raise NodelocError(
                "签到状态响应缺少 checked_in_today 字段",
                code="unexpected_response",
            )
        return bool(value), data

    def get_username(self) -> str:
        data = self._request("GET", ME_PATH)
        user = data.get("user")
        if not isinstance(user, dict):
            user = data
        for key in ("name", "username", "login", "display_name"):
            value = user.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return "未知用户"

    def get_balance(self) -> int | None:
        data = self._request("GET", POINTS_PATH)
        return _as_int(data.get("balance"))

    def _safe_username(self) -> str:
        try:
            return self.get_username()
        except NodelocError as exc:
            log.warning("读取账号名称失败：%s", exc)
            return "未知用户"

    def _safe_balance(self) -> int | None:
        try:
            return self.get_balance()
        except NodelocError as exc:
            log.warning("读取能量余额失败：%s", exc)
            return None

    def probe(self) -> tuple[str, bool, int | None]:
        """只读检查：返回账号名、今日是否已签到、当前能量。"""
        checked, _ = self.get_checkin_status()
        username = self._safe_username()
        balance = self._safe_balance()
        return username, checked, balance

    def check_in(self) -> CheckinOutcome:
        """查询状态并在需要时签到。已签到时不会重复 POST。"""
        checked, _ = self.get_checkin_status()
        username = self._safe_username()

        if checked:
            return CheckinOutcome(
                account_id=self.account_id,
                username=username,
                already_checked_in=True,
                points=None,
                balance=self._safe_balance(),
                verified=True,
            )

        try:
            payload = self._request("POST", CHECKIN_PATH)
        except SessionExpiredError:
            raise
        except NodelocError as exc:
            if exc.status == 429:
                raise
            checked_after_error = False
            try:
                checked_after_error, _ = self.get_checkin_status()
            except NodelocError as check_exc:
                log.debug("核对签到状态失败：%s", check_exc)
            if checked_after_error:
                return CheckinOutcome(
                    account_id=self.account_id,
                    username=username,
                    already_checked_in=True,
                    points=None,
                    balance=self._safe_balance(),
                    verified=True,
                    note=f"接口返回错误，但状态已更新：{exc}",
                )
            raise

        points = _as_int(payload.get("points"))
        balance = _as_int(payload.get("balance"))
        verified = False

        for attempt in range(3):
            try:
                verified, _ = self.get_checkin_status()
            except NodelocError as exc:
                log.warning("复核签到状态失败：%s", exc)
                verified = False
            if verified:
                break
            if attempt < 2:
                time.sleep(1)

        if balance is None:
            balance = self._safe_balance()

        note = "" if verified else "签到接口已返回成功，但状态复核未通过，请稍后到网页确认"
        return CheckinOutcome(
            account_id=self.account_id,
            username=username,
            already_checked_in=False,
            points=points,
            balance=balance,
            verified=verified,
            note=note,
        )

