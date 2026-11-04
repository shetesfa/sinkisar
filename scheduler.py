"""
Synksar Auto Publisher - Daily Scheduler Module
በየቀኑ እኩለ ሌሊት (12:00 AM / 00:00) በኢትዮጵያ ሰዓት (Africa/Addis_Ababa)
የዕለቱን ስንክሳር በራሱ የሚያትም እና ከመስመር ውጭ የቆየን (Offline Catch-Up) የሚያካክስ ሞጁል።
"""

import time
import logging
from zoneinfo import ZoneInfo
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import config
import database as db
import ethiopian_calendar as ec
import publisher as pub

logging.basicConfig(
    format="%(asctime)s - [SCHEDULER] - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("Scheduler")


def daily_publish_job():
    """በየቀኑ የሚሰራው ዋና የህትመት ስራ (ከ 3 ጊዜ ድጋሚ ሙከራ ጋር)"""
    ey, em, ed = ec.get_today_ethiopian(config.TIMEZONE)
    date_str = ec.format_ethiopian_date_str(ey, em, ed)
    logger.info(f"የዕለቱ የህትመት ሰዓት ደርሷል፦ {date_str} ({ey} ዓ.ም.)")

    if db.is_paused():
        logger.warning("ህትመት በአስተዳዳሪው ስለቆመ (Paused) አልታተመም።")
        return

    # ቀድሞ መታተሙን ማረጋገጥ
    if db.is_already_published_today(ey, em, ed):
        logger.info(f"የቀኑ ስንክሳር ({date_str}) ቀድሞ ስለታተመ ድጋሚ አልተላከም።")
        return

    # እስከ 3 ጊዜ በ exponential backoff መሞከር
    max_retries = 3
    delays = [10, 30, 60]  # ሰከንዶች

    for attempt in range(1, max_retries + 1):
        logger.info(f"ህትመት ሙከራ {attempt}/{max_retries} ለቀን፦ {date_str}")
        result = pub.publish_synksar_for_date(ey, em, ed, force=False)

        if result.get("success"):
            logger.info(f"✅ ስንክሳር በተሳካ ሁኔታ ታትሟል! መልእክት ID: {result.get('message_id')}")
            return
        else:
            err = result.get("error", "ያልታወቀ ስህተት")
            logger.error(f"❌ ሙከራ {attempt} አልተሳካም፦ {err}")
            if attempt < max_retries:
                sleep_time = delays[attempt - 1]
                logger.info(f"{sleep_time} ሰከንዶች ቆይቶ ዳግም ይሞከራል...")
                time.sleep(sleep_time)

    logger.critical(f"🚨 ለቀኑ {date_str} የተደረጉ {max_retries}ቱም ሙከራዎች አልተሳኩም!")


def check_and_catch_up_today():
    """
    ኮምፒዩተሩ ሲበራ ወይም አፕሊኬሽኑ ሲነሳ፣ የዛሬው ቀን አለመታተሙን ካየ
    ወዲያውኑ የሚያትም (Offline Catch-Up / Startup Recovery) ስርዓት።
    """
    ey, em, ed = ec.get_today_ethiopian(config.TIMEZONE)
    date_str = ec.format_ethiopian_date_str(ey, em, ed)
    logger.info(f"የማስነሻ ፍተሻ (Startup Recovery Check) ለቀን፦ {date_str}")

    if db.is_paused():
        logger.info("ህትመት ቆሟል (Paused)። የ Startup ማካካሻ አልተካሄደም።")
        return

    if not db.is_already_published_today(ey, em, ed):
        logger.warning(f"የዛሬው ስንክሳር ({date_str}) አልታተመም! አሁን ወዲያውኑ በማተም ላይ...")
        daily_publish_job()
    else:
        logger.info(f"የዛሬው ስንክሳር ({date_str}) ቀድሞ ታትሟል፤ ሁሉም ነገር ሰላም ነው!")


def create_scheduler() -> BackgroundScheduler:
    """የ APScheduler አሳታሚን ያዘጋጃል"""
    tz = ZoneInfo(config.TIMEZONE)
    scheduler = BackgroundScheduler(timezone=tz)

    # በየቀኑ በ config.PUBLISH_HOUR : config.PUBLISH_MINUTE
    trigger = CronTrigger(
        hour=config.PUBLISH_HOUR,
        minute=config.PUBLISH_MINUTE,
        timezone=tz
    )

    scheduler.add_job(
        daily_publish_job,
        trigger=trigger,
        id="synksar_daily_publisher",
        name="የዕለት ስንክሳር አውቶማቲክ አሳታሚ",
        replace_existing=True
    )

    return scheduler


def start_scheduler():
    """የቀን መቁጠሪያ ሰሌዳውን ያስነሳል"""
    scheduler = create_scheduler()
    scheduler.start()
    logger.info(f"⏰ አውቶማቲክ አሳታሚ በየቀኑ {config.PUBLISH_HOUR:02d}:{config.PUBLISH_MINUTE:02d} ({config.TIMEZONE}) እንዲሰራ ተዘጋጅቷል!")

    # በማስነሳት ወቅት የዛሬን ቀን ማረጋገጥ
    check_and_catch_up_today()
    return scheduler


if __name__ == "__main__":
    s = start_scheduler()
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        s.shutdown()
