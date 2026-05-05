---
name: codex-delegation-workflow
description: 通过 Codex CLI 执行编程任务的 Hermes ↔ Codex 协作工作流
version: 1.0
author: Hermes + purryc
tags: [codex, delegation, coding, workflow]
---

# Codex 委托工作流

## 背景
用户购买了 OpenAI $100 Plan (Codex 在 WSL 环境可用)。所有执行类任务走 Codex。

## 共享记忆桥 (Shared Memory Bridge)

Codex 在 Windows 端搭建了共享记忆系统：
- **共享记忆文件**: `F:\AGENT\memory\SHARED_AGENT_MEMORY.md` (WSL: `/mnt/f/AGENT/memory/SHARED_AGENT_MEMORY.md`)
- **Windows 定时任务**: `HermesCodexMemorySync` 每 30 分钟将 Hermes 的 raw memory 导出为 `hermes-raw-memory-export.md`
- **Codex 侧**: 通过 `AGENTS.md` 指令在每次工作前读取 SHARED_AGENT_MEMORY.md
- **双向同步**: Hermes 和 Codex 都会在各自工作完成后回写关键信息

## 我的同步职责

### 向 Codex 方向的同步 (`Hermes → Codex`)
1. **委托 Codex 前**: 读取 SHARED_AGENT_MEMORY.md，注入到 prompt 中
2. **自动导出**: Windows 定时任务每 30min 跑 `sync-agent-memory.ps1 -ExportHermesRaw`，把我的 memory 导出到 raw export 文件
3. **主动写桥**: 当我在对话中知道新信息（财务数据、项目状态变更、技能更新），立即更新 SHARED_AGENT_MEMORY.md

### 从 Codex 方向的同步 (`Codex → Hermes`)
1. **Codex 执行后**: 检查 SHARED_AGENT_MEMORY.md 是否有新变更
2. **反写入 memory**: 如果 Codex 更新了共享记忆（如项目状态、workflow 更新），用 memory tool 存入 Hermes 的持久记忆
3. **定期刷新**: 每次开始对话时，检查 SHARED_AGENT_MEMORY.md 是否有新内容

## 分工

| 角色 | 职责 |
|------|------|
| **Hermes (你)** | 需求分析、planning、加载 skill/memory、构造 prompt、回写关键发现 |
| **Codex (执行层)** | 功能开发、重构、测试、Bug修复、批量文件操作 |

## 工作流

### 1. 接收需求
- 理解用户的完整需求
- 加载相关 skill (`skill_view`)
- 检查 memory 中相关上下文

### 2. 构造 Prompt
Codex 没有 Hermes 的 memory/skills，所以 prompt 必须**自包含**：
- 项目结构和关键文件路径
- 相关 skill 的核心步骤
- 用户的偏好/约定（代码风格、命名规范等）
- 明确的可验收条件

### 3. 执行
```bash
codex exec --full-auto '完整prompt内容'
```
用 `pty=true` + 足够的 `timeout`。

### 4. 验证
- 检查 exit code
- 快速测试关键接口（curl API、页面加载等）
- 编译检查

### 5. 回写
执行完 Codex 后，关键发现写回 memory 和 skill：
- 遇到什么问题、怎么解决的
- 有没有需要记住的文件路径/配置变更
- 如果 skill 过时了，patch 它

## Prompt 模板

```markdown
## 任务：{任务标题}

### 项目背景
{项目描述、当前状态}

### 关键文件
- `{路径}` — {作用}
- `{路径}` — {作用}

### 用户偏好
{代码风格、命名规范、注意事项}

### 要实现的内容
{详细的步骤说明，含代码示例、接口定义、UI说明}

### 验收条件
- [ ] {条件1}
- [ ] {条件2}

完成后运行: {验证命令}
```

## 注意事项
- Codex 在 git repo 内工作，需要先确保 repo 已初始化
- `--full-auto` 自动批准沙箱内文件变更
- 用 `pty=true` 必须 (Codex 是交互式终端应用)
- 分批执行，一次不要超过一个完整模块
- Codex 的输出不是 100% 可信，关键结果要验证
