"""透過 Twilio REST API 發起 AI 語音外撥。

外撥流程：
  1. 由後端呼叫 place_call() → Twilio 撥打對方號碼
  2. 對方接起後，Twilio 會回來抓 {PUBLIC_BASE_URL}/api/voice/outbound?log_id=N 的 TwiML
  3. TwiML 念出訊息、告知退訂方式，並可接續問答（共用 inbound 的 /respond）
"""
from __future__ import annotations

import logging

from ..config import settings

logger = logging.getLogger(__name__)


class TelephonyError(Exception):
    pass


def _base_url() -> str:
    if not settings.public_base_url:
        raise TelephonyError("尚未設定 PUBLIC_BASE_URL，無法讓 Twilio 回呼取得 TwiML")
    return settings.public_base_url.rstrip("/")


def place_call(to_number: str, log_id: int) -> dict:
    """實際撥出電話，回傳 {sid, status}。失敗會丟 TelephonyError。"""
    if not settings.twilio_enabled:
        raise TelephonyError("尚未設定 Twilio 帳號（TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN）")
    if not settings.twilio_phone_number:
        raise TelephonyError("尚未設定 TWILIO_PHONE_NUMBER（撥出顯示號碼）")

    base = _base_url()
    try:
        from twilio.rest import Client

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        call = client.calls.create(
            to=to_number,
            from_=settings.twilio_phone_number,
            url=f"{base}/api/voice/outbound?log_id={log_id}",
            method="POST",
            status_callback=f"{base}/api/voice/status?log_id={log_id}",
            status_callback_event=["initiated", "ringing", "answered", "completed"],
            status_callback_method="POST",
        )
        return {"sid": call.sid, "status": call.status}
    except TelephonyError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("Twilio 外撥失敗：%s", exc)
        raise TelephonyError(f"Twilio 外撥失敗：{exc}") from exc
