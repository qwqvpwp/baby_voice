# Plan: Steam++ 全生命周期控制（启动 / 加速 / 开机自启 / 启动后自动加速 / 关闭）

## Summary

按你 `/plan` 列出的 4 步工作流，给 `watt-toolkit-launcher` Skill 增加 4 个**新能力**：开机自启动、启动后自动加速、关闭软件（已有但需补强）；并补"**取消开机自启动**"和"**取消启动后自动加速**"两条反向操作。同时把尝试过程中踩到的"上游 CLI 不直接暴露"的事实落到文档里，并把飞书介绍文档同步更新。

执行后 `watt-toolkit-launcher` 将覆盖 Steam++ 的**完整生命周期**（首次安装后的开机自启、启动、加速、关代理、关软件），使 TRAE CN 对话可一句话完成上述任一动作。

## Current State Analysis

### 现状

- `d:\Code\Voice\baby_voice\skill-test\.trae\skills\` 下三个 Skill：
  - `watt-toolkit-launcher/SKILL.md` — 通用 CLI 启动器，含 11 行命令矩阵（已包含 `proxy -on` / `proxy -off` / `c -silence` / `main` / `show -cert` / `Stop-Process` 等）
  - `github-access-watt-fallback/SKILL.md` — 场景化自愈（仅 `proxy -on`）
  - `steam-plus-plus-locator/SKILL.md` — 找 EXE
- `README.md` 与 `TEST_CASES.md` 已记录现有命令
- 飞书介绍文档：<https://ucnc1tzsynb3.feishu.cn/docx/BxxAdPW2goHM6hxSspgcqWHWnQh>

### 关键发现（基于阅读源码注释 + 现有 Skill 的 `description`）

- Steam++ 上游的 `src/BD.WTTS.Client/Startup/Startup.Commands.cs`（`develop` 分支）通过 `System.CommandLine` 暴露子命令，统一以 `-clt` 前缀调用。已知的子命令集：`main` / `c` / `proxy` / `steam` / `app` / `show` / `settings` / `i`。
- 上游 CLI **不**直接暴露"开机自启动"和"启动后自动加速"开关 — 这两个是 Steam++ 的**应用内配置项**，存在 `%LOCALAPPDATA%\Steam++\Configs\Default.json`（GUI 启动后由 `SettingsPageViewModel` / `ProxyService` 写入）。可被 PowerShell **读取和改写**，但有版本差异风险。
- "开机自启动"在 Windows 上更通用的实现是写注册表 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`（值名 `Steam++`，数据为 `Steam++.exe -clt c -silence` 的快捷方式）；Steam++ 自己也可能写这个键，但版本不同。
- "关闭软件"现有 Skill 用 `Stop-Process -Id <pid>`，可行但要补一个"先关代理再退主进程"的安全序列。

### 关键空白

| 你提的能力 | 当前 Skill 支持 | 缺失 |
|---|---|---|
| 启动 Steam++ | ✅ `-clt main` / `-clt c -silence` |  |
| 启动加速器（开代理） | ✅ `-clt proxy -on` |  |
| 开机自启动 | ❌ | 需新增（注册表 `Run` 键） |
| 启动后自动加速 | ❌ | 需新增（改 Steam++ 配置 `Config.AutoAccelerateOnStart`） |
| 取消开机自启动 | ❌ | 需新增（删除注册表 `Run` 键的值名） |
| 取消启动后自动加速 | ❌ | 需新增（配置项改回 false） |
| 关闭软件 | ⚠️ 有 `Stop-Process` 但无安全序列 | 补：先 `-clt proxy -off` 再 `Stop-Process` |

## Proposed Changes

### 1. 任务执行（Step 1：实操记录）

在执行时**实际跑一遍**下列命令，把每条命令的实际输出 / 副作用 / 失败情况记到一个 markdown 笔记里（`docs/STEAMPP_LIFECYCLE_NOTES.md`，新建）。这条笔记就是 Step 2 写文档的事实来源。

| 操作 | 计划执行命令 | 期望结果（待验证） |
|---|---|---|
| 启动 Steam++（GUI） | `Start-Process $steamExe -ArgumentList '-clt','main'` | 进程出现，主窗口可见 |
| 启动 Steam++（静默到托盘） | `Start-Process $steamExe -ArgumentList '-clt','c','-silence'` | 进程出现，无主窗口 |
| 启动加速器（开代理） | `Start-Process $steamExe -ArgumentList '-clt','proxy','-on'` | 进程出现；`github.com:443` 30s 内可达 |
| **开机自启动** | `Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'Steam++' -Value '"C:\Users\xxx\AppData\Local\Steam++\Steam++.exe" -clt c -silence'` | 重启后 Steam++ 进程自动出现 |
| **启动后自动加速** | 改 `%LOCALAPPDATA%\Steam++\Configs\Default.json` 的相关字段（具体键名以实际配置文件为准，需在 Step 1 实测时确定；候选键名 `AutoAccelerateOnStart` / `StartupAccelerate` / `IsProxyOnStart`） | 重启 Steam++ 后自动 `-clt proxy -on` 等价行为 |
| **取消开机自启动** | `Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'Steam++'` | 重启后 Steam++ 不再自动出现 |
| **取消启动后自动加速** | 改回配置文件相应字段为 `false` | 重启 Steam++ 后不再自动加速 |
| 关闭软件（安全序列） | `Start-Process $steamExe -ArgumentList '-clt','proxy','-off'`（让代理先收）；`Get-Process Steam++ \| Stop-Process -Force` | 进程退出，托盘图标消失，`github.com:443` 不可达（若无其他代理） |

