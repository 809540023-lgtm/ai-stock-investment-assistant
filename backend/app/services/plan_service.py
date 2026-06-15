"""把資料抓取、AI 分析、寫回計畫、產生提醒與更新紀錄串起來。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import InvestmentPlan, PlanUpdateLog, Reminder, TradeRecord
from . import ai_service, stock_data


def recompute_position(db: Session, plan: InvestmentPlan) -> InvestmentPlan:
    """依交易紀錄（時間排序）重算持股數與平均成本。"""
    trades = (
        db.query(TradeRecord)
        .filter(TradeRecord.plan_id == plan.id)
        .order_by(TradeRecord.traded_at.asc(), TradeRecord.id.asc())
        .all()
    )
    shares = 0.0
    cost_basis = 0.0
    for t in trades:
        if t.action == "buy":
            shares += t.shares
            cost_basis += t.shares * t.price
        else:  # sell
            if shares > 0:
                avg = cost_basis / shares
                sold = min(t.shares, shares)
                cost_basis -= avg * sold
                shares -= sold
    plan.shares_owned = round(shares, 4)
    plan.average_cost = round(cost_basis / shares, 4) if shares > 0 else None
    db.commit()
    db.refresh(plan)
    return plan

AI_TO_PLAN_FIELDS = [
    "ai_summary",
    "fundamental_analysis",
    "valuation_analysis",
    "buy_strategy",
    "add_position_strategy",
    "pause_strategy",
    "sell_strategy",
    "risk_notes",
]


def _plan_to_dict(plan: InvestmentPlan) -> dict:
    return {
        "plan_type": plan.plan_type,
        "stock_symbol": plan.stock_symbol,
        "monthly_amount": plan.monthly_amount,
        "investment_years": plan.investment_years,
        "risk_profile": plan.risk_profile,
        "average_cost": plan.average_cost,
        "shares_owned": plan.shares_owned,
        "target_return_percent": plan.target_return_percent,
        "max_loss_percent": plan.max_loss_percent,
    }


def _decide_action(plan: InvestmentPlan, ai: dict) -> tuple[str, str]:
    """依目前估值/分類決定本次建議動作與提醒文字。"""
    valuation = (ai.get("valuation_analysis") or "")
    classification = ai.get("stock_classification", "")
    cur = plan.current_price

    if "偏高" in valuation:
        return "pause", f"{plan.stock_name} 目前估值偏高，建議暫停或減少投入，避免追高。"
    # 停利檢查
    if plan.average_cost and plan.target_return_percent and cur:
        gain = (cur - plan.average_cost) / plan.average_cost * 100
        if gain >= plan.target_return_percent:
            return "take_profit", f"{plan.stock_name} 報酬已達 {gain:.1f}%，可考慮分批停利。"
    # 停損檢查
    if plan.average_cost and plan.max_loss_percent and cur:
        loss = (plan.average_cost - cur) / plan.average_cost * 100
        if loss >= plan.max_loss_percent:
            return "stop_loss", f"{plan.stock_name} 已跌 {loss:.1f}%，請重新評估是否停損（勿盲目攤平）。"
    if "偏低" in valuation:
        return "add", f"{plan.stock_name} 估值偏低，可考慮加碼買進。"
    return "buy", f"{plan.stock_name} 估值合理（{classification}），維持原定買進計畫。"


def run_analysis(
    db: Session, plan: InvestmentPlan, trigger: str = "manual"
) -> InvestmentPlan:
    snapshot = stock_data.build_snapshot(plan.stock_symbol)
    ai = ai_service.analyze(_plan_to_dict(plan), snapshot)

    # 基本資料
    plan.stock_name = snapshot.get("name") or plan.stock_symbol
    if snapshot.get("current_price") is not None:
        plan.current_price = snapshot["current_price"]

    # AI 文字欄位
    for field in AI_TO_PLAN_FIELDS:
        if ai.get(field) is not None:
            setattr(plan, field, ai[field])

    # 零存整付的比例
    if plan.plan_type == "recurring_investment":
        if ai.get("fixed_buy_ratio") is not None:
            plan.fixed_buy_ratio = float(ai["fixed_buy_ratio"])
        if ai.get("cash_reserve_ratio") is not None:
            plan.cash_reserve_ratio = float(ai["cash_reserve_ratio"])

    if plan.status == "draft":
        plan.status = "active"

    # 決定動作、寫提醒與更新紀錄
    action, message = _decide_action(plan, ai)
    db.add(
        PlanUpdateLog(
            plan_id=plan.id,
            trigger=trigger,
            price_at_update=plan.current_price,
            ai_summary=plan.ai_summary,
            action=action,
            detail=message,
        )
    )
    kind_title = {
        "buy": "買進提醒",
        "add": "加碼提醒",
        "pause": "暫停投入提醒",
        "take_profit": "停利提醒",
        "stop_loss": "停損提醒",
    }
    db.add(
        Reminder(
            plan_id=plan.id,
            kind=action,
            title=kind_title.get(action, "投資提醒"),
            message=message,
        )
    )

    db.commit()
    db.refresh(plan)
    return plan
