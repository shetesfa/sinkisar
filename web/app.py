"""
Synksar Auto Publisher - Web Dashboard Application (Flask)
ይህ ሞጁል ለአስተዳዳሪዎች በሞባይልና በኮምፒዩተር ምቹ የሆነ ዘመናዊ የድር ዳሽቦርድ ያቀርባል።
"""

import os
import sys
from pathlib import Path
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
    jsonify
)

# Root import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
import database as db
import ethiopian_calendar as ec
import content_manager as cm
import publisher as pub
from formatter import build_full_post_caption

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)
app.secret_key = config.DASHBOARD_SECRET_KEY


@app.context_processor
def inject_global_context():
    """ለሁሉም የ HTML ገጾች የጋራ መረጃዎችን ያቀርባል"""
    ey, em, ed = ec.get_today_ethiopian(config.TIMEZONE)
    today_str = ec.format_ethiopian_date_str(ey, em, ed)
    return {
        "today_year": ey,
        "today_month": em,
        "today_day": ed,
        "today_str": today_str,
        "is_paused": db.is_paused(),
        "config": config
    }


@app.route("/")
def index():
    """ዋና የዳሽቦርድ ገጽ"""
    ey, em, ed = ec.get_today_ethiopian(config.TIMEZONE)
    today_content = db.get_content(ey, em, ed)
    is_published_today = db.is_already_published_today(ey, em, ed)
    stats = db.get_stats(ey)
    stats["is_leap"] = ec.is_ethiopian_leap_year(ey)

    return render_template(
        "index.html",
        stats=stats,
        today_content=today_content,
        is_published_today=is_published_today
    )


@app.route("/calendar")
def calendar_view():
    """ዓመታዊ የቀን መቁጠሪያ ገጽ (13 ወራት)"""
    ey, em, ed = ec.get_today_ethiopian(config.TIMEZONE)
    selected_month = int(request.args.get("month", em))
    selected_year = int(request.args.get("year", ey))

    current_month_meta = ec.get_month_info(selected_month)
    days_count = ec.days_in_ethiopian_month(selected_year, selected_month)

    all_month_contents = {
        c["eth_day"]: c for c in db.get_all_contents(selected_year) if c["eth_month"] == selected_month
    }

    days_data = []
    ready_count = 0
    image_only_count = 0
    empty_count = 0

    for d in range(1, days_count + 1):
        content = all_month_contents.get(d)
        has_img = False
        has_txt = False

        if content:
            has_txt = bool(content.get("amharic_text") and content["amharic_text"].strip())
            img_p = content.get("image_path")
            has_img = bool(img_p and Path(img_p).exists())

        is_pub = db.is_already_published_today(selected_year, selected_month, d)

        if has_img and has_txt:
            status_class = "ready"
            ready_count += 1
        elif has_img and not has_txt:
            status_class = "warning"
            image_only_count += 1
        else:
            status_class = "missing"
            empty_count += 1

        days_data.append({
            "day": d,
            "geez_day": ec.to_geez_number(d),
            "has_image": has_img,
            "has_text": has_txt,
            "is_published": is_pub,
            "status_class": status_class
        })

    return render_template(
        "calendar.html",
        months=ec.ETHIOPIAN_MONTHS,
        selected_month=selected_month,
        selected_year=selected_year,
        current_month_meta=current_month_meta,
        current_month_days=days_data,
        month_stats={
            "ready": ready_count,
            "image_only": image_only_count,
            "empty": empty_count
        }
    )


@app.route("/edit/<int:month>/<int:day>", methods=["GET", "POST"])
def edit_day(month: int, day: int):
    """የቀን ይዘት ማረሚያ"""
    ey, _, _ = ec.get_today_ethiopian(config.TIMEZONE)
    year = int(request.args.get("year", ey))
    month_meta = ec.get_month_info(month)

    if request.method == "POST":
        amharic_text = request.form.get("amharic_text", "").strip()
        title = request.form.get("title", "").strip() or None

        # ምስል መቀበል
        image_file = request.files.get("image")
        image_path_str = None

        if image_file and image_file.filename:
            year_dir = cm.ensure_year_structure(year)
            day_folder = year_dir / month_meta["prefix"] / f"{day:02d}"
            day_folder.mkdir(parents=True, exist_ok=True)
            target_image = day_folder / "image.jpg"
            image_file.save(target_image)
            image_path_str = str(target_image)

        # በዳታቤዝ ማስቀመጥ
        existing = db.get_content(year, month, day)
        current_img = existing.get("image_path") if existing else None
        final_img = image_path_str or current_img

        db.upsert_content(
            eth_year=year,
            eth_month=month,
            eth_day=day,
            amharic_text=amharic_text,
            image_path=final_img,
            title=title,
            status="ready"
        )

        flash(f"የ{month_meta['amharic']} {day} ቀን ይዘት በተሳካ ሁኔታ ተሻሽሏል!", "success")
        return redirect(url_for("edit_day", month=month, day=day, year=year))

    content = db.get_content(year, month, day) or {}
    preview_caption = build_full_post_caption(
        month_name=month_meta["amharic"],
        day_num=day,
        amharic_body=content.get("amharic_text", ""),
        title=content.get("title"),
        use_html=False
    )

    return render_template(
        "editor.html",
        month=month,
        day=day,
        year=year,
        geez_day=ec.to_geez_number(day),
        month_name=month_meta["amharic"],
        content=content,
        preview_caption=preview_caption
    )


