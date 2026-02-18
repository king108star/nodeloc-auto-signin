# -*- coding: utf-8 -*-
import os
import logging
import requests
from typing import Optional

log = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram 消息推送器"""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        初始化 Telegram 推送器
        
        Args:
            bot_token: Telegram Bot Token (可从环境变量 TG_BOT_TOKEN 获取)
            chat_id: Telegram Chat ID (可从环境变量 TG_CHAT_ID 获取)
        """
        self.bot_token = bot_token or os.environ.get("TG_BOT_TOKEN", "")
        self.chat_id = chat_id or os.environ.get("TG_CHAT_ID", "")
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if not self.enabled:
            log.info("📱 Telegram 推送未配置，将跳过消息推送")
        else:
            log.info("📱 Telegram 推送已启用")

    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        发送 Telegram 消息
        
        Args:
            message: 消息内容
            parse_mode: 解析模式，支持 "HTML" 或 "Markdown"
        
        Returns:
            bool: 是否发送成功
        """
        if not self.enabled:
            log.debug("Telegram 推送未启用，跳过发送")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode,
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            if response.json().get("ok"):
                log.info("✅ Telegram 消息发送成功")
                return True
            else:
                log.error(f"❌ Telegram 消息发送失败: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            log.error("❌ Telegram 消息发送超时")
            return False
        except requests.exceptions.RequestException as e:
            log.error(f"❌ Telegram 消息发送异常: {e}")
            return False
        except Exception as e:
            log.error(f"❌ Telegram 未知错误: {e}")
            return False

    def format_results(self, results: list, title: str = "NodeLoc 签到结果") -> str:
        """
        格式化签到结果为 Telegram 消息
        
        Args:
            results: 签到结果列表
            title: 消息标题
        
        Returns:
            str: 格式化后的消息
        """
        from datetime import datetime
        
        # 统计结果
        success_count = sum(1 for r in results if "🎉" in r or "✅" in r)
        fail_count = sum(1 for r in results if "❌" in r)
        warning_count = sum(1 for r in results if "⚠️" in r)
        total_count = len(results)
        
        # 构建消息
        message_lines = [
            f"<b>📊 {title}</b>",
            f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"📈 总计: {total_count} 个账号",
            f"✅ 成功: {success_count}",
            f"❌ 失败: {fail_count}",
            f"⚠️ 警告: {warning_count}",
            "",
            "<b>详细结果:</b>",
        ]
        
        # 添加每个账号的结果
        for result in results:
            # HTML 转义
            result_escaped = result.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            message_lines.append(result_escaped)
        
        return "\n".join(message_lines)
