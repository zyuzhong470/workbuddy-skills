---
name: tv-pine-upload
description: Upload Pine Script v6 code to TradingView via browser CDP (Yandex/Chrome). Auto-fixes common v6 compatibility errors (ta.sum→math.sum, single-line semicolons, line continuation, forward reference). Uses PowerShell to launch browser (bash sandbox strips Yandex profile writes). Verifies compilation and saves as named script to prevent code loss on refresh.
agent_created: true
---

# TV Pine Upload: Browser CDP → TradingView Pine Editor

## Overview

Upload Pine Script v6 code to TradingView via browser CDP (Chrome DevTools Protocol).
Uses Yandex Browser/Chrome with `--remote-debugging-port=9222` + TradingView MCP.

**Prerequisites:**
- Yandex Browser or Chrome installed
- TradingView MCP configured in `~/.workbuddy/mcp.json`
- TradingView account logged in (Pine Editor requires login)

## ⚠️ Critical Pitfalls (Read First)

### 1. MSIX Desktop App Does NOT Support CDP
TradingView Desktop (Microsoft Store / MSIX installation) **cannot** be debugged via CDP.
The `--remote-debugging-port` flag is rejected, and `NODE_OPTIONS=--require hook.js` injection breaks ICU data loading (`Invalid file descriptor to ICU data received` in debug.log → crash on startup).

