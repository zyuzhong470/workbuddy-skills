# TradingView CDP 环境搭建经验教训

> 日期: 2026-07-06 | 来源: 小爪实战踩坑记录

---

## 背景

目标是让 WorkBuddy AI Agent 能通过 CDP (Chrome DevTools Protocol) 自动操作 TradingView，实现 Pine Script 代码一键上传。结果踩了五个大坑。

---

## 坑 #1: MSIX 版 TV Desktop 不支持 CDP

**现象:** 无论怎么加 `--remote-debugging-port=9222`，端口都不开。

**原因:** Windows 商店安装的 TradingView Desktop 是 MSIX 打包版（`C:\Program Files (x86)\TradingView\`），AppX 沙箱拦截了所有命令行参数。Electron 根本收不到 `--remote-debugging-port`。

**解决方案:** 弃用 TV Desktop，改用浏览器 + CDP。

**如何识别 MSIX 版:**
- 文件夹里有 `AppxManifest.xml` → MSIX
- 从 Microsoft Store 安装 → MSIX
- 官网 `.exe` 标准安装包 → 普通 Electron，CDP 可用

---

## 坑 #2: Chrome 默认 Profile 静默失败

**现象:** Chrome 启动正常，TradingView 页面正常打开，但端口 9222 **就是不监听**。没有任何报错。

**原因:** Chrome 默认 profile (`User Data`) 有后台进程或残留锁文件时，新进程不会报错也不会监听 CDP 端口——直接默默忽略。

**解决方案:** 使用独立临时 profile：
```powershell
--user-data-dir="C:\Users\Administrator\AppData\Local\Temp\tv_cdp_chrome"
```

代价：每次都要重新登录 TradingView。

---

## 坑 #3: Kill 不够快

**现象:** kill 完立刻 relaunch，端口依然不开。

**原因:** `Stop-Process` 是异步的，Chrome 进程需要时间释放文件锁和端口。

**解决方案:** kill 后至少等 **5 秒**。

---

## 坑 #4: IPv6 绑定

**现象:** curl `localhost:9222` 不通，但 `netstat` 显示端口在监听。

**原因:** Chrome 绑到了 `[::1]:9222` (IPv6)，curl 默认走 `127.0.0.1` (IPv4)。

**解决方案:** 加 `--remote-debugging-address=127.0.0.1`。

---

## 坑 #5: 登录状态丢失

**现象:** 临时 profile 没有 cookies，TradingView 未登录。

**解决方案（按优先级）:**
1. **最佳:** 用 Yandex 浏览器默认 profile → 登录一次永久保留
2. **次选:** Chrome 临时 profile → 每次手动登录
3. **进阶:** 用 CDP WebSocket 注入 cookies 或 OAuth token

---

## 已验证的有效启动命令

```powershell
# 1. 杀干净
Get-Process -Name chrome,browser -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 5

# 2. 起 Chrome + CDP
$exe = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$p = "C:\Users\Administrator\AppData\Local\Temp\tv_cdp_chrome"
mkdir $p -Force | Out-Null
Start-Process $exe -ArgumentList @(
  "--remote-debugging-port=9222",
  "--remote-debugging-address=127.0.0.1",
  "--user-data-dir=`"$p`"",
  "--no-first-run",
  "https://cn.tradingview.com/chart/"
)
Start-Sleep -Seconds 10

# 3. 验证
netstat -ano | grep "9222"          # 应该有 LISTENING
curl -s http://127.0.0.1:9222/json/list | grep "tradingview.com/chart"
```

---

## 新机器 Checklist

1. 装 Chrome（不要装 MSIX 版 TV Desktop）
2. 配 MCP: `~/.workbuddy/mcp.json` → tradingview 连 `127.0.0.1:9222`
3. PowerShell kill → 等 5s → 起 Chrome 临时 profile + CDP
4. `curl 127.0.0.1:9222/json/list` → 确认有 `tradingview.com/chart` 页面
5. 浏览器里登录 TradingView（Google/邮箱）
6. 可以开始自动化！

---

## 相关技能

- `tv-pine-upload` — Pine Script v6 一键上传到 TradingView
- 位置: `workbuddy-skills/tv-pine-upload/SKILL.md`
