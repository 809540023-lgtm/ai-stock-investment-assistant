"""把 CSV 名單匯入資料庫（一律未同意，需對方點同意連結才可外撥）。

用法：
    cd backend
    ./venv/bin/python -m scripts.import_leads <csv路徑> [來源標籤] [國別預設,如 TW]

例：
    ./venv/bin/python -m scripts.import_leads ~/Desktop/taishan-0-1km-clean.csv 泰山名單 TW
"""
import sys

from app.database import Base, SessionLocal, engine, ensure_schema
from app.services import leads


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = sys.argv[1]
    source = sys.argv[2] if len(sys.argv) > 2 else ""
    region = sys.argv[3] if len(sys.argv) > 3 else "TW"

    Base.metadata.create_all(bind=engine)
    ensure_schema()
    db = SessionLocal()
    try:
        result = leads.import_csv(db, path, source=source, default_region=region)
    finally:
        db.close()
    print("匯入完成：")
    for k, v in result.items():
        print(f"  {k}: {v}")
    print("\n提醒：名單已全部設為『未同意』。請用 /api/leads/invites.csv 匯出同意連結，")
    print("透過合法管道寄送邀請；對方點同意後才會進入可外撥狀態。")


if __name__ == "__main__":
    main()
