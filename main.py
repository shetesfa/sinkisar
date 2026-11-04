"""
Synksar Auto Publisher - Main Application Entrypoint
ይህ ፋይል ሁሉንም ክፍሎች (Scheduler, Web Dashboard, Telegram Bot)
በአንድ ላይ ወይም በተናጠል ያስነሳል።
"""

import sys
import time
import argparse
import threading
from pathlib import Path

# UTF-8 stdout configuration for Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import config
import database as db
import ethiopian_calendar as ec
import content_manager as cm
import publisher as pub
import scheduler as sch
from web.app import run_web


def run_all():
    """ሁሉንም አገልግሎቶች በአንድ ላይ ያስነሳል"""
    print("=" * 60)
    print("✝️  SYNKSAR AUTO PUBLISHER (የስንክሳር አውቶማቲክ አሳታሚ)  ✝️")
    print("=" * 60)

    # 1. ዳታቤዝ ማረጋገጥ
    db.init_db()
    ey, em, ed = ec.get_today_ethiopian(config.TIMEZONE)
    today_str = ec.format_ethiopian_date_str(ey, em, ed)
    print(f"📅 የዛሬ ቀን፦ {today_str} ({ey} ዓ.ም.)")
    print(f"📢 ዒላማ ቻናል፦ {config.CHANNEL_ID}")
    print(f"⏰ የህትመት ሰዓት፦ በየቀኑ {config.PUBLISH_HOUR:02d}:{config.PUBLISH_MINUTE:02d} ({config.TIMEZONE})")

    # 2. የይዘት ስታቲስቲክስ
    stats = db.get_stats(ey)
    print(f"📊 ይዘቶች፦ {stats['with_image']} ምስሎች፣ {stats['with_text']} ጽሑፎች")

    # 3. የቀን መቁጠሪያ ሰሌዳውን (Scheduler) በ Background Thread ማስነሳት
    print("\n⏰ 1. የቀን መቁጠሪያ ሰሌዳ (Scheduler) በማስነሳት ላይ...")
    scheduler = sch.start_scheduler()

    # 4. የቴሌግራም ቦት ካለ በ Thread ማስነሳት
    if config.BOT_TOKEN:
        print("🤖 2. የአስተዳዳሪ ቴሌግራም ቦት በማስነሳት ላይ...")
        import bot
        bot_thread = threading.Thread(target=bot.run_bot, daemon=True)
        bot_thread.start()
    else:
        print("⚠️ 2. BOT_TOKEN አልተገኘም (ቦቱ አልተነሳም፤ እባክዎ .env ውስጥ ያስገቡ)።")

    # 5. የድር ዳሽቦርድ (Web Dashboard) በዋናው thread ማስኬድ
    print(f"\n🌐 3. የድር ዳሽቦርድ በ http://localhost:{config.DASHBOARD_PORT} ተከፍቷል!")
    print("=" * 60)
    print("ስርዓቱ ያለማቋረጥ እየሰራ ነው። ለማቆም Ctrl + C ይጫኑ።\n")

    try:
        run_web(host=config.DASHBOARD_HOST, port=config.DASHBOARD_PORT)
    except (KeyboardInterrupt, SystemExit):
        print("\nስርዓቱ እየተዘጋ ነው...")
        scheduler.shutdown()
        print("ስርዓቱ በሰላም ተዘግቷል።")


def main():
    parser = argparse.ArgumentParser(description="Synksar Auto Publisher")
    parser.add_argument("--web", action="store_true", help="የድር ዳሽቦርድ ብቻ አስነሳ")
    parser.add_argument("--bot", action="store_true", help="የቴሌግራም ቦት ብቻ አስነሳ")
    parser.add_argument("--scheduler", action="store_true", help="የጊዜ ሰሌዳ (Scheduler) ብቻ አስነሳ")
    parser.add_argument("--publish-today", action="store_true", help="የዛሬን ስንክሳር አሁኑኑ አትም")
    parser.add_argument("--validate", action="store_true", help="የይዘት ማረጋገጫ ሪፖርት አሳይ")
    parser.add_argument("--reseed", action="store_true", help="ነባር ፋይሎችን ወደ ዳታቤዝ መልሰህ አመሳስል")

    args = parser.parse_args()

    if args.publish_today:
        print("የዛሬን ስንክሳር በማተም ላይ...")
        res = pub.publish_today_synksar(force=True)
        print("ውጤት፦", res)
    elif args.validate:
        ey, _, _ = ec.get_today_ethiopian(config.TIMEZONE)
        rep = cm.validate_annual_content(ey)
        print(rep["summary_text"])
    elif args.reseed:
        ey, _, _ = ec.get_today_ethiopian(config.TIMEZONE)
        res = cm.seed_existing_workspace_data(ey)
        print(f"ተመሳስሏል፦ {res['images_imported']} ምስሎች፣ {res['texts_imported']} ጽሑፎች")
    elif args.web:
        run_web()
    elif args.bot:
        import bot
        bot.run_bot()
    elif args.scheduler:
        s = sch.start_scheduler()
        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            s.shutdown()
    else:
        run_all()


if __name__ == "__main__":
    main()
