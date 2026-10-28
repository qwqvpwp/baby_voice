---
name: "github-access-watt-fallback"
description: "Detects GitHub access failures and auto-launches Steam++ (Steam++.exe) to enable GitHub proxy acceleration. Invoke when GitHub, raw.githubusercontent.com, or api.github.com requests time out / fail to connect, or when the user explicitly says GitHub is unreachable. Only supports the Steam++.exe executable; new WattToolkit.exe-only releases are not handled."
---

# GitHub Access Steam++ Fallback

This skill is used when **GitHub is unreachable in the current environment**. It probes `github.com` / `api.github.com` and, on failure, launches the locally installed **Steam++** (`Steam++.exe`) with the `-clt proxy -on` command so its built-in GitHub reverse-proxy is brought up, then verifies the proxy is working before returning.

The repository for Steam++: <https://github.com/BeyondDimension/SteamTools>.

> **要寻找的是 `Steam++.exe`（项目历史可执行文件名）。** 新版改名后的 `WattToolkit.exe` **不在本 Skill 支持范围** — 如果用户装的是只有 `WattToolkit.exe` 的新版，本 Skill 会失败并提示用户去 <https://steampp.net/> 下载带 `Steam++.exe` 的发行包。

## When to Invoke

Invoke this skill when ANY of the following are true:

- `WebFetch` / `curl` / `git clone` to `github.com` or `raw.githubusercontent.com` times out, returns DNS / connection errors, or HTTP 443/timeout.
- The user explicitly says "GitHub 访问不了 / 登不上 / 上不去 / 打不开".
- A `WebSearch` snippet points to a GitHub URL that cannot be opened.
- A task involves `git push` / `git pull` / `gh` CLI and the remote operation fails with network errors.

Do **not** invoke this skill if the user is asking about a generic Steam++ feature unrelated to GitHub access — in that case use `watt-toolkit-launcher` instead.
Do **not** invoke this skill if the user is asking about `WattToolkit.exe` — this skill only supports `Steam++.exe`.

## What It Does (Workflow)

1. **Probe GitHub reachability**
   - Prefer a fast HEAD / TCP check (PowerShell, ~5s timeout):
     ```powershell
     Test-NetConnection -ComputerName github.com -Port 443 -InformationLevel Quiet
     ```
   - If that succeeds, also test `api.github.com` and `raw.githubusercontent.com`.
2. **Locate Steam++**（**只找 `Steam++.exe`**，不找 `WattToolkit.exe`）
   - Common Windows install locations (try in this order):
     - `%LOCALAPPDATA%\Steam++\Steam++.exe`
     - `%LOCALAPPDATA%\Programs\Steam++\Steam++.exe`
     - `%PROGRAMFILES%\Steam++\Steam++.exe`
     - `%PROGRAMFILES(x86)%\Steam++\Steam++.exe`
     - Microsoft Store package: `Get-AppxPackage *Steam*` → `InstallLocation` 拼接 `Steam++.exe`
   - **Windows 文件系统不区分大小写**：`Steam++.exe` / `steam++.exe` 命中任一即可
   - If still not found, **call `steam-plus-plus-locator` as a fallback** for a wider search (env / Appx / registry / PATH / broad search). It **只搜 `Steam++.exe`**，如果连它都搜不到，说明用户装的是新版 `WattToolkit.exe` — 当前 Skill 不支持这种情形，会中止并提示用户去 <https://steampp.net/> 下载带 `Steam++.exe` 的发行包。
3. **Ensure GitHub acceleration is enabled in Steam++ settings** (best-effort, non-blocking)
   - Steam++ stores its config under `%LOCALAPPDATA%\Steam++\Configs`.
   - Do not silently rewrite user config files. Only inform the user once:
     > "Steam++ detected. Please open it once, tick 'GitHub' under 网络加速 / Network Accelerator, and let it complete a successful acceleration. After that this skill will work silently."
   - Cache this "primed" state in a tiny marker file (e.g. `%LOCALAPPDATA%\github-access-watt-fallback\primed`) so we do not nag again.
4. **Launch Steam++ silently with proxy on**
   ```powershell
   # 静默启动 + 启用代理服务 = GitHub 反代随之启动
   Start-Process -FilePath $steamExe -ArgumentList '-clt','proxy','-on'
   ```
5. **Wait & verify**
   - Poll `Test-NetConnection github.com -Port 443` every 2 seconds, up to ~30s.
   - If it succeeds, also do a real HTTP probe:
     ```powershell
     (Invoke-WebRequest -Uri 'https://github.com' -UseBasicParsing -TimeoutSec 10).StatusCode
     ```
   - Return the result (success / still failing / timed out) to the caller.
6. **Cleanup**
   - Do **not** kill the Steam++ process — the user wants the proxy to keep running for subsequent operations.
   - If verification still fails after 30s, report the failure and suggest opening the Steam++ GUI to check whether GitHub acceleration is actually toggled on.

## Command-Line Reference (Steam++)

Steam++ exposes a `System.CommandLine` based CLI under the `-clt` prefix (defined in `src/BD.WTTS.Client/Startup/Startup.Commands.cs` on the `develop` branch of the upstream repo).

| Need | Command |
|------|---------|
| 静默启动 + 启用代理 | `Steam++.exe -clt proxy -on` |
| 静默启动（仅托盘） | `Steam++.exe -clt c -silence` |
| 关闭代理 | `Steam++.exe -clt proxy -off` |
| 查看根证书 | `Steam++.exe -clt show -cert` |

There is **no** built-in flag to target a single service (e.g. `--github`); the proxy service covers all services the user enabled in the GUI. So the "GitHub-only" path is satisfied by making sure the user has ticked "GitHub" in the Steam++ GUI once, and then using `-clt proxy -on`.

## Limitations

- The skill **only** looks for `Steam++.exe`. New versions of Steam++ that ship only `WattToolkit.exe` are **not supported** — the skill will fail with a message asking the user to install a release that ships `Steam++.exe`.
- The skill cannot make Steam++ target GitHub alone; it relies on a one-time GUI setup.
- After `Steam++.exe -clt proxy -on` the GUI process stays running (minimized) — that is by design, the proxy must keep serving.
- On macOS / Linux the EXE path differs; only Windows is supported in this v1.

## Example Interaction

> User: 帮我 clone 一下 https://github.com/foo/bar.git
> Agent: clone fails with "fatal: unable to access ... Could not resolve host: github.com"
> Agent (invokes this skill): probes, finds Steam++.exe, launches `-clt proxy -on`, waits, retries the clone, succeeds.
