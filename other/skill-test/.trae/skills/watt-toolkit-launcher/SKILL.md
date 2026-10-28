---
name: "watt-toolkit-launcher"
description: "Launches and operates Steam++ (Steam++.exe) from the command line: silent start, toggle proxy/accelerator, switch Steam accounts, show certificates, configure Windows auto-start (AutoRunOnStartup in GeneralSettings.json) and post-start auto-accelerate (ProgramStartupRunProxy in ProxySettings.json), and safe-shutdown (proxy-off then Stop-Process). The exclusive target is Steam++.exe. Invoke when the user asks to start, accelerate with, configure, or control Steam++ from the terminal — including '开机自启动 Steam++ / 启动后自动加速 / 取消开机自启动 / 取消启动后自动加速 / 关掉 Steam++'."
---

# Steam++ Launcher

A small, generic CLI helper for **Steam++** (repo: <https://github.com/BeyondDimension/SteamTools>). It does **not** care *why* you want Steam++ running — it just locates the EXE (`Steam++.exe`), calls the right subcommand, and verifies the action succeeded.

> **要寻找的是 `Steam++.exe`**（项目历史可执行文件名，仓库 `BD.WTTS.Client` 早期版本 EXE 即此名：`/// 获取当前主程序文件名，例如 steam++.exe`）。
> 
> **不寻找 `WattToolkit.exe`**。新版本改名后的 `WattToolkit.exe` 不在搜索范围内。如果用户装的只有新版本，Skill 会报错并提示用户去 steampp.net 下载带 `Steam++.exe` 的发行包。

> If your goal is specifically "GitHub is down, please fix it" → use `github-access-watt-fallback` instead. This skill is the low-level launcher.

## When to Invoke

- "启动 Steam++ / Steam++.exe"
- "用 Steam++ 加速一下"
- "命令行打开 Steam++ 并开启代理"
- "切换 Steam 账号" (`-clt steam -account <name>`)
- "Steam++ 静默启动 / 不弹窗口"
- "关掉 Steam++ 的代理" (`-clt proxy -off`)
- "**开机自启动 Steam++**" / "**取消开机自启动**"（改 `GeneralSettings.AutoRunOnStartup`）
- "**启动后自动加速**" / "**取消启动后自动加速**"（改 `ProxySettings.ProgramStartupRunProxy`）
- "**关掉 Steam++**"（安全序列：先 `-clt proxy -off` 再 `Stop-Process`）

Do **not** invoke for unrelated acceleration tools (Clash, sing-box, Netch, etc.).
Do **not** invoke if the user is asking about `WattToolkit.exe` — that is a different executable and not handled here.

## Workflow

1. **Resolve the EXE path** — only `Steam++.exe` (first match wins, cached for the session):
   - `$env:LOCALAPPDATA\Steam++\Steam++.exe`
   - `$env:LOCALAPPDATA\Programs\Steam++\Steam++.exe`
   - `$env:PROGRAMFILES\Steam++\Steam++.exe`
   - `$env:PROGRAMFILES(x86)\Steam++\Steam++.exe`
   - Microsoft Store: `Get-AppxPackage *Steam* | Select -Expand InstallLocation` 然后拼接 `Steam++.exe`
   - **Windows 文件系统不区分大小写**：`Steam++.exe` / `steam++.exe` 命中任一即可，Skill 内部统一规范为 `Steam++.exe`
   - If all of the above miss, **invoke `steam-plus-plus-locator` as a fallback** to do a wider search (env / Appx / registry / PATH / broad search). It returns a prioritized candidate list (all of them are `Steam++.exe`); pick the highest-priority valid candidate.
   - If even `steam-plus-plus-locator` returns nothing, tell the user to install Steam++ from <https://steampp.net/> (note: pick a release that ships `Steam++.exe`) before retrying.
2. **Map user intent → subcommand** (see table below).
3. **Spawn with `Start-Process`** and the right `-clt …` argument list, **or** read/write a JSON config file (for auto-start / post-start auto-accelerate).
4. **Verify** based on the intent:
   - `proxy -on`: poll `Test-NetConnection github.com -Port 443` for up to 30s.
   - `c -silence`: confirm the process is alive (`Get-Process Steam++` — 进程名以 EXE 文件名实际为准，PowerShell 进程匹配不区分大小写) and has a main-window handle == 0 (minimized to tray).
   - `show -cert`: capture stdout (you must redirect via `-RedirectStandardOutput` when available; otherwise just inform the user the certificate window is open).
   - **auto-start / post-start auto-accelerate**: re-read the JSON file and confirm the field was written.
   - **safe shutdown**: poll `Get-Process Steam++` for up to 5s; if still alive, escalate to `taskkill /F /IM Steam++.exe`.
5. **Report** success / failure, the PID, the resolved EXE path, the new JSON field value (for config changes), and the time waited.

## Command Map

Steam++'s CLI is built on `System.CommandLine` and lives in `src/BD.WTTS.Client/Startup/Startup.Commands.cs` (develop branch). All subcommands require the `-clt` prefix.

| User intent | Argument list / operation |
|---|---|
| 启动 GUI（正常窗口） | `-clt main` |
| 静默启动到托盘 | `-clt c -silence` |
| 开启代理 / 加速 | `-clt proxy -on` |
| 关闭代理 / 加速 | `-clt proxy -off` |
| 切换代理状态（toggle） | `-clt proxy` |
| 切换 Steam 账号 | `-clt steam -account <username>` （需管理员） |
| 启动某个 Steam 游戏的连接服务并保持挂运行 | `-clt app -id <appId> -silence` |
| 打开某游戏的成就解锁窗口 | `-clt app -id <appId> -achievement` |
| 打开云存档管理 | `-clt app -id <appId> -cloudmanager` |
| 显示根证书信息 | `-clt show -cert` |
| **开机自启动（开）** | 改 `%LOCALAPPDATA%\Steam++\Settings\GeneralSettings.json` 的 `GeneralSettings.AutoRunOnStartup` 为 `true` |
| **开机自启动（关）** | 改 `GeneralSettings.AutoRunOnStartup` 为 `false` |
| **启动后自动加速（开）** | 改 `%LOCALAPPDATA%\Steam++\Plugins\Accelerator\Settings\ProxySettings.json` 的 `ProxySettings.ProgramStartupRunProxy` 为 `true` |
| **启动后自动加速（关）** | 改 `ProxySettings.ProgramStartupRunProxy` 为 `false` |
| **关闭主程序（安全序列）** | (a) `Start-Process $steamExe -ArgumentList '-clt','proxy','-off'` → 2s → (b) `Get-Process Steam++ \| Stop-Process -Force`；若 5s 仍存活，`taskkill /F /IM Steam++.exe` |

> **关于开机自启动 / 启动后自动加速**：上游 CLI 没有 `-clt autostart` / `-clt startup-proxy` 开关。这两项在 Steam++ GUI 里的 toggle 实际上改的是**应用内 JSON 配置**（实测确认），本 Skill 因此**直接改 JSON**，不写 Windows 注册表 `Run` 键、不在启动文件夹放快捷方式。详细实现见 §"开机自启动" 与 §"启动后自动加速"。

## 开机自启动（AutoRunOnStartup）

### 配置文件位置

```
%LOCALAPPDATA%\Steam++\Settings\GeneralSettings.json
└── GeneralSettings
    ├── AutoRunOnStartup: <bool>   ← 这个字段
    ├── MinimizeOnStartup: <bool>
    └── ...
```

### PowerShell 操作模板

```powershell
$jsonPath = "$env:LOCALAPPDATA\Steam++\Settings\GeneralSettings.json"

# 写之前先备份
Copy-Item $jsonPath "$jsonPath.bak" -Force

# 打开开机自启动
$obj = Get-Content $jsonPath -Raw | ConvertFrom-Json
$obj.GeneralSettings.AutoRunOnStartup = $true
$obj | ConvertTo-Json -Depth 10 | Set-Content -Path $jsonPath -Encoding UTF8

# 取消开机自启动
$obj.GeneralSettings.AutoRunOnStartup = $false
$obj | ConvertTo-Json -Depth 10 | Set-Content -Path $jsonPath -Encoding UTF8

# 验证
(Get-Content $jsonPath -Raw | ConvertFrom-Json).GeneralSettings.AutoRunOnStartup
```

### 关键说明

- 这个字段就是 Steam++ 自身 GUI 设置页里"开机自启" toggle 背后的字段；改它**等于**改 Steam++ 的应用配置。
- 写完**不**需要重启 Steam++，下次启动时生效。
- 不写注册表 `HKCU\...\Run`，也不在 `shell:startup` 文件夹放快捷方式（本机实测 Run 键里没有 `Steam++` 值）。
- 写之前必须先 `Get-Content` 校验字段存在；如果 Steam++ 版本较旧（2.x）字段名可能不同，**跳过**此能力并提示用户去 GUI 设置。

## 启动后自动加速（ProgramStartupRunProxy）

### 配置文件位置

```
%LOCALAPPDATA%\Steam++\Plugins\Accelerator\Settings\ProxySettings.json
└── ProxySettings
    ├── ProgramStartupRunProxy: <bool>   ← 这个字段
    ├── SystemProxyPortId: 26561
    └── ...
```

### PowerShell 操作模板

```powershell
$jsonPath = "$env:LOCALAPPDATA\Steam++\Plugins\Accelerator\Settings\ProxySettings.json"

# 写之前先备份
Copy-Item $jsonPath "$jsonPath.bak" -Force

# 打开启动后自动加速
$obj = Get-Content $jsonPath -Raw | ConvertFrom-Json
$obj.ProxySettings.ProgramStartupRunProxy = $true
$obj | ConvertTo-Json -Depth 20 | Set-Content -Path $jsonPath -Encoding UTF8

# 取消启动后自动加速
$obj.ProxySettings.ProgramStartupRunProxy = $false
$obj | ConvertTo-Json -Depth 20 | Set-Content -Path $jsonPath -Encoding UTF8

# 验证
(Get-Content $jsonPath -Raw | ConvertFrom-Json).ProxySettings.ProgramStartupRunProxy
```

### 关键说明

- `ProgramStartupRunProxy` 是 Accelerator 插件的核心开关：值为 `true` 时，Steam++ 启动后会**自动**调用本地代理服务（与 `-clt proxy -on` 行为一致）。
- 与"开机自启动"（`GeneralSettings.AutoRunOnStartup`）**独立**：可以只开其中一个，或都开，或都关。
- Accelerator 插件缺失时（比如 `Plugins\Accelerator` 目录不存在），无法启用此能力 — Skill 应当提示用户"插件未安装，去 Steam++ 设置里启用 Accelerator 插件"。
- 同上，写之前先 `Get-Content` 校验字段存在。

## 关闭软件（安全序列）

```powershell
# 步骤 1：先关代理（让本地代理端口先释放）
Start-Process $steamExe -ArgumentList '-clt','proxy','-off'
Start-Sleep 2

# 步骤 2：再退主进程
Get-Process Steam++ -ErrorAction SilentlyContinue | Stop-Process -Force

# 步骤 3（兜底）：5s 后仍存活则用 taskkill
$sw = [System.Diagnostics.Stopwatch]::StartNew()
while ((Get-Process Steam++ -ErrorAction SilentlyContinue) -and $sw.Elapsed.TotalSeconds -lt 5) {
    Start-Sleep 1
}
if (Get-Process Steam++ -ErrorAction SilentlyContinue) {
    taskkill /F /IM Steam++.exe 2>&1 | Out-Null
}
```

> 为什么先关代理？`IsMinimize + IsProxyService` 模式下 Steam++ 监听本地代理端口（如 26561），直接 `Stop-Process` 会让上游连接"半路被掐"，导致后续 git push / WebFetch 报 502 / connection reset。**先关代理 → 再退进程** 让服务有 2s 收尾时间。

## Notes & Gotchas

- **要寻找的是 `Steam++.exe`**：原项目 EXE 名就是 `Steam++.exe`，进程名以 EXE 文件名实际为准。`Get-Process Steam++` 可以命中。
- `-clt proxy -on` sets `IsMinimize = true` and `IsProxyService = true`, so the GUI never pops up but the process stays alive serving the reverse proxy. Don't kill it unless the user asked to "关闭代理 / 关掉 Steam++".
- There is no `--accelerate github` style flag. To get GitHub-only acceleration, the user must tick "GitHub" inside the Steam++ GUI **once**; after that `-clt proxy -on` will bring it up.
- The skill must run on Windows (PowerShell). macOS / Linux Steam++ builds exist but their CLI surface is not part of this v1.
- 配置文件的"前提"判断：写之前**必须**先 `Get-Content` 校验字段存在；不存在时降级为提示用户去 GUI 操作，**不**写盘。

## Example

> User: 帮我关掉 Steam++
> Agent: invokes this skill, resolves `%LOCALAPPDATA%\Steam++\Steam++.exe`, runs `Start-Process Steam++.exe -ArgumentList '-clt','proxy','-off'`, waits 2s, then `Get-Process Steam++ | Stop-Process -Force`. Reports "Steam++ 已安全关闭：先关代理（端口 26561 已释放），再退主进程（PID 12345 已结束）".

> User: 帮我开机自启动 Steam++，启动后自动加速
> Agent: invokes this skill, modifies `GeneralSettings.AutoRunOnStartup` → `true` and `ProxySettings.ProgramStartupRunProxy` → `true`, re-reads both files to verify, reports "开机自启动 ✅，启动后自动加速 ✅；下次 Steam++ 启动时会自动进入代理服务模式".

> User: 取消启动后自动加速
> Agent: invokes this skill, sets `ProxySettings.ProgramStartupRunProxy` → `false`, re-reads to verify, reports "启动后自动加速已关闭 ✅；下次启动 Steam++ 不会自动开代理，但 Steam++ 自身仍会启动".
