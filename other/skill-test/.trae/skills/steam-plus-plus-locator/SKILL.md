---
name: "steam-plus-plus-locator"
description: "Searches the local Windows machine for Steam++.exe across a manual-path override, common install paths, Microsoft Store packages, registry, PATH, and a two-phase broad search (first locate Steam++ directories, then locate Steam++.exe inside). The target is exclusively Steam++.exe (legacy executable name of Steam++ / Watt Toolkit). If no candidate is found across all sources, the skill prompts the user to set a manual path, persists it to %LOCALAPPDATA%\\steam-plus-plus-locator\\manual-path.json, and uses it on subsequent invocations. Invoke when a task needs the Steam++.exe path and it is not already known, or when the user asks to find / locate / 搜索 Steam++.exe / steam++ 安装位置 / 手动指定 Steam++ 路径."
---

# Steam++ Locator

在 Windows 上**搜索本机 Steam++.exe**（Steam++ / 原 Watt Toolkit 的可执行文件），返回候选路径列表，供 `watt-toolkit-launcher` 或 `github-access-watt-fallback` 后续启动使用。

> **要寻找的是 `Steam++.exe`**（项目历史可执行文件名，仓库 `BD.WTTS.Client` 早期版本 EXE 即此名：`/// 获取当前主程序文件名，例如 steam++.exe`）。
>
> **不寻找 `WattToolkit.exe`**。新版本改名后的 `WattToolkit.exe` 不在搜索范围内 — 如果用户装的只有新版本，会找不到并提示去安装旧版 Steam++ / 在 steampp.net 找到带 `Steam++.exe` 的发行包。
>
> **大小写说明**：Windows 文件系统默认不区分大小写，但项目历史 EXE 在源码注释里写作 `steam++.exe`（全小写）。本 Skill 同时接受 `Steam++.exe`（首字母大写）和 `steam++.exe`（全小写），命中任一即可，统一在结果里归一化为 `Steam++.exe`。

> 这是"找 EXE"层；启动动作由 `watt-toolkit-launcher` 负责。

## When to Invoke

- 用户问"Steam++.exe 在哪 / Steam++ 装哪了 / 找一下 Steam++ 路径"
- 上层 Skill（`watt-toolkit-launcher` / `github-access-watt-fallback`）拿不到 EXE 路径
- 切换了 Steam++ 安装位置（重新安装、装到非默认盘）
- 系统中可能存在多个安装源（Microsoft Store 包 + 官网安装包 + 旧版残留），需要人工选择
- 5 源扫描都未命中，需要提示用户手动指定并记忆

Do **not** invoke for macOS / Linux — v1 仅覆盖 Windows。
Do **not** invoke if the user is asking about `WattToolkit.exe` specifically — that is a different executable and not handled here.

## 搜索策略（按顺序；仅搜索 `Steam++.exe`）

> 优先级数字越小越优先，命中即返回最高优先级结果；同优先级多个候选全部返回。

| 序 | 命中来源 | `priority` | 说明 |
|---|---|---|---|
| 0 | **manual-path** | `0` | 用户手动指定的路径（持久化在 `%LOCALAPPDATA%\steam-plus-plus-locator\manual-path.json`），命中即短路返回 |
| 1 | env-path | `1` | 8 个常见环境变量路径（详见下方） |
| 2 | appx | `2` | `Get-AppxPackage *Steam*` 的 `InstallLocation` 拼接 EXE |
| 3 | registry | `3` | `HKCU\…\Uninstall\*` + `HKLM\…\Uninstall\*` 找 DisplayName 含 "Steam++" / "Watt Toolkit" |
| 4 | where | `4` | `where.exe Steam++.exe`（PATH 中） |
| 5 | **broad-search**（**两阶段**） | `5` | 先按"目录"广搜，再在候选目录里搜 EXE（详见下方 §"两阶段广搜"） |

**短路规则**：**priority 0（manual-path）一旦命中就立即返回**，不再继续其它源的扫描。
**多源合并**：同一 `Steam++.exe` 路径被多个 source 命中时合并成单条；`source` 用 `;` 拼接，`priority` 取最小。

### env-path（priority 1）

```
%LOCALAPPDATA%\Steam++\Steam++.exe
%LOCALAPPDATA%\Steam++\steam++.exe
%LOCALAPPDATA%\Programs\Steam++\Steam++.exe
%LOCALAPPDATA%\Programs\Steam++\steam++.exe
%PROGRAMFILES%\Steam++\Steam++.exe
%PROGRAMFILES%\Steam++\steam++.exe
%PROGRAMFILES(x86)%\Steam++\Steam++.exe
%APPDATA%\Steam++\Steam++.exe
```

