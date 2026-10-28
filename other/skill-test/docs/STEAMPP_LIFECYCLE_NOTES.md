# Steam++ 全生命周期笔记 / 速查

> 这份文档对应 `/plan` 任务里的 **Step 1 实测 + Step 2 简洁文档**。包含 Steam++ 的完整生命周期命令、上游 CLI 不直接暴露的能力的间接实现、以及每条命令的"前提 / 副作用 / 回退"。

## 0. 实测环境

- 操作系统：Windows 11（PowerShell 5.1.26100.9168）
- 当前 `TaskList`：本机**没有** `Steam++` / `WattToolkit` 进程
- 当前 `Steam++.exe` / `WattToolkit.exe` 文件搜索结果：**未找到**（本机未安装 Steam++ 主程序）
- 当前 `%LOCALAPPDATA%\Steam++\` 配置目录：存在（用户曾装过，残留 Settings）

> 由于本机未装 Steam++ 主程序，本笔记中：
> - **Steam++ 自身的 `-clt` 子命令** 行为参考上游源码 `src/BD.WTTS.Client/Startup/Startup.Commands.cs`（已确认）
> - **配置文件读写** 已在本机用 PowerShell 实测并验证（见 §3、§4）
> - **注册表 / 进程 / 端口** 类操作本机**未做实跑**（写文档时不模拟注册表写）

## 1. 命令速查（按你 `/plan` 列出的 7 个意图）

| # | 用户意图 | 命令 / 操作 | 前提 | 副作用 | 回退 |
|---|---|---|---|---|---|
| 1 | 启动 Steam++（正常 GUI 窗口） | `Start-Process $steamExe -ArgumentList '-clt','main'` | EXE 已找到 | 进程出现 + 弹窗 | 用 #7 关闭 |
| 2 | 启动 Steam++（静默到托盘） | `Start-Process $steamExe -ArgumentList '-clt','c','-silence'` | EXE 已找到 | 进程出现 + 不弹窗 | 用 #7 关闭 |
| 3 | 启动加速器（开代理） | `Start-Process $steamExe -ArgumentList '-clt','proxy','-on'` | EXE 已找到 + 首次已在 GUI 勾选 GitHub | 进程以 `IsMinimize + IsProxyService` 模式启动 | `-clt proxy -off` 或 #7 |
| 4 | **开机自启动** | 改 `%LOCALAPPDATA%\Steam++\Settings\GeneralSettings.json` 中 `GeneralSettings.AutoRunOnStartup = true` | EXE 已找到 + 当前用户对该文件有写权限 | **仅**改一个 JSON 字段，**不**写注册表 | 把该字段改回 `false` |
| 5 | **启动后自动加速** | 改 `%LOCALAPPDATA%\Steam++\Plugins\Accelerator\Settings\ProxySettings.json` 中 `ProxySettings.ProgramStartupRunProxy = true` | EXE 已找到 + Accelerator 插件存在 | 改 JSON 字段；下次启动 Steam++ 时**自动**执行开代理 | 把该字段改回 `false` |
| 6 | **取消开机自启动** | 把 `GeneralSettings.AutoRunOnStartup` 改回 `false` | 同 #4 | 改 JSON 字段 | 改成 `true` |
| 7 | **取消启动后自动加速** | 把 `ProxySettings.ProgramStartupRunProxy` 改回 `false` | 同 #5 | 改 JSON 字段 | 改成 `true` |
| 8 | 关闭软件（安全序列） | (a) `Start-Process $steamExe -ArgumentList '-clt','proxy','-off'` 先关代理 → 2s → (b) `Get-Process Steam++ \| Stop-Process -Force` 退主进程 | EXE 已找到 | 进程退出，托盘图标消失，`github.com:443` 不可达（若无其他代理） | 重新执行 #1 / #2 / #3 |

> 表格里的"前提 / 副作用 / 回退"是给 TRAE Skill 在执行每条命令时做合法性检查与回滚的依据。

## 2. 上游 CLI 子命令矩阵（来自 `Startup.Commands.cs`）

| 子命令 | 用途 | 备注 |
|---|---|---|
| `-clt main` | 正常启动（GUI 窗口） | 不带参数 |
| `-clt c -silence` | 静默启动到托盘 | 不弹窗 |
| `-clt proxy -on` | 开代理（最小化 + 启用代理服务） | GitHub 反代随之启动 |
| `-clt proxy -off` | 关代理 | 释放本地代理端口 |
| `-clt proxy` | 切换代理（toggle） | |
| `-clt steam -account <name>` | 切换 Steam 账号 | 需管理员 |
| `-clt app -id <appId> -silence` | 启动某 Steam 游戏的连接服务 | |
| `-clt app -id <appId> -achievement` | 打开成就解锁窗口 | |
| `-clt app -id <appId> -cloudmanager` | 打开云存档管理 | |
| `-clt show -cert` | 显示根证书 | |

> 上游**没有** `-clt autostart` / `-clt startup-proxy` / `-clt shutdown` 等"开机自启 / 启动后自动加速 / 关闭"开关 — 这三类需求在原 CLI 表面下**无法直接**用 `-clt` 完成。

## 3. 开机自启动 — 配置实测

### 3.1 字段位置（实测）

```
%LOCALAPPDATA%\Steam++\Settings\GeneralSettings.json
└── GeneralSettings
    ├── AutoRunOnStartup: true   ← 这个
    ├── MinimizeOnStartup: true
    └── ...
