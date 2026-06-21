from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..database import get_db
from ..models import InvestmentPlan, PlanUpdateLog, TradeRecord, User
from ..services import backtest, health, plan_service, stock_data

router = APIRouter(prefix="/api/plans", tags=["plans"])


def _get_owned_plan(plan_id: int, user: User, db: Session) -> InvestmentPlan:
    plan = db.get(InvestmentPlan, plan_id)
    if not plan or plan.user_id != user.id:
        raise HTTPException(status_code=404, detail="找不到投資計畫")
    return plan


@router.post("", response_model=schemas.PlanOut)
def create_plan(
    data: schemas.PlanCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if data.plan_type == "recurring_investment" and not data.monthly_amount:
        raise HTTPException(status_code=400, detail="零存整付計畫需填寫每月投入金額")

    plan = InvestmentPlan(
        user_id=user.id,
        plan_type=data.plan_type,
        stock_symbol=data.stock_symbol.strip().upper(),
        stock_name=stock_data.get_stock_name(data.stock_symbol.strip().upper()),
        monthly_amount=data.monthly_amount,
        initial_amount=data.initial_amount,
        investment_years=data.investment_years,
        risk_profile=data.risk_profile,
        max_loss_percent=data.max_loss_percent,
        target_return_percent=data.target_return_percent,
        average_cost=data.average_cost,
        shares_owned=data.shares_owned or 0,
        status="draft",
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("", response_model=list[schemas.PlanOut])
def list_plans(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return (
        db.query(InvestmentPlan)
        .filter(InvestmentPlan.user_id == user.id)
        .order_by(InvestmentPlan.created_at.desc())
        .all()
    )


@router.get("/{plan_id}", response_model=schemas.PlanOut)
def get_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _get_owned_plan(plan_id, user, db)


@router.patch("/{plan_id}", response_model=schemas.PlanOut)
def update_plan(
    plan_id: int,
    data: schemas.PlanUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plan = _get_owned_plan(plan_id, user, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}")
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plan = _get_owned_plan(plan_id, user, db)
    db.delete(plan)
    db.commit()
    return {"ok": True}


@router.post("/{plan_id}/analyze", response_model=schemas.PlanOut)
def analyze_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plan = _get_owned_plan(plan_id, user, db)
    return plan_service.run_analysis(db, plan, trigger="manual")


@router.get("/{plan_id}/updates", response_model=list[schemas.UpdateLogOut])
def plan_updates(
    plan_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_plan(plan_id, user, db)
    return (
        db.query(PlanUpdateLog)
        .filter(PlanUpdateLog.plan_id == plan_id)
        .order_by(PlanUpdateLog.created_at.desc())
        .all()
    )


@router.get("/{plan_id}/chart")
def plan_chart(
    plan_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """股價走勢 + 成本線 / 均價 / 高低點 + 實際買賣標記，供前端畫圖。"""
    plan = _get_owned_plan(plan_id, user, db)
    prices = stock_data.get_price_history(plan.stock_symbol, days=365)
    series = [{"date": p["date"], "close": p["close"]} for p in prices if p.get("close")]
    closes = [p["close"] for p in series]
    trades = (
        db.query(TradeRecord)
        .filter(TradeRecord.plan_id == plan.id)
        .order_by(TradeRecord.traded_at.asc())
        .all()
    )
    return {
        "symbol": plan.stock_symbol,
        "name": plan.stock_name,
        "prices": series,
        "average_cost": plan.average_cost,
        "current_price": closes[-1] if closes else plan.current_price,
        "high_52w": max(closes) if closes else None,
        "low_52w": min(closes) if closes else None,
        "avg_price_1y": round(sum(closes) / len(closes), 2) if closes else None,
        "trades": [
            {
                "date": (t.traded_at.date().isoformat() if t.traded_at else None),
                "action": t.action,
                "price": t.price,
                "shares": t.shares,
            }
            for t in trades
        ],
    }


@router.get("/{plan_id}/backtest")
def plan_backtest(
    plan_id: int,
    monthly: float | None = None,
    years: float | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """定期定額回測：預設用計畫的每月金額與年限，可用 query 覆寫。"""
    plan = _get_owned_plan(plan_id, user, db)
    amount = monthly if monthly is not None else (plan.monthly_amount or 3000)
    span = years if years is not None else (plan.investment_years or 3)
    return backtest.run_backtest(plan.stock_symbol, amount, span)


@router.get("/{plan_id}/health")
def plan_health(
    plan_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """計畫健康度評分（估值/趨勢/成本/本益比綜合）。"""
    plan = _get_owned_plan(plan_id, user, db)
    return health.score_plan(plan)


@router.get("/{plan_id}/trades", response_model=list[schemas.TradeOut])
def list_trades(
    plan_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_plan(plan_id, user, db)
    return (
        db.query(TradeRecord)
        .filter(TradeRecord.plan_id == plan_id)
        .order_by(TradeRecord.traded_at.desc(), TradeRecord.id.desc())
        .all()
    )


@router.post("/{plan_id}/trades", response_model=schemas.PlanOut)
def add_trade(
    plan_id: int,
    data: schemas.TradeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plan = _get_owned_plan(plan_id, user, db)
    db.add(
        TradeRecord(
            plan_id=plan.id,
            action=data.action,
            shares=data.shares,
            price=data.price,
            note=data.note,
        )
    )
    db.commit()
    return plan_service.recompute_position(db, plan)


@router.delete("/{plan_id}/trades/{trade_id}", response_model=schemas.PlanOut)
def delete_trade(
    plan_id: int,
    trade_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plan = _get_owned_plan(plan_id, user, db)
    trade = db.get(TradeRecord, trade_id)
    if not trade or trade.plan_id != plan.id:
        raise HTTPException(status_code=404, detail="找不到交易紀錄")
    db.delete(trade)
    db.commit()
    return plan_service.recompute_position(db, plan)
