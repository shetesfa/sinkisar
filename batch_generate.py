import sys, os, time
sys.stdout.reconfigure(encoding='utf-8')

from render_engine import render_sinkisar_image
from sinkisar_database import DATABASE

print(f'Starting batch generation for {len(DATABASE)} remaining Sinkisar images...')
start_time = time.time()

success_count = 0
failed = []

for (month, day), data in DATABASE.items():
    geez = data['geez']
    annual = data['annual']
    monthly = data['monthly']
    
    out_dir = month
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f'{day}.jpg')
    
    try:
        render_sinkisar_image(month, geez, annual, monthly, out_path)
        success_count += 1
    except Exception as ex:
        print(f'FAILED for {month} {day}: {ex}')
        failed.append((month, day, str(ex)))

elapsed = time.time() - start_time
print(f'Finished in {elapsed:.2f} seconds!')
print(f'Successfully rendered: {success_count}/{len(DATABASE)}')
if failed:
    print(f'Failed count: {len(failed)}: {failed}')
else:
    print('ALL 134 IMAGES GENERATED PERFECTLY WITH ZERO ERRORS!')
