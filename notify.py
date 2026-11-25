# -*- coding: utf-8 -*-
"""可选的 Telegram 签到结果通知。"""

from __future__ import annotations

import html
import logging
import os
import time
from datetime import datetime
from typing import Any

import requests

log = logging.getLogger("nodeloc")

MAX_LEN = 3900


def _env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return ""


def _config() -> tuple[str, str]:
    token = _env("TG_BOT_TOKEN", "TELEGRAM_BOT_TOKEN", "NL_TG_BOT_TOKEN")
    chat_id = _env("TG_CHAT_ID", "TELEGRAM_CHAT_ID", "NL_TG_CHAT_ID")
    return token, chat_id


def _should_notify(failed: int) -> bool:
    mode = _env("TG_NOTIFY_ON").lower() or "always"
    if mode in {"never", "off", "0", "false", "no"}:
        return False
    if mode in {"failure", "fail", "error", "errors"}:
        return failed > 0
    if mode in {"success", "ok", "always", "all"}:
        return True
    log.warning("未知的 TG_NOTIFY_ON=%s，按 always 处理", mode)
    return True


def format_summary(
    records: list[dict[str, Any]],
    total: int,
    failed: int,
    dry_run: bool,
) -> str:
    title = "NodeLoc 签到检查" if dry_run else "NodeLoc 每日签到"
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
    state = f"共 {total} 个账号：{total - failed} 成功，{failed} 失败"
    lines = [
        f"<b>{html.escape(title)}</b>",
        html.escape(stamp),
        html.escape(state),
    ]
    if dry_run:
        lines.append("模式：只读检查，未执行签到")
    lines.append("")

    for record in records:
        index = record.get("account", "?")
        if record.get("ok"):
            username = html.escape(str(record.get("username") or "未知用户"))
            balance = record.get("balance")
            suffix = f"，当前能量 {balance}" if isinstance(balance, int) else ""
            if record.get("dry_run"):
                state_text = "今日已签到" if record.get("checked_in_today") else "今日尚未签到"
                line = f"ℹ️ {username}：{state_text}{suffix}"
            elif record.get("already_checked_in"):
                line = f"✅ {username}：今日已签到{suffix}"
            else:
                points = record.get("points")
                gain = f"，+{points} 能量" if isinstance(points, int) else ""
                line = f"🎉 {username}：签到成功{gain}{suffix}"
                if record.get("verified") is False:
                    line += "（状态复核未通过）"
            note = record.get("note")
            if note and not record.get("dry_run"):
                line += f"\n   ⚠️ {html.escape(str(note)[:200])}"
            lines.append(line)
        else:
            username = html.escape(str(record.get("username") or f"账号 #{index}"))
            error = html.escape(str(record.get("error") or "未知错误")[:200])
            lines.append(f"❌ {username}：{error}")

    text = "\n".join(lines).strip()
    if len(text) > MAX_LEN:
        text = text[: MAX_LEN - 24].rstrip() + "\n…（内容已截断）"
    return text


def send_telegram(text: str) -> bool:
    token, chat_id = _config()
    if not token or not chat_id:
        log.debug("未配置 Telegram，跳过通知")
        return False

    api_base = (_env("TG_API_BASE") or "https://api.telegram.org").rstrip("/")
    url = f"{api_base}/bot{token}/sendMessage"
    timeout = 15.0
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    thread_id = _env("TG_MESSAGE_THREAD_ID", "TG_THREAD_ID")
    if thread_id:
        try:
            payload["message_thread_id"] = int(thread_id)
        except ValueError:
            log.warning("TG_MESSAGE_THREAD_ID 必须是数字，已忽略")

    for attempt in range(2):
        try:
            response = requests.post(url, json=payload, timeout=timeout)
        except requests.RequestException as exc:
            log.warning(
                "Telegram 通知请求失败（第 %d 次，%s）",
                attempt + 1,
                type(exc).__name__,
            )
            if attempt == 0:
                time.sleep(1)
                continue
            return False

        if response.ok:
            try:
                body = response.json()
            except ValueError:
                body = None
            if isinstance(body, dict) and body.get("ok") is False:
                detail = str(body.get("description") or "")
                log.warning("Telegram 通知失败：%s", detail[:180])
                return False
            log.info("Telegram 通知已发送")
            return True

        detail = ""
        try:
            body = response.json()
            if isinstance(body, dict):
                detail = str(body.get("description") or "")
        except ValueError:
            detail = response.text[:120]
        log.warning("Telegram 通知失败：HTTP %d %s", response.status_code, detail[:180])
        if response.status_code >= 500 and attempt == 0:
            time.sleep(1)
            continue
        return False
    return False


def notify_checkin(
    records: list[dict[str, Any]],
    total: int,
    failed: int,
    dry_run: bool,
) -> bool:
    if not _should_notify(failed):
        return False
    return send_telegram(format_summary(records, total, failed, dry_run))
