---
name: dividend-dashboard-upgrade
description: 你自己写的理财 app 升级方案 — 股票分析 + 日程 + 定时买卖
version: 1.0
author: Hermes + purryc
tags: [purryc, dividend, dashboard, finance, stocks]
---

# Dividend Dashboard 升级方案

## 项目背景

你已经写了一个理财 app（F 盘 MyFinanceTool），现在升级为**综合理财 Hub**，不需要自动买卖。

**核心升级**：
1. **Polymarket 集成** — 显示你的预测市场头寸 + PnL（新增）
2. **现金流分析** — 月度收入/支出分析 + TD、Wealthsimple 聚合（新增）
3. **分红提醒系统** — 注册日、分红日、除息日自动提醒（已规划）

**技术栈**：TypeScript + Express + React + better-sqlite3（Electron 应用）

---

## 项目规划

### 已完成的详细设计
- ✅ `/home/plans/personal-finance-system.md` — 12 周完整架构 (Phase 1-3)
- ✅ `/home/plans/phase1-implementation-tasks.md` — 详细任务分解 (Task 1.1-1.5 + 单元测试)
- ✅ 数据模型设计（多账户、多数据源、交易聚合、去重）
- ✅ API 集成方案（TD、Wealthsimple、Polymarket）

### Phase 1 目标（Week 1-4）
**数据聚合层** — 统一接入 TD + Wealthsimple + Polymarket + 本地数据，建立中央数据库

验收条件：
- [ ] 5 个数据源可同时访问（无冲突）
- [ ] 交易自动标准化（源无关）
- [ ] 支持增量同步（不重复导入）
- [ ] 实时状态仪表板（同步状态 + 错误日志）
- [ ] 自动调度（每小时聚合一次）
- [ ] 单元测试覆盖 > 70%

---

## 功能 A: 股票分析引擎

### 财务健康度评分体系（基于你的选股逻辑）

```python
class StockAnalyzer:
    """
    评分标准 (0-100分):
    
    指标              权重      标准
    ──────────────────────────────────
    Dividend Growth   20%      5年CAGR>10% = 满分
    Payout Ratio      20%      30-50% = 满分，>60% = 风险
    Debt/Equity       20%      <1.0 = 满分，>2.0 = 风险
    ROE               15%      >15% = 满分
    Yield             15%      3-6% = 满分，>8% = 警惕
    """
    
    def analyze(self, ticker):
        score = (
            self.dividend_growth_score(ticker) * 0.20 +
            self.payout_ratio_score(ticker) * 0.20 +
            self.debt_equity_score(ticker) * 0.20 +
            self.roe_score(ticker) * 0.15 +
            self.yield_score(ticker) * 0.15
        )
        
        # 输出推荐
        if score >= 80:
            return "🟢 优质 — 长期复利首选"
        elif score >= 70:
            return "🟡 良好 — 适合均衡配置"
        elif score >= 60:
            return "🟠 中等 — 需要谨慎"
        else:
            return "🔴 风险 — 需要深度调研"
```

### 对标表格输出

```
┌─────────┬────────┬────────┬────────┬─────────┐
│ 标的    │ 股息率 │ 健康度 │ 费率   │ 推荐度  │
├─────────┼────────┼────────┼────────┼─────────┤
│ XDIV    │ 3.0%   │ 85     │ 0.11%  │ ★★★★★ │
│ XEI     │ 5.5%   │ 72     │ 0.20%  │ ★★★★   │
│ VDY     │ 5.2%   │ 68     │ 0.16%  │ ★★★☆   │
│ EIT.UN  │ 8.0%   │ 78     │ 0.50%  │ ★★★★   │
│ ECHI    │ 15%    │ 45     │ 0.29%  │ ★★☆    │
└─────────┴────────┴────────┴────────┴─────────┘

建议: 你的 40/25/20/15 配置完全合理，继续坚持
```

---

## 功能 B: 日程提醒系统

### 四个关键日期

