"""Twilio 語音電話 webhook（inbound AI 客服）。

設定方式：在 Twilio Console 把這支電話號碼的「A CALL COMES IN」
指向 POST {你的後端網址}/api/voice/incoming
詳見專案根目錄的 TWILIO_SETUP.md。
"""
from __future__ import annotations

import logging

from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from sqlalchemy.orm import Session
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import Gather, VoiceResponse

from .. import schemas
from ..auth import get_current_admin, get_current_user
from ..config import settings
from ..database import get_db
from ..models import Lead, User, VoiceCallLog
from ..services import settings_store, telephony, voice_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])

# 台灣國語：辨識用 cmn-Hant-TW，語音合成用 Google 台灣國語女聲
SPEECH_LANGUAGE = "cmn-Hant-TW"
TTS_LANGUAGE = "cmn-TW"
TTS_VOICE = "Google.cmn-TW-Standard-A"

GREETING = "您好，這裡是林博台股 AI 投資助理。請問有什麼台股或投資問題，可以直接說出來。"
REPROMPT = "不好意思，我沒有聽到聲音。請問有什麼台股問題嗎？"
GOODBYE = "感謝您的來電，祝您投資順利，再見。"
MAX_SILENCE = 2  # 連續沒聽到聲音幾次後，禮貌掛斷


def _twiml(resp: VoiceResponse) -> Response:
    return Response(content=str(resp), media_type="application/xml")


def _full_url(request: Request) -> str:
    """組出 Twilio 實際打過來的完整網址，供簽章驗證使用。

    Render 之類的反向代理會讓 request.url 變成 http，導致簽章對不上，
    因此優先用設定的 public_base_url。"""
    if settings.public_base_url:
        base = settings.public_base_url.rstrip("/")
        url = base + request.url.path
        if request.url.query:
            url += "?" + request.url.query
        return url
    return str(request.url)


async def _verify(request: Request) -> bool:
    """驗證 X-Twilio-Signature。設定關閉或缺 token 時直接放行（本機測試用）。"""
    if not settings.twilio_validate_signature:
        return True
    if not settings.twilio_auth_token:
        logger.warning("未設定 twilio_auth_token，略過簽章驗證")
        return True
    signature = request.headers.get("X-Twilio-Signature", "")
    form = await request.form()
    params = {k: v for k, v in form.items()}
    validator = RequestValidator(settings.twilio_auth_token)
    ok = validator.validate(_full_url(request), params, signature)
    if not ok:
        logger.warning("Twilio 簽章驗證失敗：%s", request.url.path)
    return ok


def _gather(action: str) -> Gather:
    """建立一段收音設定：邊念提示邊聽，使用者開口就會送出。"""
    return Gather(
        input="speech",
        action=action,
        method="POST",
        language=SPEECH_LANGUAGE,
        speech_timeout="auto",
        speech_model="phone_call",
        action_on_empty_result=True,  # 沒講話也回呼 action，由我們決定重問或掛斷
    )


@router.post("/incoming")
async def incoming(request: Request):
    """來電進線：問候 + 開始收音。"""
    resp = VoiceResponse()
    if not await _verify(request):
        resp.reject()
        return _twiml(resp)

    gather = _gather("/api/voice/respond")
    gather.say(GREETING, language=TTS_LANGUAGE, voice=TTS_VOICE)
    resp.append(gather)
    # 萬一 Gather 整段沒觸發 action（極少數情況），給個結尾避免靜默掛斷
    resp.redirect("/api/voice/respond", method="POST")
    return _twiml(resp)


@router.post("/respond")
async def respond(
    request: Request,
    CallSid: str = Form(default=""),
    SpeechResult: str = Form(default=""),
    silence: int = 0,
):
    """收到使用者語音轉文字後，交給 AI 回答，並繼續下一輪對話。"""
    resp = VoiceResponse()
    if not await _verify(request):
        resp.reject()
        return _twiml(resp)

    speech = (SpeechResult or "").strip()

    # 沒聽到聲音：重問幾次後禮貌掛斷
    if not speech:
        if silence >= MAX_SILENCE:
            resp.say(GOODBYE, language=TTS_LANGUAGE, voice=TTS_VOICE)
            voice_service.reset(CallSid)
            resp.hangup()
            return _twiml(resp)
        gather = _gather(f"/api/voice/respond?silence={silence + 1}")
        gather.say(REPROMPT, language=TTS_LANGUAGE, voice=TTS_VOICE)
        resp.append(gather)
        resp.redirect(f"/api/voice/respond?silence={silence + 1}", method="POST")
        return _twiml(resp)

    # 來電者表示要退訂 → 立即記錄並掛斷（合規）
    if voice_service.wants_opt_out(speech):
        _opt_out_by_call(CallSid)
        resp.say(
            "好的，已經幫您取消後續的語音來電，不會再打擾您。感謝您的來電，再見。",
            language=TTS_LANGUAGE,
            voice=TTS_VOICE,
        )
        voice_service.reset(CallSid)
        resp.hangup()
        return _twiml(resp)

    answer = voice_service.reply(CallSid, speech)

    # 念出答案後，繼續收下一個問題（silence 計數歸零）
    gather = _gather("/api/voice/respond")
    gather.say(answer, language=TTS_LANGUAGE, voice=TTS_VOICE)
    gather.pause(length=1)
    gather.say("還有其他問題嗎？", language=TTS_LANGUAGE, voice=TTS_VOICE)
    resp.append(gather)
    resp.redirect("/api/voice/respond?silence=1", method="POST")
    return _twiml(resp)


