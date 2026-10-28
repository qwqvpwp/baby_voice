---
name: "watt-toolkit-launcher"
description: "Launches and operates Watt Toolkit (Steam++) from the command line: silent start, toggle proxy/accelerator, switch Steam accounts, show certificates. Invoke when the user asks to start, accelerate with, or control Watt Toolkit from the terminal."
---

# Watt Toolkit Launcher

A small, generic CLI helper for **Watt Toolkit** (formerly Steam++, repo: <https://github.com/BeyondDimension/SteamTools>). It does **not** care *why* you want Watt Toolkit running — it just locates the EXE, calls the right subcommand, and verifies the action succeeded.

> If your goal is specifically "GitHub is down, please fix it" → use `github-access-watt-fallback` instead. This skill is the low-level launcher.

## When to Invoke

- "启动 Watt Toolkit / Steam++"
- "用 Watt Toolkit 加速一下"
- "命令行打开 Steam++ 并开启代理"
- "切换 Steam 账号" (`-clt steam -account <name>`)
- "Watt Toolkit 静默启动 / 不弹窗口"
- "关掉 Watt Toolkit 的代理" (`-clt proxy -off`)

Do **not** invoke for unrelated acceleration tools (Clash, sing-box, Netch, etc.).

## Workflow

1. **Resolve the EXE path** (first match wins, cached for the session):
   - `$env:LOCALAPPDATA\Watt Toolkit\WattToolkit.exe`
   - `$env:LOCALAPPDATA\Programs\Watt Toolkit\WattToolkit.exe`
   - `$env:PROGRAMFILES\Watt Toolkit\WattToolkit.exe`
   - Microsoft Store: `Get-AppxPackage *WattToolkit* | Select -Expand InstallLocation`
   - Fallback older name: `Steam++.exe` in the same directories.
2. **Map user intent → subcommand** (see table below).
3. **Spawn with `Start-Process`** and the right `-clt …` argument list.
4. **Verify** based on the intent:
   - `proxy -on`: poll `Test-NetConnection github.com -Port 443` for up to 30s.
   - `c -silence`: confirm the process is alive (`Get-Process WattToolkit`) and has a main-window handle == 0 (minimized to tray).
   - `show -cert`: capture stdout (you must redirect via `-RedirectStandardOutput` when available; otherwise just inform the user the certificate window is open).
5. **Report** success / failure, the PID, and the time waited.

## Command Map

Watt Toolkit's CLI is built on `System.CommandLine` and lives in `src/BD.WTTS.Client/Startup/Startup.Commands.cs` (develop branch). All subcommands require the `-clt` prefix.

| User intent | Argument list passed to `WattToolkit.exe` |
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
| 关闭主程序 | 找到 PID 后 `Stop-Process -Id <pid>` |

## Notes & Gotchas

- `-clt proxy -on` sets `IsMinimize = true` and `IsProxyService = true`, so the GUI never pops up but the process stays alive serving the reverse proxy. Don't kill it unless the user asked to "关闭代理 / 关掉 Watt Toolkit".
- There is no `--accelerate github` style flag. To get GitHub-only acceleration, the user must tick "GitHub" inside the Watt Toolkit GUI **once**; after that `-clt proxy -on` will bring it up.
- Old versions exposed the EXE as `Steam++.exe`; detect both.
- The skill must run on Windows (PowerShell). macOS / Linux Watt Toolkit builds exist but their CLI surface is not part of this v1.

## Example

> User: 用命令行静默启动 Watt Toolkit 并打开代理
> Agent: invokes this skill, resolves `%LOCALAPPDATA%\Watt Toolkit\WattToolkit.exe`, runs `Start-Process WattToolkit.exe -ArgumentList '-clt','proxy','-on'`, polls `github.com:443` until reachable, reports "Watt Toolkit 已静默启动并开启代理，PID=12345，GitHub 已恢复（耗时 8s）".