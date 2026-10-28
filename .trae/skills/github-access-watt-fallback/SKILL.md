---
name: "github-access-watt-fallback"
description: "Detects GitHub access failures and auto-launches Watt Toolkit to enable GitHub proxy acceleration. Invoke when GitHub, raw.githubusercontent.com, or api.github.com requests time out / fail to connect, or when the user explicitly says GitHub is unreachable."
---

# GitHub Access Watt Toolkit Fallback

This skill is used when **GitHub is unreachable in the current environment**. It probes `github.com` / `api.github.com` and, on failure, launches the locally installed **Watt Toolkit** (原名 Steam++) with the `-clt proxy -on` command so its built-in GitHub reverse-proxy is brought up, then verifies the proxy is working before returning.

The repository for Watt Toolkit: <https://github.com/BeyondDimension/SteamTools>.

## When to Invoke

Invoke this skill when ANY of the following are true:

- `WebFetch` / `curl` / `git clone` to `github.com` or `raw.githubusercontent.com` times out, returns DNS / connection errors, or HTTP 443/timeout.
- The user explicitly says "GitHub 访问不了 / 登不上 / 上不去 / 打不开".
- A `WebSearch` snippet points to a GitHub URL that cannot be opened.
- A task involves `git push` / `git pull` / `gh` CLI and the remote operation fails with network errors.

Do **not** invoke this skill if the user is asking about a generic Watt Toolkit feature unrelated to GitHub access — in that case use `watt-toolkit-launcher` instead.

## What It Does (Workflow)

1. **Probe GitHub reachability**
   - Prefer a fast HEAD / TCP check (PowerShell, ~5s timeout):
     ```powershell
     Test-NetConnection -ComputerName github.com -Port 443 -InformationLevel Quiet
     ```
   - If that succeeds, also test `api.github.com` and `raw.githubusercontent.com`.
2. **Locate Watt Toolkit**
   - Common Windows install locations (try in this order):
     - `%LOCALAPPDATA%\Watt Toolkit\WattToolkit.exe`
     - `%LOCALAPPDATA%\Programs\Watt Toolkit\WattToolkit.exe`
     - `%PROGRAMFILES%\Watt Toolkit\WattToolkit.exe`
     - Microsoft Store package: search `Get-AppxPackage *WattToolkit*` and use `InstallLocation`.
   - If the EXE is **not** found anywhere, stop and tell the user to install Watt Toolkit from <https://steampp.net/> or Microsoft Store before retrying.
3. **Ensure GitHub acceleration is enabled in Watt Toolkit settings** (best-effort, non-blocking)
   - Watt Toolkit stores its config under `%LOCALAPPDATA%\Watt Toolkit\Configs`.
   - Do not silently rewrite user config files. Only inform the user once:
     > "Watt Toolkit detected. Please open it once, tick 'GitHub' under 网络加速 / Network Accelerator, and let it complete a successful acceleration. After that this skill will work silently."
   - Cache this "primed" state in a tiny marker file (e.g. `%LOCALAPPDATA%\github-access-watt-fallback\primed`) so we do not nag again.
4. **Launch Watt Toolkit silently with proxy on**
   ```powershell
   # 静默启动 + 启用代理服务 = GitHub 反代随之启动
   Start-Process -FilePath $wattExe -ArgumentList '-clt','proxy','-on'
   ```
5. **Wait & verify**
   - Poll `Test-NetConnection github.com -Port 443` every 2 seconds, up to ~30s.
   - If it succeeds, also do a real HTTP probe:
     ```powershell
     (Invoke-WebRequest -Uri 'https://github.com' -UseBasicParsing -TimeoutSec 10).StatusCode
     ```
   - Return the result (success / still failing / timed out) to the caller.
6. **Cleanup**
   - Do **not** kill the Watt Toolkit process — the user wants the proxy to keep running for subsequent operations.
   - If verification still fails after 30s, report the failure and suggest opening the Watt Toolkit GUI to check whether GitHub acceleration is actually toggled on.

## Command-Line Reference (Watt Toolkit)

Watt Toolkit exposes a `System.CommandLine` based CLI under the `-clt` prefix (defined in `src/BD.WTTS.Client/Startup/Startup.Commands.cs` on the `develop` branch of the upstream repo).

| Need | Command |
|------|---------|
| 静默启动 + 启用代理 | `WattToolkit.exe -clt proxy -on` |
| 静默启动（仅托盘） | `WattToolkit.exe -clt c -silence` |
| 关闭代理 | `WattToolkit.exe -clt proxy -off` |
| 查看根证书 | `WattToolkit.exe -clt show -cert` |

There is **no** built-in flag to target a single service (e.g. `--github`); the proxy service covers all services the user enabled in the GUI. So the "GitHub-only" path is satisfied by making sure the user has ticked "GitHub" in the Watt Toolkit GUI once, and then using `-clt proxy -on`.

## Limitations

- The skill cannot make Watt Toolkit target GitHub alone; it relies on a one-time GUI setup.
- After `WattToolkit.exe -clt proxy -on` the GUI process stays running (minimized) — that is by design, the proxy must keep serving.
- On macOS / Linux the EXE path differs; only Windows is supported in this v1.

## Example Interaction

> User: 帮我 clone 一下 https://github.com/foo/bar.git
> Agent: clone fails with "fatal: unable to access ... Could not resolve host: github.com"
> Agent (invokes this skill): probes, finds Watt Toolkit, launches `-clt proxy -on`, waits, retries the clone, succeeds.