如果 Step 1 实操发现某条命令的"实际行为"与上表"期望结果"不同（例如 "启动后自动加速" 实际是靠 GUI toggle 控制、改 JSON 不生效），就把这一行标注 `❌ 行不通` 并改用备选方案（如改用"把 Steam++.exe 的快捷方式放到 `shell:startup` 文件夹"实现开机自启）。

### 2. 任务执行（Step 2：编写简洁的文档）

新建 `docs/STEAMPP_LIFECYCLE_NOTES.md`（或在主 README 增节"Steam++ 全生命周期命令"），基于 Step 1 的实测结果，列：

- 每个意图（启动 / 加速 / 开机自启 / 启动后自动加速 / 取消 / 关闭）的**最终命令**
- 命令的**前提**（管理员权限？EXE 路径？）
- 命令的**副作用**（写注册表？改 JSON？）
- 命令的**回退方式**（怎么撤销）
- 任何"尝试了但失败"的项，明确写出"为什么不行"和"建议的替代"

### 3. 任务执行（Step 3：改写 Skill 的执行命令）

更新 `d:\Code\Voice\baby_voice\skill-test\.trae\skills\watt-toolkit-launcher\SKILL.md`：

- 现有 "Command Map" 表格**追加** 6 行：开/关开机自启、开/关启动后自动加速、安全关闭
- 新增小节"开机自启动（Windows Run 键）"，含 PowerShell 命令模板 + 注册表路径 + 撤销方式
- 新增小节"启动后自动加速（改 Steam++ 配置）"，含 JSON 路径 + 关键字段（以 Step 1 实测结果为准）+ 撤销方式
- 重写"关闭主程序"条目为安全序列（先关代理再 Stop-Process）
- 更新 `description` 字段，把 "auto start, post-start auto-accelerate" 加入能力描述，让模型能路由到该 Skill

不改动 `steam-plus-plus-locator` 与 `github-access-watt-fallback`，除非 Step 1 实测发现这两个 Skill 内部也要用新的"关闭 / 自启"逻辑（一般不会）。

### 4. 任务执行（Step 4：更新飞书文档）

overwrite 飞书介绍文档 <https://ucnc1tzsynb3.feishu.cn/docx/BxxAdPW2goHM6hxSspgcqWHWnQh>：

- "原理（Steam++ CLI）" 章节追加"全生命周期命令矩阵"（开/关启动、代理、开机自启、启动后自动加速、关闭）
- "已知限制" 章节追加"开机自启动 / 启动后自动加速 是通过 Windows 注册表与 Steam++ 配置文件间接实现，非上游 CLI 暴露的开关"
- 飞书文档 URL 保持不变（仅 overwrite）

## Assumptions & Decisions

> **A1. "开机自启动" 的实现方式**：用 Windows 注册表 `HKCU\...\Run` 写值，**不**放进 `shell:startup` 文件夹。理由：注册表方案更接近 Steam++ 自己的实现（其配置页的"开机自启" toggle 大概率是写这个键），且便于用 `Remove-ItemProperty` 一键撤销。如果你期望"放到启动文件夹"或"创建 Windows 计划任务"，告诉我我改方案。

> **A2. "启动后自动加速" 的实现方式**：直接改 Steam++ 配置文件 `%LOCALAPPDATA%\Steam++\Configs\Default.json`。如果该字段不存在或不生效（实测可能发生），降级方案是**让 Skill 在调用时**把"启动 Steam++ + 立即 -clt proxy -on"绑定为一个原子动作（等价于"启动后自动加速"），但**不**修改用户配置文件（保留 T-SEC-01 约定）。

> **A3. "关闭软件" 的安全序列**：先 `-clt proxy -off`（让代理先收尾），再 `Stop-Process -Force`。如果用户只说"关掉 Steam++"（不含代理），Skill 默认走安全序列并在回报里说明"代理已先关闭"。

> **A4. Skill 描述更新方向**：`watt-toolkit-launcher` 的 `description` 字段新增 "configure Windows auto-start (Run key) and post-start auto-accelerate (config file)" 这类语义，让 TRAE 模型在用户说"开机自动启动 Steam++" / "启动后自动加速"时路由到该 Skill。

