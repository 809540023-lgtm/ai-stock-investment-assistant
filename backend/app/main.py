import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import auth, dashboard, plans, reminders
from .scheduler import run_monthly_update, scheduler, start_scheduler

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="AI 投資助理平台 API", lifespan=lifespan)

# FRONTEND_ORIGIN 可用逗號分隔多個來源；另以 regex 放行 Render 靜態站台網域
_origins = [o.strip() for o in settings.frontend_origin.split(",") if o.strip()]
_origins += ["http://localhost:5173", "http://127.0.0.1:5173"]
allowed_origins = list(dict.fromkeys(_origins))  # 去重、保序

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(plans.router)
app.include_router(reminders.router)
app.include_router(dashboard.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "ai_enabled": settings.ai_enabled}


@app.post("/api/admin/run-monthly-update")
def trigger_monthly_update():
    """手動觸發每月更新（方便測試排程邏輯）。"""
    run_monthly_update()
    return {"ok": True}
