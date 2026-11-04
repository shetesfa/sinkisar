"""
Synksar Auto Publisher - Telegram Admin Bot
ይህ ሞጁል ለአስተዳዳሪዎች ብቻ የሚሰራ ኃይለኛ የቴሌግራም ቦት ነው።
12ቱን ሜኑዎች፣ የዚፕ አፕሎድ፣ የቀን ቅድመ-ዕይታ፣ እና የቻናል ፎርዋርድን ያካትታል።
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

import config
import database as db
import ethiopian_calendar as ec
import content_manager as cm
import publisher as pub
from formatter import build_full_post_caption

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# የተጠቃሚ ሁኔታ (State) ለግንኙነት
USER_STATES: Dict[int, Dict[str, Any]] = {}


def is_admin(user_id: int) -> bool:
    """ተጠቃሚው የተፈቀደለት አስተዳዳሪ መሆኑን ያረጋግጣል"""
    if not config.ADMIN_IDS:
        # የአስተዳዳሪ ID ካልተገደበ የመጀመሪያውን ሰው እንደ አስተዳዳሪ ይቆጥራል
        return True
    return user_id in config.ADMIN_IDS


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """12ቱን ዋና ዋና የአስተዳዳሪ ሜኑዎች ያዘጋጃል"""
    paused = db.is_paused()
    pause_label = "▶️ ህትመትን አስጀምር (Resume)" if paused else "⏸️ ህትመትን አቁም (Pause)"

    keyboard = [
        [
            InlineKeyboardButton("📖 የዛሬን ስንክሳር እይ", callback_data="view_today"),
            InlineKeyboardButton("🔮 የነገን ቅድመ-ዕይታ", callback_data="preview_tomorrow")
        ],
        [
            InlineKeyboardButton("🚀 የሙከራ መልእክት ላክ", callback_data="send_test"),
            InlineKeyboardButton("📅 ዓመታዊ ካላንደር", callback_data="view_calendar")
        ],
        [
            InlineKeyboardButton("📤 ዓመታዊ ዳታ ስቀል (ZIP)", callback_data="upload_zip_guide"),
            InlineKeyboardButton("📋 የማስመጣት ሪፖርት", callback_data="view_report")
        ],
        [
            InlineKeyboardButton("✏️ ይዘት አርትዕ", callback_data="menu_edit_content"),
            InlineKeyboardButton("🖼️ ምስል ተካ", callback_data="menu_replace_image")
        ],
        [
            InlineKeyboardButton("📝 ጽሑፍ ተካ", callback_data="menu_replace_text"),
            InlineKeyboardButton("📊 የህትመት ታሪክ", callback_data="view_history")
        ],
        [
            InlineKeyboardButton("⚙️ የህትመት ቅንብሮች", callback_data="view_settings"),
            InlineKeyboardButton(pause_label, callback_data="toggle_pause")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የ /start ትዕዛዝ ሲጠራ"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            f"⛔ ይቅርታ {user.first_name}፣ ይህ ቦት ለተፈቀደላቸው የሰንበት ት/ቤት አስተዳዳሪዎች ብቻ የተዘጋጀ ነው።\n"
            f"የእርስዎ Telegram ID: <code>{user.id}</code>",
            parse_mode="HTML"
        )
        return

    today_ey, today_em, today_ed = ec.get_today_ethiopian()
    today_str = ec.format_ethiopian_date_str(today_ey, today_em, today_ed)

    welcome_text = (
        f"✝️ <b>እንኳን ወደ ስንክሳር አውቶማቲክ አሳታሚ (Synksar Auto Publisher) በደህና መጡ!</b>\n\n"
        f"📅 <b>የዛሬ ቀን፦</b> {today_str} ({today_ey} ዓ.ም.)\n"
        f"📢 <b>የሚታተምበት ቻናል፦</b> {config.CHANNEL_ID}\n"
        f"⏰ <b>የህትመት ሰዓት፦</b> በየቀኑ {config.PUBLISH_HOUR:02d}:{config.PUBLISH_MINUTE:02d} (እኩለ ሌሊት 12:00 AM)\n"
        f"📊 <b>የስርዓት ሁኔታ፦</b> {'⏸️ ቆሟል (Paused)' if db.is_paused() else '🟢 ነቅቷል (Active)'}\n\n"
        f"ከዚህ በታች ካሉት አማራጮች አንዱን ይምረጡ፦"
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የ Inline አዝራሮች ምላሽ"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("⛔ ይህንን ተግባር ለማከናወን ፈቃድ የለዎትም።")
        return

    data = query.data

    # 1. የዛሬን ስንክሳር እይ
    if data == "view_today":
        ey, em, ed = ec.get_today_ethiopian()
        await show_date_content(query, ey, em, ed, "የዛሬ ስንክሳር")

    # 2. የነገን ቅድመ-ዕይታ
    elif data == "preview_tomorrow":
        ey, em, ed = ec.get_tomorrow_ethiopian()
        await show_date_content(query, ey, em, ed, "የነገ ስንክሳር ቅድመ-ዕይታ")

    # 3. የሙከራ መልእክት ላክ (Send Test Message)
    elif data == "send_test":
        ey, em, ed = ec.get_today_ethiopian()
        await query.edit_message_text("⏳ የዛሬን ስንክሳር ወደ ቻናሉ በመላክ ላይ ነው...")
        result = pub.publish_today_synksar(force=True)
        if result.get("success"):
            await query.message.reply_text(
                f"✅ <b>የሙከራ መልእክት በተሳካ ሁኔታ ተልኳል!</b>\n"
                f"📅 ቀን: {result.get('date')}\n"
                f"🆔 መልእክት ID: {result.get('message_id')}\n"
                f"📢 ቻናል: {config.CHANNEL_ID}",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await query.message.reply_text(
                f"❌ <b>መልእክት መላክ አልተሳካም!</b>\n"
                f"ስህተት: {result.get('error', result.get('message'))}",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard()
            )

    # 4. ዓመታዊ ካላንደር
    elif data == "view_calendar":
        stats = db.get_stats(config.DEFAULT_YEAR)
        cal_text = (
            f"📅 <b>ዓመታዊ የቀን መቁጠሪያ ማጠቃለያ ({config.DEFAULT_YEAR} ዓ.ም.)</b>\n\n"
            f"• አጠቃላይ የሚጠበቁ ቀናት: {stats['expected_days']}\n"
            f"• የተሟሉ የተመዘገቡ ቀናት: {stats['total_records']}\n"
            f"• ምስል ያላቸው ቀናት: {stats['with_image']}\n"
            f"• ጽሑፍ ያላቸው ቀናት: {stats['with_text']}\n"
            f"• እስካሁን የታተሙ ቀናት: {stats['published_count']}\n"
            f"• የጎደሉ ቀናት: {stats['missing_days']}\n\n"
            f"<i>ለሙሉ 13ቱ ወራት የቀን በዓላት ዝርዝር እና የቀለም አመልካች የድር ዳሽቦርዱን ይመልከቱ።</i>"
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ወደ ዋና ሜኑ", callback_data="main_menu")]])
        await query.edit_message_text(cal_text, reply_markup=back_kb, parse_mode="HTML")

    # 5. ዓመታዊ ዳታ ስቀል (Upload Annual Data)
    elif data == "upload_zip_guide":
        guide_text = (
            f"📤 <b>ዓመታዊ የዚፕ ማህደር (Annual ZIP) መመሪያ</b>\n\n"
            f"የአንድ ሙሉ ዓመት የስንክሳር ምስሎችንና ጽሑፎችን በአንድ ጊዜ ለመስቀል፦\n\n"
            f"1. ፋይሎቹን በፎልደር ያደራጁ (ምሳሌ፦ <code>01_Meskerem/01/text.txt</code> እና <code>image.jpg</code>)\n"
            f"2. ፎልደሩን በ .zip ያሽጉት።\n"
            f"3. የዚፕ ፋይሉን በቀጥታ <b>ለዚህ ቦት እንደ Document ይላኩለት</b>!\n\n"
            f"⚠️ <i>ማሳሰቢያ፦ የቴሌግራም ቦት ፋይል መጠን ገደብ 20MB ወይም 50MB ሊሆን ስለሚችል፣ እጅግ በጣም ትላልቅ ዚፕ ፋይሎችን በዌብ ዳሽቦርዱ በኩል መጫን ይመረጣል።</i>"
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ወደ ዋና ሜኑ", callback_data="main_menu")]])
        await query.edit_message_text(guide_text, reply_markup=back_kb, parse_mode="HTML")

    # 6. የማስመጣት ሪፖርት (Import Report)
    elif data == "view_report":
        report = cm.validate_annual_content(config.DEFAULT_YEAR)
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ወደ ዋና ሜኑ", callback_data="main_menu")]])
        await query.edit_message_text(report["summary_text"], reply_markup=back_kb)

    # 7. ህትመትን አቁም / አስጀምር (Toggle Pause)
    elif data == "toggle_pause":
        new_state = not db.is_paused()
        db.set_paused(new_state)
        status_msg = "⏸️ <b>አውቶማቲክ ህትመት ቆሟል (Paused)!</b>" if new_state else "🟢 <b>አውቶማቲክ ህትመት እንደገና ተጀምሯል (Resumed)!</b>"
        await query.message.reply_text(
            status_msg,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )

    # 8. የህትመት ታሪክ
    elif data == "view_history":
        logs = db.get_publication_history(limit=10)
        if not logs:
            hist_text = "📊 እስካሁን የተመዘገበ የህትመት ታሪክ የለም።"
        else:
            hist_text = "📊 <b>የቅርብ ጊዜ የህትመት ታሪክ፦</b>\n\n"
            for log in logs:
                m_info = ec.get_month_info(log["eth_month"])
                date_str = f"{m_info['amharic']} {log['eth_day']}"
                status_icon = "✅" if log["status"] == "success" else ("⏸️" if log["status"] == "skipped" else "❌")
                hist_text += f"{status_icon} <b>{date_str}</b> | {log['status']} | {log['published_at']}\n"
                if log["error_message"]:
                    hist_text += f"   └ <i>{log['error_message']}</i>\n"

        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ወደ ዋና ሜኑ", callback_data="main_menu")]])
        await query.edit_message_text(hist_text, reply_markup=back_kb, parse_mode="HTML")

    # 9. የህትመት ቅንብሮች
    elif data == "view_settings":
        settings_text = (
            f"⚙️ <b>የስርዓት ቅንብሮች</b>\n\n"
            f"• ቻናል፦ <code>{config.CHANNEL_ID}</code>\n"
            f"• የሰዓት ዞን፦ {config.TIMEZONE}\n"
            f"• የህትመት ሰዓት፦ {config.PUBLISH_HOUR:02d}:{config.PUBLISH_MINUTE:02d}\n"
            f"• ነባሪ ዓመት፦ {config.DEFAULT_YEAR} ዓ.ም.\n"
            f"• የቻናል ሊንክ፦ {config.CHANNEL_LINK_URL}\n"
            f"• የግሩፕ ሊንክ፦ {config.GROUP_LINK_URL}\n"
            f"• የቦት ሊንክ፦ <i>(የለም - ተጠቃሚው አስወግዶታል)</i>\n"
            f"• ዳሽቦርድ ፖርት፦ {config.DASHBOARD_PORT}\n"
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ወደ ዋና ሜኑ", callback_data="main_menu")]])
        await query.edit_message_text(settings_text, reply_markup=back_kb, parse_mode="HTML")

    # 10. ምስል ተካ / ጽሑፍ ተካ / ይዘት አርትዕ
    elif data in ["menu_edit_content", "menu_replace_image", "menu_replace_text"]:
        USER_STATES[user_id] = {"action": data}
        prompt = (
            "እባክዎ ማስተካከል የሚፈልጉትን ወር እና ቀን ያስገቡ።\n"
            "ምሳሌ፦ <code>ሐምሌ 1</code> ወይም <code>11/1</code>"
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ሰርዝ", callback_data="main_menu")]])
        await query.edit_message_text(prompt, reply_markup=back_kb, parse_mode="HTML")

    # ዋና ሜኑ
    elif data == "main_menu":
        USER_STATES.pop(user_id, None)
        await query.edit_message_text(
            "✝️ <b>የስንክሳር አውቶማቲክ አሳታሚ ዋና ሜኑ፦</b>",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )


async def show_date_content(query, year: int, month: int, day: int, label: str):
    """የተወሰነን ቀን ይዘት ለተጠቃሚው ያሳያል"""
    month_info = ec.get_month_info(month)
    month_name = month_info["amharic"]
    date_label = f"{month_name} {ec.to_geez_number(day)} ({day}) ቀን"

    content = db.get_content(year, month, day)
    back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ወደ ዋና ሜኑ", callback_data="main_menu")]])

    if not content:
        await query.edit_message_text(
            f"⚠️ <b>{label} ({date_label})</b>\n\nለዚህ ቀን የተመዘገበ ይዘት አልተገኘም!",
            reply_markup=back_kb,
            parse_mode="HTML"
        )
        return

    amharic_body = content.get("amharic_text", "")
    image_path_str = content.get("image_path")
    full_caption = build_full_post_caption(
        month_name=month_name,
        day_num=day,
        amharic_body=amharic_body,
        use_html=True
    )

    image_path = Path(image_path_str) if image_path_str else None
    has_image = image_path and image_path.exists() and image_path.stat().st_size > 0

    if has_image:
        await query.message.reply_photo(
            photo=open(image_path, "rb"),
            caption=f"📌 <b>{label}፦</b>\n\n{full_caption[:950]}...",
            parse_mode="HTML",
            reply_markup=back_kb
        )
    else:
        preview_msg = f"📌 <b>{label}፦</b>\n\n{full_caption[:3500]}"
        await query.edit_message_text(preview_msg, reply_markup=back_kb)


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የተላከውን የዚፕ (ZIP) ፋይል ይቀበላል"""
    user = update.effective_user
    if not is_admin(user.id):
        return

    doc = update.message.document
    if not doc.file_name.lower().endswith(".zip"):
        await update.message.reply_text("⚠️ እባክዎ የ .zip ማህደር ፋይል ብቻ ይላኩ።")
        return

    status_msg = await update.message.reply_text("⏳ የዚፕ ፋይሉ እየወረደና ወደ ሲስተሙ እየገባ ነው...")
    try:
        file = await context.bot.get_file(doc.file_id)
        temp_zip_path = Path(config.SYNKSAR_DATA_DIR) / f"upload_{user.id}_{doc.file_name}"
        temp_zip_path.parent.mkdir(parents=True, exist_ok=True)
        await file.download_to_drive(custom_path=temp_zip_path)

        # ማስመጣት
        import_res = cm.import_annual_zip(temp_zip_path, config.DEFAULT_YEAR)
        if temp_zip_path.exists():
            temp_zip_path.unlink()

        if import_res.get("status") == "success":
            val = import_res["validation_report"]
            await status_msg.edit_text(
                f"✅ <b>ዓመታዊ ዳታ በተሳካ ሁኔታ ገብቷል!</b>\n\n"
                f"• የገቡ ፋይሎች: {import_res['imported_files']}\n"
                f"{val['summary_text']}",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await status_msg.edit_text(
                f"❌ <b>ዳታውን ማስገባት አልተሳካም!</b>\n"
                f"ስህተት: {import_res.get('error_message')}",
                reply_markup=get_main_menu_keyboard()
            )
    except Exception as e:
        await status_msg.edit_text(f"❌ ስህተት ተከስቷል: {e}", reply_markup=get_main_menu_keyboard())


async def forward_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ከሌላ ቻናል ፎርዋርድ የተደረገ ፖስት ይቀበላል"""
    user = update.effective_user
    if not is_admin(user.id):
        return

    msg = update.message
    caption_or_text = msg.caption or msg.text or ""
    has_photo = bool(msg.photo)

    ey, em, ed = ec.get_today_ethiopian()
    
    # ጽሑፉ ውስጥ የወር ስም መፈለግ
    for m_meta in ec.ETHIOPIAN_MONTHS:
        if m_meta["amharic"] in caption_or_text:
            em = m_meta["index"]
            break

    USER_STATES[user.id] = {
        "action": "confirm_forward",
        "text": caption_or_text,
        "photo": msg.photo[-1] if has_photo else None,
        "month": em,
        "day": ed,
        "year": ey
    }

    m_info = ec.get_month_info(em)
    confirm_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ አዎ አስቀምጥ", callback_data="save_forwarded"),
            InlineKeyboardButton("❌ ሰርዝ", callback_data="main_menu")
        ]
    ])
    await msg.reply_text(
        f"📥 <b>ከቻናል የተላለፈ ፖስት ተገኝቷል!</b>\n\n"
        f"ቀን፦ <b>{m_info['amharic']} {ed} ቀን</b> ({ey} ዓ.ም.)\n"
        f"ምስል፦ {'አለው' if has_photo else 'የለውም'}\n\n"
        f"ይህንን ይዘት ለዚህ ቀን ማስቀመጥ ይፈልጋሉ?",
        reply_markup=confirm_kb,
        parse_mode="HTML"
    )


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የጽሑፍ መልእክቶችን ያስተናግዳል"""
    user = update.effective_user
    if not is_admin(user.id):
        return

    state = USER_STATES.get(user.id)
    if not state:
        return

    action = state.get("action")
    text = update.message.text.strip()

    # ወር እና ቀን መምረጥ
    if action in ["menu_edit_content", "menu_replace_image", "menu_replace_text"]:
        # ወር እና ቀን መለየት
        parsed_month = None
        parsed_day = None

        for m_meta in ec.ETHIOPIAN_MONTHS:
            if m_meta["amharic"] in text:
                parsed_month = m_meta["index"]
                break

        parts = text.replace("/", " ").replace("-", " ").split()
        for p in parts:
            if p.isdigit():
                val = int(p)
                if parsed_month is None and 1 <= val <= 13:
                    parsed_month = val
                elif 1 <= val <= 30:
                    parsed_day = val

        if parsed_month and parsed_day:
            state["month"] = parsed_month
            state["day"] = parsed_day
            m_info = ec.get_month_info(parsed_month)

            if action == "menu_replace_image":
                state["action"] = "awaiting_photo"
                await update.message.reply_text(
                    f"📷 ለ <b>{m_info['amharic']} {parsed_day} ቀን</b> የሚተካውን አዲሱን ምስል አሁን ይላኩ።",
                    parse_mode="HTML"
                )
            elif action in ["menu_edit_content", "menu_replace_text"]:
                state["action"] = "awaiting_text"
                existing = db.get_content(config.DEFAULT_YEAR, parsed_month, parsed_day)
                old_txt = existing["amharic_text"] if existing else "የለም"
                await update.message.reply_text(
                    f"📝 ለ <b>{m_info['amharic']} {parsed_day} ቀን</b> የሚተካውን አዲሱን የአማርኛ ጽሑፍ ይላኩ።\n\n"
                    f"<i>የቀድሞው ጽሑፍ፦</i>\n{old_txt[:300]}...",
                    parse_mode="HTML"
                )
        else:
            await update.message.reply_text("⚠️ እባክዎ ትክክለኛ ወር እና ቀን ያስገቡ (ምሳሌ፡ ሐምሌ 1)")

    elif action == "awaiting_text":
        m = state["month"]
        d = state["day"]
        db.upsert_content(config.DEFAULT_YEAR, m, d, amharic_text=text)
        m_info = ec.get_month_info(m)
        USER_STATES.pop(user.id, None)
        await update.message.reply_text(
            f"✅ የ <b>{m_info['amharic']} {d} ቀን</b> ጽሑፍ በተሳካ ሁኔታ ተተክቷል!",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የተላከን ምስል ለመተካት ይቀበላል"""
    user = update.effective_user
    if not is_admin(user.id):
        return

    state = USER_STATES.get(user.id)
    if not state or state.get("action") != "awaiting_photo":
        return

    m = state["month"]
    d = state["day"]
    m_info = ec.get_month_info(m)

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    year_dir = cm.ensure_year_structure(config.DEFAULT_YEAR)
    target_dir = year_dir / m_info["prefix"] / f"{d:02d}"
    target_img = target_dir / "image.jpg"

    await file.download_to_drive(custom_path=target_img)

    existing = db.get_content(config.DEFAULT_YEAR, m, d)
    txt = existing["amharic_text"] if existing else ""
    db.upsert_content(config.DEFAULT_YEAR, m, d, amharic_text=txt, image_path=str(target_img))

    USER_STATES.pop(user.id, None)
    await update.message.reply_text(
        f"✅ የ <b>{m_info['amharic']} {d} ቀን</b> ምስል በተሳካ ሁኔታ ተተክቷል!",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard()
    )


def run_bot():
    """ቴሌግራም ቦትን ያስነሳል"""
    if not config.BOT_TOKEN:
        print("⚠️ የቦት ቶከን አልተገኘም! እባክዎ .env ውስጥ ያስገቡ።")
        return

    app = ApplicationBuilder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.FORWARDED, forward_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print(f"🤖 የቴሌግራም ቦት ስራ ጀምሯል...")
    app.run_polling()


if __name__ == "__main__":
    run_bot()
