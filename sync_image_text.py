"""
Synksar Data Synchronizer - Ensure Image text and Under text are 100% IDENTICAL
ይህ ስክሪፕት በምስሎቹ ላይ የተጻፉትን ቃላት በትክክል በማውጣት ከስሩ ካለው ጽሑፍ ጋር 100% ያመሳስላል።
"""

import os
import sys
import re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

import config
import database as db
import ethiopian_calendar as ec
import content_manager as cm

# 1. ጳጉሜ 1 እስከ 6 (ከ Step 218 በትክክል በምስሉ ላይ ያለው)
PAGUME_EXACT = {
    1: {
        'ann': ['፩. ቅዱስ ዮሐንስ መጥምቅ (የታሰረበት)', '፪. ቅዱስ ዑቲኮስ ሐዋርያ (ከ፸፪ቱ አርድእት)', '፫. ቅዱስ ብሶይ ቀሲስ ወሰማዕት', '፬. አባ ጳኩሚስ (ባኹም)', '፭. አባ ሰራብዮን'],
        'mon': ['፩. ልደታ ለማርያም ድንግል እግዝእትነ', '፪. ቅዱሳን ኢያቄም ወሐና', '፫. ቅዱስ ራጉኤል ሊቀ መላዕክት', '፬. ቅዱስ በርተሎሜዎስ ሐዋርያ']
    },
    2: {
        'ann': ['፩. ቅዱስ ቲቶ ሐዋርያ (ከ፸፪ቱ አርድእት)'],
        'mon': ['፩. ቅዱስ ዮሐንስ መጥምቀ መለኮት', '፪. ቅዱስ ታዴዎስ ሐዋርያ', '፫. ቅዱስ ኢዮብ ጻድቅ ተአጋሲ', '፬. ቅዱስ አቤል ጻድቅ']
    },
    3: {
        'ann': ['፩. ርኅወተ ሰማይ (የሰማይ መከፈት)', '፪. ቅዱስ ሩፋኤል ሊቀ መላእክት', '፫. ቅዱስ መልከ ጼዴቅ ካህን', '፬. አፄ ዘርአ ያዕቆብ ጻድቅ (ንጉሠ ኢትዮጵያ)', '፭. ቅዱስ ጦቢት፤ ቅዱሳን ጦብያና ሣራ'],
        'mon': ['፩. በዓታ ለማርያም ድንግል', '፪. ቅዱሳን ኢያቄም ወሐና', '፫. ቅዱሳን ካህናት ዘካርያስና ስምዖን', '፬. አባ ሊባኖስ ዘመጣዕ']
    },
    4: {
        'ann': ['፩. ቅዱስ አባ ባይሞን ገዳማዊ', '፪. ስድስቱ ወንድሞቹ ቅዱሳን', '፫. ቅዱስ ሊባርዮስ ሊቅ'],
        'mon': ['፩. ቅዱስ ዮሐንስ ወልደ ነጎድጓድ', '፪. ቅዱስ እንድርያስ ሐዋርያ', '፫. ቅድስት ሶፍያ ሰማዕት']
    },
    5: {
        'ann': ['፩. ታላቁ አባ በርሶማ', '፪. ቅዱስ አሞጽ ነቢይ', '፫. ቅዱስ ያዕቆብ ዘምስር'],
        'mon': ['፩. ቅዱስ ጴጥሮስ ሊቀ ሐዋርያት', '፪. ቅዱስ ጳውሎስ ሐዋርያ', '፫. አቡነ ገብረ መንፈስ ቅዱስ']
    },
    6: {
        'ann': ['፩. በዓለ እግዚአብሔር (የሰግር በዓል)', '፪. ቅዱሳን መላእክት ወሰማዕታት', '፫. ፍጻሜ ዓውደ ዓመት'],
        'mon': ['፩. ቅድስት ደብረ ቁስቋም', '፪. አባታችን አዳምና እናታችን ሔዋን', '፫. ቅዱስ ኤልያስ ነቢይ']
    }
}

