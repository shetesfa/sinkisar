import sys, re, os
sys.stdout.reconfigure(encoding='utf-8')

geez_to_int = {
    '፩': 1, '፪': 2, '፫': 3, '፬': 4, '፭': 5, '፮': 6, '፯': 7, '፰': 8, '፱': 9, '፲': 10,
    '፲፩': 11, '፲፪': 12, '፲፫': 13, '፲፬': 14, '፲፭': 15, '፲፮': 16, '፲፯': 17, '፲፰': 18, '፲፱': 19, '፳': 20,
    '፳፩': 21, '፳፪': 22, '፳፫': 23, '፳፬': 24, '፳፭': 25, '፳፮': 26, '፳፯': 27, '፳፰': 28, '፳፱': 29, '፴': 30,
    '፩፪': 12, '፩፫': 13, '፩፬': 14, '፩፭': 15, '፩፮': 16, '፩፯': 17, '፩፰': 18, '፩፱': 19, '፪፫': 23, '፪፯': 27,
    '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10
}

int_to_geez = {v: k for k, v in [
    ('፩', 1), ('፪', 2), ('፫', 3), ('፬', 4), ('፭', 5), ('፮', 6), ('፯', 7), ('፰', 8), ('፱', 9), ('፲', 10),
    ('፲፩', 11), ('፲፪', 12), ('፲፫', 13), ('፲፬', 14), ('፲፭', 15), ('፲፮', 16), ('፲፯', 17), ('፲፰', 18), ('፲፱', 19), ('፳', 20),
    ('፳፩', 21), ('፳፪', 22), ('፳፫', 23), ('፳፬', 24), ('፳፭', 25), ('፳፮', 26), ('፳፯', 27), ('፳፰', 28), ('፳፱', 29), ('፴', 30)
]}

with open('full_user_input.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# Normalize month names
# መስከረም, ጥቅምት, ህዳር (ኅዳር), ታህሳስ (ታኅሳስ), ጥር, የካቲት, መጋቢት, ሚያዚያ (ሚያዝያ), ግንቦት, ሰኔ, ሐምሌ, ነሐሴ (ነሃሴ), ጳጉሜ (ጳጉሜን)
month_aliases = {
    'መስከረም': 'መስከረም',
    'ጥቅምት': 'ጥቅምት',
    'ኅዳር': 'ህዳር',
    'ህዳር': 'ህዳር',
    'ታኅሳስ': 'ታህሳስ',
    'ታህሳስ': 'ታህሳስ',
    'ጥር': 'ጥር',
    'የካቲት': 'የካቲት',
    'መጋቢት': 'መጋቢት',
    'ሚያዝያ': 'ሚያዚያ',
    'ሚያዚያ': 'ሚያዚያ',
    'ግንቦት': 'ግንቦት',
    'ሰኔ': 'ሰኔ',
    'ሐምሌ': 'ሐምሌ',
    'ነሐሴ': 'ነሐሴ',
    'ነሃሴ': 'ነሐሴ',
    'ጳጉሜ': 'ጳጉሜ',
    'ጳጉሜን': 'ጳጉሜ'
}

# Regex to match headers like: ሐምሌ ፩ ቀን የሚከበሩ ...
# or መስከረም ፱ ቀን የሚከበሩ ...
month_names = list(month_aliases.keys())
pattern = r'(' + '|'.join(month_names) + r')\s*([፩-፴\d\s]+)\s*ቀን'

# Let's find all sections
matches = list(re.finditer(pattern, text))
print(f'Total matches found: {len(matches)}')

entries = {} # (norm_month, day_int) -> raw_text
for i, m in enumerate(matches):
    raw_m = m.group(1)
    norm_m = month_aliases[raw_m]
    raw_d = m.group(2).strip().replace(' ', '')
    d_int = geez_to_int.get(raw_d)
    if not d_int:
        print(f'Unknown day geez: {raw_d} in {raw_m}')
        continue
    
    start_pos = m.start()
    end_pos = matches[i+1].start() if i+1 < len(matches) else len(text)
    entry_text = text[start_pos:end_pos].strip()
    
    entries[(norm_m, d_int)] = entry_text

print(f'Successfully parsed {len(entries)} unique (month, day) entries!')

# Check against what user requested
requested = {
    'መስከረም': [1, 2],
    'ጥቅምት': [17, 22, 24, 28, 30],
    'ህዳር': [i for i in range(1, 31) if i not in [3, 4, 5, 6]],
    'ታህሳስ': [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 27, 30],
    'ጥር': [1, 3, 5, 12, 16, 30],
    'የካቲት': [27, 28, 29, 30],
    'መጋቢት': [8],
    'ሚያዚያ': [5, 17, 28],
    'ግንቦት': [7, 9, 18],
    'ሰኔ': list(range(1, 31)),
    'ሐምሌ': list(range(1, 31)),
    'ነሐሴ': [1, 2, 3, 6, 10, 12, 13, 14, 16, 17, 18, 21]
}

available_req = 0
missing_req = []
for m, days in requested.items():
    for d in days:
        if (m, d) in entries:
            available_req += 1
        else:
            missing_req.append((m, d))

print(f'Requested available in user text: {available_req}')
print(f'Requested missing from user text: {len(missing_req)}')
print('Missing breakdown by month:')
from collections import Counter
print(Counter([m for m, d in missing_req]))
