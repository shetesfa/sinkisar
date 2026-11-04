"""
Synksar Auto Publisher - Database Module (SQLite)
ይህ ሞጁል የስንክሳር ይዘቶችን፣ የህትመት ታሪክን እና የስርዓት ቅንብሮችን በ SQLite ያከማቻል።
"""

import sqlite3
import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
import config

DB_PATH = Path(config.DB_PATH)


def get_db_connection() -> sqlite3.Connection:
    """የዳታቤዝ ግንኙነት ይፈጥራል (row_factory = sqlite3.Row)"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """የዳታቤዝ ሠንጠረዦችን ይፈጥራል"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. የስንክሳር ይዘቶች ሠንጠረዥ
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS synksar_content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        eth_year INTEGER NOT NULL,
        eth_month INTEGER NOT NULL,
        eth_day INTEGER NOT NULL,
        title TEXT,
        amharic_text TEXT NOT NULL,
        image_path TEXT,
        status TEXT DEFAULT 'ready',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(eth_year, eth_month, eth_day)
    );
    """)

    # 2. የህትመት ታሪክ መዝገብ
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS publication_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        eth_year INTEGER NOT NULL,
        eth_month INTEGER NOT NULL,
        eth_day INTEGER NOT NULL,
        published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT NOT NULL,
        message_id INTEGER,
        caption_truncated INTEGER DEFAULT 0,
        error_message TEXT
    );
    """)

    # 3. የስርዓት ቅንብሮች
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)

    # ኢንዴክሶች ለፈጣን ፍለጋ
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_ymd ON synksar_content(eth_year, eth_month, eth_day);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_ymd ON publication_logs(eth_year, eth_month, eth_day);")

    # ነባሪ ቅንብሮች
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('is_paused', '0');")
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('auto_publish_enabled', '1');")

    conn.commit()
    conn.close()


def upsert_content(
    eth_year: int,
    eth_month: int,
    eth_day: int,
    amharic_text: str,
    image_path: Optional[str] = None,
    title: Optional[str] = None,
    status: str = "ready"
) -> int:
    """የቀኑን ይዘት ያስቀምጣል ወይም ካለ ያሻሽላል"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO synksar_content (
        eth_year, eth_month, eth_day, title, amharic_text, image_path, status, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(eth_year, eth_month, eth_day) DO UPDATE SET
        title = COALESCE(excluded.title, synksar_content.title),
        amharic_text = excluded.amharic_text,
        image_path = COALESCE(excluded.image_path, synksar_content.image_path),
        status = excluded.status,
        updated_at = CURRENT_TIMESTAMP;
    """, (eth_year, eth_month, eth_day, title, amharic_text, image_path, status))
    conn.commit()
    content_id = cursor.lastrowid
    conn.close()
    return content_id


def get_content(eth_year: int, eth_month: int, eth_day: int) -> Optional[Dict[str, Any]]:
    """የተወሰነ ቀን ይዘት ያወጣል (በተሰጠው ዓመት ወይም በሌላ ዓመት ካለ ያወጣል)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    # በመጀመሪያ በተሰጠው ዓመት ይፈልጋል፤ ካልተገኘ ግን ለዚያ ወርና ቀን የተመዘገበውን ያመጣል
    cursor.execute("""
    SELECT * FROM synksar_content 
    WHERE eth_month = ? AND eth_day = ?
    ORDER BY (eth_year = ?) DESC, id DESC
    LIMIT 1;
    """, (eth_month, eth_day, eth_year))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_contents(eth_year: int) -> List[Dict[str, Any]]:
    """የአንድ ዓመት ሙሉ ይዘቶችን በቅደም ተከተል ያወጣል"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM synksar_content 
    WHERE eth_year = ? 
    ORDER BY eth_month ASC, eth_day ASC;
    """, (eth_year,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_publication(
    eth_year: int,
    eth_month: int,
    eth_day: int,
    status: str,
    message_id: Optional[int] = None,
    caption_truncated: bool = False,
    error_message: Optional[str] = None
) -> int:
    """የህትመት ውጤቱን ይመዘግባል"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO publication_logs (
        eth_year, eth_month, eth_day, status, message_id, caption_truncated, error_message
    ) VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (eth_year, eth_month, eth_day, status, message_id, 1 if caption_truncated else 0, error_message))
    conn.commit()
    log_id = cursor.lastrowid
    conn.close()
    return log_id


def is_already_published_today(eth_year: int, eth_month: int, eth_day: int) -> bool:
    """ይህ ቀን ዛሬ ቀድሞ በተሳካ ሁኔታ መታተሙን ያረጋግጣል (ድጋሚ ህትመትን ለመከላከል)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id FROM publication_logs 
    WHERE eth_year = ? AND eth_month = ? AND eth_day = ? AND status = 'success'
    LIMIT 1;
    """, (eth_year, eth_month, eth_day))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def get_publication_history(limit: int = 50) -> List[Dict[str, Any]]:
    """የህትመት ታሪክን ያወጣል"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM publication_logs 
    ORDER BY published_at DESC 
    LIMIT ?;
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """የስርዓት ቅንብር ያወጣል"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM system_settings WHERE key = ?;", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    """የስርዓት ቅንብር ያስቀምጣል"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO system_settings (key, value) VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value;
    """, (key, str(value)))
    conn.commit()
    conn.close()


def is_paused() -> bool:
    """ህትመት መቆሙን ያረጋግጣል"""
    return get_setting("is_paused", "0") == "1"


def set_paused(paused: bool):
    """ህትመትን ያቆማል ወይም ያስጀምራል"""
    set_setting("is_paused", "1" if paused else "0")


def get_stats(eth_year: int) -> Dict[str, Any]:
    """የይዘት እና የህትመት አጠቃላይ ስታቲስቲክስ ያሰላል"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM synksar_content WHERE eth_year = ?;", (eth_year,))
    total_contents = cursor.fetchone()["total"]
    
    cursor.execute("""
    SELECT COUNT(*) as with_img FROM synksar_content 
    WHERE eth_year = ? AND image_path IS NOT NULL AND image_path != '';
    """, (eth_year,))
    with_image = cursor.fetchone()["with_img"]
    
    cursor.execute("""
    SELECT COUNT(*) as with_txt FROM synksar_content 
    WHERE eth_year = ? AND amharic_text IS NOT NULL AND length(trim(amharic_text)) > 0;
    """, (eth_year,))
    with_text = cursor.fetchone()["with_txt"]

    cursor.execute("""
    SELECT COUNT(DISTINCT eth_month || '-' || eth_day) as pub_count 
    FROM publication_logs 
    WHERE eth_year = ? AND status = 'success';
    """, (eth_year,))
    published_count = cursor.fetchone()["pub_count"]

    conn.close()

    from ethiopian_calendar import days_in_ethiopian_year
    expected_days = days_in_ethiopian_year(eth_year)

    return {
        "year": eth_year,
        "expected_days": expected_days,
        "total_records": total_contents,
        "with_image": with_image,
        "with_text": with_text,
        "missing_days": max(0, expected_days - total_contents),
        "missing_images": max(0, total_contents - with_image),
        "missing_texts": max(0, total_contents - with_text),
        "published_count": published_count,
        "is_paused": is_paused(),
    }


# ሲጠራ በራስ-ሰር ዳታቤዙን ያዘጋጃል
init_db()
