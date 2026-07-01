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

    # 管理員：可操作名單匯入/匯出、外撥、通話內容設定等管理端 API
    is_admin = Column(Boolean, default=False, nullable=False)

    # 語音外撥（outbound）相關：須先同意才可外撥，隨時可退訂
    phone_number = Column(String, nullable=True)  # E.164，例 +886912345678
    voice_consent = Column(Boolean, default=False)  # 是否同意接收 AI 語音外撥
    voice_consent_at = Column(DateTime, nullable=True)  # 同意時間（合規佐證）
    voice_opt_out = Column(Boolean, default=False)  # 是否已退訂（退訂後不再外撥）

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


class AppSetting(Base):
    """簡單的 key-value 設定表（如：外撥預設開場白）。"""

    __tablename__ = "app_settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Lead(Base):
    """匯入的開發名單（預設未同意）。只有主動點同意連結、狀態變 consented 後才可外撥。"""

    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, default="")
    phone = Column(String, nullable=False, index=True)  # 正規化後 E.164；無法正規化則存原值
    phone_valid = Column(Boolean, default=True)  # 能否確定正規化（False 需人工確認，不送出）
    category = Column(String, nullable=True)
    source = Column(String, nullable=True)  # 匯入來源（檔名等）

    # 專屬同意連結用的隨機 token
    token = Column(String, unique=True, index=True, nullable=False)

    # imported | invited | consented | declined | do_not_contact
    status = Column(String, nullable=False, default="imported", index=True)
    consent = Column(Boolean, default=False)
    consent_at = Column(DateTime, nullable=True)
    consent_ip = Column(String, nullable=True)  # 同意當下來源 IP（合規佐證）
    do_not_contact = Column(Boolean, default=False)

    invited_at = Column(DateTime, nullable=True)
    invite_count = Column(Integer, default=0)
    note = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VoiceCallLog(Base):
    """每通 AI 語音外撥的紀錄（合規佐證：誰、何時、為何、結果、當下是否同意）。"""

    __tablename__ = "voice_call_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)

    direction = Column(String, nullable=False, default="outbound")  # outbound|inbound
    to_number = Column(String, nullable=False)
    from_number = Column(String, nullable=True)
    purpose = Column(String, nullable=True)  # plan_summary|alert|custom...
    message = Column(Text, nullable=True)  # 外撥要念出來的內容
    call_sid = Column(String, nullable=True, index=True)
    status = Column(String, nullable=True, default="queued")  # queued|ringing|in-progress|completed|failed|no-answer|busy
    consent_at_call = Column(Boolean, default=False)  # 撥打當下使用者是否同意（快照）
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
