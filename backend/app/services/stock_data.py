"""台股資料來源：FinMind 免費 API。

抓取：股票名稱、近期股價、月營收、財報關鍵指標。
若 API 失敗或查無資料，回傳合理的 fallback，讓整個流程仍可運作。
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"


def _get(dataset: str, data_id: str, start_date: str, end_date: Optional[str] = None) -> list[dict]:
    params: dict[str, Any] = {
        "dataset": dataset,
        "data_id": data_id,
        "start_date": start_date,
    }
    if end_date:
        params["end_date"] = end_date
    if settings.finmind_token:
        params["token"] = settings.finmind_token
    try:
        resp = httpx.get(FINMIND_URL, params=params, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("data", []) or []
    except Exception as exc:  # 網路/限流/格式問題都退回空資料
        logger.warning("FinMind %s 查詢失敗 (%s): %s", dataset, data_id, exc)
        return []


def get_stock_name(symbol: str) -> str:
    data = _get("TaiwanStockInfo", symbol, "2020-01-01")
    if data:
        return data[-1].get("stock_name") or symbol
    return symbol


def get_price_history(symbol: str, days: int = 365) -> list[dict]:
    start = (date.today() - timedelta(days=days)).isoformat()
    data = _get("TaiwanStockPrice", symbol, start)
    out = []
    for row in data:
        out.append({"date": row.get("date"), "close": row.get("close")})
    return out


def get_monthly_revenue(symbol: str) -> list[dict]:
    start = (date.today() - timedelta(days=400)).isoformat()
    data = _get("TaiwanStockMonthRevenue", symbol, start)
    out = []
    for row in data[-12:]:
        out.append(
            {
                "year": row.get("revenue_year"),
                "month": row.get("revenue_month"),
                "revenue": row.get("revenue"),
            }
        )
    return out


def get_financials(symbol: str) -> list[dict]:
    start = (date.today() - timedelta(days=900)).isoformat()
    data = _get("TaiwanStockFinancialStatements", symbol, start)
    # 只挑常用指標，避免塞太多進 prompt
    wanted = {"EPS", "Revenue", "GrossProfit", "OperatingIncome", "NetIncome"}
    out = []
    for row in data:
        if row.get("type") in wanted:
            out.append(
                {
                    "date": row.get("date"),
                    "type": row.get("type"),
                    "value": row.get("value"),
                }
            )
    return out[-40:]


def build_snapshot(symbol: str) -> dict:
    """整理成給 AI 與前端用的單一快照。"""
    symbol = symbol.strip().upper()
    name = get_stock_name(symbol)
    prices = get_price_history(symbol)
    closes = [p["close"] for p in prices if p.get("close") is not None]

    current_price = closes[-1] if closes else None
    high_52w = max(closes) if closes else None
    low_52w = min(closes) if closes else None
    avg_price = round(sum(closes) / len(closes), 2) if closes else None

    return {
        "symbol": symbol,
        "name": name,
        "current_price": current_price,
        "high_52w": high_52w,
        "low_52w": low_52w,
        "avg_price_1y": avg_price,
        "price_points": len(closes),
        "recent_prices": prices[-30:],
        "monthly_revenue": get_monthly_revenue(symbol),
        "financials": get_financials(symbol),
        "data_available": bool(closes),
    }
