# Hermes Personal Work Agent Starter

Remote access quick path: [Vercel Remote Dashboard MVP](F:/AGENT/docs/vercel-remote-dashboard.md)

这是一个围绕 `Hermes Agent` 使用场景搭出来的个人工作代理 starter project。
它不试图替代 Hermes 本体，而是先把你这条路线里最关键的控制层落下来：

- `OpenRouter` 模型路由适配
- 三个首发工作流：`Inbox Capture`、`Drafting Assistant`、`Knowledge Distill`
- 可持久化的 `jobs / memory_candidates / skills / messages / companion events`
- 微信/企微风格 webhook 消息入口
- 人工审批状态机
- 树莓派 companion 事件入口

项目默认只依赖 Python 3.10 标准库，方便你先跑起来，再决定要不要继续替换成 FastAPI、SQLite、Redis、真正的 Hermes gateway 集成。

## 为什么这样实现

你给的目标是：

`云端 Hermes 主脑 + OpenRouter 模型层 + 微信管理入口 + 树莓派随身终端`

这个 starter 先补上“控制层”和“业务骨架”，让你可以：

1. 用统一协议收输入
2. 把任务写成 job
3. 通过 OpenRouter 产出结构化结果
4. 自动形成记忆候选
5. 在微信里查状态、审批、拒绝
6. 后面再把真实 Hermes、WeCom/iLink、Raspberry Pi 设备逐步接进来

## 目录结构

```text
F:/AGENT
├─ hermes_personal_agent/
│  ├─ cli.py
│  ├─ companion.py
│  ├─ companion_client.py
│  ├─ config.py
│  ├─ memory.py
│  ├─ messaging.py
│  ├─ openrouter.py
│  ├─ orchestrator.py
│  ├─ schemas.py
│  ├─ server.py
│  ├─ skills.py
│  └─ storage.py
├─ config/
│  └─ agent.example.json
├─ docs/
│  ├─ architecture.md
│  └─ deployment.md
├─ tests/
│  └─ test_agent.py
├─ docker-compose.example.yml
└─ Dockerfile
```

## 快速开始

### 1. 准备 OpenRouter Key

PowerShell:

```powershell
$env:OPENROUTER_API_KEY="sk-or-..."
```

如果你先不配 key，系统会自动退回到本地 deterministic mock 输出，方便先验证工作流和接口。

### 2. 启动服务

```powershell
py -m hermes_personal_agent.cli serve --config F:\AGENT\config\agent.example.json --host 127.0.0.1 --port 8787
```

### 3. 创建一个 job

```powershell
@'
{
  "workflow": "inbox_capture",
  "content": "周三前整理 Hermes + OpenRouter + 微信的 MVP 路线，并列出风险。",
  "source_channel": "terminal",
  "metadata": {
    "project": "personal-agent"
  }
}
'@ | Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8787/api/jobs -ContentType 'application/json'
```

### 4. 用微信风格入口发送消息

```powershell
@'
{
  "message_id": "wx-001",
  "text": "draft: 帮我起草一条发给合伙人的进度同步，语气直接一点",
  "sender": "me"
}
'@ | Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8787/api/messages/wechat -ContentType 'application/json'
```

### 5. 查询 job 状态

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8787/api/jobs/<job_id>
```

### 6. 模拟树莓派 companion 上报

```powershell
py -m hermes_personal_agent.cli companion-send `
  --api-base-url http://127.0.0.1:8787 `
  --queue-path F:\AGENT\data\companion-queue.json `
  --device-id pi-zero-01 `
  --event-type voice_note `
  --text "记一下，明天测试微信审批流"
```

## 当前已经实现的能力

### 工作流

- `Inbox Capture`
  - 输出统一字段：`summary`、`actions`、`open_questions`、`confidence`、`needs_approval`
  - 附带结构化内容：`priority`、`project`、`tags`、`next_step`
- `Drafting Assistant`
  - 生成可审稿草案
  - 附带结构化内容：`draft_type`、`tone`、`draft`
- `Knowledge Distill`
  - 生成摘要、知识卡、可检索关键词
  - 附带结构化内容：`knowledge_cards`、`search_terms`

### 任务状态机

`new -> planned -> running -> waiting_approval -> done / failed`

### 消息入口

- `POST /api/messages/wechat`
- `POST /api/messages/wecom`
- 支持去重、状态查询、审批、拒绝、普通任务投递

消息规则：

- `status <job_id>`：查询状态
- `approve <job_id> [comment]`：批准
- `reject <job_id> [reason]`：拒绝
- `draft: ...`：进入 `Drafting Assistant`
- `distill: ...`：进入 `Knowledge Distill`
- 其他文本：进入 `Inbox Capture`

### 树莓派 companion 入口

- `POST /api/companion/events`
- 支持 `voice_note`、`photo_note`、`quick_note`
- 自动按事件类型路由到工作流
- 附带 `CompanionClient`，支持设备侧弱网排队与补发

## 推荐下一步

1. 把这个控制层服务放到 VPS 或常开机设备。
2. 接上真实 Hermes Agent 的 dashboard / memory / tools。
3. 把微信入口替换成正式的 WeCom callback 或 Hermes 官方支持的 WeChat 接入。
4. 给树莓派做一个轻客户端，只负责采集、缓存、补发和状态显示。

详细说明见：

- [架构说明](F:/AGENT/docs/architecture.md)
- [产品规格](F:/AGENT/docs/product-spec.md)
- [部署说明](F:/AGENT/docs/deployment.md)