@app.route("/upload", methods=["GET", "POST"])
def upload_annual_zip():
    """ዓመታዊ ዚፕ መጫኛ ገጽ"""
    ey, _, _ = ec.get_today_ethiopian(config.TIMEZONE)
    target_year = int(request.form.get("target_year", ey) if request.method == "POST" else ey)

    if request.method == "POST":
        file = request.files.get("zip_file")
        if not file or not file.filename.lower().endswith(".zip"):
            flash("እባክዎ ትክክለኛ የ .zip ማህደር ፋይል ይምረጡ!", "danger")
            return redirect(url_for("upload_annual_zip"))

        temp_zip = Path(config.SYNKSAR_DATA_DIR) / f"web_upload_{file.filename}"
        temp_zip.parent.mkdir(parents=True, exist_ok=True)
        file.save(temp_zip)

        res = cm.import_annual_zip(temp_zip, target_year)
        if temp_zip.exists():
            temp_zip.unlink()

        if res.get("status") == "success":
            flash(f"ዓመታዊ ዳታ በተሳካ ሁኔታ ገብቷል! {res['imported_files']} ፋይሎች ተመዝግበዋል።", "success")
        else:
            flash(f"ዳታውን ማስገባት አልተሳካም፦ {res.get('error_message')}", "danger")

        return redirect(url_for("upload_annual_zip"))

    report = cm.validate_annual_content(target_year)
    return render_template("upload.html", year=target_year, report=report)


@app.route("/reseed", methods=["POST"])
def reseed_workspace():
    """ነባር የስራ ማውጫ ፋይሎችን መልሶ መመዝገብ"""
    ey, _, _ = ec.get_today_ethiopian(config.TIMEZONE)
    res = cm.seed_existing_workspace_data(ey)
    flash(f"ነባር ፋይሎች በተሳካ ሁኔታ ተመሳስለዋል! ({res['images_imported']} ምስሎች፣ {res['texts_imported']} ጽሑፎች)", "success")
    return redirect(url_for("upload_annual_zip"))


@app.route("/history")
def history_view():
    """የህትመት ታሪክ ገጽ"""
    logs_raw = db.get_publication_history(limit=100)
    logs = []
    for l in logs_raw:
        m_meta = ec.get_month_info(l["eth_month"])
        logs.append({
            **l,
            "date_str": f"{m_meta['amharic']} {ec.to_geez_number(l['eth_day'])} ({l['eth_day']})"
        })
    return render_template("history.html", logs=logs)


