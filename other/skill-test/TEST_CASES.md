# 测试用例 — GitHub Access Steam++ Skill Pack

> 本文档为 `github-access-watt-fallback` / `watt-toolkit-launcher` / `steam-plus-plus-locator` 三个 Skill 的功能 / 异常 / 边界测试用例。每条用例给出 **前提 → 操作 → 预期**，可直接在 TRAE CN 对话或本机 PowerShell 中执行。
> 
> **三个 Skill 都只寻找 `Steam++.exe`**（项目历史可执行文件名）。如果本机只有 `WattToolkit.exe`（新版），所有路径搜索类用例预期改为"返回空列表 / 提示用户去 steampp.net 下载带 Steam++.exe 的发行包"。

## 0. 测试前置

- 操作系统：Windows 10/11
- 本机已安装 Steam++（**带 `Steam++.exe` 的发行包**）
- 首次运行前把 Steam++ 完整打开一次并勾选 "GitHub" 加速项，让它成功完成一次"一键加速"
- PowerShell ≥ 5.1（Windows 默认）
- 关键路径变量：
  - `$steamExe` = `%LOCALAPPDATA%\Steam++\Steam++.exe`（按实际情况替换）
  - `$workDir` = `d:\Code\Voice\baby_voice\skill-test`

## 1. Skill 发现 / 导入

| ID | 标题 | 前提 | 操作 | 预期 |
|---|---|---|---|---|
| T-DISC-01 | TRAE 能识别三个 Skill | 工作区根目录有 `.trae/skills/` | 在 TRAE CN 设置 → Skills 中刷新 | 列表出现 `steam-plus-plus-locator`、`github-access-watt-fallback` 与 `watt-toolkit-launcher` |
| T-DISC-02 | `description` 字段可路由 | 已导入 | 在对话中输入 "GitHub 上不去" | 模型路由到 `github-access-watt-fallback` |
| T-DISC-03 | `description` 字段可路由 | 已导入 | 在对话中输入 "命令行静默启动 Steam++" | 模型路由到 `watt-toolkit-launcher` |
| T-DISC-04 | `description` 字段可路由 | 已导入 | 在对话中输入 "Steam++.exe 装哪了" | 模型路由到 `steam-plus-plus-locator` |

## 2. EXE 路径解析（**只搜 `Steam++.exe`**）

### 2.1 `steam-plus-plus-locator`

