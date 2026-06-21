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


def get_price_history_adj(symbol: str, days: int = 365) -> list[dict]:
    """還原權值股價（已調整除權息與分割），回測比較較準；查無則退回原始股價。"""
    start = (date.today() - timedelta(days=days)).isoformat()
    data = _get("TaiwanStockPriceAdj", symbol, start)
    out = [{"date": r.get("date"), "close": r.get("close")} for r in data if r.get("close")]
    return out or get_price_history(symbol, days)


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


_STOCK_LIST_CACHE: list[dict] = []


def list_all_stocks() -> list[dict]:
    """全台股清單（含上市櫃），用於搜尋。簡單記憶體快取。"""
    global _STOCK_LIST_CACHE
    if _STOCK_LIST_CACHE:
        return _STOCK_LIST_CACHE
    data = _get("TaiwanStockInfo", "", "2020-01-01")
    seen: set[str] = set()
    out: list[dict] = []
    for row in data:
        sid = row.get("stock_id")
        if not sid or sid in seen:
            continue
        # 只留 4 碼數字的普通股，濾掉權證/ETF 代碼雜訊較多者保留 ETF(0 開頭)
        if not (sid.isdigit() and len(sid) == 4):
            continue
        seen.add(sid)
        out.append({"symbol": sid, "name": row.get("stock_name") or sid})
    if out:
        _STOCK_LIST_CACHE = out
    return out


def search_stocks(query: str, limit: int = 12) -> list[dict]:
    q = (query or "").strip().upper()
    if not q:
        return []
    stocks = list_all_stocks()
    starts = [s for s in stocks if s["symbol"].startswith(q) or s["name"].startswith(q)]
    contains = [s for s in stocks if q in s["symbol"] or q in s["name"]]
    # 代號/名稱開頭優先，其次包含
    ordered: list[dict] = []
    seen: set[str] = set()
    for s in starts + contains:
        if s["symbol"] not in seen:
            seen.add(s["symbol"])
            ordered.append(s)
        if len(ordered) >= limit:
            break
    return ordered


def get_valuation(symbol: str) -> dict:
    """最新本益比 / 股價淨值比 / 現金殖利率（FinMind TaiwanStockPER）。"""
    start = (date.today() - timedelta(days=20)).isoformat()
    data = _get("TaiwanStockPER", symbol, start)
    if not data:
        return {"per": None, "pbr": None, "dividend_yield": None, "date": None}
    last = data[-1]
    return {
        "per": last.get("PER"),
        "pbr": last.get("PBR"),
        "dividend_yield": last.get("dividend_yield"),
        "date": last.get("date"),
    }


def get_per_history(symbol: str, days: int = 365) -> list[dict]:
    """近一年每日本益比，用於本益比河流圖。"""
    start = (date.today() - timedelta(days=days)).isoformat()
    data = _get("TaiwanStockPER", symbol, start)
    out = []
    for row in data:
        per = row.get("PER")
        if per and per > 0:
            out.append({"date": row.get("date"), "per": per})
    return out


def get_institutional(symbol: str, days: int = 30) -> list[dict]:
    """近期三大法人買賣超（張數，正為買超）。"""
    start = (date.today() - timedelta(days=days)).isoformat()
    data = _get("TaiwanStockInstitutionalInvestorsBuySell", symbol, start)
    # 依日期彙整三大法人合計（buy-sell），單位股換算張數
    by_date: dict[str, float] = {}
    for row in data:
        d = row.get("date")
        net = (row.get("buy") or 0) - (row.get("sell") or 0)
        by_date[d] = by_date.get(d, 0) + net
    out = [{"date": d, "net_lots": round(v / 1000)} for d, v in sorted(by_date.items())]
    return out[-days:]


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