@app.route("/settings", methods=["GET", "POST"])
def settings_view():
    """የስርዓት ቅንብሮች ገጽ"""
    if request.method == "POST":
        bot_tok = request.form.get("bot_token", "").strip()
        ch_id = request.form.get("channel_id", "").strip()
        adm_ids = request.form.get("admin_ids", "").strip()
        tz = request.form.get("timezone", "").strip() or "Africa/Addis_Ababa"
        p_hour = request.form.get("publish_hour", "0").strip()
        p_min = request.form.get("publish_minute", "0").strip()

        ch_link = request.form.get("channel_link_url", "").strip()
        gr_link = request.form.get("group_link_url", "").strip()
        sch_amh = request.form.get("sunday_school_amharic", "").strip()
        sch_eng = request.form.get("sunday_school_english", "").strip()
        prayer = request.form.get("opening_prayer", "").strip()

        # .env ፋይል ማዘመን
        env_content = f"""# Synksar Auto Publisher - Configuration
BOT_TOKEN={bot_tok}
CHANNEL_ID={ch_id}
ADMIN_IDS={adm_ids}
TIMEZONE={tz}
PUBLISH_HOUR={p_hour}
PUBLISH_MINUTE={p_min}
DEFAULT_YEAR={config.DEFAULT_YEAR}
DASHBOARD_HOST={config.DASHBOARD_HOST}
DASHBOARD_PORT={config.DASHBOARD_PORT}
DASHBOARD_SECRET_KEY={config.DASHBOARD_SECRET_KEY}
CHANNEL_LINK_NAME={config.CHANNEL_LINK_NAME}
CHANNEL_LINK_URL={ch_link}
GROUP_LINK_NAME={config.GROUP_LINK_NAME}
GROUP_LINK_URL={gr_link}
SUNDAY_SCHOOL_AMHARIC={sch_amh}
SUNDAY_SCHOOL_ENGLISH={sch_eng}
OPENING_PRAYER={prayer}
"""
        env_path = Path(config.BASE_DIR) / ".env"
        env_path.write_text(env_content, encoding="utf-8")

        # Config ተለዋዋጮችን በ runtime ማደስ
        config.BOT_TOKEN = bot_tok
        config.CHANNEL_ID = ch_id
        config.ADMIN_IDS = [int(i.strip()) for i in adm_ids.split(",") if i.strip().isdigit()]
        config.TIMEZONE = tz
        config.PUBLISH_HOUR = int(p_hour or 0)
        config.PUBLISH_MINUTE = int(p_min or 0)
        config.CHANNEL_LINK_URL = ch_link
        config.GROUP_LINK_URL = gr_link
        config.SUNDAY_SCHOOL_AMHARIC = sch_amh
        config.SUNDAY_SCHOOL_ENGLISH = sch_eng
        config.OPENING_PRAYER = prayer

        flash("ቅንብሮች በተሳካ ሁኔታ ተቀምጠዋል!", "success")
        return redirect(url_for("settings_view"))

    admin_ids_str = ", ".join(str(i) for i in config.ADMIN_IDS)
    return render_template("settings.html", admin_ids_str=admin_ids_str)


@app.route("/image/<int:year>/<int:month>/<int:day>")
def serve_day_image(year: int, month: int, day: int):
    """የዕለቱን ምስል ያቀርባል"""
    content = db.get_content(year, month, day)
    if content and content.get("image_path"):
        img_p = Path(content["image_path"])
        if img_p.exists():
            return send_file(img_p, mimetype="image/jpeg")

    # ምስል ከሌለ ነባሪ ባዶ
    return "", 404


@app.route("/publish-today", methods=["POST"])
def publish_today_now():
    """የዛሬን ስንክሳር አሁን ወዲያውኑ ወደ ቻናል ያትማል"""
    res = pub.publish_today_synksar(force=True)
    if res.get("success"):
        flash(f"✅ የዛሬው ስንክሳር በተሳካ ሁኔታ ወደ ቻናሉ ታትሟል! (መልእክት ID: {res.get('message_id')})", "success")
    else:
        flash(f"❌ ማተም አልተሳካም፦ {res.get('error', res.get('message'))}", "danger")
    return redirect(url_for("index"))


@app.route("/publish-date/<int:month>/<int:day>", methods=["POST"])
def publish_specific_date(month: int, day: int):
    """የተወሰነን ቀን ብቻ አሁን ያትማል"""
    ey, _, _ = ec.get_today_ethiopian(config.TIMEZONE)
    year = int(request.args.get("year", ey))
    res = pub.publish_synksar_for_date(year, month, day, force=True)
    if res.get("success"):
        flash(f"✅ የ{res.get('date')} ስንክሳር በተሳካ ሁኔታ ወደ ቻናሉ ታትሟል!", "success")
    else:
        flash(f"❌ ማተም አልተሳካም፦ {res.get('error', res.get('message'))}", "danger")
    return redirect(url_for("edit_day", month=month, day=day, year=year))


@app.route("/toggle-pause", methods=["POST"])
def toggle_pause_route():
    """ህትመትን ያቆማል ወይም ያስጀምራል"""
    new_state = not db.is_paused()
    db.set_paused(new_state)
    flash(f"ህትመት {'ቆሟል (Paused)' if new_state else 'እንደገና ተጀምሯል (Resumed)'}!", "info")
    return redirect(url_for("index"))


def run_web(host: str = None, port: int = None):
    """የድር ዳሽቦርዱን ያስነሳል"""
    h = host or config.DASHBOARD_HOST
    p = port or config.DASHBOARD_PORT
    print(f"🌐 የድር ዳሽቦርድ በ http://{h}:{p} ወይም http://localhost:{p} ተከፍቷል!")
    app.run(host=h, port=p, debug=False)


if __name__ == "__main__":
    run_web()
