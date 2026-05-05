# Hermes v3.0 Memory System Architecture
**Reference Implementation for Multi-Project Parallel Execution**

---

## Overview: Four-Layer Memory Model

Hermes v3.0 memory is NOT a flat chat log. It's a stratified system supporting long-term learning across multiple projects running in parallel.

### Layer 1: Hard Memory
**Scope:** Unchanging core preferences, brand rules, routing principles  
**Mutation:** User approval required; Git-tracked  
**Examples:** "Design decisions are gray+red always", "High-quality output or reject", "Always route code tasks to Codex first"

### Layer 2: Evolving Memory
**Scope:** Learned patterns, successful workflows, refined heuristics  
**Mutation:** Auto-proposal after validation; can update frequently  
**Examples:** "Every time we tried [X strategy], [Y metric] improved 30%", "Clients prefer [this tone] over [that tone]"

### Layer 3: Episodic Memory
**Scope:** Task execution history, raw logs, events, data  
**Mutation:** Auto-recorded; never auto-delete  
**Examples:** All runs, approvals, artifacts, external metrics (sales, engagement, errors)

### Layer 4: Context Memory
**Scope:** Current working session state  
**Mutation:** Auto-generated; expires after task completes  
**Examples:** "We're debugging the OAuth flow", "Current standing in Discord approval queue"

---

## Storage Architecture

### GitHub: Versioned Long-Term Memory
**What goes here:**  
- Hard Memory (brand rules, core workflows, non-negotiables)
- Evolving Memory (validated learning, playbooks, decision rubrics)
- Templates and policy documents

**Structure:**
```
hermes-memory/
├─ hard_memory/
│  ├─ core_values.md
│  ├─ routing_principles.yaml
│  └─ non_negotiables.md
├─ evolving_memory/
│  ├─ playbooks/
│  ├─ decision_rubrics/
│  └─ reflection/
└─ templates/
```

**Why:** Diffs, rollback, review, branch. Long-term source of truth.

---

### Hermes DB (SQLite → Postgres)
**What goes here:**  
```sql
missions (id, created_at, project_id, status, content)
runs (id, mission_id, agent_type, prompt, output, tokens, timestamp)
approvals (id, run_id, approved_by, timestamp)
artifacts (id, run_id, type, path, metadata)
episodic_events (id, project_id, event_type, metrics, timestamp)
```

**Why:** Fast query access, runtime state, event tracking. Auto-backup to Google Drive nightly.

---

### Syncthing: Real-Time File Sync
**What syncs:**  
```
HermesWorkspace/
├─ 03_memory/           ← Hard + Evolving Memory (GitHub mirror)
├─ 02_skills/           ← Active skill development
├─ 04_artifacts/        ← Generated work products
└─ 05_prompts/          ← Working prompts & tests
```

**Why:** Develop on Mac, execute on Home PC, review on iPad. No manual git push/pull.

---

### rclone → Google Drive/S3: Backup & Archive
**What backs up:**  
```bash
# Nightly
hermes backup --output ~/hermes-backups/hermes-$(date +%Y%m%d).db.gz
rclone copy ~/hermes-backups gdrive:HermesBackup/db

# Per-project snapshots
rclone copy ~/HermesWorkspace/04_artifacts gdrive:HermesBackup/projects/{project-name}
```

**Why:** Cross-site redundancy, disaster recovery, migration preparation.

---

## Concrete Example: Multi-Stream Business Project

### Setup (Week 1)

**Hard Memory Example:**
```yaml
# hard_memory/business_rules.yaml
brand:
  non_negotiables:
    - quality_first: "No low-effort output"
    - design_first: "Designer aesthetic always"
    - original_content: "Each platform gets unique creation, not reposts"
  
  content_lines:
    冰箱贴: priority=1, quality_bar=high, revenue_driver=true
    AI视频: priority=2, quality_bar=high, platform=YouTube,TikTok
    大厂漫画: priority=3, quality_bar=medium, cultural_value=high
    国学讲座: priority=4, quality_bar=high, community_focus=true
```

**Evolving Memory Example (after Month 1 data):**
```yaml
# evolving_memory/playbooks/magnet_marketing_v1.1.md
learned_from: [Guildwood Day摆摊, Etsy首月销售]
patterns:
  - male_design_converts: 20% vs female_design: 8%
  - purple_starry_option_performs: best (25% conversion)
  - price_sweet_spot: C$15-20 vs C$25 (too high for摆摊)
recommendations:
  - focus_male_demographic_Q2
  - stock_purple_variants_priority
  - test_bundle_pricing_C$25-35
```

### Episodic Memory Example

```json
{
  "event_id": "ep_20260506_guildwood_day",
  "project": "冰箱贴",
  "event_type": "摆摊执行",
  "metrics": {
    "foot_traffic": 150,
    "conversion_rate": 0.15,
    "average_order": 23,
    "total_revenue": 506,
    "design_preference": "Option B (purple) >> Option C"
  },
  "user_notes": "女性来客多但转化率低。男性来客虽少但毫不犹豫。下月重点男性向。",
  "timestamp": "2026-06-06T18:30:00Z"
}
```

### Context Memory Example (Week of May 1-5)

```yaml
context:
  week: "2026-W18"
  projects: [冰箱贴, AI视频, 大厂漫画, 国学讲座]
  
  active_missions:
    - m001: 采购设备
    - m002: 账号激活 (awaiting user input: 4 social media names)
    - m003: 首批设计生成
  
  waiting_for_user:
    - Confirm: Instagram / 小红书 / TikTok / YouTube handle
    - Provide: Etsy shop name (FIFA theme preferred)
    - Provide: First 3 design briefs
  
  upcoming_decisions:
    - Shopify vs Webflow for护身符 app landing
    - First video script topic
    - Lecture pricing tier structure
```

