from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

PlanType = Literal["full_analysis", "recurring_investment"]
RiskProfile = Literal["conservative", "balanced", "aggressive"]


# ---------- Auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = ""


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    is_admin: bool = False

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Plans ----------
class PlanCreate(BaseModel):
    plan_type: PlanType
    stock_symbol: str
    # 零存整付
    monthly_amount: Optional[float] = None
    initial_amount: Optional[float] = None
    investment_years: Optional[int] = None
    risk_profile: Optional[RiskProfile] = None
    # 風險/目標 & 持股
    max_loss_percent: Optional[float] = None
    target_return_percent: Optional[float] = None
    average_cost: Optional[float] = None
    shares_owned: Optional[float] = None


class PlanUpdateIn(BaseModel):
    status: Optional[Literal["draft", "active", "paused", "closed"]] = None
    monthly_amount: Optional[float] = None
    average_cost: Optional[float] = None
    shares_owned: Optional[float] = None
    target_return_percent: Optional[float] = None
    max_loss_percent: Optional[float] = None


class PlanOut(BaseModel):
    id: int
    user_id: int
    plan_type: str
    stock_symbol: str
    stock_name: str
    monthly_amount: Optional[float]
    initial_amount: Optional[float]
    investment_years: Optional[int]
    risk_profile: Optional[str]
    max_loss_percent: Optional[float]
    target_return_percent: Optional[float]
    current_price: Optional[float]
    average_cost: Optional[float]
    shares_owned: Optional[float]
    cash_reserve_ratio: Optional[float]
    fixed_buy_ratio: Optional[float]
    ai_summary: Optional[str]
    fundamental_analysis: Optional[str]
    valuation_analysis: Optional[str]
    buy_strategy: Optional[str]
    add_position_strategy: Optional[str]
    pause_strategy: Optional[str]
    sell_strategy: Optional[str]
    risk_notes: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UpdateLogOut(BaseModel):
    id: int
    plan_id: int
    trigger: str
    price_at_update: Optional[float]
    ai_summary: Optional[str]
    action: Optional[str]
    detail: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ReminderOut(BaseModel):
    id: int
    plan_id: int
    kind: str
    title: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Trades ----------
class TradeCreate(BaseModel):
    action: Literal["buy", "sell"]
    shares: float = Field(gt=0)
    price: float = Field(gt=0)
    note: Optional[str] = None


class TradeOut(BaseModel):
    id: int
    plan_id: int
    action: str
    shares: float
    price: float
    note: Optional[str]
    traded_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Watchlist ----------
class WatchlistCreate(BaseModel):
    stock_symbol: str
    note: Optional[str] = None


class WatchlistOut(BaseModel):
    id: int
    stock_symbol: str
    stock_name: str
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Dashboard ----------
class DashboardPlan(BaseModel):
    id: int
    stock_symbol: str
    stock_name: str
    plan_type: str
    status: str
    shares_owned: float
    average_cost: Optional[float]
    current_price: Optional[float]
    invested: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: Optional[float]


class DashboardOut(BaseModel):
    plan_count: int
    total_invested: float
    total_market_value: float
    total_unrealized_pnl: float
    total_unrealized_pnl_percent: Optional[float]
    unread_reminders: int
    plans: list[DashboardPlan]


# ---------- Voice (Twilio 語音外撥) ----------
class VoiceConsentIn(BaseModel):
    phone_number: str = Field(min_length=8, description="E.164 格式，例 +886912345678")
    consent: bool = True


class VoiceConsentOut(BaseModel):
    phone_number: Optional[str]
    voice_consent: bool
    voice_consent_at: Optional[datetime]
    voice_opt_out: bool

    class Config:
        from_attributes = True


class OutboundCallIn(BaseModel):
    """對某位會員發起 AI 語音外撥。user_id 留空則撥給目前登入者自己。"""
    user_id: Optional[int] = None
    brief: Optional[str] = Field(default=None, description="逐字念出的內容；留空則用已設定的預設開場白")
    purpose: str = "custom"


class VoiceScriptIn(BaseModel):
    script: str = Field(default="", description="外撥時逐字念出的預設開場白")


class VoiceScriptOut(BaseModel):
    script: str


class OutboundLeadCallIn(BaseModel):
    """對已同意的名單發起外撥。"""
    lead_id: int
    brief: Optional[str] = Field(default=None, description="逐字念出的內容；留空則用已設定的預設開場白")
    purpose: str = "lead_outreach"


class VoiceCallLogOut(BaseModel):
    id: int
    user_id: Optional[int]
    lead_id: Optional[int] = None
    direction: str
    to_number: str
    purpose: Optional[str]
    message: Optional[str]
    call_sid: Optional[str]
    status: Optional[str]
    consent_at_call: bool
    created_at: datetime

    class Config:
        from_attributes = True
