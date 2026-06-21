"""零存整付（定期定額）策略回測。

用 FinMind 歷史日線，模擬「過去 N 年每月固定金額買進（含零股）」的績效：
總投入、目前市值、總報酬率、年化報酬率、最大回撤，以及可畫圖的時間序列。
"""
from __future__ import annotations

from . import stock_data


def _simulate(pts: list[tuple[str, float]], monthly: float) -> dict | None:
    """對一組 (date, close) 做每月定期定額模擬，回傳結果與時間序列。"""
    monthly_points: list[tuple[str, float]] = []
    seen: set[str] = set()
    for d, c in pts:
        ym = d[:7]
        if ym not in seen and c and c > 0:
            seen.add(ym)
            monthly_points.append((d, c))
    if not monthly_points:
        return None

    total_shares = 0.0
    total_invested = 0.0
    series: list[dict] = []
    for d, price in monthly_points:
        total_shares += monthly / price
        total_invested += monthly
        series.append({"date": d, "invested": round(total_invested), "value": round(total_shares * price)})

    final_date, final_price = pts[-1]
    final_value = total_shares * final_price
    if series[-1]["date"] != final_date:
        series.append({"date": final_date, "invested": round(total_invested), "value": round(final_value)})
    else:
        series[-1]["value"] = round(final_value)

    return {
        "monthly_points": monthly_points,
        "total_shares": total_shares,
        "total_invested": total_invested,
        "final_value": final_value,
        "final_date": final_date,
        "series": series,
    }


def run_backtest(symbol: str, monthly: float, years: float, benchmark: str = "0050") -> dict:
    symbol = symbol.strip().upper()
    monthly = float(monthly or 0)
    years = float(years or 3)
    if monthly <= 0:
        return {"available": False, "reason": "每月投入金額需大於 0"}

    days = int(years * 365) + 15
    prices = stock_data.get_price_history(symbol, days=days)
    pts = [(p["date"], p["close"]) for p in prices if p.get("close")]
    if len(pts) < 2:
        return {"available": False, "reason": "查無足夠的歷史股價資料"}

    sim = _simulate(pts, monthly)
    if not sim:
        return {"available": False, "reason": "查無足夠的歷史股價資料"}

    monthly_points = sim["monthly_points"]
    total_invested = sim["total_invested"]
    final_value = sim["final_value"]
    final_date = sim["final_date"]
    series = sim["series"]

    total_return_pct = (final_value - total_invested) / total_invested * 100 if total_invested else 0.0
    elapsed_years = len(monthly_points) / 12 or 1
    annualized = (
        ((final_value / total_invested) ** (1 / elapsed_years) - 1) * 100
        if total_invested > 0 and final_value > 0
        else 0.0
    )

    # 市值最大回撤（峰值到谷底）
    peak = 0.0
    max_dd = 0.0
    for s in series:
        peak = max(peak, s["value"])
        if peak > 0:
            max_dd = max(max_dd, (peak - s["value"]) / peak * 100)

    result = {
        "available": True,
        "symbol": symbol,
        "monthly": round(monthly),
        "months": len(monthly_points),
        "years": round(elapsed_years, 1),
        "start_date": monthly_points[0][0],
        "end_date": final_date,
        "total_invested": round(total_invested),
        "total_shares": round(sim["total_shares"], 2),
        "final_price": pts[-1][1],
        "final_value": round(final_value),
        "total_return_percent": round(total_return_pct, 1),
        "annualized_return_percent": round(annualized, 1),
        "max_drawdown_percent": round(max_dd, 1),
        "series": series,
    }

    # 與大盤 ETF（0050）同條件比較（用還原股價，避免分割/除權息扭曲）
    if benchmark and benchmark.upper() != symbol:
        bprices = stock_data.get_price_history_adj(benchmark, days=days)
        bpts = [(p["date"], p["close"]) for p in bprices if p.get("close")]
        bsim = _simulate(bpts, monthly) if len(bpts) >= 2 else None
        if bsim and bsim["total_invested"] > 0:
            b_return = (bsim["final_value"] - bsim["total_invested"]) / bsim["total_invested"] * 100
            result["benchmark"] = {
                "symbol": benchmark,
                "total_return_percent": round(b_return, 1),
                "final_value": round(bsim["final_value"]),
                "outperformance_percent": round(total_return_pct - b_return, 1),
            }

    return result