| ID | 标题 | 前提 | 操作 | 预期 |
|---|---|---|---|---|
| T-LOC-01 | `Steam++.exe` 标准安装路径命中 | 装在 `%LOCALAPPDATA%\Steam++\` | 触发 Skill | 候选列表首条为 `%LOCALAPPDATA%\Steam++\Steam++.exe`，`executable=Steam++.exe`，`priority=1`，`validity=ok` |
| T-LOC-02 | Programs 目录命中 | 装在 `%LOCALAPPDATA%\Programs\Steam++\` | 触发 Skill | 命中 `Programs` 目录下 `Steam++.exe` |
| T-LOC-03 | `ProgramFiles` 命中 | 装在 `%PROGRAMFILES%\Steam++\` | 触发 Skill | 命中 `ProgramFiles` 下 `Steam++.exe` |
| T-LOC-04 | `ProgramFiles(x86)` 命中 | 装在 `%PROGRAMFILES(x86)%\Steam++\` | 触发 Skill | 命中 `ProgramFiles(x86)` 下 `Steam++.exe` |
| T-LOC-05 | 全小写 `steam++.exe` 命中 | Windows 文件系统不区分大小写 | 触发 Skill | 候选统一规范为 `Steam++.exe`（`executable` 字段），`validity=ok` |
| T-LOC-06 | Microsoft Store 包命中 | 通过 `Get-AppxPackage *Steam*` 安装 | 触发 Skill | 候选含 Appx `InstallLocation` 下的 `Steam++.exe`，`source=appx`，`priority=2` |
| T-LOC-07 | 注册表兜底命中 | 装在非标准目录但写入注册表 | 触发 Skill | 候选含注册表 `DisplayName` 包含 "Steam++" 的项，`source=registry`，`priority=3` |
| T-LOC-08 | PATH 命中 | 装到自定义目录并加入 PATH | 触发 Skill | 候选含 `where.exe Steam++.exe` 的结果，`source=where`，`priority=4` |
| T-LOC-09 | 广搜兜底 | 仅在 D 盘有备份 | 触发 Skill | 候选含 D 盘深度 ≤3 的搜索结果，`source=broad-search`，`priority=5` |
| T-LOC-10 | 多源合并 | 同一 EXE 同时被 env-path 和 appx 命中 | 触发 Skill | 单条候选，`source="env-path;appx"`，`priority=1` |
| T-LOC-11 | 全部未命中 | 任意位置都找不到 `Steam++.exe` | 触发 Skill | 候选列表为空，提示去 steampp.net 下载带 `Steam++.exe` 的发行包，**不**抛异常 |
| T-LOC-12 | **绝不**搜 `WattToolkit.exe` | 本机只有 `WattToolkit.exe`（新版） | 触发 Skill | 候选列表为空（即使 `WattToolkit.exe` 存在也不被识别） |
| T-LOC-13 | 缓存命中且候选仍在 | 已搜过一次，24h 内再次调用 | 触发 Skill | 校验候选路径后直接返回缓存结果，耗时 < 200ms |
| T-LOC-14 | 缓存失效 | 缓存存在但候选已被卸载 | 触发 Skill | 跳过缓存，重新走 5 步搜索 |
| T-LOC-15 | 可疑签名 | 候选存在但数字签名未通过 | 触发 Skill | 标记 `validity=suspect`，不自动采用但保留 |
| T-LOC-16 | 非管理员权限 | 当前用户无管理员 | 触发 Skill | 跳过 `HKLM` 注册表，继续 HKCU / Appx / PATH / 广搜 |

### 2.2 `watt-toolkit-launcher` 路径消费

| ID | 标题 | 前提 | 操作 | 预期 |
|---|---|---|---|---|
| T-PATH-01 | `Steam++.exe` 标准安装路径 | 装在 `%LOCALAPPDATA%\Steam++\` | 通过 Skill 触发"启动 Steam++" | 命中 `%LOCALAPPDATA%\Steam++\Steam++.exe` |
| T-PATH-02 | `Steam++.exe` 装在 Programs | 装在 `%LOCALAPPDATA%\Programs\Steam++\` | 同上 | 命中 Programs 目录 |
| T-PATH-03 | `Steam++.exe` 装在 ProgramFiles | 装在 `%PROGRAMFILES%\Steam++\` | 同上 | 命中 ProgramFiles 目录 |
| T-PATH-04 | Microsoft Store 包 | 通过 `Get-AppxPackage *Steam*` 安装 | 同上 | 解析 Appx `InstallLocation` 下的 `Steam++.exe` |
| T-PATH-05 | `steam++.exe` 全小写命中 | Windows 不区分大小写 | 触发 Skill | 命中并规范化为 `Steam++.exe` |
| T-PATH-06 | **绝不**找 `WattToolkit.exe` | 本机只有 `WattToolkit.exe` | 触发 Skill | **不**命中 `WattToolkit.exe`；若 locator 也找不到，提示用户安装带 `Steam++.exe` 的发行包 |
| T-PATH-07 | 未安装 | 任意目录都找不到 | 触发 Skill | **自动调用 `steam-plus-plus-locator` 兜底**，仍找不到时提示用户安装并中止 |
| T-PATH-08 | 调用 locator 兜底 | launcher 硬编码路径都不存在 | 触发 launcher | 自动调用 locator → 拿候选 → 选 `priority` 最小的 → 继续启动流程 |

## 3. `watt-toolkit-launcher` 子命令矩阵

| ID | 子命令 / 操作 | 操作 | 预期 |
|---|---|---|---|
| T-CLI-01 | `proxy -on` | `Start-Process $steamExe -ArgumentList '-clt','proxy','-on'` | 进程 `Steam++` 出现，主窗口句柄 = 0（最小化到托盘），`github.com:443` 30s 内可达 |
| T-CLI-02 | `proxy -off` | `Start-Process $steamExe -ArgumentList '-clt','proxy','-off'` | 代理关闭，30s 内 `github.com:443` 再次不可达（若本来没有别的代理） |
| T-CLI-03 | `proxy` (toggle) | 当前关闭 → 调用 | 转为开启；反之亦然 |
| T-CLI-04 | `c -silence` | `Start-Process $steamExe -ArgumentList '-clt','c','-silence'` | 进程启动但不弹窗，托盘区出现图标 |
| T-CLI-05 | `steam -account <name>` | PowerShell 用管理员身份运行 | 当前 Steam 用户切换为 `<name>` |
| T-CLI-06 | `app -id 730 -silence` | Steam 已安装 | 启动 CS:GO 的连接服务，进程保持运行 |
| T-CLI-07 | `show -cert` | 同上 | 控制台输出根证书信息 |
| T-CLI-08 | **开机自启动（开）** | 改 `GeneralSettings.AutoRunOnStartup` → `true`，重新读回校验 | 字段为 `true`；下次 Steam++ 启动时**自动**进入托盘模式 |
| T-CLI-09 | **开机自启动（关）** | 改 `GeneralSettings.AutoRunOnStartup` → `false`，重新读回校验 | 字段为 `false`；下次 Steam++ 启动时**不会**自动启动 |
| T-CLI-10 | **启动后自动加速（开）** | 改 `ProxySettings.ProgramStartupRunProxy` → `true`，重新读回校验 | 字段为 `true`；下次 Steam++ 启动时**自动**开代理（`proxy -on` 等价行为） |
| T-CLI-11 | **启动后自动加速（关）** | 改 `ProxySettings.ProgramStartupRunProxy` → `false`，重新读回校验 | 字段为 `false`；下次 Steam++ 启动时**不会**自动开代理 |
| T-CLI-12 | **安全关闭** | (a) `Start-Process $steamExe -clt proxy -off` → 2s → (b) `Get-Process Steam++ \| Stop-Process -Force` | 进程 5s 内退出；`github.com:443` 不可达（若无其他代理）；端口 26561 释放 |
| T-CLI-13 | **配置字段不存在** | 旧版 Steam++（2.x）没有 `AutoRunOnStartup` / `ProgramStartupRunProxy` 字段 | Skill **不**写盘，直接提示用户去 GUI 操作 |
| T-CLI-14 | 备份机制 | 写配置前 Skill 应自动 `Copy-Item $jsonPath "$jsonPath.bak" -Force` | 写前存在 `.bak` 文件，原始值可回滚 |

## 4. `github-access-watt-fallback` 端到端

### 4.1 探测

| ID | 标题 | 前提 | 操作 | 预期 |
|---|---|---|---|---|
| T-PROBE-01 | TCP 探测 github.com | 正常网络 | `Test-NetConnection github.com -Port 443` | `True`，5s 内返回 |
| T-PROBE-02 | api.github.com 探测 | 正常网络 | `Test-NetConnection api.github.com -Port 443` | `True` |
| T-PROBE-03 | raw.githubusercontent.com 探测 | 正常网络 | `Test-NetConnection raw.githubusercontent.com -Port 443` | `True` |

### 4.2 异常路径 → 自动唤起

| ID | 标题 | 前提 | 操作 | 预期 |
|---|---|---|---|---|
| T-FAIL-01 | GitHub 不可达时自动拉起 | 已 mock 路由黑洞 `github.com`；Steam++ 已装 | 在 TRAE 对话中请求 "fetch 一下 https://github.com/BeyondDimension/SteamTools/blob/develop/README.md" | 探测失败 → 自动 `Steam++.exe -clt proxy -on` → 30s 内 `Test-NetConnection github.com -Port 443` 变 `True` → `WebFetch` 重试成功 |
| T-FAIL-02 | `git clone` 失败时拉起 | 同上 | 在 TRAE 对话中执行 `git clone https://github.com/foo/bar.git` | 失败 → Skill 触发 → Steam++ 启动 → `git clone` 重试成功 |
| T-FAIL-03 | 用户口语化触发 | 正常网络 | 在 TRAE 对话中输入 "GitHub 上不去了，帮我看看" | Skill 触发；Steam++ 启动；给出恢复耗时报告 |
| T-FAIL-04 | Steam++ 未安装 | GitHub 不可达 + 未装 Steam++ | 触发 Skill | Skill 立即返回并提示用户去 steampp.net 安装带 `Steam++.exe` 的发行包，**不**抛出 stack trace |
| T-FAIL-05 | 30s 内未恢复 | mock 网络黑洞 | 触发 Skill | 返回失败并提示用户打开 Steam++ GUI 检查 GitHub 是否真的勾选 |
| T-FAIL-06 | **只装了 `WattToolkit.exe` 不支持** | GitHub 不可达 + 本机只有 `WattToolkit.exe` | 触发 Skill | Skill 立即返回并提示用户去 steampp.net 下载带 `Steam++.exe` 的发行包；**不**调用 `WattToolkit.exe` |

