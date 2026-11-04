import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('full_user_input.txt', 'r', encoding='utf-8') as f:
    text = f.read()

geez_to_int = {
    '፩': 1, '፪': 2, '፫': 3, '፬': 4, '፭': 5, '፮': 6, '፯': 7, '፰': 8, '፱': 9, '፲': 10,
    '፲፩': 11, '፲፪': 12, '፲፫': 13, '፲፬': 14, '፲፭': 15, '፲፮': 16, '፲፯': 17, '፲፰': 18, '፲፱': 19, '፳': 20,
    '፳፩': 21, '፳፪': 22, '፳፫': 23, '፳፬': 24, '፳፭': 25, '፳፮': 26, '፳፯': 27, '፳፰': 28, '፳፱': 29, '፴': 30,
    '፩፪': 12, '፩፫': 13, '፩፬': 14, '፩፭': 15, '፩፮': 16, '፩፯': 17, '፩፰': 18, '፩፱': 19, '፪፫': 23, '፪፯': 27,
    '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10
}

months = ['መስከረም', 'ጥቅምት', 'ኅዳር', 'ህዳር', 'ታኅሳስ', 'ታህሳስ', 'ጥር', 'የካቲት', 'መጋቢት', 'ሚያዝያ', 'ሚያዚያ', 'ግንቦት', 'ሰኔ', 'ሐምሌ', 'ነሐሴ', 'ነሃሴ', 'ጳጉሜ']
m_str = '|'.join(months)
pattern = r'(' + m_str + r')\s*([፩-፴\d\s]+?)\s*(?:ቀን)?\s*(?:የሚከበሩ|ሚከበሩ|የሚከቀሩ|ነሚከበሪ|የ\s*ቅዱሳን|በዓላት)'

matches = list(re.finditer(pattern, text))
print(f'Total matches: {len(matches)}')
found = set()
for m in matches:
    mon = m.group(1).replace('ኅዳር', 'ህዳር').replace('ታኅሳስ', 'ታህሳስ').replace('ሚያዝያ', 'ሚያዚያ').replace('ነሃሴ', 'ነሐሴ')
    d_raw = m.group(2).strip().replace(' ', '')
    d_int = geez_to_int.get(d_raw)
    if d_int:
        found.add((mon, d_int))

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

avail = 0
missing = []
for m, days in requested.items():
    for d in days:
        if (m, d) in found:
            avail += 1
        else:
            missing.append((m, d))

total_req = sum(len(v) for v in requested.values())
print(f'Requested available: {avail}/{total_req}')
print(f'Missing ({len(missing)}): {missing}')
