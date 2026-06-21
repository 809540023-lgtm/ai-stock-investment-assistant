from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..database import get_db
from ..models import User, WatchlistItem
from ..services import stock_data

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("")
def list_watchlist(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """觀察清單，附上目前股價與漲跌（即時抓 FinMind）。"""
    items = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user.id)
        .order_by(WatchlistItem.created_at.desc())
        .all()
    )
    out = []
    for it in items:
        prices = stock_data.get_price_history(it.stock_symbol, days=10)
        closes = [p["close"] for p in prices if p.get("close")]
        cur = closes[-1] if closes else None
        prev = closes[-2] if len(closes) >= 2 else None
        change_pct = round((cur - prev) / prev * 100, 2) if cur and prev else None
        out.append(
            {
                "id": it.id,
                "stock_symbol": it.stock_symbol,
                "stock_name": it.stock_name,
                "note": it.note,
                "current_price": cur,
                "change_percent": change_pct,
                "created_at": it.created_at,
            }
        )
    return out


@router.post("", response_model=schemas.WatchlistOut)
def add_watchlist(
    data: schemas.WatchlistCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    symbol = data.stock_symbol.strip().upper()
    exists = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user.id, WatchlistItem.stock_symbol == symbol)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="此股票已在觀察清單中")
    item = WatchlistItem(
        user_id=user.id,
        stock_symbol=symbol,
        stock_name=stock_data.get_stock_name(symbol),
        note=data.note,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}")
def remove_watchlist(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = db.get(WatchlistItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="找不到觀察項目")
    db.delete(item)
    db.commit()
    return {"ok": True}
