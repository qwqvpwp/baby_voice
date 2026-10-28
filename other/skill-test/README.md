# GitHub Access Steam++ Skill Pack

> 让 TRAE CN 在 **GitHub 访问不通** 时自动拉起本地 **Steam++**（EXE 文件名是 `Steam++.exe`）的反代能力，并在用户层面提供"何时用 / 怎么用 / 怎么验证"的完整说明。

## 仓库结构

```
skill-test/
├── README.md                                 # 本文件
├── TEST_CASES.md                             # 手动 / 自动化测试用例
└── .trae/
    └── skills/
        ├── steam-plus-plus-locator/
        │   └── SKILL.md                      # 找 EXE：在本机搜索 Steam++.exe 安装位置
        ├── github-access-watt-fallback/
        │   └── SKILL.md                      # 面向场景的 Skill（GitHub 不通时使用）
        └── watt-toolkit-launcher/
            └── SKILL.md                      # Steam++ 通用 CLI 启动器（底层能力）
```

## 这是什么 / 不是什么

| 是什么 | 不是什么 |
|---|---|
| 三个 TRAE CN 自定义 Skill 的最小工程样例 | 完整的代理客户端（需要用户自己装 Steam++） |
| 当 `WebFetch` / `git clone` / `gh` 失败时自动接管 | 替换系统的 hosts / 防火墙规则 |
| 一组可被 TRAE 模型路由自动调用的指令 | 后台守护进程（Skill 只在对话被触发时运行） |
| **只**寻找 `Steam++.exe`（历史 EXE 名） | 寻找 `WattToolkit.exe`（新版改名后的 EXE，**不在支持范围**） |

## 触发条件速查

| 你说 / 遇到 | 会调用哪个 Skill |
|---|---|
| "GitHub 上不去 / clone 失败 / 帮我连一下 GitHub" | `github-access-watt-fallback` |
| "命令行启动 Steam++ / 静默启动 Steam++.exe / 加速一下" | `watt-toolkit-launcher` |
| "Steam++.exe 装哪了 / 找一下 Steam++ 路径" | `steam-plus-plus-locator` |
| "我手动指定 Steam++ 路径 / 用我之前设的路径" | `steam-plus-plus-locator`（读 `manual-path.json`） |
| "重新搜索 / 忘记手动路径" | `steam-plus-plus-locator`（删 `cache.json` / `manual-path.json`） |
| `WebFetch https://github.com/...` 超时 | `github-access-watt-fallback`（自动） |
| `git push` / `git pull` 网络错 | `github-access-watt-fallback`（自动） |
| "切换 Steam 账号 xxx" | `watt-toolkit-launcher` (`-clt steam -account xxx`) |

> 三个 Skill 是分层关系：`steam-plus-plus-locator` 负责"找 EXE"，`watt-toolkit-launcher` 负责"启动 / 控制"，`github-access-watt-fallback` 在 GitHub 不可达时调度后两者完成自愈。
>
> **三个 Skill 都只找 `Steam++.exe`**。如果本机只有 `WattToolkit.exe`（新版），会失败并提示去 <https://steampp.net/> 下载带 `Steam++.exe` 的发行包。

## v1.1 增强：手动路径 + 两阶段广搜

适用于本机 Steam++ 装在非默认位置、或者 5 源扫描全部 miss 的情况。

### 手动路径（manual-path）

- **存储位置**：`%LOCALAPPDATA%\steam-plus-plus-locator\manual-path.json`
- **优先级**：0（**最高**，比 env-path 还优先；命中后立即短路返回，跳过所有其它源）
- **生命周期**：
  - 5 源全部 miss → Skill 提示"我没能在本机找到 Steam++.exe。Steam++ 装在哪了？…" → 用户回复路径 → 写入
  - `Test-Path` 失败（文件被移走）→ 标记 `validity=missing` 并继续 5 源扫描；**不**自动覆盖
  - "忘记手动路径" → 删除 `manual-path.json`
  - "重新搜索" → 仅删除 `cache.json`；**保留** manual-path