```python
class DividendEvent:
    """
    1. Ex-Dividend Date (除息日)
       - 这天收盘后股价会被"调整"（下跌分红金额）
       - 必须在这天前持有才能获得分红
       - 策略：如果股价过高，可能在除息日前卖出
    
    2. Record Date (注册日)
       - 确认分红权属的截止日
       - 通常在除息日之后 1 天
    
    3. Payment Date (支付日)
       - 实际获得分红的日期
       - 通常比除息日晚 1-2 个月
    
    4. Distribution Date (分红日)
       - 公司公布分红的日期
    """
```

### 自动提醒规则

```python
# 例子 1: 除息日前 3 天提醒
reminder = {
    'ticker': 'XDIV',
    'event_type': 'ex_dividend',
    'days_before': 3,
    'message': '📅 XDIV 除息日在 3 天后，请确保已持有'
}

# 例子 2: 分红支付日当天通知
reminder = {
    'ticker': 'XEI',
    'event_type': 'payment',
    'days_before': 0,
    'message': '💰 XEI 分红预计到账 C$45，已纳入总资产'
}

# 例子 3: 定时买入机会提醒
reminder = {
    'ticker': 'XDIV',
    'trigger': 'payment_received',
    'action': 'prompt_to_buy',
    'amount': 'auto_calculate_from_dividend'  # 用分红自动买
}
```

---

## 功能 D: 支出分析 (已实现)

**状态**: ✅ 2026-05-04 实施
**文件**: `src/components/SpendingDashboard.tsx`, `src/spending-categorizer.ts`
**详见**: `references/spending-analysis-module.md`

### 数据源
- **信用卡 CSV** (`Spending/credit card/`): transaction_date,post_date,type,details,amount,currency
- **Chequing CSV** (`Spending/chequing account/`): date,transaction,description,amount,balance,currency

### 核心能力
1. **自动分类引擎** — 11 个预置分类（餐饮/购物/交通/住房/宠物/娱乐/旅行/医疗/订阅/转账/其他），基于关键词匹配（中英文商户名），支持用户自定义规则
2. **批量 CSV 导入** — 一键导入信用卡或 Chequing 流水，自动分类并去重
3. **支出分析仪表板** — 月度总览卡片、月度趋势柱状图、类别饼图、类别明细表、Top 商户排行、环比变化指示器
4. **分类管理** — REST API 支持 CRUD 分类规则，刷新后自动更新分类引擎缓存

### 数据库新增表
- `spending_categories`: id, category_name, emoji, keywords (JSON), monthly_budget, color, is_active
- `spending_transactions`: id, account_type, transaction_date, post_date, type, description, amount, currency, category, merchant, raw_data, source_file, created_at

---

## 已知问题 / Pitfalls

### 项目环境
1. **`node_modules` 跨平台不兼容**: 项目 npm install 在 Windows 运行，WSL 使用前需 `npm rebuild esbuild`，否则 tsx 报 esbuild 二进制错误
2. **`package.json` 格式损坏**: 项目有重复 `},` 和游离依赖项（如 tailwind-merge 不在 dependencies 块内），需先修复 JSON 结构
3. **缺失依赖项**: `uuid` 包可能不在 node_modules 中（虽然 package-lock.json 有引用），需要在目标平台重新 `npm install`
4. **peer dependency 冲突**: lucide-react 需要 react@18.x 但 react 不是顶层依赖。用 `npm install --legacy-peer-deps` 安装

### Codex 执行
- Codex (OpenAI) 使用 Responses API (`wss://api.openai.com/v1/responses`)，需要 API key 有该 endpoint 的权限。标准 Chat Completions key 不兼容
- Codex 需要 git repo（已初始化，初始 commit 可用）
- Codex 在 401 auth 错误后无 graceful fallback，直接退出

### 前端
- 支出分析使用独立标签页 (`viewMode: 'spending'`)，与现有分红功能完全隔离，不影响已有逻辑
- 分类器匹配顺序：用户自定义规则 > 通用关键词 > '其他' 兜底
- 首日导入测试建议先用信用卡 CSV，数据量较小（Nov 2025 - Apr 2026）

---

## 功能 C: 定时买卖日程

### 交易规则定义