### 4.3 正常路径（不应误触）

| ID | 标题 | 前提 | 操作 | 预期 |
|---|---|---|---|---|
| T-OK-01 | 正常 fetch GitHub | GitHub 可达 | `WebFetch https://github.com` | 成功，不调用 Skill |
| T-OK-02 | 正常 `git push` | 凭证 + 网络正常 | `git push` | 成功，不调用 Skill |
| T-OK-03 | 仅本地操作 | — | 请求本地文件读取 | 不调用 Skill |

## 5. 性能 / 资源

| ID | 标题 | 操作 | 预期 |
|---|---|---|---|
| T-PERF-01 | 启动耗时 | 冷启动 `-clt proxy -on` | `Get-Process Steam++` 在 5s 内出现 |
| T-PERF-02 | 恢复耗时 | mock 黑洞后调用 Skill | 95% 场景下 30s 内 `github.com:443` 恢复 |
| T-PERF-03 | 内存占用 | 静默态 `Steam++.exe` | < 200 MB 工作集（参考值，需以本机为准） |

## 6. 安全 / 副作用

| ID | 标题 | 操作 | 预期 |
|---|---|---|---|
| T-SEC-01 | 不静默改 GitHub 加速项勾选 | 首次运行 | Skill 仅提示用户去 GUI 勾选 GitHub；**不**直接修改 `ProxySettings.SupportProxyServicesStatus`（即"哪些服务被加速"的列表） |
| T-SEC-02 | 不自动 kill Steam++ | 验证成功后 | Steam++ 进程保持运行（反代需要常驻） |
| T-SEC-03 | marker 文件隔离 | 已首次完成 GUI 勾选 | `%LOCALAPPDATA%\github-access-watt-fallback\primed` 存在，不再提示 |
| T-SEC-04 | 不写 hosts / 防火墙 | 任意 | 系统中 `%WINDIR%\System32\drivers\etc\hosts` 与 `netsh advfirewall` 不被改动 |
| T-SEC-05 | 开自启后必须能取消 | 写 `AutoRunOnStartup=true` 之后 | Skill 应能直接改回 `false`；不得"以为会启动所以让用户去 GUI 取消" |

