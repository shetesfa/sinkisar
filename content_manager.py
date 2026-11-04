"""
Synksar Auto Publisher - Content Manager Module
ይህ ሞጁል የዓመታዊ የስንክሳር መረጃዎችን (ምስሎች፣ ጽሑፎች፣ manifest.csv) ያደራጃል፣
የዚፕ ማህደርን ያስመጣል፣ እንዲሁም የይዘት ማረጋገጫ (Validation) ሪፖርት ያመነጫል።
"""

import os
import sys
import shutil
import zipfile
import csv
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

import config
import database as db
import ethiopian_calendar as ec
from formatter import build_full_post_caption

SYNKSAR_DATA_DIR = Path(config.SYNKSAR_DATA_DIR)


def ensure_year_structure(eth_year: int) -> Path:
    """ለተሰጠው ዓመት የ 13ቱን ወራት ፎልደር መዋቅር ያዘጋጃል"""
    year_dir = SYNKSAR_DATA_DIR / str(eth_year)
    year_dir.mkdir(parents=True, exist_ok=True)

    for month_meta in ec.ETHIOPIAN_MONTHS:
        month_prefix = month_meta["prefix"]
        month_dir = year_dir / month_prefix
        month_dir.mkdir(parents=True, exist_ok=True)
        days_count = ec.days_in_ethiopian_month(eth_year, month_meta["index"])
        for d in range(1, days_count + 1):
            day_dir = month_dir / f"{d:02d}"
            day_dir.mkdir(parents=True, exist_ok=True)

    return year_dir


