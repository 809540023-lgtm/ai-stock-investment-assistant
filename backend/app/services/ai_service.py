"""呼叫 Claude API 產生投資分析。

沒有 ANTHROPIC_API_KEY 時，自動切換成規則式 demo 輸出，
讓整個平台在沒有金鑰的情況下也能完整展示流程。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

from ..config import settings
from . import prompts

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> dict:
    text = text.strip()
    # 容錯：若 Claude 包了 ```json ... ``` 仍能解析
    fenced = re.search(r"\{.*\}", text, re.DOTALL)
    if fenced:
        text = fenced.group(0)
    return json.loads(text)


def _call_claude(system: str, user: str) -> dict:
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    resp = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=8192,
        # 固定的系統指令加上 cache_control，重複分析時可命中快取、降低成本與延遲
        system=[
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}},
        ],
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(block.text for block in resp.content if block.type == "text")
    usage = getattr(resp, "usage", None)
    if usage is not None:
        logger.info(
            "Claude usage in=%s out=%s cache_read=%s cache_write=%s",
            getattr(usage, "input_tokens", "?"),
            getattr(usage, "output_tokens", "?"),
            getattr(usage, "cache_read_input_tokens", 0),
            getattr(usage, "cache_creation_input_tokens", 0),
        )
    return _extract_json(text)


def _enrich(snapshot: dict, symbol: str) -> dict:
    """把估值與法人籌碼補進快照，讓 AI 有更多依據。"""
    try:
        from . import stock_data

        snapshot = dict(snapshot)
        snapshot["valuation"] = stock_data.get_valuation(symbol)
        inst = stock_data.get_institutional(symbol, days=10)
        snapshot["institutional_recent"] = inst[-5:]
    except Exception as exc:  # 補充資料失敗不影響主流程
        logger.warning("補充估值/法人資料失敗：%s", exc)
    return snapshot


def analyze(plan: dict, snapshot: dict) -> dict:
    plan_type = plan.get("plan_type", "full_analysis")
    snapshot = _enrich(snapshot, snapshot.get("symbol") or plan.get("stock_symbol", ""))

    system = (
        prompts.SYSTEM_RECURRING
        if plan_type == "recurring_investment"
        else prompts.SYSTEM_FULL
    )
    user = prompts.user_content(plan, snapshot)

    if settings.ai_enabled:
        try:
            return _call_claude(system, user)
        except Exception as exc:
            logger.warning("Claude 分析失敗，改用規則式輸出：%s", exc)

    return _demo_analysis(plan, snapshot)


# ----------------- 規則式 demo（無金鑰時使用）-----------------
def _classify(snapshot: dict) -> str:
    """用 52 週價格振幅粗略判斷穩定型 vs 景氣循環。"""
    hi, lo = snapshot.get("high_52w"), snapshot.get("low_52w")
    if hi and lo and lo > 0:
        swing = (hi - lo) / lo
        if swing > 0.6:
            return "cyclical"
        if swing < 0.25:
            return "stable"
    return "growth"


def _valuation(snapshot: dict) -> str:
    cur, avg = snapshot.get("current_price"), snapshot.get("avg_price_1y")
    if cur and avg:
        if cur > avg * 1.15:
            return "偏高"
        if cur < avg * 0.85:
            return "偏低"
    return "合理"


def _demo_analysis(plan: dict, snapshot: dict) -> dict:
    classification = _classify(snapshot)
    valuation = _valuation(snapshot)
    cur = snapshot.get("current_price")
    name = snapshot.get("name", snapshot.get("symbol"))

    if classification == "stable":
        buy_ratio, cash_ratio = 0.9, 0.1
    elif classification == "cyclical":
        buy_ratio, cash_ratio = 0.6, 0.4
    else:
        buy_ratio, cash_ratio = 0.75, 0.25

    if valuation == "偏高":
        buy_ratio = max(0.3, buy_ratio - 0.25)
        cash_ratio = round(1 - buy_ratio, 2)

    result = {
        "stock_classification": classification,
        "ai_summary": (
            f"{name} 目前股價約 {cur}，估值判斷為「{valuation}」，"
            f"屬性偏向「{classification}」。本摘要為示範（規則式）輸出，"
            f"設定 ANTHROPIC_API_KEY 後可獲得 Claude 完整分析。"
        ),
        "fundamental_analysis": (
            f"近一年股價區間 {snapshot.get('low_52w')} ~ {snapshot.get('high_52w')}，"
            f"均價 {snapshot.get('avg_price_1y')}。"
            f"（demo：已抓取 {snapshot.get('price_points')} 個交易日資料）"
        ),
        "valuation_analysis": f"以一年均價為基準，目前估值{valuation}。",
        "buy_strategy": f"建議在接近一年均價（約 {snapshot.get('avg_price_1y')}）或以下分批買進。",
        "add_position_strategy": "股價較均價回檔 10% 以上且基本面未轉弱時加碼。",
        "pause_strategy": "估值明顯偏高、或基本面轉弱時暫停投入，避免追高。",
        "sell_strategy": (
            f"停利：達目標報酬率 {plan.get('target_return_percent') or 25}% 分批停利；"
            f"停損：跌破 {plan.get('max_loss_percent') or 15}% 重新評估。"
        ),
        "risk_notes": "本為示範輸出，未串接 Claude；投資決策請以實際資料與專業判斷為準。",
    }

    if plan.get("plan_type") == "recurring_investment":
        monthly = plan.get("monthly_amount") or 0
        est_shares = round((monthly * buy_ratio) / cur, 2) if cur else None
        result.update(
            {
                "fixed_buy_ratio": buy_ratio,
                "cash_reserve_ratio": cash_ratio,
                "estimated_shares_per_month": est_shares,
            }
        )
    return result
