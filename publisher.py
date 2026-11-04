"""
Synksar Auto Publisher - Telegram Publisher Module
ይህ ሞጁል የስንክሳር ምስልና ጽሑፍን ወደ ቴሌግራም ቻናል በቀጥታ ያትማል።
የካፕሽን ገደብ (1024 ፊደላት)፣ ድጋሚ ህትመት ጥበቃ፣ እና የውጤት ምዝገባን ያካትታል።
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import requests

import config
import database as db
import ethiopian_calendar as ec
from formatter import build_full_post_caption, split_text_for_telegram


def send_telegram_photo(
    bot_token: str,
    chat_id: str,
    photo_path: Path,
    caption: str = "",
    parse_mode: Optional[str] = None
) -> Dict[str, Any]:
    """ምስልን ወደ ቴሌግራም በ requests ይልካል"""
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    data = {
        "chat_id": chat_id,
        "caption": caption
    }
    if parse_mode:
        data["parse_mode"] = parse_mode

    with open(photo_path, "rb") as photo_file:
        files = {"photo": photo_file}
        resp = requests.post(url, data=data, files=files, timeout=60)
        return resp.json()


def send_telegram_message(
    bot_token: str,
    chat_id: str,
    text: str,
    parse_mode: Optional[str] = None
) -> Dict[str, Any]:
    """ጽሑፍን ወደ ቴሌግራም በ requests ይልካል"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text
    }
    if parse_mode:
        data["parse_mode"] = parse_mode

    resp = requests.post(url, data=data, timeout=30)
    return resp.json()