### 两阶段广搜（priority 5）

> **设计动机**：按 EXE 名在多根盘上做深递归会非常慢且容易漏。Steam++ 实际目录树可能嵌套很深（便携版通常是 `Steam++-Portable-v3.0.0-x64\Steam++\Steam++.exe`），按 EXE 名全局深度 5 搜会遍历海量文件；按目录先聚类再局部深搜是工业界普遍做法。

#### 第一阶段 — 广搜"Steam++ 目录"（深度 5，跨根盘）

```powershell
# 步骤 1：取所有可用的文件系统根（而非写死 C:\ D:\ E:\ F:\）
$roots = (Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -ne $null }).Root

# 步骤 2：每个根做深度 5 的"目录"枚举，匹配 *Steam++* 命名（兼容 Steam++/steam++/Steam++-Portable/Steam++-x64/中文 Steam++ 等）
$dirHits = foreach ($root in $roots) {
    Get-ChildItem -Path $root -Directory -Recurse -Depth 5 -ErrorAction SilentlyContinue -Force |
        Where-Object { $_.Name -match '(?i)steam\+\+' }
}
```

> 兼容的目录命名变体（通过 `(?i)steam\+\+` 正则）：`Steam++`、`steam++`、`Steam++-Portable`、`Steam++-v3.0.0-x64`、`Steam++ (x64)`、未来可能的中文 `Steam++` 等。

#### 第二阶段 — 在每个候选目录里全盘搜 `Steam++.exe`

```powershell
# 步骤 3：在每个候选目录里"全盘"（不限深度，但单目录深度有限）找 Steam++.exe
$exeHits = foreach ($dir in $dirHits) {
    Get-ChildItem -Path $dir.FullName -Filter 'Steam++.exe' -Recurse -ErrorAction SilentlyContinue -File
}
```

> 命中 EXE 后立刻把外层"目录命中"丢给上层按目录权重排序；不需要再继续在同一目录内深挖。

#### 目录权重（用于两阶段广搜的二级排序）

| 路径特征 | 权重 |
|---|---|
| `…\Steam++\Steam++.exe`（EXE 与父目录同名） | 100（标准安装） |
| `…\Steam++\bin\Steam++.exe` / `…\Steam++\app\Steam++.exe` | 90 |
| `…\Steam++-*Portable*\…\Steam++\Steam++.exe` | 80（便携版） |
| `…\Steam++*\Steam++.exe`（父目录含 Steam++ 前缀） | 60 |
| 其它 | 40 |

排序键 = `priority * 10000 + (100 - 目录权重)`，越小越优先。

#### 跨平台 / 根盘边界

- `Get-PSDrive -PSProvider FileSystem` 会拿到**所有挂载的文件系统**（网络盘、U 盘、外接硬盘）；这些会显著拖慢扫描，本 Skill 默认**只取固定盘**（DriveType = 3）
- 用户可以通过 `locator config --include-removable` 显式开启（未来扩展点）

## 全部未命中 — 提示用户手动设置 + 记忆

> **这是 v1.1 引入的新行为**。当上面 5 个 source 全部未命中时，**不要**直接报错，而是提示用户手动指定路径并**持久化记忆**。

### 提示语（标准话术）

> "我没能在本机找到 Steam++.exe。Steam++ 装在哪了？或者你可以把 EXE 的完整路径直接告诉我。
> 路径示例：`C:\Tools\Steam++\Steam++.exe`
> 如果你不再用 Steam++，可以告诉我，我就不再问了。"

### 手动路径的存储

- 文件位置：`%LOCALAPPDATA%\steam-plus-plus-locator\manual-path.json`
- 文件结构（最小化）：

```json
{
  "executable": "Steam++.exe",
  "path": "C:\\Tools\\Steam++\\Steam++.exe",
  "setAt": "2026-08-21T10:30:00+08:00",
  "setBy": "user-prompt",
  "lastVerified": null
}
```

- 每次读取 manual-path 时都执行 `Test-Path -LiteralPath`，命中即直接返回 `priority=0, source=manual-path, validity=ok|missing` 的单条结果
- `lastVerified` 字段记录最后一次 `Test-Path=true` 的时间，便于排查"为什么 manual-path 不生效"

### 手动路径的生命周期