**How to identify MSIX vs EXE version:**
- Path contains `C:\Program Files (x86)\TradingView\` + folder has `AppxManifest.xml` → MSIX (reject)
- Installed from Microsoft Store or `App Installer` → MSIX (reject)
- Standard installer `.exe` from tradingview.com → regular Electron (CDP works)

**Must use Yandex Browser or Chrome instead of TradingView Desktop.**

### 2. NEVER Use `mcp__tradingview__tv_launch` (Yandex Hijacks Port)
The `tv_launch` tool auto-detects any Chromium browser with CDP. If TradingView Desktop isn't running with CDP (it can't, see above), `tv_launch` falls back to Yandex Browser — but launches it as a **blank page**, not TradingView. The 9222 port gets hijacked by an empty Yandex tab, and all subsequent `pine_*` calls fail with "No TradingView chart target found."

**Always launch the browser manually via PowerShell (Step 2 below), never via `tv_launch`.**

### 3. Bash Sandbox Strips Yandex Profile Writes (MUST Use PowerShell)
Launching Yandex Browser from bash fails with:
```
Lock file can not be created! Error code: 5
Failed to create a ProcessSingleton for your profile directory.
```
The bash sandbox strips write access to `C:\Users\Administrator\AppData\Local\Yandex\...`, so Yandex cannot create its process singleton lock → startup aborts to avoid profile corruption.

**MUST use PowerShell `Start-Process` to launch the browser.** See Step 2.

### 4. Chrome Default Profile Blocks CDP Port (MUST Use Temp Profile)
When Chrome's default user profile (`C:\Users\Administrator\AppData\Local\Google\Chrome\User Data`) is already in use by a background Chrome process or has a stale lock file, launching with `--remote-debugging-port=9222` will silently fail — the browser starts but port 9222 never opens.

**Always use a fresh temp profile for Chrome CDP.** Yandex Browser can use its default profile because it's less likely to have a conflicting session.

### 5. Always Kill Browser Processes + Wait 5 Seconds
`Stop-Process` is async — Chrome processes take a moment to fully exit. If you relaunch too fast, the new process shares the old profile silently and CDP flags are ignored.

**Minimum 5 seconds after kill before relaunch.**

## Workflow

### 1. Kill Existing Browser Instances (PowerShell)

```powershell
Get-Process -Name chrome,browser -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 5
```

**CRITICAL: Wait at least 5 seconds.** Chrome takes time to fully exit — relaunching too soon causes profile conflicts and CDP port silently fails.

Verify nothing left:
```powershell
Get-Process -Name chrome,browser -ErrorAction SilentlyContinue   # should be empty
```

Verify port 9222 is free:
```bash
netstat -ano | grep ":9222"   # should be empty
```

### 2. Launch Browser with CDP (PowerShell — CRITICAL)

```powershell
# Yandex (recommended - preserves login via default user-data-dir)
$exe = "C:\Program Files\Yandex\YandexBrowser\Application\browser.exe"
$udd = "C:\Users\Administrator\AppData\Local\Yandex\YandexBrowser\User Data"
Start-Process -FilePath $exe -ArgumentList @(
  "--remote-debugging-port=9222",
  "--user-data-dir=`"$udd`"",
  "--no-first-run",
  "--no-default-browser-check",
  "https://www.tradingview.com/chart/"
)
Start-Sleep -Seconds 10
```

```powershell
# Chrome (alternative - MUST use temp profile; default profile conflicts with CDP)
$exe = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$tempProfile = "C:\Users\Administrator\AppData\Local\Temp\tv_cdp_chrome"
if (!(Test-Path $tempProfile)) { New-Item -ItemType Directory -Path $tempProfile -Force | Out-Null }

Start-Process -FilePath $exe -ArgumentList @(
  "--remote-debugging-port=9222",
  "--remote-debugging-address=127.0.0.1",
  "--user-data-dir=`"$tempProfile`"",
  "--no-first-run",
  "--no-default-browser-check",
  "--disable-features=RendererCodeIntegrity",
  "https://cn.tradingview.com/chart/"
)
Start-Sleep -Seconds 10
```

**Key points:**
- Yandex default profile → preserves login state (no re-login needed)
- Chrome **MUST** use temp profile → default profile silently ignores CDP flags
- `--remote-debugging-address=127.0.0.1` prevents IPv6 binding issues
- Wait 10s for browser to start and TradingView chart to load
- TV URL: use `cn.tradingview.com` for Chinese region / `www.tradingview.com` for global

**Verify CDP is live:**
```bash
netstat -ano | grep ":9222"   # should show LISTENING
curl -s http://127.0.0.1:9222/json/list | grep "tradingview.com/chart"
```

### 3. Verify MCP Connection

Use `mcp__tradingview__tv_health_check` — confirm:
- `cdp_connected: true`
- `target_url` contains `tradingview.com/chart`
- `chart_symbol` is present

If `cdp_connected: false` or no chart target, kill browser and relaunch (Step 1-2).

### 4. Open Pine Editor

Use `mcp__tradingview__pine_new` with `type: "indicator"` (or `"strategy"` / `"library"`).

If `pine_new` fails with "Could not open Pine Editor", the Pine Editor is likely already open from a previous session. Use `mcp__tradingview__pine_get_source` to check — if it returns existing code, the editor is open; proceed to Step 5.

Wait ~3-5s for Pine Editor to fully load after `pine_new`.

### 5. Set Source Code

**Use `mcp__tradingview__pine_set_source`** with the full Pine Script v6 code:

```json
{
  "source": "<full Pine Script v6 code>"
}
```

The `source` parameter handles large code (400+ lines, 16k+ chars).

**Do NOT use `pine_compile` or `pine_smart_compile` directly with code params** — these tools take NO parameters (the schema rejects additional properties). The flow is always: `pine_set_source` → `pine_smart_compile`.

### 6. Compile and Check Errors

Use `mcp__tradingview__pine_smart_compile` (NO parameters — it reads from the editor).

This tool will:
- Click the "Add to chart" / "Save" button
- Detect compilation errors
- Report `has_errors`, `errors[]` (with line/column/message/severity)
- Report whether the study was added to chart

### 7. Fix Common Pine Script v6 Compilation Errors

**Apply fixes in this order:**

| Error Pattern | Root Cause | Fix |
|---------------|------------|-----|
| `Could not find function 'ta.sum'` | v6 moved arithmetic aggregation to `math.*` | Replace `ta.sum(` → `math.sum(` (ALL occurrences) |
| `Could not find function 'ta.max'` / `ta.min'` | v6 namespace cleanup | Replace → `math.max(` / `math.min(` |
| `no viable alternative at ";"` | v6 does NOT support single-line multi-statements | Split `a:=x; b:=y; c:=z` into 3 separate lines |
| `Syntax error: end of line without line continuation` | v6 rejects line break after `or`/`and` operators | Merge the multi-line condition into ONE line, or wrap entire expression in parentheses |
| `Undeclared identifier "xxx"` | v6 is stricter than v5 — NO forward references allowed | Move variable/state declarations BEFORE first usage (e.g., declare `STATE_*` constants and `var int state` before any `if state == ...` block) |
| `plot.style_dashed` | v6 removed this style | Remove `style=plot.style_dashed` from `plot()` calls |
| `security()` | v6 renamed | → `request.security()` |
| `study()` | v6 renamed | → `indicator()` |

**After fixing:** call `pine_set_source` again with the fixed code → `pine_smart_compile` to re-check.

**Tip:** Pine v6 enforces "declare before use" more strictly than v5. If you reorganize code, always put `var` declarations and constants at the top, before any logic that references them.

### 8. Verify No Errors

```json
mcp__tradingview__pine_smart_compile → has_errors: false, errors: []
```

### 9. Save Script (Ctrl+S)

Use `mcp__tradingview__pine_save` (NO parameters — dispatches Ctrl+S in editor).

**This step is critical** — unsaved scripts are lost on page refresh. The script must have a name (set via `indicator("Name", ...)` / `strategy("Name", ...)` in the code) to persist.

### 10. Verify Final State

- `mcp__tradingview__pine_get_source` — confirms code is still in editor
- `mcp__tradingview__capture_screenshot` — visual confirmation that indicator is on chart
- `mcp__tradingview__tv_health_check` — `api_available: true`

## Pine Script v6 Compatibility Reference

### Namespace Changes (v5/v4 → v6)
- `ta.sum()` → `math.sum()`
- `ta.max()` → `math.max()`
- `ta.min()` → `math.min()`
- `security()` → `request.security()`
- `study()` → `indicator()`

### Syntax Restrictions (v6 stricter than v5)
- **No single-line multi-statements**: `a:=1; b:=2` is illegal → must be separate lines
- **No line continuation after `or`/`and`**: `x or \n y` fails → write on one line or use parentheses
- **No forward references**: variables must be declared before use (v5 was lenient)
- `plot.style_dashed` removed → use default solid line

### Common Pitfalls
- Variable declarations with `=` (not `:=`) cannot be reassigned
- `var` keyword required for one-time initialization
- `na` handling: use `nz()` to provide default values
- `ta.*` functions called inside `if` blocks may warn about inconsistent calculations → extract to a global variable first

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Yandex launch fails: `Lock file can not be created! Error code: 5` | Bash sandbox stripped write access to Yandex profile dir | Use PowerShell `Start-Process` (Step 2), NOT bash |
| Chrome launches but port 9222 NOT listening | Default Chrome profile conflicts (background process or stale lock) | Kill ALL Chrome → wait 5s → use **temp profile** (`tv_cdp_chrome`) instead of default |
| `tv_launch` reports success but `pine_*` fails: "No TradingView chart target" | `tv_launch` launched Yandex as blank page (not TradingView) | Kill browser, relaunch manually via PowerShell with TradingView URL |
| `pine_new` fails: "Could not open Pine Editor" | Editor already open from previous session | Check `pine_get_source` — if it returns code, editor is open; skip to `pine_set_source` |
| `pine_compile` / `pine_smart_compile` rejects params | These tools take NO parameters (schema: `additionalProperties: false`) | Use `pine_set_source` to inject code first, THEN call `pine_smart_compile` with `{}` |
| `pine_set_source` succeeds but errors persist | Old compiled version cached on chart | Fix code → `pine_set_source` → `pine_smart_compile` → `pine_save` |
| Code disappears after refresh | Not saved as named script | Always call `pine_save` (Ctrl+S) after successful compile |
| CDP port shows `[::1]:9222` (IPv6) | Browser bound to IPv6 | Kill and relaunch with `--remote-debugging-address=127.0.0.1` |
| `cdp_connected: false` after browser launch | Browser didn't start with CDP, or Yandex hijacked by `tv_launch` | Verify `netstat` shows 9222 LISTENING by `browser.exe`, and `/json/list` contains a `tradingview.com/chart` page target |
| Both Chrome & Yandex fail silently | Port 9222 already taken by another process | `netstat -ano \| grep 9222` → find PID → `taskkill /F /PID <pid>` |
| Chrome temp profile = logged out | Temp profile is fresh, no cookies | Re-login to TradingView (Google/email) in the newly opened window — login persists for that temp profile session |

## Quick Reference: MCP Tool Call Order

```
1. (PowerShell) Kill browsers → Launch Yandex with CDP + TV chart URL
2. tv_health_check              → cdp_connected: true
3. pine_new(type="indicator")   → new script created (skip if editor already open)
4. pine_set_source(source=CODE) → inject code
5. pine_smart_compile()         → check errors
6. (if errors) fix code → goto 4
7. pine_save()                  → Ctrl+S persist
8. capture_screenshot()         → visual verify
```

## Environment Notes (This Machine)

- Yandex Browser: `C:\Program Files\Yandex\YandexBrowser\Application\browser.exe`
- Chrome: `C:\Program Files\Google\Chrome\Application\chrome.exe`
- Yandex default user-data-dir: `C:\Users\Administrator\AppData\Local\Yandex\YandexBrowser\User Data` (preserves login)
- Chrome temp profile: `C:\Users\Administrator\AppData\Local\Temp\tv_cdp_chrome` (re-login each session)
- TradingView Desktop (MSIX): `C:\Program Files (x86)\TradingView\TradingView.exe` (v3.2.0, Electron 38, AppX sandbox) — **DO NOT use for CDP**
- CDP port: `9222`, bound to `127.0.0.1` only
- TV URL: `https://cn.tradingview.com/chart/`

## New Machine Setup Checklist

Follow this exact order on any fresh machine:

1. **Install Chrome** (`C:\Program Files\Google\Chrome\Application\chrome.exe`)
2. **Verify TV Desktop is NOT MSIX**: open folder → if `AppxManifest.xml` exists → MSIX, reject it
3. **Configure MCP**: `tradingview` MCP server in `~/.workbuddy/mcp.json` pointing to port 9222
4. **First launch**: PowerShell kill → 5s wait → Chrome temp profile + CDP → login to TradingView
5. **Verify**: `curl http://127.0.0.1:9222/json/list` must return a `tradingview.com/chart` page target
