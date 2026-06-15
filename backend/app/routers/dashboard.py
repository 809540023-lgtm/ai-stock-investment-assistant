from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..database import get_db
from ..models import InvestmentPlan, Reminder, User

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=schemas.DashboardOut)
def get_dashboard(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    plans = (
        db.query(InvestmentPlan)
        .filter(InvestmentPlan.user_id == user.id)
        .order_by(InvestmentPlan.created_at.desc())
        .all()
    )

    rows: list[schemas.DashboardPlan] = []
    total_invested = 0.0
    total_market = 0.0

    for p in plans:
        shares = p.shares_owned or 0
        avg = p.average_cost
        price = p.current_price
        invested = round(shares * avg, 2) if (shares and avg) else 0.0
        market_value = round(shares * price, 2) if (shares and price) else 0.0
        pnl = round(market_value - invested, 2)
        pnl_pct = round(pnl / invested * 100, 2) if invested else None

        total_invested += invested
        total_market += market_value

        rows.append(
            schemas.DashboardPlan(
                id=p.id,
                stock_symbol=p.stock_symbol,
                stock_name=p.stock_name,
                plan_type=p.plan_type,
                status=p.status,
                shares_owned=shares,
                average_cost=avg,
                current_price=price,
                invested=invested,
                market_value=market_value,
                unrealized_pnl=pnl,
                unrealized_pnl_percent=pnl_pct,
            )
        )

    total_pnl = round(total_market - total_invested, 2)
    total_pct = round(total_pnl / total_invested * 100, 2) if total_invested else None

    unread = (
        db.query(Reminder)
        .join(InvestmentPlan, Reminder.plan_id == InvestmentPlan.id)
        .filter(InvestmentPlan.user_id == user.id, Reminder.is_read.is_(False))
        .count()
    )

    return schemas.DashboardOut(
        plan_count=len(plans),
        total_invested=round(total_invested, 2),
        total_market_value=round(total_market, 2),
        total_unrealized_pnl=total_pnl,
        total_unrealized_pnl_percent=total_pct,
        unread_reminders=unread,
        plans=rows,
    )
