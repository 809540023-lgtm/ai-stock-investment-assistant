from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..database import get_db
from ..models import InvestmentPlan, Reminder, User

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


@router.get("", response_model=list[schemas.ReminderOut])
def list_reminders(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = (
        db.query(Reminder)
        .join(InvestmentPlan, Reminder.plan_id == InvestmentPlan.id)
        .filter(InvestmentPlan.user_id == user.id)
    )
    if unread_only:
        q = q.filter(Reminder.is_read.is_(False))
    return q.order_by(Reminder.created_at.desc()).all()


@router.post("/{reminder_id}/read", response_model=schemas.ReminderOut)
def mark_read(
    reminder_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reminder = (
        db.query(Reminder)
        .join(InvestmentPlan, Reminder.plan_id == InvestmentPlan.id)
        .filter(Reminder.id == reminder_id, InvestmentPlan.user_id == user.id)
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=404, detail="找不到提醒")
    reminder.is_read = True
    db.commit()
    db.refresh(reminder)
    return reminder
