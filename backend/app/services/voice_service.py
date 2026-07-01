"""Twilio 語音電話的 AI 對話邏輯。

把使用者在電話中說的話交給 Claude，回傳「適合用語音念出來」的口語短答。
電話是多輪對話，但每次 webhook 都是獨立請求，因此用 CallSid 當 key
在記憶體裡保留對話歷史（Render 免費方案單一執行緒，夠用；多機部署需改 Redis）。
"""
from __future__ import annotations

import logging
import time
from collections import OrderedDict
from threading import Lock

from ..config import settings

logger = logging.getLogger(__name__)

# 口語化系統指令：強調「會被念出來」，所以不要 markdown、條列、網址、表情符號。
SYSTEM_VOICE = (
    "你是「林博台股 AI 投資助理」的電話語音客服，正在用電話和來電者對話。"
    "請用繁體中文、台灣口語、自然親切地回答台股與投資相關問題。"
    "因為你的回答會被語音念出來，請務必：不要用條列符號、不要用 markdown、"
    "不要念網址或表情符號；數字盡量口語化（例如「兩成」而非「20%」）。"
    "每次回答控制在三句話、約八十字以內，講重點即可。"
    "務必中立客觀、主動提醒投資風險，不做漲跌保證、不提供明牌。"
    "若問題與台股或投資無關，禮貌說明你只能協助投資相關問題。"
)

# CallSid -> {"history": [...], "ts": epoch}
_SESSIONS: "OrderedDict[str, dict]" = OrderedDict()
_LOCK = Lock()
_SESSION_TTL = 30 * 60          # 30 分鐘沒動就清掉
_MAX_SESSIONS = 500            # 上限，避免記憶體無限長
_MAX_TURNS = 12               # 每通電話最多保留的對話則數（user+assistant 合計）


def _prune(now: float) -> None:
    """清掉過期或超量的 session（呼叫前需持有 _LOCK）。"""
    expired = [sid for sid, s in _SESSIONS.items() if now - s["ts"] > _SESSION_TTL]
    for sid in expired:
        _SESSIONS.pop(sid, None)
    while len(_SESSIONS) > _MAX_SESSIONS:
        _SESSIONS.popitem(last=False)  # 丟掉最舊的


def reset(call_sid: str) -> None:
    with _LOCK:
        _SESSIONS.pop(call_sid, None)


# 使用者在電話中表達想退訂時的關鍵詞（命中即標記 opt-out）
_OPT_OUT_KEYWORDS = (
    "取消訂閱", "退訂", "不要再打", "不要再撥", "別再打", "別再撥",
    "停止來電", "不想接到", "拒絕來電", "退出", "unsubscribe", "stop",
)


def wants_opt_out(text: str) -> bool:
    t = (text or "").lower().replace(" ", "")
    return any(k.lower() in t for k in _OPT_OUT_KEYWORDS)


def compose_outbound_message(brief: str, name: str = "") -> str:
    """把一句重點 brief 轉成適合電話念出來的口語開場。

    沒有 AI 金鑰時直接回傳 brief（仍可正常外撥）。"""
    brief = (brief or "").strip()
    if not brief or not settings.ai_enabled:
        return brief

    greeting = f"{name}您好，" if name else "您好，"
    system = (
        "你要把一段投資提醒改寫成適合『電話語音念出來』的開場白。"
        "繁體中文、台灣口語、自然親切；不要 markdown、不要條列、不要念網址或表情符號；"
        "數字口語化；兩到三句、約六十字內；中立、提醒風險、不做漲跌保證。"
    )
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.anthropic_api_key)
        resp = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=400,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": f"稱呼開頭：「{greeting}」\n提醒重點：{brief}"}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        return text or brief
    except Exception as exc:  # noqa: BLE001
        logger.warning("外撥訊息改寫失敗，改用原文：%s", exc)
        return brief


def reply(call_sid: str, user_text: str) -> str:
    """回傳要念給來電者聽的一段話。"""
    user_text = (user_text or "").strip()
    if not user_text:
        return "不好意思，我沒聽清楚，可以再說一次嗎？"

    if not settings.ai_enabled:
        return (
            "目前系統還沒設定 AI 金鑰，暫時無法回答。"
            "您可以稍後再撥，或到我們的網站查詢台股分析。"
        )

    now = time.time()
    with _LOCK:
        _prune(now)
        sess = _SESSIONS.get(call_sid)
        if sess is None:
            sess = {"history": [], "ts": now}
            _SESSIONS[call_sid] = sess
        history = sess["history"]

    messages = history + [{"role": "user", "content": user_text}]

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.anthropic_api_key)
        resp = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=512,
            system=[
                {"type": "text", "text": SYSTEM_VOICE, "cache_control": {"type": "ephemeral"}},
            ],
            messages=messages,
        )
        answer = "".join(b.text for b in resp.content if b.type == "text").strip()
    except Exception as exc:  # noqa: BLE001 — 任何錯誤都不能讓電話掛掉
        logger.warning("語音 AI 回答失敗：%s", exc)
        return "不好意思，系統忙線中，請稍後再撥，謝謝。"

    if not answer:
        answer = "不好意思，我沒能整理出答案，您可以換個方式再問一次嗎？"

    # 寫回對話歷史，只保留最近幾輪
    with _LOCK:
        sess = _SESSIONS.get(call_sid)
        if sess is not None:
            sess["history"] = (messages + [{"role": "assistant", "content": answer}])[-_MAX_TURNS:]
            sess["ts"] = now

    return answer
