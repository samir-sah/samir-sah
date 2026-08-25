#!/usr/bin/env python3
"""
dotify.py — photo → dot-matrix portrait SVG

Usage:
  python dotify.py input.png -o assets/portrait.svg --cols 88 --equalize --detail 0.5 --color
  python dotify.py input.png -o assets/portrait.svg --cols 88 --equalize --detail 0.5 --circle
  python dotify.py input.png -o assets/portrait.txt --mode ascii --cols 80
"""

import argparse
import sys
import math
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter, ImageEnhance

def parse_args():
    p = argparse.ArgumentParser(description="Convert photo to dot-matrix SVG")
    p.add_argument("input", help="Input image file (PNG/JPG)")
    p.add_argument("-o", "--output", required=True, help="Output SVG/TXT file")
    p.add_argument("--cols", type=int, default=88, help="Dots across (default: 88)")
    p.add_argument("--equalize", action="store_true", help="Histogram equalize before sampling (required for faces)")
    p.add_argument("--detail", type=float, default=0.5, help="Local contrast enhancement factor (default: 0.5)")
    p.add_argument("--color", action="store_true", help="Sample true color per dot (single SVG for both themes)")
    p.add_argument("--circle", action="store_true", help="Circular mask with feathered edge")
    p.add_argument("--square", action="store_true", help="Square crop (default)")
    p.add_argument("--focus", type=str, default="0.5,0.5", help="Focus point for square crop as 'x,y' (0-1 each)")
    p.add_argument("--invert", action="store_true", help="Invert brightness (dark subject on light bg)")
    p.add_argument("--mode", choices=["dots", "binary", "ascii", "braille"], default="dots", help="Output mode")
    p.add_argument("--reveal", action="store_true", help="Row-by-row draw-in animation on load")
    p.add_argument("--reveal-time", type=float, default=1.5, help="Reveal animation duration in seconds")
    p.add_argument("--reveal-fade", type=float, default=0.3, help="Reveal fade-in duration in seconds")
    p.add_argument("--reveal-dir", choices=["up", "down"], default="up", help="Reveal direction")
    p.add_argument("--animate", action="store_true", help="Slow shimmer sweep animation")
    p.add_argument("--accent", type=str, default="#58a6ff", help="Accent color for monochrome mode (default: GitHub blue)")
    p.add_argument("--bg", type=str, default="transparent", help="Background color (default: transparent)")
    p.add_argument("--dot-shape", choices=["circle", "square"], default="circle", help="Dot shape")
    return p.parse_args()

def load_image(path):
    img = Image.open(path).convert("RGBA")
    return img

def apply_alpha_mask(img):
    """If image has alpha channel, use it as mask and compute stats from non-transparent region only."""
    if img.mode != "RGBA":
        return img, None
    alpha = img.split()[-1]
    mask = alpha.point(lambda a: 255 if a > 128 else 0)
    return img, mask