def generate_manifest_csv(eth_year: int) -> Path:
    """ለተሰጠው ዓመት manifest.csv ያመነጫል"""
    year_dir = SYNKSAR_DATA_DIR / str(eth_year)
    manifest_path = year_dir / "manifest.csv"

    fieldnames = ["ethiopian_year", "month", "day", "text_file", "image_file"]
    rows = []

    for month_meta in ec.ETHIOPIAN_MONTHS:
        m_idx = month_meta["index"]
        m_prefix = month_meta["prefix"]
        days_count = ec.days_in_ethiopian_month(eth_year, m_idx)

        for d in range(1, days_count + 1):
            day_folder = year_dir / m_prefix / f"{d:02d}"
            text_file = ""
            image_file = ""

            txt_candidate = day_folder / "text.txt"
            if txt_candidate.exists() and txt_candidate.stat().st_size > 0:
                text_file = str(txt_candidate.relative_to(year_dir)).replace("\\", "/")

            for img_name in ["image.jpg", "image.png", "image.jpeg"]:
                img_cand = day_folder / img_name
                if img_cand.exists() and img_cand.stat().st_size > 0:
                    image_file = str(img_cand.relative_to(year_dir)).replace("\\", "/")
                    break

            rows.append({
                "ethiopian_year": eth_year,
                "month": m_idx,
                "day": d,
                "text_file": text_file,
                "image_file": image_file
            })

    with open(manifest_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return manifest_path


def validate_annual_content(eth_year: int) -> Dict[str, Any]:
    """
    የይዘት ማረጋገጫ (Content Validation) ያካሂዳል።
    የጎደሉ ቀናት፣ ምስሎች፣ ጽሑፎች፣ የተደገሙ መዛግብት እና ባዶ ፋይሎችን ይመረምራል።
    """
    expected_days = ec.days_in_ethiopian_year(eth_year)
    year_dir = SYNKSAR_DATA_DIR / str(eth_year)

    report = {
        "year": eth_year,
        "is_leap_year": ec.is_ethiopian_leap_year(eth_year),
        "expected_days": expected_days,
        "imported_dates": 0,
        "images_found": 0,
        "texts_found": 0,
        "missing_dates": [],
        "missing_images": [],
        "missing_texts": [],
        "empty_files": [],
        "duplicate_records": 0,
        "is_ready_for_publish": False,
        "summary_text": ""
    }

    if not year_dir.exists():
        report["summary_text"] = f"ለዓመተ ምሕረት {eth_year} የተገኘ ምንም ዳታ የለም!"
        return report

    all_db_contents = { (c["eth_month"], c["eth_day"]): c for c in db.get_all_contents(eth_year) }

    for month_meta in ec.ETHIOPIAN_MONTHS:
        m_idx = month_meta["index"]
        m_amharic = month_meta["amharic"]
        m_prefix = month_meta["prefix"]
        days_in_m = ec.days_in_ethiopian_month(eth_year, m_idx)

        for d in range(1, days_in_m + 1):
            date_label = f"{m_amharic} {d}"
            day_folder = year_dir / m_prefix / f"{d:02d}"

            # ጽሑፍ መፈተሽ
            txt_file = day_folder / "text.txt"
            has_valid_text = False
            if txt_file.exists():
                if txt_file.stat().st_size == 0:
                    report["empty_files"].append(str(txt_file.relative_to(year_dir)))
                else:
                    has_valid_text = True
            elif (m_idx, d) in all_db_contents and all_db_contents[(m_idx, d)]["amharic_text"].strip():
                has_valid_text = True

            # ምስል መፈተሽ
            has_valid_image = False
            for img_name in ["image.jpg", "image.png", "image.jpeg"]:
                img_f = day_folder / img_name
                if img_f.exists() and img_f.stat().st_size > 0:
                    has_valid_image = True
                    break
            if not has_valid_image:
                # በዳታቤዝ ውስጥ ካለ
                if (m_idx, d) in all_db_contents and all_db_contents[(m_idx, d)]["image_path"]:
                    img_db_path = Path(all_db_contents[(m_idx, d)]["image_path"])
                    if img_db_path.exists():
                        has_valid_image = True

            if has_valid_text or has_valid_image:
                report["imported_dates"] += 1

            if has_valid_image:
                report["images_found"] += 1
            else:
                report["missing_images"].append(date_label)

            if has_valid_text:
                report["texts_found"] += 1
            else:
                report["missing_texts"].append(date_label)

            if not has_valid_text and not has_valid_image:
                report["missing_dates"].append(date_label)

    # ዝግጁነት
    report["is_ready_for_publish"] = (report["imported_dates"] == expected_days and 
                                     len(report["missing_images"]) == 0 and 
                                     len(report["missing_texts"]) == 0)

    # የማጠቃለያ ጽሑፍ ማዘጋጀት
    summary_lines = [
        f"📊 የይዘት ማረጋገጫ ሪፖርት ({eth_year} ዓ.ም.)",
        f"━━━━━━━━━━━━━━━━━━",
        f"• የሚጠበቁ ቀናት ድምር: {expected_days}",
        f"• የገቡ የተሟሉ ቀናት: {report['imported_dates']}",
        f"• የተገኙ ምስሎች: {report['images_found']}",
        f"• የተገኙ ጽሑፎች: {report['texts_found']}",
        f"• የጎደሉ ቀናት ብዛት: {len(report['missing_dates'])}",
        f"• ምስል የሌላቸው ቀናት: {len(report['missing_images'])}",
        f"• ጽሑፍ የሌላቸው ቀናት: {len(report['missing_texts'])}",
        f"• ባዶ ፋይሎች: {len(report['empty_files'])}",
        f"• የተደገሙ መዛግብት: {report['duplicate_records']}",
        f"━━━━━━━━━━━━━━━━━━",
        f"ሁኔታ: {'✅ ለማተም ሙሉ በሙሉ ዝግጁ ነው!' if report['is_ready_for_publish'] else '⚠️ ያልተሟሉ መረጃዎች አሉ።'}"
    ]
    report["summary_text"] = "\n".join(summary_lines)

    return report


def seed_existing_workspace_data(target_year: int = 2018) -> Dict[str, Any]:
    """
    በአሁኑ ሰዓት በስራ ማውጫው ውስጥ ያሉትን 13 የወራት ፎልደሮች ምስሎች እና
    የ sinkisar_database.py ጽሑፎችን በቀጥታ ወደ SYNKSAR_DATA/ እና SQLite በፍጥነት ያስገባል።
    """
    year_dir = ensure_year_structure(target_year)

    conn = db.get_db_connection()
    cursor = conn.cursor()

    # 1. ጽሑፎችን ከ sinkisar_database.py ማንበብ
    texts_imported = 0
    try:
        import sinkisar_database
        sink_db = getattr(sinkisar_database, "DATABASE", {})
        for (m_name, day_num), day_data in sink_db.items():
            m_idx = ec.MONTH_NAME_TO_INDEX.get(m_name)
            if not m_idx:
                continue
            m_meta = ec.get_month_info(m_idx)
            day_folder = year_dir / m_meta["prefix"] / f"{day_num:02d}"
            day_folder.mkdir(parents=True, exist_ok=True)

            annual_lines = "\n".join(day_data.get("annual", []))
            monthly_lines = "\n".join(day_data.get("monthly", []))
            
            body_parts = []
            if annual_lines.strip():
                body_parts.append(annual_lines.strip())
            if monthly_lines.strip():
                body_parts.append(f"ወርኃዊ በዓላት\n\n{monthly_lines.strip()}")
            
            raw_body = "\n\n".join(body_parts)
            
            txt_path = day_folder / "text.txt"
            txt_path.write_text(raw_body, encoding="utf-8")

            cursor.execute("""
            INSERT INTO synksar_content (eth_year, eth_month, eth_day, title, amharic_text, status, updated_at)
            VALUES (?, ?, ?, ?, ?, 'ready', CURRENT_TIMESTAMP)
            ON CONFLICT(eth_year, eth_month, eth_day) DO UPDATE SET
                title = excluded.title,
                amharic_text = excluded.amharic_text,
                updated_at = CURRENT_TIMESTAMP;
            """, (target_year, m_idx, day_num, day_data.get("title", f"{m_name} {day_num}"), raw_body))
            texts_imported += 1
    except Exception as e:
        print(f"Error seeding texts: {e}")

    conn.commit()

    # 2. ምስሎችን ከ 13ቱ የወራት ፎልደሮች ማስተላለፍ
    images_imported = 0
    base_dir = Path(config.BASE_DIR)
    for m_meta in ec.ETHIOPIAN_MONTHS:
        m_name = m_meta["amharic"]
        m_idx = m_meta["index"]
        m_dir = base_dir / m_name

        if not m_dir.exists():
            continue

        days_count = ec.days_in_ethiopian_month(target_year, m_idx)
        for d in range(1, days_count + 1):
            day_folder = year_dir / m_meta["prefix"] / f"{d:02d}"
            target_img = day_folder / "image.jpg"

            # ፈልግ
            for candidate_name in [f"{d}.jpg", f"{d}.png", f"{d:02d}.jpg", f"{d:02d}.png"]:
                cand = m_dir / candidate_name
                if cand.exists() and cand.stat().st_size > 0:
                    if not target_img.exists() or target_img.stat().st_size == 0:
                        shutil.copy2(cand, target_img)
                    
                    cursor.execute("""
                    INSERT INTO synksar_content (eth_year, eth_month, eth_day, amharic_text, image_path, status, updated_at)
                    VALUES (?, ?, ?, '', ?, 'ready', CURRENT_TIMESTAMP)
                    ON CONFLICT(eth_year, eth_month, eth_day) DO UPDATE SET
                        image_path = excluded.image_path,
                        updated_at = CURRENT_TIMESTAMP;
                    """, (target_year, m_idx, d, str(target_img)))
                    images_imported += 1
                    break

    conn.commit()
    conn.close()

    # 3. Manifest ማመንጨት
    generate_manifest_csv(target_year)

    # 4. የማረጋገጫ ሪፖርት ማውጣት
    report = validate_annual_content(target_year)
    return {
        "texts_imported": texts_imported,
        "images_imported": images_imported,
        "validation_report": report
    }


def import_annual_zip(zip_path: Path, target_year: int) -> Dict[str, Any]:
    """ዓመታዊ የዚፕ ማህደርን ያስመጣል"""
    year_dir = ensure_year_structure(target_year)
    temp_extract_dir = SYNKSAR_DATA_DIR / f"temp_extract_{target_year}"

    if temp_extract_dir.exists():
        shutil.rmtree(temp_extract_dir)
    temp_extract_dir.mkdir(parents=True, exist_ok=True)

    conn = db.get_db_connection()
    cursor = conn.cursor()

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(temp_extract_dir)

        imported_count = 0
        for root, dirs, files in os.walk(temp_extract_dir):
            for file in files:
                file_path = Path(root) / file
                rel_parts = file_path.relative_to(temp_extract_dir).parts
                
                month_idx = None
                day_num = None
                
                for part in rel_parts:
                    part_lower = part.lower()
                    for m_info in ec.ETHIOPIAN_MONTHS:
                        if m_info["amharic"] in part or m_info["english"].lower() in part_lower:
                            month_idx = m_info["index"]
                            break
                    if part.isdigit() and 1 <= int(part) <= 30:
                        day_num = int(part)

                file_stem = file_path.stem
                if day_num is None and file_stem.isdigit() and 1 <= int(file_stem) <= 30:
                    day_num = int(file_stem)

                if month_idx and day_num:
                    month_meta = ec.get_month_info(month_idx)
                    target_day_dir = year_dir / month_meta["prefix"] / f"{day_num:02d}"
                    target_day_dir.mkdir(parents=True, exist_ok=True)

                    if file_path.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                        dest_img = target_day_dir / "image.jpg"
                        shutil.copy2(file_path, dest_img)
                        cursor.execute("""
                        INSERT INTO synksar_content (eth_year, eth_month, eth_day, amharic_text, image_path, status, updated_at)
                        VALUES (?, ?, ?, '', ?, 'ready', CURRENT_TIMESTAMP)
                        ON CONFLICT(eth_year, eth_month, eth_day) DO UPDATE SET
                            image_path = excluded.image_path,
                            updated_at = CURRENT_TIMESTAMP;
                        """, (target_year, month_idx, day_num, str(dest_img)))
                        imported_count += 1
                    elif file_path.suffix.lower() in [".txt"]:
                        dest_txt = target_day_dir / "text.txt"
                        shutil.copy2(file_path, dest_txt)
                        txt_content = dest_txt.read_text(encoding="utf-8", errors="ignore")
                        cursor.execute("""
                        INSERT INTO synksar_content (eth_year, eth_month, eth_day, amharic_text, status, updated_at)
                        VALUES (?, ?, ?, ?, 'ready', CURRENT_TIMESTAMP)
                        ON CONFLICT(eth_year, eth_month, eth_day) DO UPDATE SET
                            amharic_text = excluded.amharic_text,
                            updated_at = CURRENT_TIMESTAMP;
                        """, (target_year, month_idx, day_num, txt_content))
                        imported_count += 1

        conn.commit()
        generate_manifest_csv(target_year)
        val_report = validate_annual_content(target_year)
        return {
            "status": "success",
            "imported_files": imported_count,
            "validation_report": val_report
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "validation_report": None
        }
    finally:
        conn.close()
        if temp_extract_dir.exists():
            shutil.rmtree(temp_extract_dir, ignore_errors=True)
