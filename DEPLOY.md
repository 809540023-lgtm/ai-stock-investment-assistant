# 部署指南（Render）

本專案附 `render.yaml` Blueprint，可一鍵建立三個資源：
PostgreSQL 資料庫、FastAPI 後端、Vite 靜態前端。

## 步驟

1. 將此 repo 推上 GitHub。
2. 登入 [Render](https://dashboard.render.com) →「New +」→「Blueprint」。
3. 選擇此 GitHub repo，Render 會讀取 `render.yaml` 並列出要建立的服務。
4. 按「Apply」開始建立。
5. 建立完成後，到 **ai-invest-api** 服務的 **Environment** 分頁，填入機密環境變數：
   - `ANTHROPIC_API_KEY`：你的 Claude API 金鑰（必填，啟用真實 AI 分析）
   - `FINMIND_TOKEN`：選填，留空使用免費額度
6. `SECRET_KEY` 由 Render 自動產生（強隨機），`DATABASE_URL` 自動接上 PostgreSQL，
   前端 `VITE_API_BASE` 自動指向後端網址，皆無需手動設定。

## 注意事項

- **資料庫**：已從 SQLite 改為 PostgreSQL。Render 免費 PostgreSQL 有使用期限，
  正式營運建議升級付費方案以保留資料。
- **CORS**：後端預設放行所有 `*.onrender.com` 網域；若綁自訂網域，
  在後端設定 `FRONTEND_ORIGIN`（可逗號分隔多個）。
- **免費方案**：閒置一段時間後服務會休眠，首次請求需數十秒喚醒，屬正常現象。

## 本機開發

```bash
# 後端
cd backend && ./venv/bin/uvicorn app.main:app --reload

# 前端
cd frontend && npm run dev
```
