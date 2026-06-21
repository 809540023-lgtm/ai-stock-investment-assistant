"""計畫健康度評分：用估值、趨勢、成本位置等綜合出 0–100 分與燈號。

純規則式、可解釋，給使用者一個快速體檢；不取代 AI 深度分析。
"""
from __future__ import annotations

from . import stock_data


def score_plan(plan, snapshot: dict | None = None) -> dict:
    snap = snapshot or stock_data.build_snapshot(plan.stock_symbol)
    cur = snap.get("current_price")
    avg = snap.get("avg_price_1y")
    hi = snap.get("high_52w")
    lo = snap.get("low_52w")

    reasons: list[str] = []
    score = 50.0

    # 1) 估值：現價相對一年均價（越低越有空間）
    if cur and avg:
        ratio = cur / avg
        if ratio <= 0.9:
            score += 20; reasons.append("股價低於一年均價，估值相對便宜（+）")
        elif ratio <= 1.1:
            score += 8; reasons.append("股價接近一年均價，估值合理")
        elif ratio <= 1.25:
            score -= 6; reasons.append("股價高於一年均價，估值偏高（−）")
        else:
            score -= 16; reasons.append("股價明顯高於一年均價，追高風險（−−）")

    # 2) 52 週位置（越接近低點空間越大）
    if cur and hi and lo and hi > lo:
        pos = (cur - lo) / (hi - lo)
        if pos <= 0.4:
            score += 12; reasons.append("位於 52 週相對低檔")
        elif pos >= 0.85:
            score -= 12; reasons.append("逼近 52 週高點，短線過熱（−）")

    # 3) 持股成本位置（已持有時）
    if plan.average_cost and cur:
        if cur >= plan.average_cost:
            score += 8; reasons.append("目前股價在你的成本之上，帳上獲利")
        else:
            score -= 4; reasons.append("目前股價低於你的成本，帳上虧損")

    # 4) 本益比合理性
    val = stock_data.get_valuation(plan.stock_symbol)
    per = val.get("per")
    if per:
        if per <= 15:
            score += 10; reasons.append(f"本益比 {per} 偏低")
        elif per <= 25:
            score += 2; reasons.append(f"本益比 {per} 中性")
        elif per <= 35:
            score -= 8; reasons.append(f"本益比 {per} 偏高（−）")
        else:
            score -= 16; reasons.append(f"本益比 {per} 過高（−−）")

    score = max(0, min(100, round(score)))
    if score >= 70:
        level, label = "good", "體質良好"
    elif score >= 45:
        level, label = "neutral", "中性觀望"
    else:
        level, label = "caution", "謹慎"

    return {
        "score": score,
        "level": level,
        "label": label,
        "reasons": reasons,
        "per": per,
        "dividend_yield": val.get("dividend_yield"),
        "pbr": val.get("pbr"),
    }