## 7. 自动化钩子（可选）

如果要在 CI 里跑，可以用 Pester 写一个最小验证：

```powershell
Describe 'Steam++ CLI' {
    It 'starts and becomes reachable' {
        Start-Process $steamExe -ArgumentList '-clt','proxy','-on'
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        do {
            $ok = (Test-NetConnection github.com -Port 443 -InformationLevel Quiet)
            Start-Sleep 2
        } until ($ok -or $sw.Elapsed.TotalSeconds -gt 30)
        $ok | Should -BeTrue -Because "代理启动后 GitHub:443 必须在 30s 内可达"
    }
}
```

## 8. 端到端验收场景

### 8.1 验收场景 #1：Watt Toolkit 未启动，无法访问 GitHub，自动调用 Skill 救活并完成代码上传

> **测试场景**：Steam++ / Watt Toolkit 没有启动，无法访问 GitHub
> **用户输入**："把这个代码上传到 GitHub 保存了"
> **验收标准**：TRAE 自动调用 `github-access-watt-fallback`（必要时顺带调用 `steam-plus-plus-locator` 找 EXE），成功启动 Steam++ 反代，使 GitHub 可达，最终完成代码上传。

#### 前置

1. 操作系统 Windows 10/11
2. 已安装 Steam++（带 `Steam++.exe` 的发行包），但 **当前未运行**（任务管理器确认无 `Steam++` 进程）
3. 已用 Steam++ GUI 一次性勾选过 "GitHub" 加速项（`%LOCALAPPDATA%\github-access-watt-fallback\primed` 标记存在）
4. 当前环境 `github.com:443` **不可达**（可用 `Test-NetConnection github.com -Port 443 -InformationLevel Quiet` 验证返回 `False`；如本机实际可达，需在 hosts / 防火墙里把 `github.com` 黑洞）
5. 本地有 git 仓库，远程指向 GitHub（例：`git remote add origin https://github.com/<user>/<repo>.git`）
6. 当前分支至少有一个本地提交未推送

