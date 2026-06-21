from fastapi import APIRouter, Depends, Query

from ..auth import get_current_user
from ..models import User
from ..services import stock_data

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("/search")
def search(q: str = Query(..., min_length=1), user: User = Depends(get_current_user)):
    """依代號或名稱搜尋台股，給建立計畫/觀察清單時自動完成用。"""
    return stock_data.search_stocks(q)


@router.get("/{symbol}/valuation")
def valuation(symbol: str, user: User = Depends(get_current_user)):
    """最新本益比 / 股價淨值比 / 現金殖利率。"""
    v = stock_data.get_valuation(symbol)
    v["name"] = stock_data.get_stock_name(symbol)
    return v


@router.get("/{symbol}/per-band")
def per_band(symbol: str, user: User = Depends(get_current_user)):
    """近一年每日本益比，前端用來畫本益比河流圖。"""
    history = stock_data.get_per_history(symbol)
    pers = [h["per"] for h in history]
    bands = None
    if pers:
        s = sorted(pers)

        def pct(p):
            return round(s[min(len(s) - 1, int(len(s) * p))], 1)

        bands = {"low": pct(0.1), "mid": pct(0.5), "high": pct(0.9)}
    return {"symbol": symbol, "history": history, "bands": bands}


@router.get("/{symbol}/institutional")
def institutional(symbol: str, user: User = Depends(get_current_user)):
    """近 30 日三大法人買賣超（張）。"""
    return {"symbol": symbol, "data": stock_data.get_institutional(symbol)}


@router.get("/{symbol}/revenue")
def revenue(symbol: str, user: User = Depends(get_current_user)):
    """近 24 個月營收（億元）與年增率。"""
    return {"symbol": symbol, "data": stock_data.get_monthly_revenue_full(symbol)}


@router.get("/{symbol}/financials")
def financials(symbol: str, user: User = Depends(get_current_user)):
    """各季 EPS 與三率（毛利率/營益率/淨利率）。"""
    return {"symbol": symbol, "data": stock_data.get_financial_metrics(symbol)}


@router.get("/{symbol}/dividends")
def dividends(symbol: str, user: User = Depends(get_current_user)):
    """歷年配息。"""
    return {"symbol": symbol, "data": stock_data.get_dividends(symbol)}


@router.get("/{symbol}/margin")
def margin(symbol: str, user: User = Depends(get_current_user)):
    """融資餘額趨勢（張）。"""
    return {"symbol": symbol, "data": stock_data.get_margin_trading(symbol)}


@router.get("/compare")
def compare(symbols: str, user: User = Depends(get_current_user)):
    """多檔個股並列比較（最多 4 檔）：現價、近一年漲幅、估值。"""
    out = []
    for sym in [s.strip().upper() for s in symbols.split(",") if s.strip()][:4]:
        prices = stock_data.get_price_history(sym, days=365)
        closes = [p["close"] for p in prices if p.get("close")]
        val = stock_data.get_valuation(sym)
        change = (
            round((closes[-1] - closes[0]) / closes[0] * 100, 1)
            if len(closes) >= 2 and closes[0]
            else None
        )
        out.append(
            {
                "symbol": sym,
                "name": stock_data.get_stock_name(sym),
                "current_price": closes[-1] if closes else None,
                "year_change_percent": change,
                "per": val.get("per"),
                "pbr": val.get("pbr"),
                "dividend_yield": val.get("dividend_yield"),
            }
        )
    return out
