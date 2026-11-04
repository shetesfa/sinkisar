"""
Synksar Auto Publisher - Comprehensive Automated Tests
ይህ ሞጁል ሁሉንም የስርዓቱ ክፍሎች በራስ-ሰር ይፈትሻል።
"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import database as db
import ethiopian_calendar as ec
import formatter as fmt
import content_manager as cm
import scheduler as sch
from web.app import app


class TestSynksarAutoPublisher(unittest.TestCase):

    def setUp(self):
        db.init_db()

    # 1. የኢትዮጵያ ካላንደር ፈተና
    def test_ethiopian_calendar_conversion(self):
        # 2024 Sept 11 -> Meskerem 1, 2017
        y, m, d = ec.gregorian_to_ethiopian(2024, 9, 11)
        self.assertEqual((y, m, d), (2017, 1, 1))

        # Back to Gregorian
        gy, gm, gd = ec.ethiopian_to_gregorian(2017, 1, 1)
        self.assertEqual((gy, gm, gd), (2024, 9, 11))

    def test_geez_numbers(self):
        self.assertEqual(ec.to_geez_number(1), "፩")
        self.assertEqual(ec.to_geez_number(5), "፭")
        self.assertEqual(ec.to_geez_number(10), "፲")
        self.assertEqual(ec.to_geez_number(25), "፳፭")
        self.assertEqual(ec.to_geez_number(30), "፴")

    def test_month_days_and_leap(self):
        # Regular months always 30
        for m in range(1, 13):
            self.assertEqual(ec.days_in_ethiopian_month(2018, m), 30)
        # Pagume 2018 (non-leap) -> 5 days
        self.assertEqual(ec.days_in_ethiopian_month(2018, 13), 5)
        # Pagume 2019 (leap year 2019 % 4 == 3) -> 6 days
        self.assertEqual(ec.days_in_ethiopian_month(2019, 13), 6)

    # 2. የዳታቤዝ ፈተና
    def test_database_operations(self):
        # Upsert test content
        cid = db.upsert_content(
            eth_year=9999,
            eth_month=1,
            eth_day=1,
            amharic_text="የሙከራ ስንክሳር ጽሑፍ",
            image_path="test_image.jpg",
            title="ሙከራ መስከረም 1"
        )
        self.assertIsNotNone(cid)

        # Retrieve
        row = db.get_content(9999, 1, 1)
        self.assertIsNotNone(row)
        self.assertEqual(row["amharic_text"], "የሙከራ ስንክሳር ጽሑፍ")

        # Publication log
        lid = db.log_publication(9999, 1, 1, status="success", message_id=12345)
        self.assertIsNotNone(lid)
        self.assertTrue(db.is_already_published_today(9999, 1, 1))

        # Pause setting
        db.set_paused(True)
        self.assertTrue(db.is_paused())
        db.set_paused(False)
        self.assertFalse(db.is_paused())

    # 3. የመልእክት ፎርማተር ፈተና (በተለይ የቦት ሊንክ አለመኖሩን ማረጋገጥ!)
    def test_message_formatting_and_no_bot(self):
        caption = fmt.build_full_post_caption(
            month_name="ሐምሌ",
            day_num=1,
            amharic_body="፩.ቅዱስ አግናጥዮስ ሐዋርያዊ ሰማዕት",
            use_html=False
        )
        # የመክፈቻ ጸሎት መኖሩን
        self.assertIn("ለእግዚአብሔር ምስጋና ይሁን", caption)
        # የወርና ቀን ርዕስ
        self.assertIn("ሐምሌ ፩ ቀን", caption)
        # የቅዱሳኑ ስም
        self.assertIn("ቅዱስ አግናጥዮስ", caption)
        # የቻናል ሊንክ መኖሩን
        self.assertIn(config.CHANNEL_LINK_NAME, caption)
        # የግሩፕ ሊንክ መኖሩን
        self.assertIn(config.GROUP_LINK_NAME, caption)
        # የሰንበት ትምህርት ቤቱ ስም መኖሩን
        self.assertIn(config.SUNDAY_SCHOOL_AMHARIC, caption)
        # ወሳኝ ማረጋገጫ፦ "Telegram bot" ወይም "bot" የሚል ሊንክ በፍጹም አለመኖሩን ማረጋገጥ!
        self.assertNotIn("telegram bot", caption.lower())
        self.assertNotIn("Telegram bot", caption)

    # 4. የይዘት ማኔጀር እና Manifest ፈተና
    def test_manifest_and_validation(self):
        year_dir = cm.ensure_year_structure(2018)
        self.assertTrue(year_dir.exists())

        manifest_file = cm.generate_manifest_csv(2018)
        self.assertTrue(manifest_file.exists())
        self.assertGreater(manifest_file.stat().st_size, 0)

        report = cm.validate_annual_content(2018)
        self.assertIn("expected_days", report)
        self.assertEqual(report["expected_days"], 365)

    # 5. የጊዜ ሰሌዳ (Scheduler) ፈተና
    def test_scheduler_creation(self):
        scheduler = sch.create_scheduler()
        self.assertIsNotNone(scheduler)
        jobs = scheduler.get_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].id, "synksar_daily_publisher")

    # 6. የድር ዳሽቦርድ (Flask routes) ፈተና
    def test_flask_routes(self):
        client = app.test_client()
        # Home
        resp = client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ስንክሳር አሳታሚ".encode("utf-8"), resp.data)

        # Calendar
        resp_cal = client.get("/calendar?month=1")
        self.assertEqual(resp_cal.status_code, 200)

        # Upload
        resp_up = client.get("/upload")
        self.assertEqual(resp_up.status_code, 200)

        # History
        resp_hist = client.get("/history")
        self.assertEqual(resp_hist.status_code, 200)

        # Settings
        resp_set = client.get("/settings")
        self.assertEqual(resp_set.status_code, 200)


if __name__ == "__main__":
    unittest.main()
