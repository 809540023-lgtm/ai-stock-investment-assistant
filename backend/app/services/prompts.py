"""Claude AI 分析的 prompt 模板。

兩種計畫各一個模板，都要求 Claude 回傳「純 JSON」，欄位對應 investment_plans。
"""
import json

OUTPUT_FIELDS_COMMON = """
請「只」回傳一個 JSON 物件（不要任何前後說明、不要 markdown code block），欄位如下：
{
  "stock_classification": "stable | cyclical | growth | turnaround 其中之一",
  "ai_summary": "3-5 句的投資摘要，給會員快速理解",
  "fundamental_analysis": "公司基本面分析（營收、獲利、財務體質、產業地位）",
  "valuation_analysis": "估值分析與合理股價區間判斷（偏低/合理/偏高）",
  "buy_strategy": "買進規則：在什麼價格或條件買進",
  "add_position_strategy": "加碼規則：何時加碼、加碼幅度",
  "pause_strategy": "暫停投入規則：什麼情況暫停",
  "sell_strategy": "停利與停損規則（含建議百分比）",
  "risk_notes": "主要風險提醒"
}
"""

RECURRING_EXTRA_FIELDS = """
另外，因為這是「零存整付（定期定額）」計畫，JSON 還要包含：
  "fixed_buy_ratio": 0~1 的數字，建議每月把投入金額的多少比例用來買進
  "cash_reserve_ratio": 0~1 的數字，建議保留多少比例現金等待回檔
  "estimated_shares_per_month": 數字，依目前股價估算每月可買進的股數
請依下列策略邏輯調整比例：
- 穩定型公司：每月投入比例可提高（80%-100%），現金保留比例低
- 景氣循環股：每月投入比例降低（50%-70%），保留 30%-50% 等待回檔，高估時暫停投入
- 估值偏高：降低每月買進金額、增加現金保留、提醒避免追高
- 基本面轉弱：暫停投入、重新評估、不自動加碼攤平
"""


def _data_block(snapshot: dict) -> str:
    return json.dumps(snapshot, ensure_ascii=False, indent=2)


# ---- 供 prompt caching 使用：固定的系統指令（可被快取）與動態的資料區 ----

SYSTEM_FULL = (
    "你是一位專業的台股投資分析師。會員會提供單一股票的市場與財報資料，"
    "請做「完整股票分析」，協助判斷是否適合長期持有，並產出明確的操作規則。\n"
    + OUTPUT_FIELDS_COMMON
)

SYSTEM_RECURRING = (
    "你是一位專業的台股投資分析師。會員會提供單一股票資料，"
    "請為「零存整付（定期定額）」會員設計每月投入計畫，"
    "重點在每月投入多少、買多少股、保留多少現金、何時加碼或暫停。\n"
    + OUTPUT_FIELDS_COMMON
    + RECURRING_EXTRA_FIELDS
)


def user_content(plan: dict, snapshot: dict) -> str:
    extra = ""
    if plan.get("monthly_amount"):
        extra = (
            f"- 每月投入金額：{plan.get('monthly_amount')} 元\n"
            f"- 投資年限：{plan.get('investment_years')} 年\n"
            f"- 風險偏好：{plan.get('risk_profile')}\n"
        )
    return f"""股票代號：{snapshot.get('symbol')}（{snapshot.get('name')}）
會員設定：
- 持股成本（如有）：{plan.get('average_cost')}
- 目前持股數（如有）：{plan.get('shares_owned')}
- 目標報酬率(%)：{plan.get('target_return_percent')}
- 可承受最大虧損(%)：{plan.get('max_loss_percent')}
{extra}
以下是抓到的市場與財報資料（data_available 為 false 代表查無即時資料，請謹慎分析並於 risk_notes 標註）：
{_data_block(snapshot)}
"""


def full_analysis_prompt(plan: dict, snapshot: dict) -> str:
    return f"""你是一位專業的台股投資分析師。請針對以下單一股票做「完整股票分析」，
協助會員判斷是否適合長期持有，並產出明確的操作規則。

股票代號：{snapshot.get('symbol')}（{snapshot.get('name')}）
會員設定：
- 持股成本（如有）：{plan.get('average_cost')}
- 目前持股數（如有）：{plan.get('shares_owned')}
- 目標報酬率(%)：{plan.get('target_return_percent')}
- 可承受最大虧損(%)：{plan.get('max_loss_percent')}

以下是抓到的市場與財報資料（若 data_available 為 false 代表查無即時資料，請依代號與常識謹慎分析並在 risk_notes 標註資料受限）：
{_data_block(snapshot)}

{OUTPUT_FIELDS_COMMON}
"""


def recurring_prompt(plan: dict, snapshot: dict) -> str:
    return f"""你是一位專業的台股投資分析師。請針對以下股票，為「零存整付（定期定額）」會員
設計每月投入計畫，重點在於每月投入多少、買多少股、保留多少現金、何時加碼或暫停。

股票代號：{snapshot.get('symbol')}（{snapshot.get('name')}）
會員設定：
- 每月投入金額：{plan.get('monthly_amount')} 元
- 投資年限：{plan.get('investment_years')} 年
- 風險偏好：{plan.get('risk_profile')}
- 目標報酬率(%)：{plan.get('target_return_percent')}
- 可承受最大虧損(%)：{plan.get('max_loss_percent')}

以下是抓到的市場與財報資料：
{_data_block(snapshot)}

{OUTPUT_FIELDS_COMMON}
{RECURRING_EXTRA_FIELDS}
"""