def equalize_image(img, mask=None):
    """Histogram equalize the luminance channel, optionally masked."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    r, g, b, a = img.split()
    y = Image.merge("L", (r, g, b)).convert("L")
    if mask:
        y = Image.composite(y, Image.new("L", y.size, 0), mask)
    y_eq = ImageOps.equalize(y, mask=mask)
    r_eq = ImageOps.colorize(y_eq, (0, 0, 0), (255, 255, 255)).split()[0]
    g_eq = ImageOps.colorize(y_eq, (0, 0, 0), (255, 255, 255)).split()[0]
    b_eq = ImageOps.colorize(y_eq, (0, 0, 0), (255, 255, 255)).split()[0]
    return Image.merge("RGBA", (r_eq, g_eq, b_eq, a))

def enhance_detail(img, factor):
    """Local contrast enhancement (unsharp mask style)."""
    if factor <= 0:
        return img
    blurred = img.filter(ImageFilter.GaussianBlur(radius=2))
    enhanced = Image.blend(img, blurred, -factor)
    return enhanced

def crop_and_resize(img, cols, circle, focus, mask=None):
    """Crop to square/circle and resize to target grid."""
    w, h = img.size
    size = min(w, h)
    fx, fy = map(float, focus.split(","))
    fx = max(0.0, min(1.0, fx))
    fy = max(0.0, min(1.0, fy))
    left = int((w - size) * fx)
    top = int((h - size) * fy)
    right = left + size
    bottom = top + size
    img = img.crop((left, top, right, bottom))
    if mask:
        mask = mask.crop((left, top, right, bottom))
    img = img.resize((cols, cols), Image.Resampling.LANCZOS)
    if mask:
        mask = mask.resize((cols, cols), Image.Resampling.LANCZOS)
    return img, mask

def sample_grid(img, cols, invert, color_mode, mask=None):
    """Sample brightness/color at each grid cell."""
    pixels = img.load()
    mask_px = mask.load() if mask else None
    grid = []
    for y in range(cols):
        row = []
        for x in range(cols):
            if mask_px and mask_px[x, y] < 128:
                row.append(None)
                continue
            r, g, b, a = pixels[x, y]
            if color_mode:
                brightness = 1.0 - (0.299*r + 0.587*g + 0.114*b) / 255.0
                row.append((brightness, (r, g, b)))
            else:
                brightness = 1.0 - (0.299*r + 0.587*g + 0.114*b) / 255.0
                if invert:
                    brightness = 1.0 - brightness
                row.append((brightness, None))
        grid.append(row)
    return grid

def brightness_to_radius(b, max_r, min_r=0.15):
    """Map brightness 0-1 to dot radius factor."""
    return min_r + (max_r - min_r) * b

def generate_svg(grid, cols, color_mode, accent, bg, dot_shape, circle, reveal, reveal_time, reveal_fade, reveal_dir, animate, output_path):
    """Generate SVG from sampled grid."""
    cell_size = 1000 / cols
    max_r = cell_size * 0.5
    svg_parts = []
    svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" width="1000" height="1000">')
    
    if bg != "transparent":
        svg_parts.append(f'<rect width="1000" height="1000" fill="{bg}"/>')
    
    if circle:
        svg_parts.append('<defs><mask id="circleMask"><circle cx="500" cy="500" r="500" fill="white"/></mask></defs>')
        svg_parts.append('<g mask="url(#circleMask)">')
    
    style_defs = []
    if reveal or animate:
        style_defs.append('<style>')
        if reveal:
            delay_step = reveal_time / cols
            for y in range(cols):
                delay = y * delay_step if reveal_dir == "up" else (cols - 1 - y) * delay_step
                style_defs.append(f'.row{y} {{ opacity: 0; animation: reveal {reveal_fade}s ease-out {delay}s forwards; }}')
            style_defs.append(f'@keyframes reveal {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}')
        if animate:
            style_defs.append(f'.shimmer {{ animation: shimmer 3s ease-in-out infinite; }}')
            style_defs.append('@keyframes shimmer { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }')
        style_defs.append('</style>')
        svg_parts.append(''.join(style_defs))
    
    for y in range(cols):
        row_class = f' class="row{y}"' if reveal else ''
        if animate:
            row_class = f' class="shimmer"' if not row_class else row_class.replace('class="', 'class="shimmer ')
        svg_parts.append(f'<g{row_class}>')
        for x in range(cols):
            cell = grid[y][x]
            if cell is None:
                continue
            brightness, color = cell
            r = brightness_to_radius(brightness, max_r)
            if r <= 0.5:
                continue
            cx = x * cell_size + cell_size / 2
            cy = y * cell_size + cell_size / 2
            fill = f"rgb{color}" if color_mode and color else accent
            if dot_shape == "circle":
                svg_parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}"/>')
            else:
                half = r
                svg_parts.append(f'<rect x="{cx-half:.1f}" y="{cy-half:.1f}" width="{2*half:.1f}" height="{2*half:.1f}" fill="{fill}"/>')
        svg_parts.append('</g>')
    
    if circle:
        svg_parts.append('</g>')
    svg_parts.append('</svg>')
    
    Path(output_path).write_text(''.join(svg_parts), encoding="utf-8")

def generate_text(grid, cols, mode, invert, output_path):
    """Generate ASCII/braille/binary text output."""
    chars = {
        "ascii": "@%#*+=-:. ",
        "braille": "⣿⣷⣯⣟⡿⢿⣻⣽⣾⣷⣶⣵⣴⣳⣲⣱⣰⣯⣮⣭⣬⣫⣪⣩⣨⣧⣦⣥⣤⣣⣢⣡⣠⣟⣞⣝⣜⣛⣚⣙⣘⣗⣖⣕⣔⣓⣒⣑⣐⣏⣎⣍⣌⣋⣊⣉⣈⣇⣆⣅⣄⣃⣂⣁⣀",
        "binary": "10"
    }
    ramp = chars[mode]
    lines = []
    for y in range(cols):
        line = []
        for x in range(cols):
            cell = grid[y][x]
            if cell is None:
                line.append(" ")
                continue
            brightness, _ = cell
            if invert:
                brightness = 1.0 - brightness
            idx = int(brightness * (len(ramp) - 1))
            line.append(ramp[idx])
        lines.append("".join(line))
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")

def main():
    args = parse_args()
    img = load_image(args.input)
    img, mask = apply_alpha_mask(img)
    
    if args.equalize:
        img = equalize_image(img, mask)
    
    if args.detail > 0:
        img = enhance_detail(img, args.detail)
    
    focus = args.focus if args.square else "0.5,0.5"
    img, mask = crop_and_resize(img, args.cols, args.circle, focus, mask)
    
    grid = sample_grid(img, args.cols, args.invert, args.color, mask)
    
    if args.mode in ("ascii", "braille", "binary"):
        generate_text(grid, args.cols, args.mode, args.invert, args.output)
    else:
        generate_svg(
            grid, args.cols, args.color, args.accent, args.bg, args.dot_shape,
            args.circle, args.reveal, args.reveal_time, args.reveal_fade, args.reveal_dir,
            args.animate, args.output
        )

if __name__ == "__main__":
    main()