#### 执行步骤（在 TRAE CN 对话窗口中）

1. 打开 TRAE CN，确保工作区是上述 git 仓库所在目录
2. 在 TRAE 的 Skills 面板确认已导入 `skill-test`，三个 Skill 全部可见
3. 在对话中输入："把这个代码上传到 GitHub 保存了"
4. **不要**手动打开 Steam++ GUI，让 TRAE 自行处理

#### 预期（按时间顺序）

| 阶段 | 预期现象 |
|---|---|
| 0 ~ 2s | TRAE 模型识别到 `git push` 即将失败，调用 `github-access-watt-fallback` |
| 0 ~ 5s | Skill 执行 Step 1：探测 `github.com:443` → 失败（`Test-NetConnection` 返回 `False`） |
| 5 ~ 10s | Skill 执行 Step 2：按 env-path / Programs / ProgramFiles 顺序搜 `Steam++.exe`（或在硬编码路径全失败后调用 `steam-plus-plus-locator` 兜底）→ 命中 |
| 10 ~ 15s | Skill 执行 Step 4：`Start-Process -FilePath $steamExe -ArgumentList '-clt','proxy','-on'` → `Steam++` 进程出现，主窗口句柄 = 0（最小化到托盘，不弹窗） |
| 15 ~ 45s | Skill 执行 Step 5：每 2s 轮询 `Test-NetConnection github.com -Port 443`，最多 30s。**预期在 15 ~ 30s 之间返回 `True`** |
| 45 ~ 60s | Skill 返回成功消息给主对话，主对话继续执行 `git push`（可能需要提示用户输入凭据） |
| 60 ~ 90s | `git push` 成功，TRAE 提示 "代码已上传到 GitHub" |

#### 验收判定

**通过**：