# =====================================================================
# 通話內容（外撥逐字念出的預設開場白）
# =====================================================================
@router.get("/script", response_model=schemas.VoiceScriptOut)
def get_script(db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    return {"script": settings_store.get_setting(db, settings_store.OUTBOUND_SCRIPT_KEY)}


@router.put("/script", response_model=schemas.VoiceScriptOut)
def set_script(
    body: schemas.VoiceScriptIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    settings_store.set_setting(db, settings_store.OUTBOUND_SCRIPT_KEY, body.script.strip())
    return {"script": settings_store.get_setting(db, settings_store.OUTBOUND_SCRIPT_KEY)}


# =====================================================================
# 同意管理（會員自行設定電話與同意狀態）
# =====================================================================
@router.get("/consent", response_model=schemas.VoiceConsentOut)
def get_consent(user: User = Depends(get_current_user)):
    return user


@router.post("/consent", response_model=schemas.VoiceConsentOut)
def set_consent(
    body: schemas.VoiceConsentIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """會員留電話並同意接收 AI 語音外撥。同意會記錄時間作為合規佐證。"""
    user.phone_number = body.phone_number.strip()
    user.voice_consent = body.consent
    user.voice_consent_at = datetime.utcnow() if body.consent else None
    if body.consent:
        user.voice_opt_out = False  # 重新同意即解除退訂
    db.commit()
    db.refresh(user)
    return user


@router.post("/opt-out", response_model=schemas.VoiceConsentOut)
def opt_out(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """會員退訂語音外撥。"""
    user.voice_opt_out = True
    user.voice_consent = False
    db.commit()
    db.refresh(user)
    return user


@router.get("/calls", response_model=list[schemas.VoiceCallLogOut])
def list_calls(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    # 管理員可檢視所有外撥紀錄（含名單與會員）
    return (
        db.query(VoiceCallLog)
        .order_by(VoiceCallLog.created_at.desc())
        .all()
    )


def _opt_out_by_call(call_sid: str) -> None:
    """來電者在電話中說退訂時，依 CallSid 找出對應使用者並標記退訂。"""
    if not call_sid:
        return
    db = next(get_db())
    try:
        log = (
            db.query(VoiceCallLog)
            .filter(VoiceCallLog.call_sid == call_sid)
            .order_by(VoiceCallLog.created_at.desc())
            .first()
        )
        if log and log.user_id:
            u = db.query(User).filter(User.id == log.user_id).first()
            if u:
                u.voice_opt_out = True
                u.voice_consent = False
        if log and log.lead_id:
            ld = db.query(Lead).filter(Lead.id == log.lead_id).first()
            if ld:
                ld.do_not_contact = True
                ld.consent = False
                ld.status = "do_not_contact"
        if log:
            log.detail = (log.detail or "") + " [來電者語音退訂]"
        db.commit()
    finally:
        db.close()


# =====================================================================
# 外撥：發起 + Twilio 回呼取 TwiML + 狀態回報
# =====================================================================
@router.post("/outbound-call", response_model=schemas.VoiceCallLogOut)
def trigger_outbound(
    body: schemas.OutboundCallIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    """對某位會員發起 AI 語音外撥（須對方已同意且未退訂）。"""
    target = user
    if body.user_id and body.user_id != user.id:
        target = db.query(User).filter(User.id == body.user_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="找不到該會員")

    if not target.phone_number:
        raise HTTPException(status_code=400, detail="該會員尚未提供電話號碼")
    if target.voice_opt_out:
        raise HTTPException(status_code=409, detail="該會員已退訂語音外撥，不可外撥")
    if not target.voice_consent:
        raise HTTPException(status_code=409, detail="該會員尚未同意語音外撥，不可外撥")

    # 逐字念出已設定的預設開場白（不經 AI 改寫）；未設定則擋下
    message = (body.brief or settings_store.get_setting(db, settings_store.OUTBOUND_SCRIPT_KEY)).strip()
    if not message:
        raise HTTPException(status_code=400, detail="尚未設定通話內容，請先到「通話內容」設定開場白")

    log = VoiceCallLog(
        user_id=target.id,
        direction="outbound",
        to_number=target.phone_number,
        from_number=settings.twilio_phone_number,
        purpose=body.purpose,
        message=message,
        status="queued",
        consent_at_call=bool(target.voice_consent and not target.voice_opt_out),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    try:
        result = telephony.place_call(target.phone_number, log.id)
    except telephony.TelephonyError as exc:
        log.status = "failed"
        log.detail = str(exc)
        db.commit()
        db.refresh(log)
        raise HTTPException(status_code=502, detail=str(exc))

    log.call_sid = result["sid"]
    log.status = result["status"]
    db.commit()
    db.refresh(log)
    return log


@router.post("/outbound-call-lead", response_model=schemas.VoiceCallLogOut)
def trigger_outbound_lead(
    body: schemas.OutboundLeadCallIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    """對已同意的名單（Lead）發起 AI 語音外撥。"""
    lead = db.query(Lead).filter(Lead.id == body.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="找不到該名單")
    if lead.do_not_contact:
        raise HTTPException(status_code=409, detail="該名單已退出，不可外撥")
    if not lead.consent:
        raise HTTPException(status_code=409, detail="該名單尚未同意，不可外撥（請先讓對方點同意連結）")
    if not lead.phone_valid:
        raise HTTPException(status_code=400, detail="該名單電話未確認，請先人工確認號碼")

    # 逐字念出已設定的預設開場白（不經 AI 改寫）；未設定則擋下
    message = (body.brief or settings_store.get_setting(db, settings_store.OUTBOUND_SCRIPT_KEY)).strip()
    if not message:
        raise HTTPException(status_code=400, detail="尚未設定通話內容，請先到「通話內容」設定開場白")
    log = VoiceCallLog(
        lead_id=lead.id,
        direction="outbound",
        to_number=lead.phone,
        from_number=settings.twilio_phone_number,
        purpose=body.purpose,
        message=message,
        status="queued",
        consent_at_call=bool(lead.consent and not lead.do_not_contact),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    try:
        result = telephony.place_call(lead.phone, log.id)
    except telephony.TelephonyError as exc:
        log.status = "failed"
        log.detail = str(exc)
        db.commit()
        db.refresh(log)
        raise HTTPException(status_code=502, detail=str(exc))

    log.call_sid = result["sid"]
    log.status = result["status"]
    db.commit()
    db.refresh(log)
    return log


@router.post("/outbound")
async def outbound(request: Request, log_id: int = 0):
    """對方接起後 Twilio 來抓的 TwiML：念出訊息 + 退訂說明 + 接續問答。"""
    resp = VoiceResponse()
    if not await _verify(request):
        resp.reject()
        return _twiml(resp)

    db = next(get_db())
    try:
        log = db.query(VoiceCallLog).filter(VoiceCallLog.id == log_id).first()
    finally:
        db.close()

    message = (log.message if log else "") or "您好，這是林博台股 AI 投資助理的來電。"

    resp.say(message, language=TTS_LANGUAGE, voice=TTS_VOICE)
    resp.pause(length=1)
    notice = "如果您不想再接到這類來電，隨時說「取消訂閱」就可以。"
    gather = _gather("/api/voice/respond")
    gather.say(notice + "另外，有任何台股問題也都可以直接問我。", language=TTS_LANGUAGE, voice=TTS_VOICE)
    resp.append(gather)
    resp.redirect("/api/voice/respond?silence=1", method="POST")
    return _twiml(resp)


@router.post("/status")
async def status_callback(
    request: Request,
    log_id: int = 0,
    CallStatus: str = Form(default=""),
    CallSid: str = Form(default=""),
):
    """Twilio 回報通話狀態，更新外撥紀錄。"""
    if not await _verify(request):
        return Response(status_code=403)
    db = next(get_db())
    try:
        log = db.query(VoiceCallLog).filter(VoiceCallLog.id == log_id).first()
        if log:
            if CallStatus:
                log.status = CallStatus
            if CallSid and not log.call_sid:
                log.call_sid = CallSid
            db.commit()
    finally:
        db.close()
    return Response(status_code=204)
