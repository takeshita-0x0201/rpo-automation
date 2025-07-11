#!/usr/bin/env python3
"""
Chrome拡張機能用のアイコンを生成するスクリプト
SVGから各サイズのPNGを生成（Pillowライブラリのみ使用）
"""

import os
from PIL import Image, ImageDraw, ImageFont

def create_icon(size):
    """指定サイズのアイコンを作成"""
    # 背景色とテキスト色
    bg_color = (44, 62, 80)  # #2c3e50
    text_color = (255, 255, 255)  # #ffffff
    bar_colors = [
        (52, 152, 219),  # #3498db
        (39, 174, 96),   # #27ae60
        (231, 76, 60)    # #e74c3c
    ]
    
    # 画像を作成
    img = Image.new('RGBA', (size, size), bg_color)
    draw = ImageDraw.Draw(img)
    
    # 角丸の背景を描画
    corner_radius = int(size * 0.125)  # 16/128 = 0.125
    draw.rounded_rectangle(
        [(0, 0), (size-1, size-1)],
        radius=corner_radius,
        fill=bg_color
    )
    
    # "RPO" テキストを描画
    # フォントサイズを調整
    font_size = max(8, int(size * 0.28))  # 最小8px、36/128 = 0.28
    try:
        # システムフォントを試す
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except:
        # デフォルトフォントを使用
        font = None
    
    text = "RPO"
    # テキストの位置を計算
    if font:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (size - text_width) // 2
        text_y = int(size * 0.15)  # 上部に配置
        draw.text((text_x, text_y), text, fill=text_color, font=font)
    else:
        # フォントがない場合は簡易的なテキスト表示
        text_x = size // 4
        text_y = int(size * 0.15)
        draw.text((text_x, text_y), text, fill=text_color)
    
    # プログレスバーを描画
    bar_width = int(size * 0.625)  # 80/128 = 0.625
    bar_height = int(size * 0.0625)  # 8/128 = 0.0625
    bar_x = int(size * 0.1875)  # 24/128 = 0.1875
    bar_spacing = int(size * 0.125)  # 16/128 = 0.125
    
    # 3本のバー（異なる長さ）
    bar_lengths = [1.0, 0.75, 0.5]  # 100%, 75%, 50%
    
    for i, (color, length) in enumerate(zip(bar_colors, bar_lengths)):
        y = int(size * 0.47) + (bar_height + int(bar_spacing * 0.5)) * i
        actual_width = int(bar_width * length)
        
        # 角丸の四角形を描画
        draw.rounded_rectangle(
            [(bar_x, y), (bar_x + actual_width, y + bar_height)],
            radius=bar_height // 2,
            fill=color
        )
    
    return img

def main():
    """メイン処理"""
    # アイコンサイズ
    sizes = [16, 32, 48, 128]
    
    # 出力ディレクトリ
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'src', 'extension', 'icons')
    os.makedirs(output_dir, exist_ok=True)
    
    print("Generating Chrome extension icons...")
    
    for size in sizes:
        # アイコンを生成
        icon = create_icon(size)
        
        # ファイルパス
        output_path = os.path.join(output_dir, f'icon-{size}.png')
        
        # 保存
        icon.save(output_path, 'PNG')
        print(f"Created: icon-{size}.png")
    
    print("Icon generation completed!")

if __name__ == "__main__":
    main()