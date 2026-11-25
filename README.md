# NodeLoc 自动签到（新站适配版）

NodeLoc 站点改版后，顶部仍有签到按钮，但旧 Selenium 方案失效了：旧脚本依赖的
`li.header-dropdown-toggle.checkin-icon button.checkin-button` 选择器已经匹配不到
新按钮。新按钮由前端脚本渲染，点击后实际调用的是本站 JSON 接口。

本版改为直接调用新站前端正在使用的 JSON 接口，不再启动浏览器，也不需要
Chrome / Chromedriver：

- `GET /api/v1/checkin`：查询今天是否已签到
- `POST /api/v1/checkin`：执行签到
- `GET /api/v1/points`：查询当前能量
- `GET /api/v1/me`：查询当前账号名

脚本只复用你已经登录的 Cookie，支持多账号、重复执行幂等、成功后复核状态、
可选的 Telegram 通知，并带有 GitHub Actions 每日定时任务。

## 快速开始

```bash
python -m pip install -r requirements.txt
python main.py
```

首次使用前，需要把登录 Cookie 放到脚本同目录的 `cookie.txt`，或设置
`NL_COOKIE` 环境变量。详见下一节。

Windows 下如果 `python` 不在 PATH，可用：

```powershell
py -3 -m pip install -r requirements.txt
py -3 main.py
```

## 获取 Cookie

Cookie 等同于登录凭证，请只保存在自己的机器或仓库 Secret 中，不要提交、
截图或发到公开群组。

1. 在浏览器里登录 <https://www.nodeloc.com>。
2. 按 `F12` 打开开发者工具，切换到 **Network（网络）**。
3. 刷新页面，点开第一条 `www.nodeloc.com` 文档请求。
4. 在 **Request Headers（请求标头）** 中找到 `Cookie`，复制完整的值。
   不需要筛选 Cookie 名称，整段复制即可；不建议用无痕窗口，关闭后会话会消失。
5. 新建 `cookie.txt`，把值粘贴进去；一行一个账号。

`cookie.txt` 里可以只放 Cookie 的值，也可以放 `Cookie: ...` 前缀。
Chrome / Edge 的 “Copy as cURL” 整段粘贴也能识别（脚本会提取其中的
cookie 请求头）。

示例（实际值请勿公开）：

```text
session=xxxxxxxxxxxxxxxx; other_cookie=yyyyyyyy
# 第二行是第二个账号，空行和 # 开头的注释会被忽略
session=aaaaaaaaaaaaaaaa; other_cookie=bbbbbbbb
```

如果使用了 GitHub Actions，把上面的内容（多账号用换行分隔）保存到仓库
Secret `NL_COOKIE` 中即可，不需要提交 `cookie.txt`。

## 配置方式

按以下优先级读取：

1. `--cookie` 参数
2. `--cookie-file` 参数
3. `NL_COOKIE` 环境变量
4. `NL_COOKIE_FILE` 环境变量
5. 脚本同目录的 `cookie.txt`

多账号用换行分隔；`NL_COOKIE` 里写成字面量 `\n` 也会自动展开。

## 常用命令

```bash
# 正常签到
python main.py

# 只查询状态，不产生签到请求
python main.py --dry-run

# 输出 JSON（便于其它程序读取；日志走 stderr）
python main.py --json

# 指定 Cookie 文件
python main.py --cookie-file /path/to/cookie.txt

# 直接传 Cookie，临时测试
python main.py --cookie "session=xxxxx"

# 调试
python main.py --debug
```

退出码：

| 退出码 | 含义 |
| --- | --- |
| `0` | 所有账号都成功（含“今天已签到”） |
| `1` | 至少一个账号失败，例如 Cookie 失效、网络错误 |
| `2` | 没有配置 Cookie，或 Cookie 文件无法读取 |
| `130` | 被 Ctrl+C 中断 |

## 每天自动签到

### GitHub Actions（推荐）

仓库已包含 `.github/workflows/checkin.yml`，每天北京时间 **08:05** 运行一次，
对应 UTC `00:05`。这个时间点在站点自然日之内，避免因服务器时区不同在午夜
前后漏签。

1. 把本项目推送到 GitHub。
2. 打开 **Settings → Secrets and variables → Actions → New repository secret**。
3. Name 填 `NL_COOKIE`，Value 填 Cookie；多账号直接换行。
4. 打开 **Actions → NodeLoc 每日签到 → Run workflow** 手动跑一次，确认成功。

注意：

- GitHub 的定时任务可能有几分钟到几十分钟的延迟，这是正常现象。
- 公开仓库若连续 60 天没有提交，计划任务可能被自动暂停；到 Actions 页面
  重新启用即可。