> **A5. 不引入新 Skill**。所有能力都归到 `watt-toolkit-launcher` 一处，避免 Skill 数量膨胀（当前 3 个已经够清晰）。

> **A6. macOS / Linux 不在范围**。原有 v1 限制（仅 Windows PowerShell）保持不变；开机自启方案仅覆盖 Windows 注册表。

## Verification

执行完成后按以下顺序验证：

1. **Skill 文件可被 TRAE 识别**：把 `skill-test` 目录在 TRAE CN 重新导入一次（覆盖旧版本），确认三个 Skill 都还在。
2. **description 路由可用**：在 TRAE 对话中输入 "开机自启动 Steam++" / "取消启动后自动加速" / "关掉 Steam++"，确认模型路由到 `watt-toolkit-launcher` 而非其他 Skill。
3. **生命周期命令可执行**：
   - 启动：`Start-Process $steamExe -clt main` → 进程出现
   - 静默启动：`Start-Process $steamExe -clt c -silence` → 进程出现、无主窗口
   - 开代理：`Start-Process $steamExe -clt proxy -on` → `github.com:443` 30s 内可达
   - 关代理：`Start-Process $steamExe -clt proxy -off` → `github.com:443` 不可达
   - 开自启：注册表 Run 键有 `Steam++` 值 → 重启后进程出现
   - 取消自启：注册表 Run 键无 `Steam++` 值 → 重启后进程不出现
   - 启动后自动加速：配置文件相应字段为 `true` → 重启 Steam++ 后代理自动为开
   - 取消启动后自动加速：配置文件相应字段为 `false` → 重启 Steam++ 后代理为关
   - 安全关闭：进程退出 + 代理关闭
4. **回退有效**：上述每条"开"操作都对应"关"操作能撤销。
5. **飞书文档可读**：在浏览器打开 <https://ucnc1tzsynb3.feishu.cn/docx/BxxAdPW2goHM6hxSspgcqWHWnQh>，确认"全生命周期命令矩阵"小节存在且与本地文档一致。
6. **TEST_CASES 同步**：在 `TEST_CASES.md` §3 追加 6 条子命令矩阵用例（T-CLI-08 ~ T-CLI-13），覆盖开/关开机自启与启动后自动加速；§6 安全侧加 1 条（T-SEC-05：开自启后必须能取消）。

## Files to be Modified / Created

| 路径 | 变更类型 | 关键变更 |
|---|---|---|
| `d:\Code\Voice\baby_voice\skill-test\.trae\skills\watt-toolkit-launcher\SKILL.md` | Edit | Command Map 加 6 行；新增"开机自启动（Run 键）"与"启动后自动加速（配置文件）"小节；改写"关闭主程序"为安全序列；更新 `description` 字段 |
| `d:\Code\Voice\baby_voice\skill-test\docs\STEAMPP_LIFECYCLE_NOTES.md` | Create | Step 1 实测笔记 + Step 2 简洁文档（每条命令的前提 / 副作用 / 回退） |
| `d:\Code\Voice\baby_voice\skill-test\README.md` | Edit | 在"Steam++ 命令行速查"表追加 6 行；新增"全生命周期"小节链接到 notes |
| `d:\Code\Voice\baby_voice\skill-test\TEST_CASES.md` | Edit | §3 加 T-CLI-08 ~ T-CLI-13；§6 加 T-SEC-05 |
| 飞书文档 `<BxxAdPW2goHM6hxSspgcqWHWnQh>` | Overwrite | "原理"章加"全生命周期命令矩阵"；"已知限制"加 Windows 注册表 / 配置文件说明 |

## Out of Scope

- 改写 Steam++ 自身的配置文件结构（依赖 Steam++ 内部字段名，以 Step 1 实测为准）
- 增加定时任务（Schedule 工具）实现"后台守望"（属于另一个 Plan）
- macOS / Linux 自启实现
- 把这三个 Skill 部署到 git 仓库 / 注册到内部分发平台
- 端到端验收场景的更新（除非 Step 1 实测发现"开自启失败"这类阻塞问题）

## Risks

| 风险 | 缓解 |
|---|---|
| 配置文件字段名在 Steam++ 不同版本间不一致 | Step 1 实测时若找不到字段，按 A2 降级方案（绑定启动+加速为原子动作）处理 |
| 写注册表 `Run` 键失败（权限/杀软拦截） | 失败时回退到 `shell:startup` 快捷方式 |
| `Stop-Process -Force` 之后代理没收尾导致后续 git push 仍失败 | 安全序列前置 `-clt proxy -off`，等 2s 再 Stop-Process |
| description 字段加太多语义导致误触发其他 Skill | 仍保留"only Steam++.exe"的负向描述，避免被误解为通用工具 |
