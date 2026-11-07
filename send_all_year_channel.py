"""
Synksar Auto Publisher - Send Full Year (366 Days) with Resume Support
ይህ ስክሪፕት ሙሉውን ዓመት (መስከረም 1 እስከ ጳጉሜ 6) በቅደም ተከተል
ካቆመበት የመቀጠል (Resume) ችሎታ፣ በ 1.2 ሰከንድ ማረፊያ እና በ 429 Rate Limit ጥበቃ ወደ ቴሌግራም ቻናል ይልካል።
"""

import os
import sys
import time
import json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

import config
import database as db
import ethiopian_calendar as ec
import formatter as fmt
import publisher as pub

PROGRESS_FILE = Path("sent_progress.json")
LOG_FILE = Path("send_all.log")


def load_sent_progress() -> set:
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(tuple(x) for x in data)
        except Exception:
            return set()
    return set()


def save_sent_progress(sent_set: set):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(sent_set), f)


def log_progress(msg: str):
    print(msg, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")


def send_entire_year(target_chat_id: str = None):
    chat_id = target_chat_id or config.CHANNEL_ID
    bot_token = config.BOT_TOKEN
    target_year = 2019

    sent_progress = load_sent_progress()

    log_progress("=" * 60)
    log_progress(f"🚀 የሙሉ ዓመት (366 ቀናት) ስንክሳር ወደ ቻናል {chat_id} መላክ ተጀምሯል...")
    log_progress(f"📌 ቀድመው የተላኩ ቀናት ብዛት፦ {len(sent_progress)}")
    log_progress("=" * 60)

    total_days = 366
    current_index = 0
    newly_sent = 0

    for month_meta in ec.ETHIOPIAN_MONTHS:
        m_idx = month_meta["index"]
        m_name = month_meta["amharic"]
        days_in_m = 6 if m_idx == 13 else 30

        for d in range(1, days_in_m + 1):
            current_index += 1
            date_key = (m_idx, d)
            date_label = f"{m_name} {d} ({ec.to_geez_number(d)})"

            # ቀድሞ ከተላከ መዝለል (Resume support)
            if date_key in sent_progress:
                log_progress(f"[{current_index}/{total_days}] ⏩ {date_label} ቀድሞ ስለተላከ ተዘልሏል።")
                continue

            # ይዘቱን ከዳታቤዝ ማውጣት
            content = db.get_content(target_year, m_idx, d)
            if not content:
                log_progress(f"[{current_index}/{total_days}] ⚠️ ይዘት አልተገኘም፦ {date_label}")
                continue

            amharic_body = content.get("amharic_text", "")
            image_path_str = content.get("image_path")
            title = content.get("title")

            full_caption = fmt.build_full_post_caption(
                month_name=m_name,
                day_num=d,
                amharic_body=amharic_body,
                title=title,
                use_html=True
            )

            image_path = Path(image_path_str) if image_path_str else None
            has_image = image_path and image_path.exists() and image_path.stat().st_size > 0

            max_retries = 5
            attempt = 0
            success = False

            while attempt < max_retries and not success:
                attempt += 1
                try:
                    if has_image:
                        if len(full_caption) <= 1024:
                            resp = pub.send_telegram_photo(
                                bot_token=bot_token,
                                chat_id=chat_id,
                                photo_path=image_path,
                                caption=full_caption,
                                parse_mode="HTML"
                            )
                        else:
                            header_brief = f"{config.OPENING_PRAYER}\n{m_name} {ec.to_geez_number(d)} ቀን የሚከበሩ ዓመታዊ እና ወርኃዊ በዓላት"
                            resp = pub.send_telegram_photo(
                                bot_token=bot_token,
                                chat_id=chat_id,
                                photo_path=image_path,
                                caption=header_brief[:1024],
                                parse_mode="HTML"
                            )
                            # ሁለተኛ ክፍል
                            chunks = fmt.split_text_for_telegram(full_caption, max_length=4000)
                            for chunk in chunks:
                                time.sleep(0.5)
                                pub.send_telegram_message(
                                    bot_token=bot_token,
                                    chat_id=chat_id,
                                    text=chunk,
                                    parse_mode="HTML"
                                )
                    else:
                        resp = pub.send_telegram_message(
                            bot_token=bot_token,
                            chat_id=chat_id,
                            text=full_caption[:4000],
                            parse_mode="HTML"
                        )

                    if resp.get("ok"):
                        msg_id = resp["result"]["message_id"]
                        log_progress(f"[{current_index}/{total_days}] ✅ {date_label} ተልኳል! (Msg ID: {msg_id})")
                        sent_progress.add(date_key)
                        save_sent_progress(sent_progress)
                        success = True
                        newly_sent += 1
                    else:
                        error_code = resp.get("error_code")
                        desc = resp.get("description", "")
                        if error_code == 429:
                            params = resp.get("parameters", {})
                            retry_after = params.get("retry_after", 10)
                            log_progress(f"⏳ Rate Limit (429)! {retry_after} ሰከንዶች በመጠበቅ ላይ...")
                            time.sleep(retry_after + 1)
                        else:
                            log_progress(f"[{current_index}/{total_days}] ❌ {date_label} አልተላከም፦ {desc}")
                            break
                except Exception as e:
                    log_progress(f"[{current_index}/{total_days}] ⚠️ ሙከራ {attempt} ስህተት፦ {e}")
                    time.sleep(3)

            # መደበኛ ማረፊያ
            time.sleep(1.2)

    log_progress("=" * 60)
    log_progress(f"🎉 መላክ ተጠናቋል! አጠቃላይ የተላኩ፦ {len(sent_progress)}/{total_days}")
    log_progress("=" * 60)


if __name__ == "__main__":
    send_entire_year()
