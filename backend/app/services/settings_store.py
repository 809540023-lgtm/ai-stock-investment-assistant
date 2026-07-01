"""簡單的 key-value 設定存取（存於 app_settings 表）。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import AppSetting

# 外撥時要逐字念出的預設開場白
OUTBOUND_SCRIPT_KEY = "outbound_script"


def get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    return (row.value or "") if row else default


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row is None:
        row = AppSetting(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    db.commit()
