"""開發名單匯入與電話正規化。

重要：匯入只是把名單存進資料庫（一律 consent=false），
絕不等於可以外撥。要外撥必須對方先點同意連結、status 變 consented。
"""
from __future__ import annotations

import csv
import logging
import re
import secrets

from sqlalchemy.orm import Session

from ..models import Lead

logger = logging.getLogger(__name__)

# 各檔案可能的欄位名稱（大小寫/中英都涵蓋）
_NAME_KEYS = ("name", "公司名稱", "名稱", "店名")
_PHONE_KEYS = ("normalized_phone", "phone", "電話", "電話號碼", "tel", "mobile", "手機")
_CATEGORY_KEYS = ("category", "類別", "產業", "國家/地區", "攤位")


def normalize_phone(raw: str, default_region: str = "TW") -> tuple[str, bool]:
    """回傳 (E.164字串, 是否可信)。

    用 google libphonenumber 正確解析：能驗證為有效號碼才回傳 valid=True。
    對混合國別的名單尤其重要——避免把日本/印度本地號碼誤加上 +886。
    無法確定時回傳 (清理後原值, False)，預設不送邀請。"""
    if not raw:
        return "", False
    try:
        import phonenumbers

        num = phonenumbers.parse(raw, default_region)
        if phonenumbers.is_valid_number(num):
            return phonenumbers.format_number(
                num, phonenumbers.PhoneNumberFormat.E164
            ), True
        # 解析得出但無效 → 標記待確認，存可能的 E.164 供人工參考
        return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164), False
    except Exception:
        pass
    # 萬一解析失敗，退回最保守處理：只信任已帶國碼的（+ 或 00 開頭）
    s = re.sub(r"[\s\-().]", "", raw.strip())
    if s.startswith("+"):
        return "+" + re.sub(r"\D", "", s[1:]), False
    if s.startswith("00"):
        return "+" + re.sub(r"\D", "", s[2:]), False
    return re.sub(r"\D", "", s), False


def _pick(row: dict, keys) -> str:
    for k in keys:
        for actual in row:
            if actual and actual.strip().lower().lstrip("﻿") == k.lower():
                v = (row[actual] or "").strip()
                if v:
                    return v
    return ""


def import_reader(
    db: Session, reader: "csv.DictReader", source: str, default_region: str = "TW"
) -> dict:
    """從 csv.DictReader 匯入。回傳統計。重複電話（已存在）會略過。"""
    existing = {p for (p,) in db.query(Lead.phone).all()}
    added = skipped_dup = invalid = 0

    for row in reader:
        raw_phone = _pick(row, _PHONE_KEYS)
        if not raw_phone:
            continue
        phone, valid = normalize_phone(raw_phone, default_region)
        if not phone:
            continue
        if phone in existing:
            skipped_dup += 1
            continue
        existing.add(phone)
        if not valid:
            invalid += 1
        db.add(
            Lead(
                name=_pick(row, _NAME_KEYS),
                phone=phone,
                phone_valid=valid,
                category=_pick(row, _CATEGORY_KEYS),
                source=source,
                token=secrets.token_urlsafe(16),
                status="imported",
            )
        )
        added += 1
    db.commit()
    return {
        "source": source,
        "added": added,
        "skipped_duplicates": skipped_dup,
        "needs_review": invalid,  # 已匯入但號碼正規化不確定，預設不送邀請
    }


def import_csv(db: Session, path: str, source: str = "", default_region: str = "TW") -> dict:
    """從檔案路徑匯入 CSV。"""
    source = source or path.rsplit("/", 1)[-1]
    with open(path, newline="", encoding="utf-8-sig") as f:
        return import_reader(db, csv.DictReader(f), source, default_region)


def import_text(db: Session, text: str, source: str = "", default_region: str = "TW") -> dict:
    """從上傳的 CSV 文字內容匯入。"""
    import io

    return import_reader(db, csv.DictReader(io.StringIO(text)), source or "上傳", default_region)