| 事件 | 行为 |
|---|---|
| Skill 启动 → 读 manual-path.json → `Test-Path` 通过 | 立即返回（priority 0），跳过所有其它源 |
| 读 manual-path → `Test-Path` 失败（文件被移走） | 标记 `validity=missing`；**仍**继续执行 5 源扫描；若 5 源命中则用命中结果；否则再次提示用户 |
| 用户主动说"忘记手动路径" / "清除手动路径" | 删除 `%LOCALAPPDATA%\steam-plus-plus-locator\manual-path.json`；下次回到 5 源扫描 |
| 用户主动说"重新搜索" / `--refresh` | 删除 `cache.json`，**保留** manual-path.json（手动路径优先于自动搜索） |
| 用户主动更新路径 | 直接覆盖 `manual-path.json` 的 `path` 字段，`setAt` 更新 |

## 验证有效性

对每个候选执行：

```powershell
Test-Path -LiteralPath $candidate
```

如果候选存在但 `.exe` 文件大小为 0 KB、或者数字签名提示"未知发布者"，标记为 `validity: suspect`，不直接采用但保留供用户查看。

## 输出格式

返回结构化列表（PowerShell 对象数组），每条记录：

| 字段 | 说明 |
|---|---|
| `path` | EXE 完整路径（按文件系统原样保留大小写） |
| `executable` | 统一为字符串 `"Steam++.exe"` |
| `source` | 命中来源（`manual-path` / `env-path` / `appx` / `registry` / `where` / `broad-search`） |
| `priority` | 整数，越小越优先；`manual-path` 始终为 0 |
| `validity` | `ok` / `missing` / `suspect` |
| `sizeBytes` | 文件大小（缺则为 `null`） |
| `version` | `FileVersionInfo.FileVersion`（缺则为 `null`） |
| `setAt` | 仅 `source=manual-path` 时存在，记录手动路径设置时间 |

调用方默认取 `priority` 最小且 `validity=ok` 的那条；如果没有 `ok`，则把候选全交给用户挑选。

## 缓存

- 在 `%LOCALAPPDATA%\steam-plus-plus-locator\cache.json` 缓存**5 源扫描**的最近一次结果（含时间戳），TTL 24h
- 缓存命中时**不**直接返回 — 而是先用 `Test-Path` 校验候选是否仍存在；只有全部候选都还在才走缓存，否则重搜
- 卸载 / 重新安装 Steam++ 时提示用户手动 `Remove-Item` 该缓存文件，或让上层 Skill 调用一个 `--refresh` 开关强制重搜
- `manual-path.json` **不**进缓存（手动设置永远新鲜）

## 异常 / 边界

- 全部 5 步都未命中 → **走"全部未命中"流程**（提示用户手动设置，**不是**抛异常）
- 多源命中同一条路径：在结果中合并，`source` 字段用 `;` 拼接，`priority` 取最小
- 用户没有管理员权限：跳过 `HKLM` 注册表扫描，但继续 HKCU / Appx / PATH
- PowerShell 5.1 与 PowerShell 7 行为差异：本 Skill 默认兼容 5.1（`Get-ChildItem -Depth` 5.1 不支持 → 用 5.1 兼容写法：`Get-ChildItem … -Recurse \| ForEach-Object { … }` 限制深度）

## 示例

> User: Steam++.exe 装哪了
> Agent: 触发本 Skill → 命中 1 条 manual-path →
> 1. `C:\Tools\Steam++\Steam++.exe`（manual-path, setAt 2026-08-21, ok, priority=0）
> Agent: 采用该条；如需切换可告知。

> User: 找一下 Steam++ 路径
> Agent: 触发本 Skill → manual-path 缺 → 5 源全 miss → 提示"我没能在本机找到 Steam++.exe。Steam++ 装在哪了？或者你可以把 EXE 的完整路径直接告诉我…"
> User: D:\Apps\Steam++-Portable-x64\Steam++\Steam++.exe
> Agent: 写入 manual-path.json（priority 0）→ 立即返回该路径

> User: 重新搜索 Steam++.exe（已设置过 manual-path）
> Agent: 删除 cache.json，**保留** manual-path.json → manual-path 仍 priority 0 命中

## 不在本 Skill 范围

- 启动 Steam++ → `watt-toolkit-launcher`
- 检测 GitHub 是否可达并拉起反代 → `github-access-watt-fallback`
- 寻找 `WattToolkit.exe`（新版本）→ 不支持；本 Skill 仅处理 `Steam++.exe`
- 卸载 / 升级 Steam++ → 引导用户走其自带安装器