- **拒绝**写入以下路径：相对路径（不以盘符开头）、`WattToolkit.exe`、不存在的路径（可选）
- 完整规范见 [SKILL.md "全部未命中" 章节](computer://d:\Code\Voice\baby_voice\skill-test\.trae\skills\steam-plus-plus-locator\SKILL.md)

### 两阶段广搜（broad-search 重构）

不再"按 EXE 名全局深度 5 扫"，改为：

1. **第一阶段**：在所有固定盘（`Get-PSDrive -PSProvider FileSystem`）根目录下，深度 5 枚举 `*Steam++*` 目录（兼容 `Steam++` / `steam++` / `Steam++-Portable` / `Steam++中文` 等命名变体）
2. **第二阶段**：在每个候选目录里全盘搜 `Steam++.exe`（不限深度，但单目录深度有限）

> **设计动机**：按 EXE 名在多根盘上深递归会非常慢且容易漏。Steam++ 实际目录树可能嵌套很深（便携版通常是 `Steam++-Portable-v3.0.0-x64\Steam++\Steam++.exe`）。按目录先聚类再局部深搜是工业界普遍做法。

**目录权重（二级排序）**：
- `…\Steam++\Steam++.exe`（EXE 与父目录同名）= 100（标准安装）
- `…\Steam++\bin\Steam++.exe` / `…\Steam++\app\Steam++.exe` = 90
- `…\Steam++-*Portable*\…\Steam++\Steam++.exe` = 80（便携版）
- `…\Steam++*\Steam++.exe`（父目录含 Steam++ 前缀）= 60
- 其它 = 40

**默认仅扫固定盘**（DriveType=3）。U 盘 / 网络盘需用户用 `locator config --include-removable` 显式开启。

## Steam++ 命令行速查

源码入口：`src/BD.WTTS.Client/Startup/Startup.Commands.cs`（`develop` 分支），使用 `System.CommandLine`，所有子命令以 `-clt` 前缀调用。

> **要寻找的是 `Steam++.exe`**（项目历史 EXE 名）。本 Skill **不**寻找 `WattToolkit.exe`。

| 你的意图 | 调用方式 |
|---|---|
| 静默启动 + 开代理 | `Steam++.exe -clt proxy -on` |
| 仅最小化到托盘 | `Steam++.exe -clt c -silence` |
| 关代理 | `Steam++.exe -clt proxy -off` |
| 切换代理（toggle） | `Steam++.exe -clt proxy` |
| 切换 Steam 账号（需管理员） | `Steam++.exe -clt steam -account <name>` |
| 启动某 Steam 游戏的连接服务 | `Steam++.exe -clt app -id <appId> -silence` |
| 打开云存档 / 成就管理 | `Steam++.exe -clt app -id <appId> -cloudmanager` / `-achievement` |
| 显示根证书 | `Steam++.exe -clt show -cert` |
| **开机自启动（开）** | 改 `GeneralSettings.AutoRunOnStartup` → `true` |
| **开机自启动（关）** | 改 `GeneralSettings.AutoRunOnStartup` → `false` |
| **启动后自动加速（开）** | 改 `ProxySettings.ProgramStartupRunProxy` → `true` |
| **启动后自动加速（关）** | 改 `ProxySettings.ProgramStartupRunProxy` → `false` |
| **安全关闭软件** | 先 `-clt proxy -off` → 2s → `Get-Process Steam++ \| Stop-Process -Force` |

> 上游没有 `--github` / `--accelerate <service>` 这种按服务过滤的开关。GitHub 加速需要在 GUI 里**一次性勾选**，之后 `-clt proxy -on` 会顺带把 GitHub 反代带起来。
> 
> **完整生命周期命令速查 + 实测笔记** 见 [docs/STEAMPP_LIFECYCLE_NOTES.md](computer://d:\Code\Voice\baby_voice\skill-test\docs\STEAMPP_LIFECYCLE_NOTES.md)。注意："开机自启动" 与 "启动后自动加速" 是改 Steam++ 自身的 JSON 配置（**不**写注册表），由 `watt-toolkit-launcher` Skill 直接读写。

## 导入到 TRAE CN

TRAE CN 的自定义技能通过工作区根目录的 `.trae/skills/<name>/SKILL.md` 自动识别，本仓库已经按规范组织好。

**导入步骤**

1. 打开 TRAE CN。
2. 设置 → **Skills / 自定义技能** → **从本地文件夹导入**。
3. 选择本仓库根目录（即包含 `.trae/skills/` 的那一层）。
4. TRAE 会扫描并注册三个 Skill：`steam-plus-plus-locator`、`github-access-watt-fallback`、`watt-toolkit-launcher`。
5. 在对话中触发任意一个 Skill 路径（见上方"触发条件速查"），TRAE 会按 `description` 字段路由到对应 Skill。

**前置依赖**

- 本机已安装 Steam++（Microsoft Store / <https://steampp.net/> / GitHub Releases — 注意要选择带 `Steam++.exe` 的发行包；新版仅 `WattToolkit.exe` 不被本 Skill 支持）
- 首次使用 `github-access-watt-fallback` 时，需要打开一次 Steam++ GUI 勾选 "GitHub" 加速项（之后由 CLI 接管，不再提示）

## 文件清单

| 路径 | 用途 |
|---|---|
| `.trae/skills/steam-plus-plus-locator/SKILL.md` | 搜索本机 `Steam++.exe` 安装位置（**只找 `Steam++.exe`**） |
| `.trae/skills/github-access-watt-fallback/SKILL.md` | GitHub 不通时自动唤起 Steam++ 的 Skill 定义 |
| `.trae/skills/watt-toolkit-launcher/SKILL.md` | Steam++ 通用 CLI 启动器 |
| `README.md` | 本说明文档 |
| `TEST_CASES.md` | 测试用例（覆盖正常 / 异常 / 边界） |

## 已知限制

- v1 仅覆盖 Windows（PowerShell），macOS / Linux 暂未支持
- 三个 Skill **只寻找 `Steam++.exe`**。如果用户装的是新版（仅 `WattToolkit.exe`），所有 Skill 都会失败并提示去 <https://steampp.net/> 下载带 `Steam++.exe` 的发行包
- `Steam++.exe -clt proxy -on` 启动后 Steam++ 进程常驻（不弹窗但服务持续）— 这是设计如此
- Skill 不能强制 Steam++ 只针对 GitHub — 由 GUI 一次性配置决定
- `Test-NetConnection github.com -Port 443` 在 30s 内未恢复时返回失败，由用户决定是否人工介入

## 参考

- 上游源码：<https://github.com/BeyondDimension/SteamTools>
- Steam++ 官网：<https://steampp.net/>
- TRAE CN 自定义技能规范：TRAE 内置 `skill-creator` Skill

## 验收场景：GitHub 不通时自动救活并完成代码上传

> **场景**：Steam++ / Watt Toolkit 没有启动，GitHub 不可达
> **用户输入**："把这个代码上传到 GitHub 保存了"
> **验收标准**：TRAE 自动调用 `github-access-watt-fallback` → 拉起 Steam++ → 验证 GitHub 可达 → 完成 `git push`

### 手动复现步骤

1. 准备工作
   - 装好带 `Steam++.exe` 的 Steam++ 发行包；任务管理器确认**无 `Steam++` 进程**
   - 用 Steam++ GUI 一次性勾选过 "GitHub" 加速项（`%LOCALAPPDATA%\github-access-watt-fallback\primed` 存在）
   - 准备一个本地 git 仓库，远程指向 GitHub，且有未推送的 commit
   - 当前环境 `Test-NetConnection github.com -Port 443` 返回 `False`（必要时把 `github.com` 加入 hosts 黑洞）
2. 在 TRAE CN 中打开工作区，导入 `skill-test` 三个 Skill
3. 在对话中输入 **"把这个代码上传到 GitHub 保存了"**
4. **不要**手动打开 Steam++ GUI
5. 观察对话窗口与任务管理器

### 预期链路

```
T+0s   模型路由到 github-access-watt-fallback
T+5s   Test-NetConnection github.com:443 → False
T+10s  解析 Steam++.exe 路径（可能顺带调用 steam-plus-plus-locator）
T+15s  Start-Process Steam++.exe -clt proxy -on
T+15~45s  每 2s 轮询 TCP 探测 → True
T+50s  Skill 返回成功；主对话重试 git push
T+90s  git push 成功，对话窗口输出 "代码已上传到 GitHub"
```

### 验收通过 / 不通过的判断

**通过**：90s 内完成 push，全程 TRAE 自驱，Steam++ 由 Skill 拉起

**不通过**的常见原因：模型没把错误路由到 Skill、本机只有 `WattToolkit.exe`（新版不被支持）、用户没在 GUI 一次性勾选过 GitHub

详细子用例与排错步骤见 [TEST_CASES.md §8](computer://d:\Code\Voice\baby_voice\skill-test\TEST_CASES.md) "端到端验收场景"。
