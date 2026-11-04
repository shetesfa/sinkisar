import os, sys
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image, ImageDraw, ImageFont

W, H = 960, 1280

C_YELLOW = (244, 188, 18)
C_BLUE = (43, 76, 175)
C_WHITE = (255, 255, 255)
C_TITLE_YELLOW = (255, 215, 0)
C_TEXT_BLACK = (0, 0, 0)

FONT_PATH = 'C:/Windows/Fonts/VGUnicode.TTF'

# Prepare clean footer once
footer_path = 'footer_clean.png'
if not os.path.exists(footer_path):
    footer = Image.open('footer_sample.png').resize((W, 100))
    f_draw = ImageDraw.Draw(footer)
    f_draw.rectangle([(0, 0), (28, 100)], fill=C_BLUE)
    footer.save(footer_path)

CLEAN_FOOTER = Image.open(footer_path)

def wrap_text(text, font, max_w, draw):
    # If text fits in max_w, return [text]
    bbox = draw.textbbox((0, 0), text, font=font)
    if bbox[2] - bbox[0] <= max_w:
        return [text]
    # Otherwise wrap by words
    words = text.split(' ')
    lines = []
    curr = ''
    for w in words:
        cand = (curr + ' ' + w).strip()
        bbox = draw.textbbox((0, 0), cand, font=font)
        if bbox[2] - bbox[0] <= max_w:
            curr = cand
        else:
            if curr:
                lines.append(curr)
            curr = '   ' + w # indent continuation line
    if curr:
        lines.append(curr)
    return lines

def render_sinkisar_image(month_name, day_geez, annual_items, monthly_items, output_path):
    """
    Renders a complete, authentic PixelLab-styled Ethiopian Synaxarium poster.
    """
    img = Image.new('RGB', (W, H), C_YELLOW)
    draw = ImageDraw.Draw(img)
    
    # 1. Fonts selection based on total content length
    total_items = len(annual_items) + len(monthly_items)
    
    if total_items <= 10:
        f_size = 42
        line_h = 60
        b_font_size = 54
        title_font_size = 68
    elif total_items <= 15:
        f_size = 38
        line_h = 53
        b_font_size = 52
        title_font_size = 66
    elif total_items <= 20:
        f_size = 34
        line_h = 47
        b_font_size = 48
        title_font_size = 64
    else:
        f_size = 30
        line_h = 41
        b_font_size = 46
        title_font_size = 62

    font_text = ImageFont.truetype(FONT_PATH, f_size)
    font_banner = ImageFont.truetype(FONT_PATH, b_font_size)
    font_title = ImageFont.truetype(FONT_PATH, title_font_size)
    
    # Wrap all items
    max_text_w = 720
    ann_lines = []
    for it in annual_items:
        ann_lines.extend(wrap_text(it, font_text, max_text_w, draw))
        
    mon_lines = []
    for it in monthly_items:
        mon_lines.extend(wrap_text(it, font_text, max_text_w, draw))
        
    # Calculate heights
    banner_h = 95
    y_start_ann = 115 + banner_h + 15
    ann_total_h = len(ann_lines) * line_h
    
    # Ideal split position for monthly banner
    # Available height between 115 and 1180 is 1065px
    y_banner2 = y_start_ann + ann_total_h + 20
    # Keep banner2 in reasonable bounds
    min_b2 = 450
    max_b2 = 1180 - banner_h - (len(mon_lines) * line_h) - 20
    if max_b2 > min_b2:
        y_banner2 = max(min_b2, min(y_banner2, max_b2))
    else:
        y_banner2 = min_b2
        
    y_banner2_end = y_banner2 + banner_h
    
    # Draw Background Chevrons
    # Tip 1 is between 115 and y_banner2
    mid1 = (115 + y_banner2) // 2
    poly1 = [
        (0, 115),
        (762, 115),
        (762, 215),
        (912, mid1),
        (762, y_banner2),
        (0, y_banner2)
    ]
    draw.polygon(poly1, fill=C_WHITE)
    
    # Tip 2 is between y_banner2 and 1180
    mid2 = (y_banner2 + 1180) // 2
    poly2 = [
        (0, y_banner2),
        (762, y_banner2),
        (762, y_banner2_end),
        (912, mid2),
        (762, 1180),
        (0, 1180)
    ]
    draw.polygon(poly2, fill=C_WHITE)
    
    # Header: Blue block + white separator
    draw.rectangle([(0, 0), (W, 112)], fill=C_BLUE)
    draw.rectangle([(0, 113), (W, 115)], fill=C_WHITE)
    
    # Header Title
    title_text = f'ስንክሳር {month_name} {day_geez}'
    t_bbox = draw.textbbox((0, 0), title_text, font=font_title)
    tw = t_bbox[2] - t_bbox[0]
    th = t_bbox[3] - t_bbox[1]
    ty = (112 - th) // 2 - 4
    draw.text(((W - tw)//2, ty), title_text, fill=C_TITLE_YELLOW, font=font_title, stroke_width=1, stroke_fill=C_TITLE_YELLOW)
    
    # Banner 1
    draw.rectangle([(0, 116), (762, 215)], fill=C_BLUE)
    b1_text = 'ዓመታዊ የቅዱሳን በዓላት'
    b1_bbox = draw.textbbox((0, 0), b1_text, font=font_banner)
    b1_h = b1_bbox[3] - b1_bbox[1]
    draw.text((25, 116 + (99 - b1_h)//2), b1_text, fill=C_WHITE, font=font_banner, stroke_width=1, stroke_fill=C_WHITE)
    
    # Annual Items Text
    curr_y = y_start_ann
    for line in ann_lines:
        draw.text((25, curr_y), line, fill=C_TEXT_BLACK, font=font_text, stroke_width=1, stroke_fill=C_TEXT_BLACK)
        curr_y += line_h
        
    # Banner 2
    draw.rectangle([(0, y_banner2), (762, y_banner2_end)], fill=C_BLUE)
    b2_text = 'ወርኃዊ የቅዱሳን በዓላት'
    b2_bbox = draw.textbbox((0, 0), b2_text, font=font_banner)
    b2_h = b2_bbox[3] - b2_bbox[1]
    draw.text((25, y_banner2 + (banner_h - b2_h)//2), b2_text, fill=C_WHITE, font=font_banner, stroke_width=1, stroke_fill=C_WHITE)
    
    # Monthly Items Text
    curr_y = y_banner2_end + 20
    for line in mon_lines:
        draw.text((25, curr_y), line, fill=C_TEXT_BLACK, font=font_text, stroke_width=1, stroke_fill=C_TEXT_BLACK)
        curr_y += line_h
        
    # Footer
    img.paste(CLEAN_FOOTER, (0, 1180))
    
    # Ensure directory exists and save
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    img.save(output_path, quality=95)
    print(f'Successfully rendered {output_path}')

if __name__ == '__main__':
    # Quick test
    ann = ['፩. ቅዱስ እስጢፋኖስ ቀዳሜ ሰማዕት', '፪. ቅዱሳን ሰማዕታተ አክሚም']
    mon = ['፩. ልደታ ለማርያም ድንግል', '፪. ቅዱሳን ኢያቄም ወሐና']
    render_sinkisar_image('ጥር', '፩', ann, mon, 'test_sample_tir1.jpg')
