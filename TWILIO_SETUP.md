# Twilio 語音電話 AI 客服 — 設定指南

第一階段：**inbound（使用者打進 Twilio 號碼，AI 用台灣國語語音回答台股問題）**。

## 運作流程

```
使用者撥打 Twilio 號碼
  → Twilio POST  {後端}/api/voice/incoming   → 回 TwiML：問候 + 開始收音
  → 使用者說話，Twilio 轉文字
  → Twilio POST  {後端}/api/voice/respond    → 呼叫 Claude → 回 TwiML：念出答案 + 繼續收音
  → 多輪對話，沉默兩次後禮貌掛斷
```

- 語音辨識：台灣國語 `cmn-Hant-TW`
- 語音合成：Google 台灣國語女聲 `Google.cmn-TW-Standard-A`
- 多輪記憶：以 `CallSid` 為 key 暫存於後端記憶體（30 分鐘過期）

## 一、設定環境變數

在後端 `.env`（本機）或 Render 後台（正式）填入：

| 變數 | 說明 |
|------|------|
| `TWILIO_ACCOUNT_SID` | Twilio Console 首頁 |
| `TWILIO_AUTH_TOKEN` | Twilio Console 首頁（機密） |
| `TWILIO_PHONE_NUMBER` | 你的號碼，E.164 格式，例 `+15551234567` |
| `PUBLIC_BASE_URL` | 後端對外網址，例 `https://ai-invest-api.onrender.com`（**簽章驗證需要**） |
| `TWILIO_VALIDATE_SIGNATURE` | 正式環境 `true`；本機 ngrok 測試可暫設 `false` |
| `ANTHROPIC_API_KEY` | 沒填時電話會念「尚未設定金鑰」的提示 |

## 二、把號碼的 webhook 指到後端

Twilio Console → **Phone Numbers → Manage → Active numbers → 點你的號碼**：

- **Voice Configuration → A call comes in**
  - 設為 **Webhook**
  - URL：`https://你的後端網址/api/voice/incoming`
  - HTTP 方法：**POST**
- 儲存。

> 只需設定這一個進線 URL；`/api/voice/respond` 是程式內部用 TwiML 的 `action` 自動接續，不用在 Console 設定。

## 三、本機測試（選用）