- TRAE 在**没有用户手动打开 Steam++ GUI** 的前提下完成代码上传
- Steam++ 进程在 TRAE 触发后才出现（任务管理器时间戳佐证）
- 总耗时在 90s 以内
- 终端日志中能看到 `Test-NetConnection` 由 `False` 变 `True` 的轮询过程

**不通过**的典型症状：

| 症状 | 可能的根因 |
|---|---|
| TRAE 报告"git push 失败：connection timed out"且**没**自动调用 Skill | 模型未把错误路由到 Skill；可能需要让用户输入更明确（"GitHub 上不去了，帮我用 Steam++ 救活"） |
| Skill 被调用但找不到 `Steam++.exe` | 本机装的可能只有 `WattToolkit.exe`（新版）— 请改装带 `Steam++.exe` 的发行包 |
| 启动了 Steam++ 但 `github.com:443` 30s 内未恢复 | 用户未在 Steam++ GUI 勾选过 GitHub 加速项；或 Steam++ 反代服务异常 |
| 恢复后 `git push` 仍失败 | 凭据问题（SSH key / PAT 失效），与 Skill 无关 |
| 弹出 Steam++ 主窗口（不静默） | 用了 `-clt c`（正常命令）而非 `-clt proxy -on`；或 Steam++ 自身 bug |

#### 子用例