- Secret 必须建在 `Secrets` 下，不能建在 `Variables` 下。
- Cookie 失效后工作流会失败，重新抓取并更新 Secret 即可。

### 青龙面板

```bash
pip3 install -r requirements.txt
```

环境变量：

```text
NL_COOKIE=<一行一个账号的完整 Cookie>
```

定时规则（容器时区为 Asia/Shanghai）：

```text
5 8 * * *
```

执行命令：

```text
python3 main.py
```

如果容器是 UTC 时区，定时规则改为 `5 0 * * *`。

### Windows 计划任务

把 Cookie 保存到 `cookie.txt`，然后在“任务计划程序”中新建每日任务：

```text
程序：C:\Python313\python.exe
参数："C:\path\to\main.py" --cookie-file "C:\path\to\cookie.txt"
起始于：C:\path\to
```

请把路径替换成实际位置，并确认运行任务的用户能读取 `cookie.txt`。

## Telegram 通知（可选）

不配置也能正常签到，只是不会发送消息。配置后每次签到结束会发送一条摘要，
包含成功/失败数量、每个账号的能量和错误原因；不会包含 Cookie 的值。

在 Telegram 里找 `@BotFather` 创建机器人，拿到 Bot Token；再让机器人进入
目标会话，取得 Chat ID。

| 环境变量 | 必需 | 说明 |
| --- | --- | --- |
| `TG_BOT_TOKEN` | 是 | BotFather 给的机器人 Token |
| `TG_CHAT_ID` | 是 | 私聊、群组或频道的 Chat ID，例如 `123456789`、`-1001234567890`、`@channel` |
| `TG_NOTIFY_ON` | 否 | `always`（默认）、`failure` 只推失败、`never` 关闭 |
| `TG_API_BASE` | 否 | 自定义 Bot API 地址，默认 `https://api.telegram.org`，末尾不要带 `/` |
| `TG_MESSAGE_THREAD_ID` | 否 | 群组话题（Topic）下的消息线程 ID |

本地测试：

```powershell
$env:TG_BOT_TOKEN = "123456:ABC..."
$env:TG_CHAT_ID = "123456789"
python main.py --dry-run
```

GitHub Actions 中，在仓库 Secret 里新增同名变量 `TG_BOT_TOKEN` 和
`TG_CHAT_ID` 即可；不添加就不发通知。工作流的发送步骤被单独捕获，Telegram
网络故障只会打印警告，不会影响签到本身和签到退出码。

Bot Token 也是凭证。不要写进仓库、截图或发到公开群组；泄露后到
`@BotFather` 执行 `/revoke` 重新生成。

## 行为说明

- 网页顶部的签到按钮带 `data-checkin` 属性；点击它时，前端执行的就是
  `POST /api/v1/checkin`，所以本脚本直接用接口可完成同样动作，且无需浏览器。
- 先 `GET /api/v1/checkin`，如果 `checked_in_today` 为 `true`，直接结束，
  不会重复签到。
- 未签到时发送 `POST /api/v1/checkin`。
- POST 成功后再次查询状态，并读取能量余额。
- 如果 POST 报错但状态已变为“已签到”（例如并发或重试导致），按成功处理。
- 网络错误、429 和 5xx 会带退避重试；每次签到调用生成一个
  `Idempotency-Key`，底层重试沿用同一个键，避免重复记账。
- 日志不会打印 Cookie 内容，只显示 Cookie 的 8 位哈希标识，便于区分账号。

## 常见问题

**提示 `Cookie 已失效或未登录（请先登录）`**

Cookie 复制不完整、账号已退出，或站点轮换了会话。重新登录后按上文再复制一次。
注意要复制 **Request Headers** 里的 `Cookie`，不是响应里的 `Set-Cookie`。

**返回 403 或 HTML、提示“非 JSON 内容”**

通常是站点风控或接口变更。先确认网页还能正常签到；若网页正常而脚本不行，
请更新脚本。不要把完整 Cookie 贴到 issue 里。

**GitHub Actions 失败，本地却正常**

检查 `NL_COOKIE` Secret 是否为空、是否包含了完整 Cookie、多账号是否用换行分隔。
Secret 更新后需要重新运行工作流。

**Cookie 多久失效？**

取决于站点会话策略，脚本无法续期。建议每周手动跑一次，或关注 Actions 失败通知。

## 说明

本项目的接口来自 NodeLoc 网页前端，不是官方文档化 API，站点更新后可能再次失效。
请仅用于自己的账号，保持低频访问，并遵守站点规则。

## License

MIT