---

## Memory Update Flow

### Standard Process

```
1. Task completed
   ↓
2. Hermes generates Reflection (3-5 learnings)
   ↓
3. Check: Does this belong in Hard / Evolving / Episodic?
   ↓
4a. If Hard: Generate Memory Update Proposal → user approval → git commit
4b. If Evolving: Generate proposal → user quick yes/no → auto-commit
4c. If Episodic: Auto-log to DB
   ↓
5. Reindex memory
   ↓
6. Next task uses updated memory
```

### For Multi-Project Scenarios

```
Parallel project A completes
  → Episodic event logged
  → Reflection checks for cross-project pattern
  
Parallel project B completes
  → Same reflection engine runs
  
After N events, Hermes proposes:
  "Pattern found: [strategy X] works across projects A and B.
   Suggest moving to Evolving Memory as general principle."
```

---

## MVP Implementation (4-Week Path)

### Week 1: Foundation
```
[ ] Create GitHub hermes-memory repo (private)
[ ] Initialize structure: hard_memory/, evolving_memory/, templates/
[ ] You write: hard_memory/core_values.md (15 min)
[ ] Setup Hermes DB schema (6 tables)
[ ] Initial context.yaml for first project
```

### Week 2: Data Capture
```
[ ] First major event completes (e.g.,摆摊, video launch)
[ ] Auto-log to episodic_events table
[ ] Hermes generates Reflection
[ ] You approve first Evolving Memory update
[ ] Auto git-commit + reindex
```

### Week 3: Validation
```
[ ] Second event completes
[ ] Compare: does new data confirm last week's pattern?
[ ] If yes: solidify in Evolving Memory v1.1
[ ] If no: mark as "hypothesis rejected", plan A/B test
```

### Week 4: Scale
```
[ ] Setup Syncthing sync across devices
[ ] Configure rclone backup to Google Drive
[ ] Document context handoff for cross-device work
[ ] First full weekly reflection + GitHub commit
```

---

## Prevention: Memory Pollution Rules

### What Should NEVER Be Hard Memory
- Time-specific data ("Q2 is a good time")
- One-off failures ("that one video flopped")
- Temporary whims ("I like blue this week")
- External events ("TikTok algorithm changed")

### What CAN Be Evolving Memory
- Patterns found 3+ times (with data)
- User explicitly approved changes
- Marked as "hypothesis tested" with success rate

### What IS Episodic Memory
- ALL execution details (no filter)
- Raw logs and errors
- User feedback (unedited)
- Costs and effort

---

## Key Decision Checkpoints

**When setting up for a new project:**

```
□ Is project a 1-off or long-term parallel stream? (determines memory lifetime)
□ What metrics matter to capture? (shapes episodic events)
□ What patterns are we testing? (seeds Evolving Memory hypotheses)
□ Who approves Evolved rules? (user only, or thresholds for auto-seal)
□ Backup frequency? (daily / weekly / monthly)
□ Cross-project learning ON or OFF? (merge patterns or keep isolated)
```

---

## Integration with Other Hermes v3.0 Components

**Memory System feeds into:**
- **Routing Engine:** Hard Memory routing_principles.yaml determines which agent (Codex/Claude/Gemini) gets each task type
- **Skill Evolution:** Episodic patterns → validated playbooks → automated skill updates
- **Dashboard Display:** Latest episodic_events → KPI tiles, alerts, trend charts
- **Cost Tracking:** Run logs + tokens → per-project burn rate, ROI per project

**Other components feed into Memory:**
- **Worker (Home PC):** Uploads execution logs
- **Brain (Mac mini):** Runs reflection engine nightly
- **Mobile (Pocket):** Enables quick context switches via approval interface

---

## When to Migrate from SQLite to Postgres

**Conditions:**
- 10K+ runs per month (SQLite hits concurrency limits)
- 100+ concurrent reflection queries (need proper connection pooling)
- Multiple machines writing simultaneously (need ACID guarantees)
- >2 years of data (query performance matters)

**Setup Example:**
```yaml
# config.yaml
database:
  type: postgres
  url: "postgresql://user:pass@127.0.0.1/hermes"
  connection_pool: 10
  backup_interval_hours: 6
```

**Then:**
```bash
hermes migrate-db sqlite:///hermes.db postgresql://...
```

---

## Debugging: What If Memory Gets Corrupted?

**Scenario 1: Bad Evolving Memory Rule**
```
1. Git revert to last-known-good commit
2. Hermes reindex --memory
3. User re-approves the rule with corrections
```

**Scenario 2: Episodic DB corruption**
```
1. Restore from latest rclone backup
2. Missing recent data? Hermes can re-log from artifact history
3. Validate against run logs
```

**Scenario 3: Context leak (confidential data in Hard Memory)**
```
1. Remove from GitHub
2. Purge from Syncthing
3. Mark to-delete in DB (will be removed next backup cycle)
4. Update privacy policy
```

---

## Next Session Handoff

If you pick up this project in a future session, look for:

```yaml
current_state:
  last_reflection: "2026-05-31_month1_review.md"
  memory_version:
    hard_memory: 1.0 (unchanged)
    evolving_memory: 1.3 (3 updates this month)
    episodic_events: 847 records
  next_focus: Cross-project pattern analysis
  pending_decisions: [video script direction, comic topic strategy]
```

All stored in DB and indexed, ready to query.