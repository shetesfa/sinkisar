"""
Synksar Auto Publisher - Telegram Message Formatter
ይህ ሞጁል የስንክሳር መልእክትን በተጠቃሚው ትክክለኛ ቅርጸት ያዘጋጃል (ክሊክ በሚደረግ HTML Link!)።
"""

import html
import re
import config
from ethiopian_calendar import get_month_info, to_geez_number


def build_full_post_caption(
    month_name: str,
    day_num: int,
    amharic_body: str,
    title: str = None,
    use_html: bool = True
) -> str:
    """
    ለቴሌግራም ቻናል የሚላከውን ሙሉ መልእክት ያዘጋጃል።
    ተጠቃሚው በሰጠው መመሪያ መሰረት፦
    - መክፈቻ ጸሎት
    - [ወር] [ቀን] ቀን የሚከበሩ ዓመታዊ የቅዱሳን በዓላት (እና ወርኃዊ)
    - telegram channel (hyperlink)
    - telegram channel (hyperlink)
    - Telegram group (hyperlink)
    - Telegram group (hyperlink)
    - አጸደ ትጉሃን ሰንበት ትምህርት ቤት / Atsede tguhan sunday school
    (የቦት ሊንክ አይካተትም!)
    """
    day_geez = to_geez_number(day_num)
    
    # የሰው ጽሑፍ በ HTML እንዳይበላሽ escape ማድረግ
    if use_html:
        body_clean = html.escape(amharic_body.strip())
    else:
        body_clean = amharic_body.strip()

    # የመክፈቻ ጸሎት ካልተካተተ እንጨምራለን
    has_prayer = "ለእግዚአብሔር ምስጋና ይሁን" in body_clean
    prayer_header = ""
    if not has_prayer:
        prayer_header = f"{config.OPENING_PRAYER}\n"

    # የወርና ቀን ርዕስ ካልተካተተ እንጨምራለን
    expected_header_match = f"{month_name}" in body_clean and ("ቀን" in body_clean or "በዓላት" in body_clean)
    date_header = ""
    if not expected_header_match:
        date_header = f"{month_name} {day_geez} ቀን የሚከበሩ ዓመታዊ የቅዱሳን በዓላት\n\n"

    # ግርጌ (Footer hyperlinks - NO BOT)
    if use_html:
        footer = (
            f"\n\n"
            f"<a href=\"{config.CHANNEL_LINK_URL}\">{config.CHANNEL_LINK_NAME}</a>\n"
            f"<a href=\"{config.CHANNEL_LINK_URL}\">{config.CHANNEL_LINK_NAME}</a>\n\n"
            f"<a href=\"{config.GROUP_LINK_URL}\">{config.GROUP_LINK_NAME}</a>\n"
            f"<a href=\"{config.GROUP_LINK_URL}\">{config.GROUP_LINK_NAME}</a>\n\n"
            f"{config.SUNDAY_SCHOOL_AMHARIC}\n"
            f"{config.SUNDAY_SCHOOL_ENGLISH}"
        )
    else:
        footer = (
            f"\n\n"
            f"{config.CHANNEL_LINK_NAME} ({config.CHANNEL_LINK_URL})\n"
            f"{config.CHANNEL_LINK_NAME} ({config.CHANNEL_LINK_URL})\n\n"
            f"{config.GROUP_LINK_NAME} ({config.GROUP_LINK_URL})\n"
            f"{config.GROUP_LINK_NAME} ({config.GROUP_LINK_URL})\n\n"
            f"{config.SUNDAY_SCHOOL_AMHARIC}\n"
            f"{config.SUNDAY_SCHOOL_ENGLISH}"
        )

    full_message = f"{prayer_header}{date_header}{body_clean}{footer}".strip()
    return full_message


def split_text_for_telegram(text: str, max_length: int = 4096) -> list[str]:
    """ረጅም ጽሑፍን ወደ ቴሌግራም ገደብ በንጽህና ይከፋፍላል"""
    if len(text) <= max_length:
        return [text]

    chunks = []
    lines = text.split("\n")
    current_chunk = ""

    for line in lines:
        if len(current_chunk) + len(line) + 1 <= max_length:
            current_chunk += (line + "\n")
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = line + "\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks
