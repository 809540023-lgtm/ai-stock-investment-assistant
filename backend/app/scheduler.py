"""每月自動更新排程：對所有 active 計畫重新跑 AI 分析、寫提醒。"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from .database import SessionLocal
from .models import InvestmentPlan
from .services import plan_service

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone="Asia/Taipei")


def run_monthly_update():
    db = SessionLocal()
    try:
        plans = (
            db.query(InvestmentPlan)
            .filter(InvestmentPlan.status == "active")
            .all()
        )
        logger.info("每月更新：共 %d 個計畫", len(plans))
        for plan in plans:
            try:
                plan_service.run_analysis(db, plan, trigger="monthly")
            except Exception as exc:
                logger.warning("計畫 %d 更新失敗：%s", plan.id, exc)
    finally:
        db.close()


def start_scheduler():
    if scheduler.running:
        return
    # 每月 1 號早上 9 點（台北時間）執行
    scheduler.add_job(
        run_monthly_update,
        trigger="cron",
        day=1,
        hour=9,
        minute=0,
        id="monthly_update",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("排程已啟動：每月 1 號 09:00 自動更新")
