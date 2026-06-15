from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..database import get_db
from ..models import InvestmentPlan, PlanUpdateLog, TradeRecord, User
from ..services import plan_service, stock_data

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