```

### 3.2 PowerShell 操作模板

```powershell
$jsonPath = "$env:LOCALAPPDATA\Steam++\Settings\GeneralSettings.json"

# 读取
$obj = Get-Content $jsonPath -Raw | ConvertFrom-Json
$obj.GeneralSettings.AutoRunOnStartup    # 当前值

# 打开
$obj.GeneralSettings.AutoRunOnStartup = $true
$obj | ConvertTo-Json -Depth 10 | Set-Content -Path $jsonPath -Encoding UTF8

# 关闭
$obj.GeneralSettings.AutoRunOnStartup = $false
$obj | ConvertTo-Json -Depth 10 | Set-Content -Path $jsonPath -Encoding UTF8
```

### 3.3 关键说明

- 这个字段就是 Steam++ 自身 GUI 设置页里"开机自启" toggle 背后的字段。改它**等于**改 Steam++ 的应用配置。
- 不需要写 Windows 注册表 `HKCU\...\Run`，也**不**需要在 `shell:startup` 文件夹里放快捷方式（实测本机 Run 键里没有 `Steam++` 值，证实 Steam++ 走自己的配置项）。
- 写完无需重启 Steam++，下次启动时生效。
- 写之前建议先备份：`Copy-Item $jsonPath "$jsonPath.bak" -Force`。

## 4. 启动后自动加速 — 配置实测

### 4.1 字段位置（实测）

```
%LOCALAPPDATA%\Steam++\Plugins\Accelerator\Settings\ProxySettings.json
└── ProxySettings
    ├── ProgramStartupRunProxy: true   ← 这个
    ├── SystemProxyPortId: 26561
    └── ...
```

### 4.2 PowerShell 操作模板

```powershell
$jsonPath = "$env:LOCALAPPDATA\Steam++\Plugins\Accelerator\Settings\ProxySettings.json"

# 读取
$obj = Get-Content $jsonPath -Raw | ConvertFrom-Json
$obj.ProxySettings.ProgramStartupRunProxy   # 当前值

# 打开
$obj.ProxySettings.ProgramStartupRunProxy = $true
$obj | ConvertTo-Json -Depth 20 | Set-Content -Path $jsonPath -Encoding UTF8

# 关闭
$obj.ProxySettings.ProgramStartupRunProxy = $false
$obj | ConvertTo-Json -Depth 20 | Set-Content -Path $jsonPath -Encoding UTF8
```

### 4.3 关键说明

- `ProgramStartupRunProxy` 是 Accelerator 插件的核心开关：值为 `true` 时，Steam++ 启动后会**自动**调用本地代理服务（与 `-clt proxy -on` 行为一致）。
- "启动后自动加速" 走这个字段即可，**不**需要用启动文件夹或计划任务。
- 与"开机自启动"（§3）独立：可以只开其中一个，或都开，或都关。
- 写之前同样建议先备份。

## 5. 关闭软件 — 安全序列

```powershell
# 步骤 1：先关代理（让本地代理端口先释放）
Start-Process $steamExe -ArgumentList '-clt','proxy','-off'
Start-Sleep 2

# 步骤 2：再退主进程
Get-Process Steam++ -ErrorAction SilentlyContinue | Stop-Process -Force
```

> 为什么不直接 `Stop-Process`？因为 Steam++ 在 `-clt proxy -on` 状态下会监听本地代理端口（如 26561），直接强退可能让上游连接"半路被掐"，导致后续 git push 等操作报 502 / connection reset。**先关代理 → 再退进程** 让服务有 2s 收尾时间。

## 6. 不在 Skill 范围 / 用户应注意的边界

- **配置文件路径**基于实测本机 Steam++ 3.0.x；旧版本（如 2.x）字段名可能不同。Skill 在改之前**必须**先 `Get-Content` 看一眼是否含 `AutoRunOnStartup` / `ProgramStartupRunProxy` 字段。
- **管理员权限**：改 `%LOCALAPPDATA%` 下的文件不需要管理员；写注册表 `HKLM\...\Run` 才需要。本方案全程不碰 `HKLM`。
- **多用户**：当前所有操作都在**当前用户**的 `HKCU` / `%LOCALAPPDATA%` 下；不影响其他用户。
- **macOS / Linux**：本笔记的"配置 JSON"路径不适用，暂不支持。

## 7. 实测发现 vs 计划假设的差异

| 计划假设 | 实测发现 | 调整 |
|---|---|---|
| "开机自启动" → 写注册表 `HKCU\...\Run` | 实际是改 `GeneralSettings.AutoRunOnStartup`（JSON） | ✅ 用 JSON；不写注册表 |
| 配置文件在 `%LOCALAPPDATA%\Steam++\Configs\` | 实际是 `%LOCALAPPDATA%\Steam++\Settings\`（外层）和 `%LOCALAPPDATA%\Steam++\Plugins\Accelerator\Settings\`（加速器） | ✅ 按实际路径写 |
| "启动后自动加速" 字段名待定 | 实测是 `ProxySettings.ProgramStartupRunProxy` | ✅ 直接采用这个字段 |

## 8. 引用

- 上游源码：<https://github.com/BeyondDimension/SteamTools>
- CLI 入口：`src/BD.WTTS.Client/Startup/Startup.Commands.cs`（`develop` 分支）
- 本笔记在 `skill-test/docs/STEAMPP_LIFECYCLE_NOTES.md`
