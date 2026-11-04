"""
Ethiopian Calendar Utility Module
ይህ ሞጁል የኢትዮጵያን ዘመን አቆጣጠር እና የጎርጎርዮሳውያንን የቀን መቁጠሪያ በትክክል ያሰላል።
"""

import datetime
from zoneinfo import ZoneInfo
from typing import Tuple, Optional

# 13ቱ የኢትዮጵያ ወራት
ETHIOPIAN_MONTHS = [
    {"index": 1, "amharic": "መስከረም", "english": "Meskerem", "prefix": "01_Meskerem"},
    {"index": 2, "amharic": "ጥቅምት", "english": "Tikimt", "prefix": "02_Tikimt"},
    {"index": 3, "amharic": "ህዳር", "english": "Hidar", "prefix": "03_Hidar"},
    {"index": 4, "amharic": "ታህሳስ", "english": "Tahsas", "prefix": "04_Tahsas"},
    {"index": 5, "amharic": "ጥር", "english": "Tir", "prefix": "05_Tir"},
    {"index": 6, "amharic": "የካቲት", "english": "Yekatit", "prefix": "06_Yekatit"},
    {"index": 7, "amharic": "መጋቢት", "english": "Megabit", "prefix": "07_Megabit"},
    {"index": 8, "amharic": "ሚያዚያ", "english": "Miyazya", "prefix": "08_Miyazya"},
    {"index": 9, "amharic": "ግንቦት", "english": "Ginbot", "prefix": "09_Ginbot"},
    {"index": 10, "amharic": "ሰኔ", "english": "Sene", "prefix": "10_Sene"},
    {"index": 11, "amharic": "ሐምሌ", "english": "Hamle", "prefix": "11_Hamle"},
    {"index": 12, "amharic": "ነሐሴ", "english": "Nehase", "prefix": "12_Nehase"},
    {"index": 13, "amharic": "ጳጉሜ", "english": "Pagume", "prefix": "13_Pagume"},
]

MONTH_NAME_TO_INDEX = {m["amharic"]: m["index"] for m in ETHIOPIAN_MONTHS}
MONTH_NAME_TO_INDEX.update({m["english"].lower(): m["index"] for m in ETHIOPIAN_MONTHS})
INDEX_TO_MONTH = {m["index"]: m for m in ETHIOPIAN_MONTHS}


def to_geez_number(num: int) -> str:
    """የአረብኛ ቁጥሮችን ወደ ግዕዝ ቁጥሮች ይለውጣል (1 -> ፩, 25 -> ፳፭)"""
    if num <= 0:
        return str(num)
    geez_ones = ["", "፩", "፪", "፫", "፬", "፭", "፮", "፯", "፰", "፱"]
    geez_tens = ["", "፲", "፳", "፴", "፵", "፶", "፷", "፸", "፹", "፺"]
    
    if num < 10:
        return geez_ones[num]
    elif num < 100:
        ten = num // 10
        one = num % 10
        return geez_tens[ten] + geez_ones[one]
    elif num < 1000:
        hundred = num // 100
        rem = num % 100
        h_str = ("" if hundred == 1 else geez_ones[hundred]) + "፻"
        if rem == 0:
            return h_str
        return h_str + to_geez_number(rem)
    elif num < 10000:
        thousand = num // 100
        rem = num % 100
        res = ""
        if thousand > 0:
            res += to_geez_number(thousand) + "፻"
        if rem > 0:
            res += to_geez_number(rem)
        return res
    return str(num)


def is_ethiopian_leap_year(year: int) -> bool:
    """የኢትዮጵያ ዓመት ሰግር (ዘመነ ሉቃስ) መሆኑን ያረጋግጣል። (በየ4 ዓመቱ ቀሪው 3 ከሆነ)"""
    return (year % 4) == 3


def days_in_ethiopian_month(year: int, month: int) -> int:
    """በተሰጠው ወር ውስጥ ያሉትን የቀናት ብዛት ይመልሳል (1-12 ወራት 30 ቀናት፣ ጳጉሜ 5 ወይም 6 ቀናት)"""
    if 1 <= month <= 12:
        return 30
    elif month == 13:
        return 6 if is_ethiopian_leap_year(year) else 5
    raise ValueError(f"ልክ ያልሆነ የኢትዮጵያ ወር: {month} (ከ 1 እስከ 13 መሆን አለበት)")