def publish_synksar_for_date(
    eth_year: int,
    eth_month: int,
    eth_day: int,
    force: bool = False,
    custom_chat_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    የተሰጠውን የኢትዮጵያ ቀን ስንክሳር ወደ ቴሌግራም ቻናል ያትማል።
    - force=False ከሆነና ቀድሞ ከታተመ ህትመቱ ይዘለላል።
    - ስኬትን ወይም ውድቀትን በዳታቤዝ ውስጥ ይመዘግባል።
    """
    chat_id = custom_chat_id or config.CHANNEL_ID
    bot_token = config.BOT_TOKEN

    month_info = ec.get_month_info(eth_month)
    month_name = month_info["amharic"]
    date_label = f"{month_name} {eth_day}"

    # 1. ቦት ቶከን መኖሩን ማረጋገጥ
    if not bot_token:
        err = "የቦት ቶከን (BOT_TOKEN) አልተሞላም! እባክዎ በ .env ውስጥ ያስገቡ።"
        db.log_publication(eth_year, eth_month, eth_day, status="failed", error_message=err)
        return {"success": False, "status": "failed", "error": err}

    # 2. ህትመት መቆሙን ማረጋገጥ (force ካልሆነ)
    if not force and db.is_paused():
        msg = "ህትመት በአስተዳዳሪው ቆሟል (Paused)።"
        db.log_publication(eth_year, eth_month, eth_day, status="skipped", error_message=msg)
        return {"success": False, "status": "skipped", "message": msg}

    # 3. ቀድሞ መታተሙን ማረጋገጥ (Idempotency)
    if not force and not custom_chat_id and db.is_already_published_today(eth_year, eth_month, eth_day):
        msg = f"የዕለቱ ስንክሳር ({date_label}) ዛሬ ቀድሞ በተሳካ ሁኔታ ታትሟል። ድጋሚ አልተላከም።"
        return {"success": True, "status": "already_published", "message": msg}

    # 4. ይዘቱን ከዳታቤዝ ማውጣት
    content = db.get_content(eth_year, eth_month, eth_day)
    if not content:
        err = f"ለቀኑ {date_label} {eth_year} ዓ.ም. የተመዘገበ የስንክሳር ይዘት አልተገኘም!"
        db.log_publication(eth_year, eth_month, eth_day, status="failed", error_message=err)
        return {"success": False, "status": "failed", "error": err}

    amharic_body = content.get("amharic_text", "")
    image_path_str = content.get("image_path")
    title = content.get("title")

    # 5. ሙሉውን የቴሌግራም መልእክት ማዘጋጀት (በ HTML Hyperlink!)
    full_caption = build_full_post_caption(
        month_name=month_name,
        day_num=eth_day,
        amharic_body=amharic_body,
        title=title,
        use_html=True
    )

    image_path = Path(image_path_str) if image_path_str else None
    has_image = image_path and image_path.exists() and image_path.stat().st_size > 0

    message_id = None
    caption_truncated = False

    try:
        if has_image:
            # ምስል አለ - የካፕሽን ገደብ 1024 ፊደላት ነው
            if len(full_caption) <= 1024:
                resp = send_telegram_photo(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    photo_path=image_path,
                    caption=full_caption,
                    parse_mode="HTML"
                )
                if not resp.get("ok"):
                    raise Exception(resp.get("description", "Failed to send photo with caption"))
                message_id = resp["result"]["message_id"]
            else:
                # ጽሑፉ ከ 1024 በላይ ሲሆን፡
                # 1. ምስሉን በዕለቱ አጭር ርዕስ ብቻ መላክ
                header_brief = f"{config.OPENING_PRAYER}\n{month_name} {ec.to_geez_number(eth_day)} ቀን የሚከበሩ ዓመታዊ እና ወርኃዊ በዓላት"
                resp_photo = send_telegram_photo(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    photo_path=image_path,
                    caption=header_brief[:1024],
                    parse_mode="HTML"
                )
                if not resp_photo.get("ok"):
                    raise Exception(resp_photo.get("description", "Failed to send photo"))
                
                # 2. ሙሉውን ጽሑፍ ተከትሎ መላክ
                chunks = split_text_for_telegram(full_caption, max_length=4000)
                last_msg_id = None
                for chunk in chunks:
                    resp_msg = send_telegram_message(
                        bot_token=bot_token,
                        chat_id=chat_id,
                        text=chunk,
                        parse_mode="HTML"
                    )
                    if not resp_msg.get("ok"):
                        raise Exception(resp_msg.get("description", "Failed to send caption message"))
                    last_msg_id = resp_msg["result"]["message_id"]
                message_id = last_msg_id
                caption_truncated = True
        else:
            # ምስል የለም - ጽሑፍ ብቻ መላክ
            chunks = split_text_for_telegram(full_caption, max_length=4000)
            last_msg_id = None
            for chunk in chunks:
                resp = send_telegram_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    text=chunk,
                    parse_mode="HTML"
                )
                if not resp.get("ok"):
                    raise Exception(resp.get("description", "Failed to send text message"))
                last_msg_id = resp["result"]["message_id"]
            message_id = last_msg_id

        # በዳታቤዝ ውስጥ ስኬትን መመዝገብ
        if not custom_chat_id:
            db.log_publication(
                eth_year=eth_year,
                eth_month=eth_month,
                eth_day=eth_day,
                status="success",
                message_id=message_id,
                caption_truncated=caption_truncated
            )

        return {
            "success": True,
            "status": "success",
            "message_id": message_id,
            "date": date_label,
            "caption_truncated": caption_truncated
        }

    except Exception as e:
        err_msg = str(e)
        if not custom_chat_id:
            db.log_publication(
                eth_year=eth_year,
                eth_month=eth_month,
                eth_day=eth_day,
                status="failed",
                error_message=err_msg
            )
        return {
            "success": False,
            "status": "failed",
            "error": err_msg,
            "date": date_label
        }


def publish_today_synksar(force: bool = False, custom_chat_id: Optional[str] = None) -> Dict[str, Any]:
    """የዛሬን ትክክለኛ የኢትዮጵያ ቀን ስንክሳር ያትማል"""
    ey, em, ed = ec.get_today_ethiopian()
    return publish_synksar_for_date(ey, em, ed, force=force, custom_chat_id=custom_chat_id)
