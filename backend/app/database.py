from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

# Render / Heroku 提供的連線字串開頭是 postgres://，SQLAlchemy 2.0 需要 postgresql://
db_url = settings.database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

is_sqlite = db_url.startswith("sqlite")

engine = create_engine(
    db_url,
    connect_args={"check_same_thread": False} if is_sqlite else {},
    # PostgreSQL：連線前先 ping，避免雲端閒置斷線後拿到失效連線
    pool_pre_ping=not is_sqlite,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# create_all 只會建「缺少的資料表」，不會幫既有資料表補欄位。
# 這裡用輕量、可重複執行的 ALTER 把新欄位補上（SQLite 與 PostgreSQL 皆適用）。
_NEW_COLUMNS: dict[str, dict[str, str]] = {
    "users": {
        "is_admin": "BOOLEAN DEFAULT FALSE",
        "phone_number": "VARCHAR",
        "voice_consent": "BOOLEAN DEFAULT FALSE",
        "voice_consent_at": "TIMESTAMP",
        "voice_opt_out": "BOOLEAN DEFAULT FALSE",
    },
    "voice_call_logs": {
        "lead_id": "INTEGER",
    },
}


def ensure_schema() -> None:
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, columns in _NEW_COLUMNS.items():
            if table not in tables:
                continue  # 全新表由 create_all 直接建好完整結構
            existing = {c["name"] for c in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