| ID | 标题 | 变体 | 预期 |
|---|---|---|---|
| T-E2E-01 | 标准环境 | `Steam++.exe` 在默认路径 | 全流程 60 ~ 90s 完成 |
| T-E2E-02 | 装在非默认路径 | `Steam++.exe` 在 `D:\Tools\Steam++\` | 触发 `steam-plus-plus-locator` 兜底搜索，命中后继续 |
| T-E2E-03 | Steam++ 进程残留 | 后台已有 `Steam++` 进程但代理未开 | Skill 不重复启动，只执行 `Start-Process $steamExe -clt proxy -on`（幂等） |
| T-E2E-04 | 30s 内未恢复 | mock 网络黑洞 | Skill 返回失败，由用户决定下一步（重试 / 检查 GUI） |
| T-E2E-05 | GitHub 可达但 push 失败 | 凭证过期 | Skill **不**触发（探测通过），TRAE 直接报认证错误；用户需更新 PAT |
| T-E2E-06 | 装的是 `WattToolkit.exe`（新版） | 本机只有新版本 | Skill 立即提示 "本 Skill 只支持 Steam++.exe，请去 steampp.net 下载带 Steam++.exe 的发行包"，**不**调用 WattToolkit.exe |
| T-E2E-07 | 首次未在 GUI 勾选 GitHub | marker 文件不存在 | Skill 仍然能启动 Steam++，但 30s 探测会失败；最终提示用户去 GUI 勾选 |

#### 复现 / 调试

如果验收失败，按以下顺序定位：

1. **模型是否路由成功**：对话窗口里搜索 "github-access-watt-fallback" 字样；如无，调用的不是这个 Skill
2. **`Steam++.exe` 是否被找到**：看 Skill 输出 "EXE resolved: <path>"
3. **进程是否启动**：任务管理器里查 `Steam++` 进程
4. **代理端口是否起来**：`netstat -ano | findstr :443`（Steam++ 默认监听本地代理端口）
5. **TCP 探测日志**：Skill 应该输出每次 `Test-NetConnection` 的结果
6. **30s 后的最终结果**：Skill 应明确告诉主对话 "success" 或 "failed"

## 9. 缺陷记录模板

| 字段 | 内容 |
|---|---|
| 用例 ID | T-XXX-NN |
| 复现步骤 | … |
| 实际结果 | … |
| 预期结果 | … |
| 优先级 | P0 / P1 / P2 |
| 备注 | … |

## 10. v1.1 增强：manual-path + 两阶段广搜

> 目标：① 5 源全部 miss 时**提示用户手动设置路径**并持久化到 `%LOCALAPPDATA%\steam-plus-plus-locator\manual-path.json`（priority 0）；② 重构 broad-search 为两阶段：先在所有文件系统根上深度 5 搜 `*Steam++*` 目录，再在每个候选目录里全盘搜 `Steam++.exe`。

### 10.1 manual-path 写入与读取

| ID | 标题 | 前提 | 操作 | 预期 |
|---|---|---|---|---|
| T-MANUAL-01 | 5 源全部 miss 时提示手动设置 | 本机无任何 `Steam++.exe`、manual-path.json 不存在 | 触发 `steam-plus-plus-locator` | Skill 不抛异常；输出标准提示语（含示例路径）；创建空 `manual-path.json` 模板**或不**创建（等用户回复） |
| T-MANUAL-02 | 用户回复路径后写入 | T-MANUAL-01 后用户回复 `D:\Tools\Steam++\Steam++.exe` | Skill 写入 `manual-path.json`（含 `setAt` UTC 时间戳） | 文件存在，结构符合 SKILL.md §"手动路径的存储"；再次调用立即返回该路径，priority=0 |
| T-MANUAL-03 | priority=0 短路 | manual-path.json 存在且 `Test-Path=true` | 触发 Skill | **跳过**所有其它源；返回单条结果，source=`manual-path`, priority=0 |
| T-MANUAL-04 | 手动路径失效 | manual-path.json 中路径被用户手动删除/移动 | 触发 Skill | `validity=missing`；**继续**执行 5 源扫描；若 5 源命中则用命中结果；若仍 miss 则再次提示用户（**不**自动覆盖 manual-path.json） |
| T-MANUAL-05 | 重新搜索保留手动路径 | manual-path.json 已存在；cache.json 存在 | 用户说"重新搜索" | 仅删除 `cache.json`；**保留** manual-path.json；manual-path 仍 priority 0 命中 |
| T-MANUAL-06 | 忘记手动路径 | manual-path.json 已存在 | 用户说"忘记手动路径" | 删除 `manual-path.json`；下次 Skill 调用回到 5 源扫描 |
| T-MANUAL-07 | 更新手动路径 | manual-path.json 已存在 | 用户说"改路径为 X" | 覆盖 `path` 字段；`setAt` 更新；不删 `cache.json` |
| T-MANUAL-08 | 路径大小写归一 | 用户回复 `c:\tools\steam++\steam++.exe`（全小写） | Skill 写入 | `path` 字段保留文件系统原样；`executable` 字段统一为 `Steam++.exe`；后续 `Test-Path` 通过 |
| T-MANUAL-09 | 拒绝 WattToolkit.exe | 用户回复 `C:\Program Files\Watt Toolkit\WattToolkit.exe` | Skill 写入 | **拒绝**写入；提示"本 Skill 仅支持 Steam++.exe，请去 steampp.net 下载带 Steam++.exe 的发行包" |
| T-MANUAL-10 | 拒绝相对路径 | 用户回复 `Steam++\Steam++.exe` | Skill 写入 | **拒绝**写入；提示"请提供绝对路径（以盘符开头）" |
| T-MANUAL-11 | 拒绝路径不存在 | 用户回复 `Z:\Fake\Steam++.exe` | Skill 写入 | 可选：仍写入但 `lastVerified=null`；或立即 `Test-Path=false` 并提示"路径不存在，确认一下？"。推荐后者更友好 |
| T-MANUAL-12 | 目录权限隔离 | manual-path.json 父目录无写权限 | Skill 写入 | `Write-Error` 但**不**抛 stack trace；提示用户检查 `%LOCALAPPDATA%` 权限 |

### 10.2 两阶段广搜（broad-search 重构）

| ID | 标题 | 前提 | 操作 | 预期 |
|---|---|---|---|---|
| T-BROAD-01 | 单根盘标准位置 | 仅 `C:\Tools\Steam++\Steam++.exe`（自定义目录） | 触发 Skill | 命中 1 条；priority=5；source=`broad-search`；目录权重=100（EXE 与父目录同名） |
| T-BROAD-02 | 便携版多级嵌套 | `D:\Portable\Steam++-Portable-v3.0.0-x64\Steam++\Steam++.exe` | 触发 Skill | 命中 1 条；priority=5；目录权重=80（命中 `Steam++-*Portable*\…\Steam++\Steam++.exe` 模式） |
| T-BROAD-03 | bin 子目录 | `D:\Tools\Steam++\bin\Steam++.exe` | 触发 Skill | 命中 1 条；目录权重=90 |
| T-BROAD-04 | 跨多个根盘 | C/D/E 都有 Steam++ 文件夹 | 触发 Skill | 命中 3 条；按"根盘字母 + 目录权重"二级排序 |
| T-BROAD-05 | 深度 5 边界 | Steam++ 目录在第 6 层 | 触发 Skill | **不**命中该目录（深度边界外）；候选列表为空 → 走"全部未命中"流程 |
| T-BROAD-06 | 仅固定盘扫描 | 系统有 U 盘 D:\USB\Steam++\Steam++.exe | 触发 Skill | U 盘路径**不**被默认扫描；用户用 `locator config --include-removable` 开启后才扫 |
| T-BROAD-07 | 目录命名变体 | `D:\Steam++中文\`（含中文）、`D:\Steam++ (x64)\`、`D:\steam++-v3.0.0\` | 触发 Skill | 通过 `(?i)steam\+\+` 正则全部命中候选目录；EXE 命中则加入结果 |
| T-BROAD-08 | EXE 名大小写 | `D:\Steam++\steam++.exe`（全小写） | 触发 Skill | 命中；`executable` 字段统一为 `Steam++.exe`；`path` 字段保留原样 |
| T-BROAD-09 | 旧版残留 | `D:\OldSteam++\Steam++.exe`（目录名 `OldSteam++`） | 触发 Skill | 命中；`source=broad-search`；由调用方决定是否采用 |
| T-BROAD-10 | EXE 在目录内深层 | `D:\Steam++-Portable\foo\bar\baz\Steam++.exe` | 触发 Skill | 第一阶段命中 `Steam++-Portable`（深度 1）；第二阶段全盘搜命中 EXE；不影响结果 |
| T-BROAD-11 | 性能 | 全盘扫描 1TB 机械盘 D: | 触发 Skill | 深度 5 目录枚举 < 30s（粗略指标，需以本机为准） |
| T-BROAD-12 | 与 manual-path 共存 | manual-path.json 存在；broad-search 也能命中 | 触发 Skill | **仅**返回 manual-path 一条；broad-search 命中被短路（priority 0 永远优先） |
| T-BROAD-13 | 拒绝扫描系统目录 | 系统还原点目录 `C:\System Volume Information\` | 触发 Skill | 该目录**不**被扫描（`-Force` 不开启系统卷影）；即使有同名文件也被跳过 |

### 10.3 描述 / 路由（TRAE 模型侧）

| ID | 标题 | 操作 | 预期 |
|---|---|---|---|
| T-DESC-01 | description 含 manual-path 关键词 | TRAE 模型读 SKILL.md frontmatter | description 字段含"manual path"、"set a manual path"、"manual-path.json" 关键词，模型可路由用户说"我手动指定路径" / "用我之前设的 Steam++ 路径" |
| T-DESC-02 | description 含两阶段广搜 | 同上 | description 字段含"two-phase broad search" / "broad search directories" / "广搜" 关键词 |
| T-DESC-03 | 用户说"忘记手动路径" | TRAE 对话 | 模型路由到 `steam-plus-plus-locator` 并执行"删除 manual-path.json"流程 |
| T-DESC-04 | 用户说"重新搜索" | TRAE 对话 | 模型路由到 `steam-plus-plus-locator` 并执行"删除 cache.json"流程 |