def days_in_ethiopian_year(year: int) -> int:
    """በዓመቱ ውስጥ ያሉትን አጠቃላይ ቀናት ይመልሳል (365 ወይም 366)"""
    return 366 if is_ethiopian_leap_year(year) else 365


def gregorian_to_jdn(year: int, month: int, day: int) -> int:
    """የጎርጎርዮሳውያን ቀንን ወደ ጁሊያን ቀን ቁጥር (Julian Day Number) ይለውጣል"""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def jdn_to_gregorian(jdn: int) -> Tuple[int, int, int]:
    """የጁሊያን ቀን ቁጥርን ወደ ጎርጎርዮሳውያን ቀን ይለውጣል"""
    l = jdn + 68569
    n = (4 * l) // 146097
    l = l - (146097 * n + 3) // 4
    i = (4000 * (l + 1)) // 1461001
    l = l - (1461 * i) // 4 + 31
    j = (80 * l) // 2447
    day = l - (2447 * j) // 80
    l = j // 11
    month = j + 2 - (12 * l)
    year = 100 * (n - 49) + i + l
    return year, month, day


def jdn_to_ethiopian(jdn: int) -> Tuple[int, int, int]:
    """የጁሊያን ቀን ቁጥርን ወደ ኢትዮጵያ ቀን ይለውጣል"""
    r = (jdn - 1723856) % 1461
    n = (r % 365) + 365 * (r // 1460)
    year = 4 * ((jdn - 1723856) // 1461) + (r // 365) - (r // 1460)
    month = (n // 30) + 1
    day = (n % 30) + 1
    return year, month, day


def ethiopian_to_jdn(year: int, month: int, day: int) -> int:
    """የኢትዮጵያን ቀን ወደ ጁሊያን ቀን ቁጥር ይለውጣል"""
    return (1723856 + 365) + 365 * (year - 1) + (year // 4) + 30 * (month - 1) + day - 1


def gregorian_to_ethiopian(year: int, month: int, day: int) -> Tuple[int, int, int]:
    """የጎርጎርዮሳውያን ቀንን ወደ ኢትዮጵያ ቀን ይለውጣል (ዓመት፣ ወር፣ ቀን)"""
    jdn = gregorian_to_jdn(year, month, day)
    return jdn_to_ethiopian(jdn)


def ethiopian_to_gregorian(year: int, month: int, day: int) -> Tuple[int, int, int]:
    """የኢትዮጵያን ቀን ወደ ጎርጎርዮሳውያን ቀን ይለውጣል (ዓመት፣ ወር፣ ቀን)"""
    jdn = ethiopian_to_jdn(year, month, day)
    return jdn_to_gregorian(jdn)


def get_addis_ababa_now(tz_name: str = "Africa/Addis_Ababa") -> datetime.datetime:
    """የአዲስ አበባን ወቅታዊ ሰዓት እና ቀን ይመልሳል"""
    tz = ZoneInfo(tz_name)
    return datetime.datetime.now(tz)


def get_today_ethiopian(tz_name: str = "Africa/Addis_Ababa") -> Tuple[int, int, int]:
    """የዛሬን ትክክለኛ የኢትዮጵያ ቀን ይመልሳል (ዓመት፣ ወር፣ ቀን)"""
    now = get_addis_ababa_now(tz_name)
    return gregorian_to_ethiopian(now.year, now.month, now.day)


def get_tomorrow_ethiopian(tz_name: str = "Africa/Addis_Ababa") -> Tuple[int, int, int]:
    """የነገን ትክክለኛ የኢትዮጵያ ቀን ይመልሳል (ዓመት፣ ወር፣ ቀን)"""
    now = get_addis_ababa_now(tz_name)
    tomorrow = now + datetime.timedelta(days=1)
    return gregorian_to_ethiopian(tomorrow.year, tomorrow.month, tomorrow.day)


def get_month_info(month: int) -> dict:
    """የወሩን መረጃ ይመልሳል"""
    return INDEX_TO_MONTH.get(month, {"index": month, "amharic": f"ወር {month}", "english": f"Month {month}"})


def format_ethiopian_date_str(year: int, month: int, day: int, use_geez: bool = True) -> str:
    """ቀኑን በሚያምር የአማርኛ ቅርጸት ያዘጋጃል (ምሳሌ፡ ሐምሌ ፩ ቀን ወይም ሐምሌ 1 ቀን)"""
    month_info = get_month_info(month)
    month_name = month_info["amharic"]
    day_str = to_geez_number(day) if use_geez else str(day)
    return f"{month_name} {day_str} ቀን"
