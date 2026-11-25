# -*- coding: utf-8 -*-
"""NodeLoc 每日签到入口。"""

from __future__ import annotations

import argparse
import json
import logging
import os
import pathlib
import sys
import time
from typing import Any

from client import (
    ConfigError,
    NodelocClient,
    NodelocError,
    SessionExpiredError,
    parse_cookie_accounts,
)
from notify import notify_checkin

ROOT = pathlib.Path(__file__).resolve().parent
log = logging.getLogger("nodeloc")


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass


def read_cookie_file(path: str) -> str:
    file_path = pathlib.Path(path).expanduser()
    try:
        return file_path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ConfigError(f"读取 Cookie 文件失败：{file_path}（{exc}）") from exc


def collect_cookie_text(args: argparse.Namespace) -> str:
    parts = list(args.cookie)
    for path in args.cookie_file:
        parts.append(read_cookie_file(path))
    if parts:
        return "\n".join(parts)

    env_cookie = os.environ.get("NL_COOKIE", "")
    if env_cookie.strip():
        return env_cookie

    env_file = os.environ.get("NL_COOKIE_FILE", "")
    if env_file.strip():
        return read_cookie_file(env_file.strip())

    default_file = ROOT / "cookie.txt"
    if default_file.is_file():
        return read_cookie_file(str(default_file))

    raise ConfigError(
        "未配置 Cookie：请设置 NL_COOKIE，或创建 cookie.txt"
        "（也可用 --cookie-file 指定）"
    )


def decode_escaped_newlines(text: str) -> str:
    if "\n" not in text and "\\n" in text:
        return text.replace("\\r\\n", "\n").replace("\\n", "\n")
    return text


def energy_suffix(balance: int | None) -> str:
    if balance is None:
        return ""
    return f"；当前能量 {balance}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="NodeLoc 新站每日签到（支持多账号）",
        epilog="Telegram 通知：设置 TG_BOT_TOKEN、TG_CHAT_ID；"
        "TG_NOTIFY_ON=always|failure|never。",
    )
    parser.add_argument(
        "--cookie",
        action="append",
        default=[],
        metavar="COOKIE",
        help="直接传入 Cookie 请求头，可重复",
    )
    parser.add_argument(
        "--cookie-file",
        action="append",
        default=[],
        metavar="PATH",
        help="从文件读取 Cookie（一行一个账号），可重复",
    )
    parser.add_argument("--dry-run", action="store_true", help="只查询状态，不签到")
    parser.add_argument("--json", action="store_true", help="输出 JSON 结果")
    parser.add_argument("--debug", action="store_true", help="输出调试日志")
    parser.add_argument("--timeout", type=float, default=30.0, help="请求超时秒数")
    parser.add_argument("--retries", type=int, default=3, help="失败重试次数")
    parser.add_argument("--delay", type=float, default=5.0, help="多账号间隔秒数")
    return parser


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.timeout <= 0:
        parser.error("--timeout 必须大于 0")
    if not 0 <= args.retries <= 10:
        parser.error("--retries 必须在 0 到 10 之间")
    if args.delay < 0:
        parser.error("--delay 不能为负数")


def process_account(
    index: int,
    total: int,
    cookie: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "account": index,
        "dry_run": bool(args.dry_run),
    }
    client: NodelocClient | None = None
    try:
        client = NodelocClient(cookie, timeout=args.timeout, retries=args.retries)
        record["account_id"] = client.account_id
        log.info("—— 账号 %d/%d（%s）——", index, total, client.account_id)

        if args.dry_run:
            username, checked, balance = client.probe()
            state = "今日已签到" if checked else "今日尚未签到"
            log.info("[ℹ️] %s %s%s", username, state, energy_suffix(balance))
            record.update(
                {
                    "ok": True,
                    "username": username,
                    "checked_in_today": checked,
                    "balance": balance,
                }
            )
            return record

        outcome = client.check_in()
        if outcome.already_checked_in:
            log.info(
                "[✅] %s 今日已签到%s",
                outcome.username,
                energy_suffix(outcome.balance),
            )
        else:
            gained = ""
            if outcome.points is not None:
                gained = f"，+{outcome.points} 能量"
            log.info(
                "[🎉] %s 签到成功%s%s",
                outcome.username,
                gained,
                energy_suffix(outcome.balance),
            )
        if outcome.note:
            log.warning("[⚠️] %s %s", outcome.username, outcome.note)

        record.update(
            {
                "ok": True,
                "username": outcome.username,
                "already_checked_in": outcome.already_checked_in,
                "points": outcome.points,
                "balance": outcome.balance,
                "verified": outcome.verified,
            }
        )
        if outcome.note:
            record["note"] = outcome.note
        return record

    except ConfigError as exc:
        log.error("[❌] 账号 %d/%d 配置错误：%s", index, total, exc)
        record.update({"ok": False, "error_code": "config", "error": str(exc)})
    except SessionExpiredError as exc:
        log.error("[❌] 账号 %d/%d Cookie 已失效：%s", index, total, exc)
        record.update(
            {
                "ok": False,
                "error_code": "session_expired",
                "status": exc.status,
                "error": str(exc),
            }
        )
    except NodelocError as exc:
        log.error("[❌] 账号 %d/%d 签到失败：%s", index, total, exc)
        record.update(
            {
                "ok": False,
                "error_code": exc.code or "request_failed",
                "status": exc.status,
                "error": str(exc),
            }
        )
    except Exception as exc:
        log.error("[❌] 账号 %d/%d 出现未预期错误：%s", index, total, exc)
        if args.debug:
            log.exception("调用栈")
        record.update({"ok": False, "error_code": "unexpected", "error": str(exc)})
    finally:
        if client is not None:
            client.close()
    return record


def main(argv: list[str] | None = None) -> int:
    configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_args(parser, args)

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr if args.json else sys.stdout,
        force=True,
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    try:
        raw = decode_escaped_newlines(collect_cookie_text(args))
        cookies = parse_cookie_accounts(raw)
    except ConfigError as exc:
        log.error("[❌] %s", exc)
        return 2

    if not cookies:
        log.error("[❌] 没有找到有效的 Cookie")
        return 2

    total = len(cookies)
    log.info("共 %d 个账号，开始%s", total, "检查" if args.dry_run else "签到")
    records: list[dict[str, Any]] = []
    failed = 0

    try:
        for index, cookie in enumerate(cookies, start=1):
            record = process_account(index, total, cookie, args)
            records.append(record)
            if not record.get("ok"):
                failed += 1
            if index < total and args.delay > 0:
                time.sleep(args.delay)
    except KeyboardInterrupt:
        log.error("已中断")
        return 130

    if args.json:
        print(json.dumps(records, ensure_ascii=False, indent=2))

    success = total - failed
    try:
        notify_checkin(records, total, failed, args.dry_run)
    except Exception as exc:
        log.warning("Telegram 通知发送失败：%s", type(exc).__name__)
    log.info("完成：%d 成功，%d 失败", success, failed)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
