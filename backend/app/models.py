from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False, default="")
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    plans = relationship(
        "InvestmentPlan", back_populates="user", cascade="all, delete-orphan"
    )


class InvestmentPlan(Base):
    __tablename__ = "investment_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # full_analysis | recurring_investment
    plan_type = Column(String, nullable=False, default="full_analysis")

    stock_symbol = Column(String, nullable=False, index=True)
    stock_name = Column(String, nullable=False, default="")

    # 零存整付相關
    monthly_amount = Column(Float, nullable=True)
    initial_amount = Column(Float, nullable=True)
    investment_years = Column(Integer, nullable=True)
    risk_profile = Column(String, nullable=True)  # conservative|balanced|aggressive

    # 風險與目標
    max_loss_percent = Column(Float, nullable=True)
    target_return_percent = Column(Float, nullable=True)

    # 部位狀態
    current_price = Column(Float, nullable=True)
    average_cost = Column(Float, nullable=True)
    shares_owned = Column(Float, nullable=True, default=0)

    # AI 試算出的配置
    cash_reserve_ratio = Column(Float, nullable=True)
    fixed_buy_ratio = Column(Float, nullable=True)

    # AI 分析輸出
    ai_summary = Column(Text, nullable=True)
    fundamental_analysis = Column(Text, nullable=True)
    valuation_analysis = Column(Text, nullable=True)
    buy_strategy = Column(Text, nullable=True)
    add_position_strategy = Column(Text, nullable=True)
    pause_strategy = Column(Text, nullable=True)
    sell_strategy = Column(Text, nullable=True)
    risk_notes = Column(Text, nullable=True)

    # draft | active | paused | closed
    status = Column(String, nullable=False, default="draft")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="plans")
    updates = relationship(
        "PlanUpdateLog", back_populates="plan", cascade="all, delete-orphan"
    )
    reminders = relationship(
        "Reminder", back_populates="plan", cascade="all, delete-orphan"
    )
    trades = relationship(
        "TradeRecord", back_populates="plan", cascade="all, delete-orphan"
    )


class PlanUpdateLog(Base):
    """每月（或手動）重新分析的快照紀錄。"""

    __tablename__ = "plan_update_logs"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("investment_plans.id"), nullable=False, index=True)

    trigger = Column(String, nullable=False, default="monthly")  # monthly|manual
    price_at_update = Column(Float, nullable=True)
    ai_summary = Column(Text, nullable=True)
    action = Column(String, nullable=True)  # buy|add|pause|take_profit|stop_loss|hold
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    plan = relationship("InvestmentPlan", back_populates="updates")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("investment_plans.id"), nullable=False, index=True)

    kind = Column(String, nullable=False)  # buy|add|pause|take_profit|stop_loss
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    plan = relationship("InvestmentPlan", back_populates="reminders")


class WatchlistItem(Base):
    """觀察清單：尚未建立完整計畫，但想追蹤的股票。"""

    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    stock_symbol = Column(String, nullable=False, index=True)
    stock_name = Column(String, nullable=False, default="")
    note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TradeRecord(Base):
    """會員實際買進／賣出的紀錄。"""

    __tablename__ = "trade_records"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("investment_plans.id"), nullable=False, index=True)

    action = Column(String, nullable=False)  # buy|sell
    shares = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    note = Column(String, nullable=True)
    traded_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    plan = relationship("InvestmentPlan", back_populates="trades")