電話 webhook 需要公開網址，本機用 [ngrok](https://ngrok.com/)：

```bash
# 終端機 A：啟動後端
cd backend
env -u ANTHROPIC_API_KEY ./venv/bin/uvicorn app.main:app --port 8000
# （env -u 是因為本機空的 ANTHROPIC_API_KEY 會蓋掉 .env）

# 終端機 B：開隧道
ngrok http 8000
```

把 ngrok 給的 `https://xxxx.ngrok-free.app` 填進 `PUBLIC_BASE_URL`，並把 Twilio 號碼的進線 URL 設成 `https://xxxx.ngrok-free.app/api/voice/incoming`，然後打那支 Twilio 號碼測試。

驗證後端是否就緒：

```bash
curl https://你的後端網址/api/health
# {"status":"ok","ai_enabled":true,"twilio_enabled":true}
```

## 四、AI 主動外撥（outbound）

> ⚠️ 外撥前一定要有**同意紀錄**。系統會在每次外撥檢查同意狀態，並把當下是否同意寫進通話紀錄，作為合規佐證。

### 流程

```
後端 POST /api/voice/outbound-call（檢查同意/退訂）
  → Twilio 撥打對方號碼
  → 對方接起，Twilio 抓 {後端}/api/voice/outbound?log_id=N 的 TwiML
  → 念出訊息 + 告知「說『取消訂閱』即可退訂」 + 接續問答（共用 inbound 問答）
  → Twilio 回報狀態到 {後端}/api/voice/status，更新通話紀錄
```

外撥**需要 `PUBLIC_BASE_URL`**（Twilio 要能回呼抓 TwiML），不用在 Console 設定任何 URL。

### 相關 API（皆需登入）

| 方法 | 路徑 | 說明 |
|------|------|------|
| `POST` | `/api/voice/consent` | 會員留電話 + 同意外撥（記錄同意時間） |
| `GET` | `/api/voice/consent` | 查目前同意狀態 |
| `POST` | `/api/voice/opt-out` | 退訂語音外撥 |
| `POST` | `/api/voice/outbound-call` | 發起外撥，body：`{user_id?, brief, purpose?}` |
| `GET` | `/api/voice/calls` | 查自己的外撥紀錄 |

`brief` 是「重點」，系統會用 Claude 改寫成自然的電話口語開場（沒金鑰則原文念出）。

### 退訂機制（三種都已內建）

1. 會員在網站呼叫 `POST /api/voice/opt-out`
2. 通話中說「取消訂閱／退訂／不要再打」→ 自動標記退訂並掛斷
3. 退訂後再呼叫外撥 API 會被擋下（回 409）

## 五、名單匯入與「邀請同意」管道（opt-in）

爬來的、未同意的名單**不可直接外撥**。流程是：匯入（一律未同意）→ 送專屬同意連結 → 對方點同意 → 才進入可外撥狀態。

### 1. 匯入名單

```bash
cd backend
./venv/bin/python -m scripts.import_leads ~/Desktop/taishan-0-1km-clean.csv 泰山名單 TW
```

- 第三個參數是**國別預設**（`TW`/`JP`/…），用 google libphonenumber 正確解析。
- 混合國別名單若用錯國別，外國本地號碼會被標記 `needs_review`（不會被誤撥），需指定正確國別重匯。
- 重複電話自動略過。匯入後**全部 consent=false**。

### 2. 匯出同意連結，用任何合法管道寄送

```
GET /api/leads/invites.csv     # 需登入，輸出 name,phone,invite_url
```

每筆有專屬 `invite_url`（`{PUBLIC_BASE_URL}/invite/{token}`）。你可用簡訊、Email、QR code 等寄送。
> 注意：Twilio 發簡訊到台灣需 sender ID／A2P 登記，門檻高；連結設計成管道無關就是為此。

### 3. 對方點連結 → 同意頁

- `GET /invite/{token}`：公開同意頁（含身分揭露、僅供參考聲明、隨時可取消）
- 按「我同意」→ status 變 `consented`，記錄同意時間與 IP（合規佐證）
- 按「不需要」→ 標記 `do_not_contact`，永不再聯繫

### 4. 查看進度

```
GET /api/leads/stats           # 各狀態統計、已同意數、待確認數
GET /api/leads?status=consented
```

只有 `consented` 的名單，才應該進入第四節的語音外撥。

## 六、合規提醒（重要）

- **外撥（outbound）在台灣個資法/電信法、美國 TCPA 下都要求事先明確同意 + 隨時可退出**。本系統已內建同意紀錄、通話紀錄與三種退訂方式；務必確保每位被撥打對象都有真實的同意來源（不要匯入未同意名單）。
- 建議**撥打時段**避開夜間，並控制頻率，避免被標記為騷擾號碼導致封號。
- 電話內容為投資資訊，AI 已被指示**中立、提醒風險、不報明牌**；建議在外撥開場或網站再加上「僅供參考，非投資建議」聲明。

## 涉及檔案

- `backend/app/routers/voice.py` — webhook、TwiML、同意/外撥 API
- `backend/app/services/voice_service.py` — Claude 對話、多輪記憶、外撥訊息改寫、退訂判斷
- `backend/app/services/telephony.py` — Twilio REST 外撥
- `backend/app/models.py` — User 同意欄位、`VoiceCallLog` 通話紀錄
- `backend/app/config.py` — Twilio 設定
- `backend/app/services/leads.py` — 名單匯入、libphonenumber 電話正規化
- `backend/app/routers/leads.py` — 同意頁、同意/退出、名單管理 API
- `backend/scripts/import_leads.py` — CSV 匯入 CLI
