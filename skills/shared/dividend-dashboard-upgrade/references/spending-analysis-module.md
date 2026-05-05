# Spending Analysis Module — Implementation Reference

> **Implemented**: 2026-05-04
> **Project**: `/mnt/f/MyFinanceTool/dividend-dashboard/`
> **Data dir**: `F:/MyFinanceTool/FinanceData/Spending/`

---

## Data Source Formats

### Credit Card CSV (`Spending/credit card/credit-card-statement-transactions-YYYY-MM-DD.csv`)

| Column | Example | Notes |
|--------|---------|-------|
| transaction_date | 2025-10-13 | ISO date |
| post_date | 2025-10-13 | ISO date |
| type | Purchase / Payment | **Payment 跳过**（还款，非真实支出） |
| details | AMAZON.CA\*NF1GB3QT2 | 商户名 + 交易ID（星号后为随机ID，清洗时去掉） |
| amount | 22.54 | 正数为 Purchase，负数为 Payment |
| currency | CAD | |

### Chequing CSV (`Spending/chequing account/Chequing-monthly-statement-transactions-...csv`)

| Column | Example | Notes |
|--------|---------|-------|
| date | 2025-01-01 | |
| transaction | INT / AFT_OUT / EFT / TRFOUT / VISA | 交易类型识别 |
| description | Pre-authorized Debit to TORONTO HYDRO | 商户/用途描述 |
| amount | -88.10 | 负数为支出，正数为收入 |
| balance | 24.92 | 余额 |
| currency | CAD | |

### 导入筛选规则
- 信用卡: 只导入 `type=Purchase`，跳过 `type=Payment`（还款不是真支出）
- Chequing: 只导入 `isExpense(amount, type)` 为 true 的。支出行为 AFT_OUT/TRFOUT/VISA + 负金额。跳过 INT(利息)/EFT(存款)/Deposit

---

## Database Schema

```sql
-- 支出分类表
CREATE TABLE spending_categories (
  id TEXT PRIMARY KEY,
  category_name TEXT NOT NULL,      -- '餐饮', '购物', ...
  emoji TEXT DEFAULT '📦',         -- 显示图标
  keywords TEXT NOT NULL,           -- JSON array: ["AMAZON", "WALMART", ...]
  monthly_budget REAL,              -- 月预算 (nullable)
  color TEXT DEFAULT '#64748b',     -- 图表颜色
  is_active INTEGER DEFAULT 1
);

-- 支出交易表
CREATE TABLE spending_transactions (
  id TEXT PRIMARY KEY,
  account_type TEXT NOT NULL CHECK (account_type IN ('credit_card', 'chequing')),
  transaction_date TEXT NOT NULL,
  post_date TEXT,
  type TEXT,                        -- 'PURCHASE', 'AFT_OUT', etc.
  description TEXT NOT NULL,
  amount REAL NOT NULL,             -- 全部为正数 (ABS of original)
  currency TEXT DEFAULT 'CAD',
  category TEXT,                    -- FK to spending_categories.category_name
  merchant TEXT,                    -- cleaned merchant name
  raw_data TEXT,                    -- JSON of original CSV row
  source_file TEXT,                 -- original CSV filename
  created_at INTEGER NOT NULL
);

CREATE INDEX idx_spending_date ON spending_transactions(transaction_date);
CREATE INDEX idx_spending_category ON spending_transactions(category);
CREATE INDEX idx_spending_account ON spending_transactions(account_type);
```

---

## API Endpoints

| Method | Path | Purpose | Query/Body |
|--------|------|---------|-----------|
| GET | `/api/spending/csv-list` | 列出 Spending 文件夹中所有 CSVs | — |
| POST | `/api/spending/load` | 导入并自动分类 | `{ accountType: "credit_card"\|"chequing"\|"all" }` |
| GET | `/api/spending/transactions` | 分页查询交易 | `?month=2026-04&account_type=credit_card&category=餐饮&page=1&limit=50` |
| GET | `/api/spending/analysis` | 聚合分析数据 | `?month=2026-04` |
| GET | `/api/spending/categories` | 获取分类列表 | — |
| POST | `/api/spending/categories` | 创建/更新分类 | `{ id?, category_name, emoji, keywords, monthly_budget, color, is_active }` |
| DELETE | `/api/spending/categories/:id` | 删除分类 | — |
| POST | `/api/spending/clear` | 清空所有支出数据 | — |

