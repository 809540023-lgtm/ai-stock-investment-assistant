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
