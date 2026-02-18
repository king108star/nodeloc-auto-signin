# NodeLoc Auto-Check-in

> 基于 Selenium + undetected-chromedriver 的 NodeLoc 自动签到脚本  
> 适用于 **青龙（QingLong） / Linux Server / 本地 Python 环境**

---

## ✨ 项目简介

本项目是一个 **NodeLoc 论坛自动签到脚本**，  
通过模拟真实浏览器行为完成每日签到操作，支持：

- ✅ 多账号顺序签到  
- ✅ 无头 Chrome（Headless）  
- ✅ Cookie 登录（无需账号密码）  
- ✅ 适配青龙面板（QingLong）  
- ✅ 自动规避常见 Selenium 特征检测  
- ✅ Telegram 推送签到结果

项目结构清晰，代码已模块化拆分，  
同时也适合作为 **Selenium 自动化学习示例**。

---

## 📁 项目结构

```text
.
├── browser.py            # 浏览器创建 & Cookie 注入
├── checkin.py            # 登录检测 & 签到逻辑
├── main.py               # 程序入口 & 多账号调度
├── telegram_notifier.py  # Telegram 推送模块
├── requirements.txt
├── README.md
└── LICENSE
```

## 🚀 使用方式

### 1️⃣ 安装依赖

#### 安装 Chrome 浏览器

**方法 A：自动安装（推荐）**
```bash
chmod +x install_chrome.sh
./install_chrome.sh
```

**方法 B：手动安装 Google Chrome**
```bash
# 下载并安装
cd /tmp
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
sudo apt-get install -f -y

# 验证安装
google-chrome --version
```

**方法 C：安装 Chromium（备选）**
```bash
# Debian/Ubuntu
sudo apt install chromium -y

# 或者
sudo apt install chromium-browser -y
```

#### 安装 Python 依赖

```bash
pip install -r requirements.txt
# 或
pip3 install -r requirements.txt
```
### 2️⃣ 获取 Cookie
使用浏览器登录：https://www.nodeloc.com
打开开发者工具（F12）
在 Network / 请求头 / Application → Cookies 中获取完整 Cookie

### 3️⃣ 配置环境变量

**使用 .env 文件配置：**

```bash
# 1. 复制示例文件
cp .env.example .env

# 2. 编辑 .env 文件
nano .env

# 3. 填入配置（示例）
TG_BOT_TOKEN=你的Bot_Token
TG_CHAT_ID=你的Chat_ID
NL_COOKIE=_t=xxxxx; _forum_session=xxxxxx

# 4. 保存并设置权限
chmod 600 .env
```

**多账号配置示例：**
```bash
# .env 文件支持多行 Cookie
NL_COOKIE=_t=account1; _forum_session=session1
_t=account2; _forum_session=session2
_t=account3; _forum_session=session3
```

**Telegram 推送配置（可选）：**
- 与 [@BotFather](https://t.me/BotFather) 创建 Bot 获取 Token
- 与 [@userinfobot](https://t.me/userinfobot) 获取 Chat ID

### 4️⃣ 运行脚本
```bash
python3 main.py
```

### 5️⃣ 设置定时任务（可选）

使用 crontab 设置每天自动签到：

```bash
# 1. 创建日志目录
mkdir -p ~/nodeloc-auto-signin/logs

# 2. 编辑 crontab
crontab -e

# 3. 添加定时任务（每天 0:01 执行）
1 0 * * * cd ~/nodeloc-auto-signin && /usr/bin/python3 main.py >> ~/nodeloc-auto-signin/logs/cron.log 2>&1
```

**注意事项：**
- 确保已配置 `.env` 文件
- 确保服务器时区为北京时间：`timedatectl set-timezone Asia/Shanghai`
- 查看执行日志：`tail -f ~/nodeloc-auto-signin/logs/cron.log`

> **提示**：未配置 Telegram 推送时程序仍会正常运行，只是不会发送通知消息。

---

## � 故障排查

### 问题：浏览器启动失败（版本不匹配）

**症状：**
```
This version of ChromeDriver only supports Chrome version 145
Current browser version is 120.0.6099.224
```

**解决方案：**

```bash
# 方法 1：清理驱动缓存（推荐）
rm -rf ~/.local/share/undetected_chromedriver
python3 main.py

# 方法 2：使用检查脚本
chmod +x check_chrome.sh
./check_chrome.sh

# 方法 3：更新 Chrome 浏览器
# Ubuntu/Debian
sudo apt update && sudo apt upgrade chromium-browser

# CentOS/RHEL
sudo yum update chromium
```

### 问题：Cookie 失效

**症状：** 日志显示"登录失败，Cookie 可能失效"

**解决方案：**
1. 用无痕浏览器重新登录 NodeLoc
2. F12 → Application → Cookies → 复制新的 Cookie
3. 更新 `.env` 文件或 `run.sh` 中的 `NL_COOKIE`

### 问题：Telegram 推送失败

**检查：**
```bash
# 测试 Token 和 Chat ID 是否正确
curl -X POST "https://api.telegram.org/bot<你的TOKEN>/sendMessage" \
  -d "chat_id=<你的CHAT_ID>" \
  -d "text=测试消息"
```

---

## �📜 License
本项目采用 MIT License 开源协议。

## ⭐ Star
如果这个项目对你有帮助，欢迎点个 ⭐
你的支持是我继续维护和优化的动力 ❤️