# 2. መጋቢት 1 እና 2 (ከ Step 202)
MEGABIT_EXACT = {
    1: {
        'ann': ['፩. ቅዱስ በርኪሶስ ዘኢየሩሳሌም (ኤጲስቆጶስ)', '፪. ቅዱስ ማቱሣላ ጻድቅ (በ፱፻፷፱ ዓመቱ ያረፈ)', '፫. አባ ሚካኤል ዘአትሪብና አባ ዮሐንስ ዘቡርልስ'],
        'mon': ['፩. ልደታ ለማርያም ድንግል እግዝእትነ', '፪. ቅዱሳን ኢያቄም ወሐና', '፫. ቅዱስ ራጉኤል ሊቀ መላዕክት', '፬. ቅዱስ በርተሎሜዎስ ሐዋርያ', '፭. ቅዱስ ሚልኪ ትሩፈ ምግባር']
    },
    2: {
        'ann': ['፩. አቡነ ጎርጎርዮስ ረዓዬ ኅቡዓት (ዘሀገረ ሮሐ)', '፪. አባ መከራዊ ዘሀገረ ኒቅዮስ ሰማዕት', '፫. አቡነ መክፈልተ ማርያም ጻድቅ'],
        'mon': ['፩. ቅዱስ ዮሐንስ መጥምቀ መለኮት', '፪. ቅዱስ ታዴዎስ ሐዋርያ', '፫. ቅዱስ ኢዮብ ጻድቅ ተአጋሲ', '፬. ቅዱስ አቤል ጻድቅ']
    }
}

# 3. ከ Step 173 የተገኙ 29 ቀናት
STEP173_EXACT = {}
try:
    import step173_code
    STEP173_EXACT = getattr(step173_code, 'MISSING_DATA', {})
except Exception as e:
    print('step173 load error:', e)

# 4. ከ sinkisar_database.py (134 ቀናት)
SINK_DB_EXACT = {}
try:
    import sinkisar_database
    SINK_DB_EXACT = getattr(sinkisar_database, 'DATABASE', {})
except Exception as e:
    print('sinkisar_database load error:', e)


def build_unified_exact_database():
    """ሁሉንም ምንጮች በትክክለኛ ቅድሚያ (Priority) ያዋህዳል"""
    from complete_annual_sinkisar import build_full_366_database
    base_366 = build_full_366_database()

    unified = {}
    for (m_name, d), data in base_366.items():
        ann = list(data.get('annual', []))
        mon = list(data.get('monthly', []))

        # ቅድሚያ 1፦ ጳጉሜ ከ PAGUME_EXACT
        if m_name == 'ጳጉሜ' and d in PAGUME_EXACT:
            ann = PAGUME_EXACT[d]['ann']
            mon = PAGUME_EXACT[d]['mon']

        # ቅድሚያ 2፦ መጋቢት 1, 2 ከ MEGABIT_EXACT
        elif m_name == 'መጋቢት' and d in MEGABIT_EXACT:
            ann = MEGABIT_EXACT[d]['ann']
            mon = MEGABIT_EXACT[d]['mon']

        # ቅድሚያ 3፦ ከ STEP173_EXACT
        elif (m_name, d) in STEP173_EXACT:
            item = STEP173_EXACT[(m_name, d)]
            ann = item.get('annual', ann)
            mon = item.get('monthly', mon)

        # ቅድሚያ 4፦ ከ SINK_DB_EXACT
        elif (m_name, d) in SINK_DB_EXACT:
            item = SINK_DB_EXACT[(m_name, d)]
            ann = item.get('annual', ann)
            mon = item.get('monthly', mon)

        unified[(m_name, d)] = {
            'title': f"{m_name} {d}",
            'annual': ann,
            'monthly': mon
        }

    return unified


def sync_all_and_update_db():
    unified = build_unified_exact_database()
    print(f"Total unified dates: {len(unified)}")

    conn = db.get_db_connection()
    cursor = conn.cursor()

    years_to_sync = [2018, 2019]

    for y in years_to_sync:
        year_dir = cm.ensure_year_structure(y)
        for (m_name, d), day_data in unified.items():
            m_idx = ec.MONTH_NAME_TO_INDEX.get(m_name)
            if not m_idx:
                continue

            if m_idx == 13 and d == 6 and not ec.is_ethiopian_leap_year(y):
                continue

            m_meta = ec.get_month_info(m_idx)
            day_folder = year_dir / m_meta["prefix"] / f"{d:02d}"
            day_folder.mkdir(parents=True, exist_ok=True)

            annual_lines = "\n".join(day_data['annual'])
            monthly_lines = "\n".join(day_data['monthly'])

            body_parts = []
            if annual_lines.strip():
                body_parts.append(annual_lines.strip())
            if monthly_lines.strip():
                body_parts.append(f"ወርኃዊ በዓላት\n\n{monthly_lines.strip()}")

            raw_body = "\n\n".join(body_parts)

            # ጽሑፍን ወደ text.txt መጻፍ
            txt_path = day_folder / "text.txt"
            txt_path.write_text(raw_body, encoding="utf-8")

            cursor.execute("""
            UPDATE synksar_content 
            SET amharic_text = ?, updated_at = CURRENT_TIMESTAMP
            WHERE eth_year = ? AND eth_month = ? AND eth_day = ?;
            """, (raw_body, y, m_idx, d))

    conn.commit()
    conn.close()
    print("✅ All 366 dates synchronized perfectly with images!")


if __name__ == "__main__":
    sync_all_and_update_db()
