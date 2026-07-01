"""開發名單與 opt-in 同意管道。

合規重點：匯入的名單一律未同意；只有對方主動點專屬連結並按下同意，
status 才會變 consented，之後才可進入語音外撥系統。
"""
from __future__ import annotations

import io
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import get_current_admin
from ..config import settings
from ..database import get_db
from ..models import Lead, User
from ..services import leads as leads_service

router = APIRouter(tags=["leads"])

BRAND = "林博台股 AI 投資助理"


def _page(title: str, body: str) -> HTMLResponse:
    html = f"""<!doctype html><html lang="zh-Hant"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
 body{{font-family:-apple-system,"PingFang TC","Microsoft JhengHei",sans-serif;
   background:#0f172a;color:#e2e8f0;margin:0;display:flex;min-height:100vh;
   align-items:center;justify-content:center;padding:24px}}
 .card{{background:#1e293b;border-radius:16px;padding:32px;max-width:440px;width:100%;
   box-shadow:0 10px 40px rgba(0,0,0,.4)}}
 h1{{font-size:20px;margin:0 0 8px}} p{{line-height:1.7;color:#cbd5e1;font-size:15px}}
 .muted{{color:#94a3b8;font-size:13px}}
 button{{font-size:16px;padding:12px 20px;border:0;border-radius:10px;cursor:pointer;width:100%;margin-top:10px}}
 .agree{{background:#22c55e;color:#04210f;font-weight:700}}
 .decline{{background:transparent;color:#94a3b8;border:1px solid #475569}}
 .ok{{color:#22c55e;font-weight:700}}
</style></head><body><div class="card">{body}</div></body></html>"""
    return HTMLResponse(html)


@router.get("/invite/{token}", response_class=HTMLResponse)
def invite_page(token: str, db: Session = Depends(get_db)):
    """對方收到的專屬同意頁。"""
    lead = db.query(Lead).filter(Lead.token == token).first()
    if not lead:
        return _page("連結無效", "<h1>連結無效</h1><p>這個連結找不到對應資料，可能已失效。</p>")
    if lead.do_not_contact:
        return _page("已取消", "<h1>您已取消接收</h1><p>我們不會再與您聯繫。</p>")
    if lead.consent:
        return _page(
            "已同意",
            f"<h1 class='ok'>已完成同意 ✓</h1><p>{BRAND} 之後可能會以電話提供您台股相關資訊。"
            f"您隨時可在通話中說「取消訂閱」或點本頁下方退出。</p>"
            f"<form method='post' action='/invite/{token}/decline'>"
            f"<button class='decline'>我要取消接收</button></form>",
        )
    greeting = f"{lead.name}　您好，" if lead.name else "您好，"
    body = (
        f"<h1>{BRAND}</h1>"
        f"<p>{greeting}我們提供台股投資分析與盤後重點提醒。"
        f"若您同意，我們未來可能以 <b>AI 語音電話</b> 提供您相關資訊。</p>"
        f"<p class='muted'>‧ 內容僅供參考，非投資建議。<br>"
        f"‧ 您隨時可取消，通話中說「取消訂閱」即可。<br>"
        f"‧ 我們只會用於提供投資資訊，不會轉作他用。</p>"
        f"<form method='post' action='/invite/{token}/consent'>"
        f"<button class='agree'>我同意接收 AI 語音來電</button></form>"
        f"<form method='post' action='/invite/{token}/decline'>"
        f"<button class='decline'>不需要，謝謝</button></form>"
    )
    return _page("邀請同意", body)


@router.post("/invite/{token}/consent", response_class=HTMLResponse)
async def invite_consent(token: str, request: Request, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.token == token).first()
    if not lead:
        return _page("連結無效", "<h1>連結無效</h1>")
    if lead.do_not_contact:
        return _page("已取消", "<h1>您先前已取消</h1><p>如需重新接收請與我們聯繫。</p>")
    lead.consent = True
    lead.consent_at = datetime.utcnow()
    lead.consent_ip = request.client.host if request.client else None
    lead.status = "consented"
    db.commit()
    return _page(
        "感謝同意",
        f"<h1 class='ok'>感謝您的同意 ✓</h1><p>{BRAND} 之後會以電話提供您台股資訊。"
        f"您隨時可取消。</p>",
    )


@router.post("/invite/{token}/decline", response_class=HTMLResponse)
def invite_decline(token: str, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.token == token).first()
    if not lead:
        return _page("連結無效", "<h1>連結無效</h1>")
    lead.consent = False
    lead.do_not_contact = True
    lead.status = "do_not_contact"
    db.commit()
    return _page("已取消", "<h1 class='ok'>已為您取消</h1><p>我們不會再與您聯繫，謝謝。</p>")


# ---------------- 管理端（需登入）----------------
@router.post("/api/leads/import")
async def import_leads_upload(
    file: UploadFile = File(...),
    source: str = Form(""),
    region: str = Form("TW"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    """上傳 CSV 匯入名單（一律未同意）。region 為電話國別預設（TW/JP…）。"""
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("big5")  # 容錯：常見的台灣 CSV 編碼
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="無法解析檔案編碼，請存成 UTF-8 CSV")
    result = leads_service.import_text(
        db, text, source=source or file.filename or "上傳", default_region=region
    )
    return result


@router.get("/api/leads/stats")
def leads_stats(db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    rows = db.query(Lead.status, func.count(Lead.id)).group_by(Lead.status).all()
    by_status = {s: c for s, c in rows}
    total = db.query(func.count(Lead.id)).scalar() or 0
    return {
        "total": total,
        "by_status": by_status,
        "consented": db.query(func.count(Lead.id)).filter(Lead.consent.is_(True)).scalar() or 0,
        "needs_review": db.query(func.count(Lead.id)).filter(Lead.phone_valid.is_(False)).scalar() or 0,
    }


@router.get("/api/leads")
def list_leads(
    status: str = "",
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    q = db.query(Lead)
    if status:
        q = q.filter(Lead.status == status)
    leads = q.order_by(Lead.created_at.desc()).limit(min(limit, 1000)).all()
    return [
        {
            "id": l.id,
            "name": l.name,
            "phone": l.phone,
            "phone_valid": l.phone_valid,
            "category": l.category,
            "status": l.status,
            "consent": l.consent,
            "invite_url": _invite_url(l.token),
        }
        for l in leads
    ]


@router.get("/api/leads/invites.csv", response_class=PlainTextResponse)
def export_invites(
    only_valid: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    """匯出 電話 + 專屬同意連結，方便你用任何合法管道（簡訊/Email/QR）寄送邀請。"""
    q = db.query(Lead).filter(Lead.status == "imported", Lead.do_not_contact.is_(False))
    if only_valid:
        q = q.filter(Lead.phone_valid.is_(True))
    buf = io.StringIO()
    buf.write("name,phone,invite_url\n")
    for l in q.all():
        name = (l.name or "").replace('"', "'")
        buf.write(f'"{name}",{l.phone},{_invite_url(l.token)}\n')
    return PlainTextResponse(buf.getvalue(), media_type="text/csv")


def _invite_url(token: str) -> str:
    base = settings.public_base_url.rstrip("/") if settings.public_base_url else ""
    return f"{base}/invite/{token}"
