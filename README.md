# AI 投資助理平台

針對單一股票，讓會員建立兩種個人化投資計畫的 AI 投資助理：

- **模式 A 完整股票分析計劃**：深入研究一檔股票 — 基本面、估值、產業循環、風險、停利停損、長期持有判斷。
- **模式 B 零存整付投資計劃**：每月固定投入 — 每月買多少、保留多少現金、何時加碼或暫停。

## 技術架構

| 層         | 技術 |
|------------|------|
| 後端       | Python FastAPI + SQLAlchemy（SQLite）|
| 前端       | React + TypeScript + Vite + React Router |
| 股價/財報  | FinMind 免費 API（台股）|
| AI 分析    | Anthropic Claude API（未設金鑰時自動切換規則式 demo）|
| 排程       | APScheduler（每月 1 號 09:00 自動更新）|

## 功能對照

| 流程節點             | 實作 |
|----------------------|------|
| 會員登入/註冊        | JWT 驗證 (`/api/auth/*`) |
| 選擇計畫類型         | `建立投資計畫` 頁 |
| 完整分析 / 零存整付表單 | 兩個獨立表單頁 |
| 抓股價/財報/營收     | `services/stock_data.py`（FinMind）|
| AI 分析基本面/估值/規則 | `services/ai_service.py` + `prompts.py` |
| 試算每月可買股數/比例 | 零存整付 prompt + demo 規則 |
| AI 分析結果頁        | `PlanResult.tsx` |
| 我的投資計畫         | `MyPlans.tsx` |
| 每月自動更新         | `scheduler.py` |
| 每月更新紀錄         | `plan_update_logs` + `UpdateRecords.tsx` |
| 提醒中心             | `reminders` + `Reminders.tsx` |

策略邏輯（穩定型 / 景氣循環 / 估值偏高 / 基本面轉弱對應的投入與現金比例）寫在
prompt 模板與 demo fallback（`ai_service.py`）中。

## 快速啟動

### 1. 後端

```bash
cd backend
python3.13 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env        # 填入 ANTHROPIC_API_KEY / FINMIND_TOKEN（皆可留空試跑）
./venv/bin/uvicorn app.main:app --reload --port 8000
```

> 沒填 `ANTHROPIC_API_KEY` 時會自動使用「規則式 demo 分析」，整個流程仍可完整跑通。

### 2. 前端

```bash
cd frontend
npm install
npm run dev                  # http://localhost:5173（已設定 /api 代理到 8000）
```

開瀏覽器到 http://localhost:5173 ，註冊帳號即可使用。

## 環境變數（backend/.env）

| 變數 | 說明 |
|------|------|
| `ANTHROPIC_API_KEY` | Claude API 金鑰，留空進入 demo 模式 |
| `ANTHROPIC_MODEL`   | 預設 `claude-sonnet-4-6` |
| `FINMIND_TOKEN`     | FinMind token，留空為匿名（每小時限制較低）|
| `SECRET_KEY`        | JWT 簽章金鑰，正式環境請更換 |
| `FRONTEND_ORIGIN`   | CORS 允許的前端網址 |

## 手動測試排程

```bash
curl -X POST http://localhost:8000/api/admin/run-monthly-update
```

對所有 `active` 計畫重新跑一次 AI 分析、寫入更新紀錄與提醒。

## 資料表 `investment_plans`

包含 `plan_type`（full_analysis / recurring_investment）、`stock_symbol/name`、
`monthly_amount`、`initial_amount`、`investment_years`、`risk_profile`、
`max_loss_percent`、`target_return_percent`、`current_price`、`average_cost`、
`shares_owned`、`cash_reserve_ratio`、`fixed_buy_ratio`、`ai_summary`、
`fundamental_analysis`、`valuation_analysis`、`buy_strategy`、`add_position_strategy`、
`pause_strategy`、`sell_strategy`、`risk_notes`、`status`、`created_at`、`updated_at`。

另有 `plan_update_logs`（每月更新快照）與 `reminders`（提醒）兩張關聯表。