```python
class TradeSchedule:
    """
    用户可以定义："分红后自动买 XDIV"
    """
    
    def add_rule(self, rule):
        """
        rule = {
            'id': 'trade_001',
            'type': 'buy' | 'sell',
            'trigger': 'payment_date' | 'ex_dividend_date' | 'fixed_date',
            'ticker': 'XDIV',
            'amount': 100,  # 买 100 股 或 卖 $100
            'conditions': {
                'only_if_yield_above': 3.0,     # 只在股息率 > 3% 时买入
                'only_if_price_below': 120,     # 只在股价 < $120 时买入
                'max_portfolio_weight': 0.45    # XDIV 占比不超过 45%
            },
            'timing_days_before': 0  # 立即执行
        }
        """
```

### 执行流程

```
每天凌晨 2 点：
1. 检查所有 trade_rule
2. 如果 trigger 条件满足
3. 检查所有 conditions
4. 如果全部通过，生成交易指令
5. 向用户申请审批（或自动执行）
```

---

## 实现路线图

### Week 1 (May 15-21)

- [ ] 信息收集
  - 你提供：代码路径 + 技术栈 + 当前 DB schema
  - 我审视现有代码，确定接入点
  
- [ ] 数据源集成
  - Yahoo Finance API（免费，延迟 15-20 分钟）
  - 或 TD Webbroker API（实时，需要账户）

- [ ] 数据库扩展
  - 添加 dividend_events 表
  - 添加 trade_schedules 表
  - 添加 stock_analysis 表

### Week 2 (May 22-28)

- [ ] 功能 A: 股票分析
  - 编写评分算法
  - 生成对标表格
  - 前端展示

- [ ] 功能 B: 日程提醒
  - 抓取分红日期（Yahoo）
  - 实现提醒逻辑
  - 与你现有 notification 系统集成

### Week 3 (May 29-Jun 4)

- [ ] 功能 C: 定时买卖
  - 规则定义 UI
  - 执行器开发
  - TD API 集成（如果需要）

---

## 与 Hermes 的集成

### Hermes 学习你的交易习惯

```python
# Hermes 记录：
每次你手动买卖时 → 记录时机、价格、原因

# Hermes 自动分析：
"你总是在 XDIV 跌到 $115 以下时买入"
"你总是在 EIT.UN 分红后买进"
"你倾向于周一卖高息股"

# Hermes 建议：
"下周 XDIV 可能触及 $114，建议关注"
"ECHI 分红日是本月 28 号，预计可入账 C$50，建议用来补仓"
```

---

## 数据库设计

### 新增表

```sql
-- 分红事件表
CREATE TABLE dividend_events (
    id INTEGER PRIMARY KEY,
    ticker TEXT,
    ex_dividend_date DATE,
    record_date DATE,
    payment_date DATE,
    dividend_per_share REAL,
    last_synced DATETIME
);

-- 交易日程表
CREATE TABLE trade_schedules (
    id INTEGER PRIMARY KEY,
    ticker TEXT,
    trade_type TEXT,  -- buy/sell
    trigger TEXT,     -- ex_dividend_date / payment_date
    amount REAL,
    conditions_json TEXT,  -- JSON 条件
    is_active BOOLEAN,
    created_at DATETIME
);

-- 股票分析表
CREATE TABLE stock_analysis (
    id INTEGER PRIMARY KEY,
    ticker TEXT,
    health_score REAL,
    dividend_growth_score REAL,
    payout_ratio_score REAL,
    debt_equity_score REAL,
    roe_score REAL,
    yield_score REAL,
    last_updated DATETIME
);
```

---

## 成功指标

- [ ] 能对标你的 5 个标的，给出清晰的健康度评分
- [ ] 至少提前 3 天提醒分红日期 (准确率 95%+)
- [ ] 能设定 5 条交易规则，并自动执行
- [ ] Hermes 学到你的 3+ 个交易模式

---

## 注意事项

**暂不做**:
- 自动连接 TD API（太复杂，需要安全审查）
- 期权/衍生品交易
- 跨币种复杂对冲

**优先**:
- 数据准确性（宁可晚一点，不要错）
- 用户确认审批（大额交易前必须提醒）
- 简洁的 UI（易于理解）

---

## 这个升级的目标

让你的理财 app 从"被动记录"升级到"主动顾问"。

Hermes 会从你的交易历史中学习，然后在合适的时机自动提醒和建议，最终省去你每周 1 小时的"看数据"时间。