### `/api/spending/analysis` Response Shape

```json
{
  "totalSpending": 3521.45,
  "byCategory": [
    { "category": "餐饮", "emoji": "🍜", "amount": 850.20, "count": 42, "percentage": 24, "budget": null },
    { "category": "购物", "emoji": "🛍️", "amount": 623.10, "count": 18, "percentage": 18, "budget": null }
  ],
  "monthlyTrend": [
    { "month": "2025-06", "total": 2800.0 },
    { "month": "2025-07", "total": 3100.0 }
  ],
  "topMerchants": [
    { "merchant": "AMAZON.CA", "amount": 320.50, "count": 8, "category": "购物" }
  ],
  "vsPreviousMonth": { "change": 421.45, "percentage": 13.6 }
}
```

---

## Categorizer Rules

在 `src/spending-categorizer.ts` 中实现。匹配逻辑：

1. 从数据库 `spending_categories` 表加载活跃分类及其关键词
2. 对每条交易：将 `merchant || description` 转为大写，逐个关键词查找
3. 匹配关键词 → 返回该分类。无匹配 → '其他'
4. 修改分类后调用 `invalidateCache()` 刷新

### 预置 11 分类关键词

| 分类 | 关键词 (大写) |
|------|-------------|
| 餐饮 🍜 | RESTAURANT, BISTRO, BURRITO, SUSHI, RAMEN, COFFEE, STARBUCKS, TIM HORTON, MCDONALD, KFC, PIZZA, TAO BISTRO, FAT BASTARD, FOOD, CAFE, BAKERY, DINING |
| 购物 🛍️ | AMAZON, AMZN, WALMART, COSTCO, SHOP, MALL, STORE, TARGET |
| 交通 🚗 | GAS, SHELL, ESSO, PETRO, UBER, TRANSIT, PARKING, PARKADE, TOLL, ENBRIDGE |
| 住房 🏠 | HYDRO, TORONTO HYDRO, RENT, MORTGAGE, PROPERTY TAX |
| 宠物 🐾 | PET VALU, PETSMART, VET, GROOM, PET |
| 娱乐 🎮 | NETFLIX, SPOTIFY, DISNEY, GAME, CINEMA, THEATRE |
| 旅行 ✈️ | AIRBNB, HOTEL, AIRLINE, FLIGHT, EXPEDIA, BOOKING |
| 医疗 💊 | PHARMACY, DRUG, CLINIC, DENTAL, DOCTOR, HOSPITAL, SHOPPERS |
| 订阅 📋 | SUBSCRIPTION, MEMBERSHIP, PATREON, ONEDRIVE, ICLOUD |
| 转账 💰 | TRANSFER, EFT, DEPOSIT |
| 其他 📦 | (兜底) |

---

## File Structure

```
dividend-dashboard/
├── server.ts                        # + /api/spending/* 端点
├── src/
│   ├── db.ts                        # + spending_categories/_transactions 表 + CRUD + 聚合
│   ├── spending-categorizer.ts      # [NEW] 自动分类引擎
│   └── components/
│       ├── Dashboard.tsx            # + Spending 标签页导航
│       └── SpendingDashboard.tsx    # [NEW] 支出分析仪表板
```

---

## Troubleshooting

### Server won't start (esbuild platform error)
```bash
npm rebuild esbuild
```

### Missing uuid module
```bash
# Windows (not WSL):
cd F:\MyFinanceTool\dividend-dashboard
npm install --legacy-peer-deps
```

### `package.json` parse error
Open package.json and fix duplicate `},` braces. Dependencies block should have exactly one closing brace.
