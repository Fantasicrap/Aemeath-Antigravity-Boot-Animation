# -*- coding: utf-8 -*-
"""
Aemeath Multi-AI Boot Animation — Promotional Video Generator
Produces 4 cinema-grade MP4 showcase videos (16:9 horizontal + 9:16 Douyin vertical,
both Compact Beat-Synced Edit ~25.2s AND Full 3-Mode Showcase ~57.0s):
  Desktop hook -> Mouse glide & double-click DeepSeek Harness (Mode A)
               -> Desktop -> double-click Antigravity (Mode B)
               -> Desktop -> double-click Codex (Mode C)
               -> Grand 4-in-1 Outro (DeepSeek / Antigravity / Codex / Claude + GitHub)
"""
import argparse
import math
import os
import shutil
import subprocess
import time

import cv2
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(REPO_ROOT, "windows-overlay", "assets")
AUDIO_22S = os.path.join(REPO_ROOT, "tools", "source_audio", "aemeath_original_22s.mp3")
AUDIO_14S5 = os.path.join(REPO_ROOT, "tools", "source_audio", "aemeath_boot_14s5.wav")
OUT_DIR = os.path.join(REPO_ROOT, "dist", "promo")
SCRATCH_ICONS = r"C:\Users\yang2\.gemini\antigravity\brain\d2cd8584-0e12-4d6e-836f-4885a4bb1d96\scratch\icons"
WIN11_WALLPAPER = r"C:\Windows\Web\Wallpaper\Windows\img19.jpg"

FONT_SERIF = r"C:\Windows\Fonts\NotoSerifSC-VF.ttf"
FONT_SANS = r"C:\Windows\Fonts\NotoSansSC-VF.ttf"
FONT_MSYH = r"C:\Windows\Fonts\msyh.ttc"
FONT_MSYH_BD = r"C:\Windows\Fonts\msyhbd.ttc"
FONT_SEGOE = r"C:\Windows\Fonts\segoeui.ttf"
FONT_SEGOE_SB = r"C:\Windows\Fonts\seguisb.ttf"
FONT_CONSOLA = r"C:\Windows\Fonts\consola.ttf"

W16, H16 = 1920, 1080
W9, H9 = 1080, 1920
FPS = 30
SR = 44100

# Desktop icon grid (left column on 1920x1080 Windows 11 desktop)
ICON_X = 68
ICON_Y0 = 64
ICON_DY = 148
ICON_TILE_W = 128
ICON_TILE_H = 128

APPS = [
    {
        "key": "deepseek",
        "name": "DeepSeek Harness",
        "short": "DeepSeek",
        "win_title": "DeepSeek Harness — Workspace",
        "mode": "a",
        "mode_tag": "模式 A · 星海苏醒",
        "mode_en": "MODE A · AWAKENING",
        "accent": (110, 185, 255),
        "tile_cx": ICON_X + ICON_TILE_W // 2,
        "tile_cy": ICON_Y0 + 0 * ICON_DY + 46,
        "row": 0,
    },
    {
        "key": "antigravity",
        "name": "Antigravity",
        "short": "Antigravity",
        "win_title": "Antigravity — Aemeath-Antigravity-Boot-Animation",
        "mode": "b",
        "mode_tag": "模式 B · 电子幽灵 × 隧者机兵",
        "mode_en": "MODE B · EXOSTRIDER",
        "accent": (255, 134, 198),
        "tile_cx": ICON_X + ICON_TILE_W // 2,
        "tile_cy": ICON_Y0 + 1 * ICON_DY + 46,
        "row": 1,
    },
    {
        "key": "codex",
        "name": "Codex",
        "short": "Codex",
        "win_title": "Codex — OpenAI Coding Agent",
        "mode": "c",
        "mode_tag": "模式 C · 纸飞机 × 电子星海",
        "mode_en": "MODE C · VOYAGER",
        "accent": (122, 236, 255),
        "tile_cx": ICON_X + ICON_TILE_W // 2,
        "tile_cy": ICON_Y0 + 2 * ICON_DY + 46,
        "row": 2,
    },
    {
        "key": "claude",
        "name": "Claude",
        "short": "Claude",
        "win_title": "Claude",
        "mode": "a",
        "mode_tag": "四合一同步支持",
        "mode_en": "SUPPORTED",
        "accent": (217, 119, 87),
        "tile_cx": ICON_X + ICON_TILE_W // 2,
        "tile_cy": ICON_Y0 + 3 * ICON_DY + 46,
        "row": 3,
    },
]

# App window bounds on 1920x1080 desktop (above 54px taskbar)
WIN_W, WIN_H = 1536, 864
WIN_X = (W16 - WIN_W) // 2 + 28  # slightly right so left icons peek cleanly on 16:9!
WIN_Y = 74
WIN_R = 14


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else (hi if v > hi else v)


def smoothstep(a, b, x):
    t = clamp((x - a) / max(1e-6, (b - a)))
    return t * t * (3.0 - 2.0 * t)


def smootherstep(a, b, x):
    t = clamp((x - a) / max(1e-6, (b - a)))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def ease_out_cubic(x):
    t = clamp(x)
    return 1.0 - (1.0 - t) ** 3


def ease_out_back(x, s=1.15):
    t = clamp(x) - 1.0
    return 1.0 + t * t * ((s + 1.0) * t + s)


def load_font(path, size, weight=None):
    f = ImageFont.truetype(path, size)
    if weight is not None:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f


def find_ffmpeg():
    sys_ff = shutil.which("ffmpeg")
    return sys_ff if sys_ff else imageio_ffmpeg.get_ffmpeg_exe()


# ───────────────────────── HIGH-RES ICON & CURSOR GENERATORS ─────────────────────────

def make_rounded_mask(size, radius):
    s = 4
    m = Image.new("L", (size * s, size * s), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, size * s - 1, size * s - 1], radius=radius * s, fill=255)
    return m.resize((size, size), Image.LANCZOS)


def make_codex_icon(size=256):
    """Crisp supersampled OpenAI Codex desktop icon (obsidian-indigo squircle + glowing >_ glyph + subtle orbit ring)."""
    s = 4
    S = size * s
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    # Gradient background: deep obsidian #0C1021 -> electric indigo #3540F2
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) / float(S)
    mix = np.clip(xx * 0.55 + yy * 0.65, 0.0, 1.0)
    r = (14 * (1 - mix) + 56 * mix + 38 * np.exp(-((xx - 0.72) ** 2 + (yy - 0.25) ** 2) / 0.16)).clip(0, 255)
    g = (17 * (1 - mix) + 66 * mix + 62 * np.exp(-((xx - 0.72) ** 2 + (yy - 0.25) ** 2) / 0.16)).clip(0, 255)
    b = (32 * (1 - mix) + 235 * mix + 20 * np.exp(-((xx - 0.72) ** 2 + (yy - 0.25) ** 2) / 0.16)).clip(0, 255)
    grad = np.stack([r, g, b, np.full((S, S), 255.0)], axis=-1).astype(np.uint8)
    bg = Image.fromarray(grad, "RGBA")

    mask = Image.new("L", (S, S), 0)
    md = ImageDraw.Draw(mask)
    pad = int(S * 0.04)
    rad = int(S * 0.22)
    md.rounded_rectangle([pad, pad, S - pad, S - pad], radius=rad, fill=255)
    img.paste(bg, (0, 0), mask)

    d = ImageDraw.Draw(img)
    # Subtle glass rim highlight
    d.rounded_rectangle([pad + 2, pad + 2, S - pad - 2, S - pad - 2], radius=rad, outline=(175, 195, 255, 110), width=int(S * 0.012))

    # Crisp circular inner ring (OpenAI Codex emblem motif)
    cx, cy = S * 0.5, S * 0.5
    rr = S * 0.31
    d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(255, 255, 255, 68), width=int(S * 0.018))

    # Bold crisp ">_" coding agent prompt mark
    sw = int(S * 0.062)
    # '>' chevron
    p1 = (int(S * 0.31), int(S * 0.36))
    p2 = (int(S * 0.48), int(S * 0.50))
    p3 = (int(S * 0.31), int(S * 0.64))
    d.line([p1, p2, p3], fill=(255, 255, 255, 255), width=sw, joint="curve")
    # Rounded endcaps
    for pt in (p1, p2, p3):
        cr = sw // 2
        d.ellipse([pt[0] - cr, pt[1] - cr, pt[0] + cr, pt[1] + cr], fill=(255, 255, 255, 255))
    # '_' cursor bar in glowing cyan-white
    u1 = (int(S * 0.53), int(S * 0.64))
    u2 = (int(S * 0.71), int(S * 0.64))
    d.line([u1, u2], fill=(165, 228, 255, 255), width=sw)
    for pt in (u1, u2):
        cr = sw // 2
        d.ellipse([pt[0] - cr, pt[1] - cr, pt[0] + cr, pt[1] + cr], fill=(165, 228, 255, 255))

    return img.resize((size, size), Image.LANCZOS)


def make_claude_icon(size=256):
    """Crisp supersampled Anthropic Claude Desktop icon (warm terracotta #D97757 squircle + crisp white spark)."""
    s = 4
    S = size * s
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = int(S * 0.04)
    rad = int(S * 0.22)
    d.rounded_rectangle([pad, pad, S - pad, S - pad], radius=rad, fill=(217, 119, 87, 255))
    d.rounded_rectangle([pad + 2, pad + 2, S - pad - 2, S - pad - 2], radius=rad, outline=(255, 210, 190, 95), width=int(S * 0.012))

    # Signature 12-spoke asymmetric Claude starburst
    cx, cy = S * 0.50, S * 0.50
    angles_deg = [0, 28, 60, 92, 122, 152, 180, 210, 240, 270, 300, 330]
    lengths = [0.30, 0.24, 0.31, 0.25, 0.30, 0.23, 0.31, 0.24, 0.30, 0.25, 0.31, 0.24]
    w_outer = S * 0.028
    w_inner = S * 0.014
    r_inner = S * 0.055
    for ang_d, frac in zip(angles_deg, lengths):
        ang = math.radians(ang_d - 12)
        nx, ny = -math.sin(ang), math.cos(ang)
        dx, dy = math.cos(ang), math.sin(ang)
        r_out = S * frac
        poly = [
            (cx + dx * r_inner - nx * w_inner, cy + dy * r_inner - ny * w_inner),
            (cx + dx * r_out - nx * w_outer, cy + dy * r_out - ny * w_outer),
            (cx + dx * (r_out + S * 0.012), cy + dy * (r_out + S * 0.012)),
            (cx + dx * r_out + nx * w_outer, cy + dy * r_out + ny * w_outer),
            (cx + dx * r_inner + nx * w_inner, cy + dy * r_inner + ny * w_inner),
        ]
        d.polygon(poly, fill=(255, 252, 247, 255))
    rc = int(S * 0.082)
    d.ellipse([cx - rc, cy - rc, cx + rc, cy + rc], fill=(255, 252, 247, 255))
    return img.resize((size, size), Image.LANCZOS)


def make_aemeath_tray_icon(size=64):
    """Glowing sakura-pink & cyan Aemeath star-emblem tray icon."""
    s = 4
    S = size * s
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = int(S * 0.08)
    d.ellipse([pad, pad, S - pad, S - pad], fill=(24, 14, 38, 255), outline=(100, 232, 255, 220), width=int(S * 0.05))
    cx, cy = S * 0.5, S * 0.5
    # Four-point pink-gold star
    pts = []
    for i in range(8):
        ang = math.radians(i * 45 - 90)
        rad = S * (0.31 if i % 2 == 0 else 0.10)
        pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
    d.polygon(pts, fill=(255, 148, 206, 255))
    r2 = int(S * 0.09)
    d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=(255, 248, 220, 255))
    return img.resize((size, size), Image.LANCZOS)


def make_win11_cursor(scale=1.0):
    """Authentic high-DPI crisp Windows 11 Aero white arrow cursor with dark border + soft shadow."""
    # Coordinates normalized to standard 32px Windows arrow cursor (hotspot at (2, 2))
    s = 4
    base_w, base_h = int(round(36 * scale)), int(round(44 * scale))
    W, H = base_w * s, base_h * s
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # Authentic Windows 11 cursor silhouette
    pts_norm = [
        (0.10, 0.06),
        (0.10, 0.72),
        (0.27, 0.56),
        (0.41, 0.84),
        (0.51, 0.80),
        (0.37, 0.52),
        (0.60, 0.52),
    ]
    pts = [(p[0] * W, p[1] * H) for p in pts_norm]

    # Soft drop shadow
    shad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shad)
    sh_pts = [(x + 4 * s * scale, y + 6 * s * scale) for x, y in pts]
    sd.polygon(sh_pts, fill=(0, 0, 0, 125))
    shad = shad.filter(ImageFilter.GaussianBlur(radius=2.2 * s * scale))
    img.alpha_composite(shad)

    # Crisp dark outline + pure white fill
    d = ImageDraw.Draw(img)
    d.polygon(pts, fill=(255, 255, 255, 255), outline=(18, 22, 30, 255), width=max(3, int(round(1.6 * s * scale))))
    out = img.resize((base_w, base_h), Image.LANCZOS)
    hotspot = (int(round(0.10 * base_w)), int(round(0.06 * base_h)))
    return out, hotspot


def load_all_icons():
    icons = {}
    # Real extracted 1024px DeepSeek Harness icon
    ds_hi = os.path.join(SCRATCH_ICONS, "deepseek_hi.png")
    ds_exe = os.path.join(SCRATCH_ICONS, "deepseek_exe.png")
    ds_src = ds_hi if os.path.exists(ds_hi) else ds_exe
    ds_img = Image.open(ds_src).convert("RGBA").resize((256, 256), Image.LANCZOS)
    icons["deepseek"] = ds_img

    # Real extracted 256px Antigravity icon -> place cleanly on sleek light-glass squircle like Windows/macOS shortcut
    ag_raw = Image.open(os.path.join(SCRATCH_ICONS, "antigravity_exe.png")).convert("RGBA")
    # Put Antigravity rainbow 'A' on a crisp dark-frost or pure-white rounded squircle so it pops vibrantly on dark bloom!
    ag_tile = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    ad = ImageDraw.Draw(ag_tile)
    ad.rounded_rectangle([10, 10, 246, 246], radius=56, fill=(246, 248, 255, 255), outline=(210, 220, 240, 180), width=3)
    ag_inner = ag_raw.resize((216, 216), Image.LANCZOS)
    ag_tile.alpha_composite(ag_inner, (20, 20))
    icons["antigravity"] = ag_tile

    icons["codex"] = make_codex_icon(256)
    icons["claude"] = make_claude_icon(256)
    icons["aemeath"] = make_aemeath_tray_icon(64)
    return icons


# ───────────────────────── AUTHENTIC WINDOWS 11 DESKTOP ─────────────────────────

def draw_shortcut_badge(canvas, x, y, sz=18):
    """Tiny authentic Windows shortcut curved-arrow badge on bottom-left of desktop icon."""
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle([x, y, x + sz, y + sz], radius=4, fill=(248, 250, 255, 238), outline=(120, 130, 150, 200), width=1)
    # Tiny dark blue curved arrow pointing up-right
    d.line([(x + 4, y + sz - 4), (x + sz - 5, y + 5)], fill=(26, 98, 210, 255), width=2)
    d.polygon([(x + sz - 4, y + 4), (x + sz - 10, y + 4), (x + sz - 4, y + 10)], fill=(26, 98, 210, 255))


def build_base_desktop(icons):
    """Build 1920x1080 authentic Windows 11 Dark Bloom desktop with icons + centered acrylic taskbar."""
    if os.path.exists(WIN11_WALLPAPER):
        wp = Image.open(WIN11_WALLPAPER).convert("RGB")
        # Aspect-fill crop to 1920x1080
        w0, h0 = wp.size
        target_ar = W16 / float(H16)
        cur_ar = w0 / float(h0)
        if cur_ar > target_ar:
            tw = int(round(h0 * target_ar))
            x0 = (w0 - tw) // 2
            wp = wp.crop((x0, 0, x0 + tw, h0))
        else:
            th = int(round(w0 / target_ar))
            y0 = (h0 - th) // 2
            wp = wp.crop((0, y0, w0, y0 + th))
        wp = wp.resize((W16, H16), Image.LANCZOS)
        # Subtle atmospheric depth grade
        arr = np.asarray(wp, dtype=np.float32) * 0.90
        base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    else:
        base = Image.new("RGBA", (W16, H16), (10, 16, 36, 255))

    # Draw desktop shortcut icons (static unselected layer)
    font_lbl = load_font(FONT_MSYH, 16)
    d = ImageDraw.Draw(base)
    for app in APPS:
        row = app["row"]
        tx = ICON_X
        ty = ICON_Y0 + row * ICON_DY
        ic = icons[app["key"]].resize((68, 68), Image.LANCZOS)
        ix = tx + (ICON_TILE_W - 68) // 2
        iy = ty + 10
        # Soft icon drop shadow
        sh = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
        sh.paste((0, 0, 0, 120), (6, 8), ic.split()[3])
        sh = sh.filter(ImageFilter.GaussianBlur(5))
        base.alpha_composite(sh, (ix - 6, iy - 4))
        base.alpha_composite(ic, (ix, iy))
        draw_shortcut_badge(base, ix - 2, iy + 50, sz=18)

        # Crisp centered Windows desktop label with drop shadow
        lbl = app["name"]
        bbox = d.textbbox((0, 0), lbl, font=font_lbl)
        lw = bbox[2] - bbox[0]
        lx = tx + (ICON_TILE_W - lw) // 2
        ly = iy + 74
        for dx, dy in ((0, 1), (1, 1), (0, 2)):
            d.text((lx + dx, ly + dy), lbl, font=font_lbl, fill=(0, 0, 0, 200))
        d.text((lx, ly), lbl, font=font_lbl, fill=(248, 251, 255, 255))

    # Build authentic Windows 11 acrylic centered Taskbar (bottom 54px)
    tb_h = 54
    tb_y = H16 - tb_h
    tb_crop = base.crop((0, tb_y, W16, H16)).filter(ImageFilter.GaussianBlur(18))
    tb_tint = Image.new("RGBA", (W16, tb_h), (18, 22, 32, 208))
    tb_crop.alpha_composite(tb_tint)
    base.paste(tb_crop, (0, tb_y))

    d = ImageDraw.Draw(base)
    d.line([(0, tb_y), (W16, tb_y)], fill=(255, 255, 255, 28), width=1)

    # Centered taskbar items
    cx = W16 // 2
    cy = tb_y + tb_h // 2

    # 1. Windows 11 Start logo (4 blue panes)
    sx = cx - 220
    sy = cy - 12
    for rx, ry, col in [
        (0, 0, (76, 194, 255)),
        (13, 0, (66, 180, 252)),
        (0, 13, (46, 158, 245)),
        (13, 13, (30, 136, 232)),
    ]:
        d.rounded_rectangle([sx + rx, sy + ry, sx + rx + 11, sy + ry + 11], radius=2, fill=col + (255,))

    # 2. Windows 11 Search pill
    pill_x0, pill_x1 = cx - 180, cx - 28
    d.rounded_rectangle([pill_x0, cy - 16, pill_x1, cy + 16], radius=16, fill=(255, 255, 255, 26), outline=(255, 255, 255, 36), width=1)
    # Magnifying glass
    d.ellipse([pill_x0 + 13, cy - 6, pill_x0 + 23, cy + 4], outline=(215, 226, 245, 220), width=2)
    d.line([(pill_x0 + 22, cy + 3), (pill_x0 + 26, cy + 7)], fill=(215, 226, 245, 220), width=2)
    f_search = load_font(FONT_MSYH, 14)
    d.text((pill_x0 + 36, cy - 10), "搜索", font=f_search, fill=(205, 215, 232, 220))

    # 3. File Explorer mini icon
    fx = cx - 12
    d.rounded_rectangle([fx, cy - 10, fx + 26, cy + 11], radius=4, fill=(242, 192, 68, 255))
    d.rounded_rectangle([fx, cy - 13, fx + 12, cy - 6], radius=2, fill=(216, 162, 42, 255))
    d.rectangle([fx + 3, cy + 1, fx + 23, cy + 11], fill=(255, 215, 102, 255))

    # 4. Our 4 AI app icons on taskbar (remember their x coords for active underline!)
    tb_app_x = {}
    for idx, app in enumerate(APPS):
        ax = cx + 38 + idx * 48
        tb_app_x[app["key"]] = ax
        ic_sm = icons[app["key"]].resize((30, 30), Image.LANCZOS)
        base.alpha_composite(ic_sm, (ax - 15, cy - 15))

    # Right System Tray
    # Aemeath Boot Overlay active icon (glowing subtle pink/cyan pill)
    tray_ax = W16 - 230
    d.rounded_rectangle([tray_ax - 16, cy - 16, tray_ax + 16, cy + 16], radius=8, fill=(255, 120, 190, 34), outline=(255, 148, 206, 100), width=1)
    base.alpha_composite(icons["aemeath"].resize((22, 22), Image.LANCZOS), (tray_ax - 11, cy - 11))

    # Chevron ^
    chx = W16 - 266
    d.line([(chx - 5, cy + 2), (chx, cy - 3), (chx + 5, cy + 2)], fill=(215, 222, 235, 210), width=2)

    # Language "中"
    f_tray = load_font(FONT_MSYH, 14)
    d.text((W16 - 196, cy - 10), "中", font=f_tray, fill=(235, 240, 248, 235))

    # Wi-Fi arc + Speaker minimal crisp vector icons
    wx = W16 - 162
    d.arc([wx - 9, cy - 7, wx + 9, cy + 11], 225, 315, fill=(235, 240, 248, 230), width=2)
    d.arc([wx - 5, cy - 3, wx + 5, cy + 7], 225, 315, fill=(235, 240, 248, 230), width=2)
    d.ellipse([wx - 2, cy + 3, wx + 2, cy + 7], fill=(235, 240, 248, 235))

    vx = W16 - 134
    d.polygon([(vx - 6, cy - 3), (vx - 2, cy - 3), (vx + 3, cy - 7), (vx + 3, cy + 7), (vx - 2, cy + 3), (vx - 6, cy + 3)], fill=(235, 240, 248, 230))
    d.arc([vx + 3, cy - 5, vx + 9, cy + 5], 310, 50, fill=(235, 240, 248, 220), width=2)

    # Clock (rightmost)
    f_clk = load_font(FONT_SEGOE, 14)
    d.text((W16 - 98, tb_y + 9), "20:26", font=f_clk, fill=(242, 246, 252, 245))
    d.text((W16 - 108, tb_y + 28), "2026/11/27", font=f_clk, fill=(215, 222, 235, 225))

    return base, tb_app_x


# ───────────────────────── AUTHENTIC AI APP WINDOW MOCKUPS ─────────────────────────

def draw_window_chrome(img, title, icon_img, accent_rgb, bg_rgb=(15, 18, 26)):
    """Draw authentic Windows 11 rounded dark title bar + borders."""
    d = ImageDraw.Draw(img)
    W, H = img.size
    d.rectangle([0, 0, W, H], fill=bg_rgb + (255,))
    # Title bar (42px)
    d.rectangle([0, 0, W, 42], fill=(bg_rgb[0] + 6, bg_rgb[1] + 7, bg_rgb[2] + 10, 255))
    d.line([(0, 42), (W, 42)], fill=(255, 255, 255, 22), width=1)
    # App icon + title
    ic = icon_img.resize((22, 22), Image.LANCZOS)
    img.alpha_composite(ic, (16, 10))
    f_tit = load_font(FONT_SEGOE, 14)
    d.text((48, 12), title, font=f_tit, fill=(224, 230, 242, 240))
    # Window controls: minimize, maximize, close
    d.line([(W - 122, 21), (W - 110, 21)], fill=(205, 212, 224, 210), width=1)
    d.rectangle([W - 76, 15, W - 64, 27], outline=(205, 212, 224, 210), width=1)
    d.line([(W - 30, 15), (W - 18, 27)], fill=(220, 226, 236, 220), width=1)
    d.line([(W - 18, 15), (W - 30, 27)], fill=(220, 226, 236, 220), width=1)


def build_app_mockup(app, icons):
    """Build hyper-clean, immediately recognizable AI Desktop UI (1536x864) for reveal behind loop background."""
    W, H = WIN_W, WIN_H
    img = Image.new("RGBA", (W, H), (14, 17, 25, 255))
    f_ui = load_font(FONT_MSYH, 16)
    f_ui_sm = load_font(FONT_MSYH, 13)
    f_h1 = load_font(FONT_MSYH_BD, 26)
    f_mono = load_font(FONT_CONSOLA, 15)
    f_mono_sm = load_font(FONT_CONSOLA, 13)

    key = app["key"]
    if key == "deepseek":
        draw_window_chrome(img, app["win_title"], icons["deepseek"], app["accent"], bg_rgb=(13, 17, 25))
        d = ImageDraw.Draw(img)
        # Left Sidebar (260px)
        d.rectangle([0, 42, 260, H], fill=(17, 22, 33, 255))
        d.line([(260, 42), (260, H)], fill=(255, 255, 255, 20), width=1)
        d.rounded_rectangle([18, 62, 242, 102], radius=10, fill=(48, 110, 245, 225))
        d.text((64, 71), "+ 新建 Harness 任务", font=f_ui, fill=(255, 255, 255, 255))
        for i, item in enumerate(["爱弥斯开机动画渲染管线", "多平台桌面窗口监听适配", "WPF 无缝循环背景优化", "GitHub Release 自动打包"]):
            yy = 128 + i * 44
            if i == 0:
                d.rounded_rectangle([14, yy - 6, 246, yy + 30], radius=8, fill=(255, 255, 255, 18))
            d.text((28, yy + 2), item, font=f_ui_sm, fill=(220, 230, 246, 230 if i == 0 else 160))

        # Main workspace header & DeepSeek whale emblem
        cx = 260 + (W - 260) // 2
        img.alpha_composite(icons["deepseek"].resize((68, 68), Image.LANCZOS), (cx - 34, 150))
        t1 = "DeepSeek Harness 已就绪"
        b1 = d.textbbox((0, 0), t1, font=f_h1)
        d.text((cx - (b1[2] - b1[0]) // 2, 238), t1, font=f_h1, fill=(242, 247, 255, 245))
        t2 = "DeepSeek-R1 / V3 · Multi-Agent Coding Harness · Aemeath Mode A Active"
        b2 = d.textbbox((0, 0), t2, font=f_ui_sm)
        d.text((cx - (b2[2] - b2[0]) // 2, 282), t2, font=f_ui_sm, fill=(145, 178, 228, 210))

        # Agent status cards
        for idx, (ct, cd) in enumerate([
            ("Workspace Analyzer", "已索引 42 个项目文件 · 零错误"),
            ("Terminal Runner", "WPF Overlay 编译通过 (0 warnings)"),
            ("Visual QA", "全平台启动动画校验完成"),
        ]):
            x0 = cx - 420 + idx * 290
            d.rounded_rectangle([x0, 340, x0 + 262, 438], radius=12, fill=(22, 29, 44, 215), outline=(92, 148, 255, 70), width=1)
            d.text((x0 + 18, 360), ct, font=f_ui, fill=(130, 198, 255, 245))
            d.text((x0 + 18, 394), cd, font=f_ui_sm, fill=(196, 208, 226, 200))

        # Bottom prompt input box
        d.rounded_rectangle([cx - 420, H - 156, cx + 420, H - 46], radius=16, fill=(22, 28, 42, 232), outline=(105, 165, 255, 95), width=1)
        d.text((cx - 394, H - 134), "向 DeepSeek Harness 下达任务，或输入 /plan 启动多步代理...", font=f_ui, fill=(150, 165, 192, 210))
        d.rounded_rectangle([cx + 332, H - 94, cx + 402, H - 62], radius=10, fill=(58, 128, 255, 245))
        d.text((cx + 350, H - 88), "发送", font=f_ui_sm, fill=(255, 255, 255, 255))

    elif key == "antigravity":
        draw_window_chrome(img, app["win_title"], icons["antigravity"], app["accent"], bg_rgb=(17, 17, 26))
        d = ImageDraw.Draw(img)
        # Left Explorer (248px)
        d.rectangle([0, 42, 248, H - 28], fill=(21, 22, 33, 255))
        d.line([(248, 42), (248, H - 28)], fill=(255, 255, 255, 20), width=1)
        d.text((18, 56), "EXPLORER", font=f_mono_sm, fill=(145, 152, 180, 210))
        files = [
            "▾ Aemeath-Boot-Animation",
            "  ▾ windows-overlay",
            "    ● AemeathAntigravityBoot.cs",
            "    ● build.ps1",
            "  ▾ antigravity-plugin",
            "    ● server.py",
            "    ● intro.html",
            "  ▾ tools",
            "    ● render_aemeath_boot.py",
            "    ● pack_portable_release.py",
        ]
        for i, fn in enumerate(files):
            yy = 88 + i * 32
            if "AemeathAntigravityBoot.cs" in fn:
                d.rectangle([0, yy - 4, 248, yy + 24], fill=(255, 126, 194, 34))
            col = (255, 176, 220, 250) if "AemeathAntigravityBoot.cs" in fn else (196, 204, 228, 200)
            d.text((16, yy), fn, font=f_mono_sm, fill=col)

        # Center Code Editor (x=248..1068)
        d.rectangle([248, 42, 1068, 78], fill=(24, 25, 37, 255))
        d.rectangle([248, 42, 512, 78], fill=(17, 17, 26, 255))
        d.line([(248, 42), (512, 42)], fill=(255, 134, 198, 255), width=2)
        d.text((268, 52), "AemeathAntigravityBoot.cs", font=f_mono_sm, fill=(240, 244, 255, 245))
        code_lines = [
            ("namespace AemeathAntigravityBoot", (180, 148, 255)),
            ("{", (215, 220, 235)),
            ("    // 原生全支持：Antigravity / DeepSeek / Codex / Claude", (118, 172, 136)),
            ("    public class Show : IDisposable", (110, 212, 255)),
            ("    {", (215, 220, 235)),
            ("        public string Mode = \"b\"; // 电子幽灵 × 隧者机兵", (255, 178, 132)),
            ("        public double ResidualAlpha = 0.25;", (152, 222, 255)),
            ("        public string Subtitle = \"拯救世界的事，就交给我吧……\";", (255, 166, 214)),
            ("", (200, 200, 200)),
            ("        public void LaunchBootAnimation(Target app)", (125, 230, 195)),
            ("        {", (215, 220, 235)),
            ("            overlay.Follow(app.Hwnd, force: true);", (228, 232, 245)),
            ("            intro.PlaySynced(\"aemeath_boot_14s5.mp4\");", (228, 232, 245)),
            ("            TransitionToSeamlessLoop(\"loop-x2.mp4\");", (130, 215, 255)),
            ("        }", (215, 220, 235)),
            ("    }", (215, 220, 235)),
            ("}", (215, 220, 235)),
        ]
        for idx, (ln, col) in enumerate(code_lines):
            yy = 104 + idx * 31
            d.text((266, yy), f"{idx + 1:2d}", font=f_mono_sm, fill=(95, 102, 126, 180))
            d.text((304, yy), ln, font=f_mono, fill=col + (235,))

        # Right Agent Side Panel (x=1068..W)
        d.rectangle([1068, 42, W, H - 28], fill=(22, 22, 34, 255))
        d.line([(1068, 42), (1068, H - 28)], fill=(255, 255, 255, 24), width=1)
        img.alpha_composite(icons["antigravity"].resize((28, 28), Image.LANCZOS), (1090, 56))
        d.text((1128, 59), "Antigravity Agent", font=f_ui, fill=(242, 246, 255, 245))
        # Chat bubble
        d.rounded_rectangle([1090, 106, W - 22, 222], radius=12, fill=(34, 34, 52, 235), outline=(255, 134, 198, 95), width=1)
        d.text((1108, 122), "Aemeath 演出管线已启动", font=f_ui, fill=(255, 168, 216, 255))
        d.text((1108, 152), "● 模式 B 双形态机甲背景已挂接\n● 思源宋体动态字幕已就绪", font=f_ui_sm, fill=(215, 224, 242, 225))
        # Agent composer
        d.rounded_rectangle([1090, H - 126, W - 22, H - 46], radius=12, fill=(30, 31, 46, 240), outline=(120, 210, 255, 90), width=1)
        d.text((1108, H - 106), "Ask Antigravity to build...", font=f_ui_sm, fill=(150, 160, 190, 210))

        # Status Bar
        d.rectangle([0, H - 28, W, H], fill=(28, 24, 44, 255))
        d.text((16, H - 23), "main*   Aemeath Boot v1.2 (Mode B)   C# .NET 4.x   UTF-8", font=f_mono_sm, fill=(225, 185, 235, 220))

    else:  # codex
        draw_window_chrome(img, app["win_title"], icons["codex"], app["accent"], bg_rgb=(13, 14, 20))
        d = ImageDraw.Draw(img)
        # Left Thread List (276px)
        d.rectangle([0, 42, 276, H], fill=(17, 18, 26, 255))
        d.line([(276, 42), (276, H)], fill=(255, 255, 255, 20), width=1)
        d.rounded_rectangle([18, 62, 258, 102], radius=10, fill=(255, 255, 255, 240))
        d.text((78, 71), "+ New Task", font=f_ui, fill=(14, 16, 24, 255))
        for i, item in enumerate(["Multi-App Boot Overlay", "Fix Mode C Loop Smoothness", "Build Portable Release ZIP", "Render Promo Showcase"]):
            yy = 128 + i * 46
            if i == 0:
                d.rounded_rectangle([14, yy - 6, 262, yy + 32], radius=8, fill=(102, 128, 255, 36))
            d.text((28, yy + 3), item, font=f_ui_sm, fill=(235, 240, 252, 240 if i == 0 else 160))

        # Center Codex Workspace
        cx = 276 + (W - 276) // 2
        img.alpha_composite(icons["codex"].resize((64, 64), Image.LANCZOS), (cx - 32, 134))
        t1 = "Codex Coding Agent"
        b1 = d.textbbox((0, 0), t1, font=f_h1)
        d.text((cx - (b1[2] - b1[0]) // 2, 214), t1, font=f_h1, fill=(246, 248, 255, 248))

        # Diff / Task execution card
        d.rounded_rectangle([cx - 430, 276, cx + 430, 560], radius=14, fill=(20, 22, 32, 225), outline=(120, 220, 255, 76), width=1)
        d.text((cx - 404, 296), "✓  Completed · Aemeath Multi-AI Overlay v1.2.0", font=f_ui, fill=(122, 242, 212, 245))
        diff_lines = [
            ("+ EnableAntigravity     = true;  // Antigravity.exe", (128, 238, 178)),
            ("+ EnableDeepSeekHarness = true;  // DeepSeek Harness.exe", (128, 238, 178)),
            ("+ EnableCodex           = true;  // Codex.exe / ChatGPT.exe", (128, 238, 178)),
            ("+ EnableClaude          = true;  // claude.exe (Chrome_WidgetWin_1)", (128, 238, 178)),
            ("  Mode                  = \"c\";   // 纸飞机 × 祝福 × 拯救 × 远航星", (170, 226, 255)),
        ]
        for idx, (dl, col) in enumerate(diff_lines):
            d.text((cx - 400, 344 + idx * 36), dl, font=f_mono, fill=col + (235,))

        # Bottom Composer
        d.rounded_rectangle([cx - 430, H - 154, cx + 430, H - 48], radius=16, fill=(22, 24, 34, 235), outline=(130, 152, 255, 100), width=1)
        d.text((cx - 402, H - 130), "Describe a coding task for Codex...", font=f_ui, fill=(156, 164, 188, 215))
        d.rounded_rectangle([cx + 334, H - 96, cx + 410, H - 62], radius=10, fill=(255, 255, 255, 242))
        d.text((cx + 356, H - 89), "Run", font=f_ui_sm, fill=(14, 16, 24, 255))

    return img


# ───────────────────────── LIVE 思源宋体 SUBTITLE OVERLAY ─────────────────────────

def make_subtitle_layer(w, h, primary="拯救世界的事，就交给我吧……", secondary="Leave saving the world to me..."):
    """Render crisp 思源宋体 (NotoSerifSC) bilingual subtitle layer matching AemeathAntigravityBoot.cs."""
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    main_sz = int(round(max(24, min(h * 0.047, 46))))
    sub_sz = int(round(max(15, main_sz * 0.56)))
    f_main = load_font(FONT_SERIF, main_sz, weight=600)
    f_sub = load_font(FONT_SERIF, sub_sz, weight=400)

    # Shadow pass
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    bm = sd.textbbox((0, 0), primary, font=f_main)
    mw, mh = bm[2] - bm[0], bm[3] - bm[1]
    bs = sd.textbbox((0, 0), secondary, font=f_sub)
    sw, sh_h = bs[2] - bs[0], bs[3] - bs[1]

    ym = int(round(h * 0.835 - mh * 0.5))
    xm = (w - mw) // 2
    ys = ym + mh + int(round(main_sz * 0.28))
    xs = (w - sw) // 2

    sd.text((xm, ym), primary, font=f_main, fill=(12, 4, 20, 235), stroke_width=5, stroke_fill=(12, 4, 20, 235))
    sd.text((xs, ys), secondary, font=f_sub, fill=(12, 4, 20, 225), stroke_width=4, stroke_fill=(12, 4, 20, 225))
    sh = sh.filter(ImageFilter.GaussianBlur(7))
    layer.alpha_composite(sh)

    # Crisp outline + white fill pass
    d = ImageDraw.Draw(layer)
    d.text((xm, ym), primary, font=f_main, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(16, 8, 28, 240))
    d.text((xs, ys), secondary, font=f_sub, fill=(250, 228, 244, 240), stroke_width=2, stroke_fill=(16, 8, 28, 230))
    return layer


# ───────────────────────── GRAND 4-IN-1 OUTRO CARD ─────────────────────────

def build_outro_card(w, h, icons, vertical=False):
    """Build sleek cyber-sakura glass Outro Card featuring all 4 AI apps + GitHub URL."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Deep starlight vignette card
    if not vertical:
        cx, cy = w // 2, h // 2
        card_w, card_h = 1360, 740
        x0, y0 = cx - card_w // 2, cy - card_h // 2
        d.rounded_rectangle([x0, y0, x0 + card_w, y0 + card_h], radius=28, fill=(12, 10, 22, 222), outline=(255, 152, 214, 120), width=2)
        # Soft top accent line
        d.line([(x0 + 260, y0 + 2), (x0 + card_w - 260, y0 + 2)], fill=(116, 232, 255, 210), width=3)

        f_badge = load_font(FONT_SANS, 22, weight=600)
        f_title = load_font(FONT_SERIF, 58, weight=700)
        f_sub = load_font(FONT_SANS, 26, weight=500)
        f_app = load_font(FONT_SEGOE_SB, 20)
        f_url = load_font(FONT_CONSOLA, 26)
        f_cta = load_font(FONT_SANS, 24, weight=600)

        badge = "鸣潮 · 爱弥斯（飞行雪绒）  v1.2 全平台版"
        bb = d.textbbox((0, 0), badge, font=f_badge)
        bw = bb[2] - bb[0]
        d.rounded_rectangle([cx - bw // 2 - 26, y0 + 58, cx + bw // 2 + 26, y0 + 102], radius=22, fill=(255, 124, 194, 42), outline=(255, 150, 212, 165), width=1)
        d.text((cx - bw // 2, y0 + 66), badge, font=f_badge, fill=(255, 214, 238, 255))

        title = "四大主流 AI 桌面端 · 一键开机动画"
        tb = d.textbbox((0, 0), title, font=f_title)
        d.text((cx - (tb[2] - tb[0]) // 2, y0 + 132), title, font=f_title, fill=(255, 255, 255, 255))

        sub = "100% 库洛官方原片素材  ·  A / B / C 三套方案切换  ·  自定义思源宋体台词"
        sb = d.textbbox((0, 0), sub, font=f_sub)
        d.text((cx - (sb[2] - sb[0]) // 2, y0 + 220), sub, font=f_sub, fill=(182, 232, 255, 235))

        # 4 AI App Badges Row
        spacing = 270
        start_x = cx - int(1.5 * spacing)
        iy = y0 + 302
        for i, app in enumerate(APPS):
            ax = start_x + i * spacing
            d.rounded_rectangle([ax - 112, iy, ax + 112, iy + 178], radius=20, fill=(24, 22, 40, 225), outline=app["accent"] + (140,), width=2)
            ic = icons[app["key"]].resize((92, 92), Image.LANCZOS)
            img.alpha_composite(ic, (ax - 46, iy + 22))
            ab = d.textbbox((0, 0), app["short"], font=f_app)
            d.text((ax - (ab[2] - ab[0]) // 2, iy + 132), app["short"], font=f_app, fill=(245, 248, 255, 248))

        # GitHub URL Pill
        url = "github.com/Fantasicrap/Aemeath-Antigravity-Boot-Animation"
        ub = d.textbbox((0, 0), url, font=f_url)
        uw = ub[2] - ub[0]
        d.rounded_rectangle([cx - uw // 2 - 34, y0 + 532, cx + uw // 2 + 34, y0 + 594], radius=16, fill=(18, 28, 48, 240), outline=(112, 228, 255, 185), width=2)
        d.text((cx - uw // 2, y0 + 548), url, font=f_url, fill=(176, 242, 255, 255))

        cta = "完全免费开源 · GitHub Releases 提供绿色开箱版，解压双击即用"
        cb = d.textbbox((0, 0), cta, font=f_cta)
        d.text((cx - (cb[2] - cb[0]) // 2, y0 + 634), cta, font=f_cta, fill=(255, 202, 232, 240))
    else:
        cx, cy = w // 2, h // 2 - 40
        card_w, card_h = 960, 1140
        x0, y0 = cx - card_w // 2, cy - card_h // 2
        d.rounded_rectangle([x0, y0, x0 + card_w, y0 + card_h], radius=32, fill=(12, 10, 22, 232), outline=(255, 152, 214, 130), width=2)

        f_badge = load_font(FONT_SANS, 26, weight=600)
        f_title = load_font(FONT_SERIF, 62, weight=700)
        f_sub = load_font(FONT_SANS, 28, weight=500)
        f_app = load_font(FONT_SEGOE_SB, 24)
        f_url = load_font(FONT_CONSOLA, 24)
        f_cta = load_font(FONT_SANS, 28, weight=600)

        badge = "鸣潮 · 爱弥斯  v1.2 全平台支持"
        bb = d.textbbox((0, 0), badge, font=f_badge)
        bw = bb[2] - bb[0]
        d.rounded_rectangle([cx - bw // 2 - 28, y0 + 64, cx + bw // 2 + 28, y0 + 114], radius=25, fill=(255, 124, 194, 46), outline=(255, 150, 212, 175), width=2)
        d.text((cx - bw // 2, y0 + 72), badge, font=f_badge, fill=(255, 218, 240, 255))

        for li, line in enumerate(["四大主流 AI 桌面端", "一键换上爱弥斯开机动画"]):
            tb = d.textbbox((0, 0), line, font=f_title)
            d.text((cx - (tb[2] - tb[0]) // 2, y0 + 150 + li * 82), line, font=f_title, fill=(255, 255, 255, 255))

        sub = "100% 官方原片 · A/B/C 三模式 · 思源宋体台词"
        sb = d.textbbox((0, 0), sub, font=f_sub)
        d.text((cx - (sb[2] - sb[0]) // 2, y0 + 340), sub, font=f_sub, fill=(182, 232, 255, 235))

        # 2x2 Grid of 4 AI Apps
        grid_coords = [(-210, 0), (210, 0), (-210, 235), (210, 235)]
        gy0 = y0 + 422
        for (gx, gy), app in zip(grid_coords, APPS):
            ax, ay = cx + gx, gy0 + gy
            d.rounded_rectangle([ax - 175, ay, ax + 175, ay + 200], radius=24, fill=(24, 22, 40, 235), outline=app["accent"] + (155,), width=2)
            ic = icons[app["key"]].resize((104, 104), Image.LANCZOS)
            img.alpha_composite(ic, (ax - 52, ay + 24))
            ab = d.textbbox((0, 0), app["name"], font=f_app)
            d.text((ax - (ab[2] - ab[0]) // 2, ay + 144), app["name"], font=f_app, fill=(245, 248, 255, 248))

        # GitHub Box
        url1 = "GitHub 开源免费下载："
        url2 = "Fantasicrap/Aemeath-Antigravity-Boot-Animation"
        d.rounded_rectangle([x0 + 54, y0 + 914, x0 + card_w - 54, y0 + 1018], radius=20, fill=(18, 28, 48, 244), outline=(112, 228, 255, 195), width=2)
        u1b = d.textbbox((0, 0), url1, font=f_sub)
        d.text((cx - (u1b[2] - u1b[0]) // 2, y0 + 928), url1, font=f_sub, fill=(255, 210, 236, 245))
        u2b = d.textbbox((0, 0), url2, font=f_url)
        d.text((cx - (u2b[2] - u2b[0]) // 2, y0 + 972), url2, font=f_url, fill=(168, 242, 255, 255))

        cta = "解压绿色开箱版双击即用 · 零侵入原软件"
        cb = d.textbbox((0, 0), cta, font=f_cta)
        d.text((cx - (cb[2] - cb[0]) // 2, y0 + 1054), cta, font=f_cta, fill=(255, 224, 242, 245))

    return img


# ───────────────────────── VIDEO CACHE & SOUND SYNTHESIS ─────────────────────────

class ModeMediaCache:
    """Decodes intro.mp4 and loop.mp4 for modes a/b/c resized directly to app window dimensions (WIN_W x WIN_H)."""

    def __init__(self):
        self.intros = {}
        self.loops = {}

    def _load_video(self, path, target_w, target_h):
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            raise FileNotFoundError(path)
        frames = []
        while True:
            ok, fr = cap.read()
            if not ok:
                break
            fr = cv2.resize(fr, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
            frames.append(fr)  # BGR uint8
        cap.release()
        return frames

    def load_all(self):
        for m in ("a", "b", "c"):
            t0 = time.time()
            self.intros[m] = self._load_video(os.path.join(ASSETS_DIR, m, "intro.mp4"), WIN_W, WIN_H)
            self.loops[m] = self._load_video(os.path.join(ASSETS_DIR, m, "loop.mp4"), WIN_W, WIN_H)
            print(f"[Cache] Mode {m.upper()}: intro={len(self.intros[m])}f, loop={len(self.loops[m])}f ({time.time()-t0:.1f}s)")

    def intro_at(self, mode, sec):
        arr = self.intros[mode]
        idx = int(round(clamp(sec, 0.0, (len(arr) - 1) / float(FPS)) * FPS))
        return arr[min(len(arr) - 1, max(0, idx))]

    def loop_at(self, mode, sec):
        arr = self.loops[mode]
        idx = int(round(sec * FPS)) % len(arr)
        return arr[idx]


def decode_audio_stereo(ffmpeg_bin, path):
    raw = subprocess.check_output([ffmpeg_bin, "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"])
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()


def synth_mouse_click(rng):
    """Ultra-realistic crisp mechanical mouse switch click (18ms)."""
    n = int(SR * 0.022)
    t = np.arange(n, dtype=np.float32) / SR
    # Sharp microswitch metallic click (3.4kHz + 5.8kHz burst + filtered noise transient + 220Hz shell thump)
    noise = rng.standard_normal(n).astype(np.float32)
    # High-pass emphasize crisp transient
    hp = np.diff(noise, prepend=0.0)
    click = (
        0.55 * hp * np.exp(-t / 0.0022)
        + 0.35 * np.sin(2 * np.pi * 3600 * t) * np.exp(-t / 0.0018)
        + 0.25 * np.sin(2 * np.pi * 195 * t) * np.exp(-t / 0.0045)
    )
    # Release micro-tick 4ms later
    rel = 0.20 * hp * np.exp(-np.maximum(0.0, t - 0.0045) / 0.0015) * (t >= 0.0045)
    mono = (click + rel) * 0.58
    return np.stack([mono, mono], axis=-1)


def synth_whoosh(dur=0.22, f0=320.0, f1=1200.0, gain=0.14):
    """Subtle clean UI spring/zoom air whoosh."""
    n = int(SR * dur)
    t = np.arange(n, dtype=np.float32) / SR
    u = t / dur
    env = np.sin(u * np.pi) ** 1.6
    freq = f0 + (f1 - f0) * (u ** 1.4)
    phase = np.cumsum(2 * np.pi * freq / SR)
    mono = np.sin(phase) * env * gain * 0.55 + np.sin(phase * 2.0) * env * gain * 0.22
    return np.stack([mono, mono], axis=-1)


def synth_outro_chime(dur=3.2):
    """Ethereal starlight fifth chord gently echoing out for Outro Card."""
    n = int(SR * dur)
    t = np.arange(n, dtype=np.float32) / SR
    # D#maj9 / F# sparkly electronic chime frequencies
    freqs = [523.25, 659.25, 783.99, 987.77, 1318.51]
    sig = np.zeros(n, dtype=np.float32)
    for idx, f in enumerate(freqs):
        onset = idx * 0.055
        tt = np.maximum(0.0, t - onset)
        env = np.where(t >= onset, (1.0 - np.exp(-tt / 0.018)) * np.exp(-tt / (1.35 - idx * 0.14)), 0.0)
        sig += np.sin(2 * np.pi * f * tt) * env * (0.11 / (1.0 + idx * 0.22))
    # Subtle stereo shimmer
    L = sig * (1.0 + 0.08 * np.sin(2 * np.pi * 2.4 * t))
    R = sig * (1.0 - 0.08 * np.sin(2 * np.pi * 2.4 * t))
    return np.stack([L, R], axis=-1)


def mix_at(buf, clip, t_sec, gain=1.0):
    i0 = int(round(t_sec * SR))
    if i0 >= len(buf):
        return
    if i0 < 0:
        clip = clip[-i0:]
        i0 = 0
    n = min(len(clip), len(buf) - i0)
    if n > 0:
        buf[i0 : i0 + n] += clip[:n] * gain


def save_wav(path, stereo_f32):
    import wave
    clipped = np.clip(stereo_f32, -0.98, 0.98)
    pcm = (clipped * 32767.0).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


# ───────────────────────── FRAME COMPOSITOR (16:9 + 9:16) ─────────────────────────

def alpha_blend_bgr(dst_bgr, src_rgba_np, x, y, opacity=1.0):
    """Fast in-place alpha composite of an RGBA numpy array onto BGR uint8 canvas."""
    if opacity <= 0.002:
        return
    H, W = dst_bgr.shape[:2]
    sh, sw = src_rgba_np.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + sw), min(H, y + sh)
    if x0 >= x1 or y0 >= y1:
        return
    sx0, sy0 = x0 - x, y0 - y
    sx1, sy1 = sx0 + (x1 - x0), sy0 + (y1 - y0)
    patch = src_rgba_np[sy0:sy1, sx0:sx1]
    a = (patch[:, :, 3:4].astype(np.float32) / 255.0) * opacity
    # Convert src RGB -> BGR
    src_bgr = patch[:, :, 2::-1].astype(np.float32)
    dst_roi = dst_bgr[y0:y1, x0:x1].astype(np.float32)
    dst_bgr[y0:y1, x0:x1] = np.clip(dst_roi * (1.0 - a) + src_bgr * a, 0, 255).astype(np.uint8)


def apply_camera_zoom_bgr(frame_bgr, cx, cy, zoom, out_w, out_h):
    """Smooth high-quality subpixel zoom/pan crop of a 1920x1080 desktop frame."""
    H, W = frame_bgr.shape[:2]
    crop_w = W / float(zoom)
    crop_h = crop_w * (out_h / float(out_w))
    if crop_h > H:
        crop_h = H
        crop_w = crop_h * (out_w / float(out_h))
    x0 = clamp(cx - crop_w * 0.5, 0.0, W - crop_w)
    y0 = clamp(cy - crop_h * 0.5, 0.0, H - crop_h)
    M = np.array([[out_w / crop_w, 0.0, -x0 * (out_w / crop_w)], [0.0, out_h / crop_h, -y0 * (out_h / crop_h)]], dtype=np.float32)
    return cv2.warpAffine(frame_bgr, M, (out_w, out_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


class PromoComposer:
    def __init__(self, media_cache):
        self.cache = media_cache
        self.icons = load_all_icons()
        self.desktop_pil, self.tb_app_x = build_base_desktop(self.icons)
        self.desktop_bgr = cv2.cvtColor(np.asarray(self.desktop_pil.convert("RGB")), cv2.COLOR_RGB2BGR)

        self.cursor_pil, self.cursor_hot = make_win11_cursor(scale=1.18)
        self.cursor_rgba = np.asarray(self.cursor_pil)

        # Pre-render 3 app mockups (BGR + rounded corner mask + window drop shadow)
        self.mockups_bgr = {}
        for app in APPS[:3]:
            m_pil = build_app_mockup(app, self.icons)
            self.mockups_bgr[app["key"]] = cv2.cvtColor(np.asarray(m_pil.convert("RGB")), cv2.COLOR_RGB2BGR)

        # Rounded corner alpha mask for app window (WIN_W x WIN_H)
        mask_pil = Image.new("L", (WIN_W * 2, WIN_H * 2), 0)
        ImageDraw.Draw(mask_pil).rounded_rectangle([0, 0, WIN_W * 2 - 1, WIN_H * 2 - 1], radius=WIN_R * 2, fill=255)
        self.win_mask_f = (np.asarray(mask_pil.resize((WIN_W, WIN_H), Image.LANCZOS), dtype=np.float32) / 255.0)[..., None]

        # Pre-rendered soft window drop shadow (padded by 32px)
        self.sh_pad = 32
        sh = Image.new("RGBA", (WIN_W + self.sh_pad * 2, WIN_H + self.sh_pad * 2), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle(
            [self.sh_pad, self.sh_pad + 10, self.sh_pad + WIN_W, self.sh_pad + WIN_H + 10],
            radius=WIN_R,
            fill=(0, 0, 0, 175),
        )
        sh = sh.filter(ImageFilter.GaussianBlur(18))
        self.win_shadow_rgba = np.asarray(sh)

        # Thin bright 1px window border overlay
        bdr = Image.new("RGBA", (WIN_W, WIN_H), (0, 0, 0, 0))
        ImageDraw.Draw(bdr).rounded_rectangle([0, 0, WIN_W - 1, WIN_H - 1], radius=WIN_R, outline=(255, 255, 255, 58), width=2)
        self.win_border_rgba = np.asarray(bdr)

        # Subtitle RGBA overlay (WIN_W x WIN_H)
        self.sub_rgba = np.asarray(make_subtitle_layer(WIN_W, WIN_H))

        # Floating Mode Tag pills (top-right inside desktop / above window)
        self.mode_pills = {}
        for app in APPS[:3]:
            self.mode_pills[app["key"]] = np.asarray(self._make_mode_pill(app))

        # Outro cards
        self.outro_16 = np.asarray(build_outro_card(W16, H16, self.icons, vertical=False))
        self.outro_9 = np.asarray(build_outro_card(W9, H9, self.icons, vertical=True))

        # Vertical 9:16 top/bottom static chrome overlays (per active app state)
        self.v9_headers = {"desktop": np.asarray(self._make_v9_header(None))}
        for app in APPS[:3]:
            self.v9_headers[app["key"]] = np.asarray(self._make_v9_header(app))
        self.v9_dock_cache = {}
        for active_k in (None, "deepseek", "antigravity", "codex"):
            self.v9_dock_cache[active_k] = np.asarray(self._make_v9_dock(active_k))

    def _make_mode_pill(self, app):
        f_txt = load_font(FONT_SANS, 20, weight=600)
        text = f"{app['name']}   ×   {app['mode_tag']}"
        tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        bb = tmp.textbbox((0, 0), text, font=f_txt)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        pw, ph = tw + 64, 44
        img = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=22, fill=(14, 14, 26, 215), outline=app["accent"] + (195,), width=2)
        d.ellipse([16, ph // 2 - 6, 28, ph // 2 + 6], fill=app["accent"] + (255,))
        d.text((40, (ph - th) // 2 - 2), text, font=f_txt, fill=(248, 250, 255, 255))
        return img

    def _make_v9_header(self, active_app):
        """Top header zone (1080 x 430) for 9:16 Douyin vertical layout."""
        img = Image.new("RGBA", (W9, 430), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        cx = W9 // 2
        f_tag = load_font(FONT_SANS, 25, weight=600)
        f_big = load_font(FONT_SERIF, 54, weight=700)
        f_pill = load_font(FONT_SANS, 26, weight=600)

        tag = "鸣潮 · 爱弥斯 AI 开机动画 v1.2"
        tb = d.textbbox((0, 0), tag, font=f_tag)
        tw = tb[2] - tb[0]
        d.rounded_rectangle([cx - tw // 2 - 26, 134, cx + tw // 2 + 26, 180], radius=23, fill=(255, 118, 192, 46), outline=(255, 152, 214, 175), width=2)
        d.text((cx - tw // 2, 142), tag, font=f_tag, fill=(255, 220, 240, 255))

        headline = "给主流 AI 装上爱弥斯启动动画"
        hb = d.textbbox((0, 0), headline, font=f_big)
        hx = cx - (hb[2] - hb[0]) // 2
        d.text((hx, 206), headline, font=f_big, fill=(14, 8, 24, 210), stroke_width=4, stroke_fill=(14, 8, 24, 210))
        d.text((hx, 206), headline, font=f_big, fill=(255, 255, 255, 255))

        if active_app is None:
            sub = "Windows 桌面实机演示 · 双击即触发三套官方原片方案"
            col = (182, 226, 255, 235)
            bdr = (120, 210, 255, 140)
            dot = (120, 224, 255, 255)
        else:
            sub = f"正在启动：{active_app['name']}  ·  {active_app['mode_tag']}"
            col = (255, 255, 255, 255)
            bdr = active_app["accent"] + (210,)
            dot = active_app["accent"] + (255,)
        sb = d.textbbox((0, 0), sub, font=f_pill)
        sw = sb[2] - sb[0]
        d.rounded_rectangle([cx - sw // 2 - 38, 304, cx + sw // 2 + 28, 358], radius=27, fill=(18, 18, 34, 220), outline=bdr, width=2)
        d.ellipse([cx - sw // 2 - 20, 324, cx - sw // 2 - 6, 338], fill=dot)
        d.text((cx - sw // 2 + 4, 314), sub, font=f_pill, fill=col)
        return img

    def _make_v9_dock(self, active_key):
        """Bottom 4-AI icon dock + open-source tagline (1080 x 360, placed at y=1350..1710 above Douyin caption safe area)."""
        img = Image.new("RGBA", (W9, 360), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        cx = W9 // 2
        f_lbl = load_font(FONT_SEGOE_SB, 20)
        f_ft = load_font(FONT_SANS, 25, weight=500)

        # Dock container
        d.rounded_rectangle([68, 72, W9 - 68, 224], radius=26, fill=(16, 16, 30, 215), outline=(255, 255, 255, 36), width=2)
        spacing = 224
        sx = cx - int(1.5 * spacing)
        for i, app in enumerate(APPS):
            ax = sx + i * spacing
            is_act = app["key"] == active_key
            if is_act:
                d.rounded_rectangle([ax - 88, 86, ax + 88, 210], radius=18, fill=app["accent"] + (42,), outline=app["accent"] + (215,), width=2)
            ic = self.icons[app["key"]].resize((68, 68), Image.LANCZOS)
            img.alpha_composite(ic, (ax - 34, 98))
            lb = d.textbbox((0, 0), app["short"], font=f_lbl)
            d.text((ax - (lb[2] - lb[0]) // 2, 174), app["short"], font=f_lbl, fill=(255, 255, 255, 255 if is_act else 165))

        ft = "GitHub 开源免费 · 四合一全平台绿色开箱版"
        fb = d.textbbox((0, 0), ft, font=f_ft)
        d.text((cx - (fb[2] - fb[0]) // 2, 254), ft, font=f_ft, fill=(235, 210, 232, 230))
        return img

    def render_desktop_frame(self, state):
        """
        Render the raw 1920x1080 desktop + optional hover/click highlight + app window + boot/loop overlay + cursor.
        state dict keys:
          - cursor: (x, y) or None
          - hover_row: int or None
          - click_row: int or None
          - click_ripple: float 0..1 or 0
          - active_app: dict or None
          - win_scale: float 0..1 (spring open / minimize)
          - win_alpha: float 0..1
          - mode_kind: "intro" | "reveal" | "loop"
          - intro_t: float (seconds into intro.mp4)
          - loop_t: float (seconds into loop.mp4)
          - overlay_alpha: float 0..1 (1.0 during full intro, fades down to 0.34 during reveal)
          - sub_alpha: float 0..1
          - flash_alpha: float 0..1 (optional brief white/pink flash on beat cut)
          - pill_alpha: float 0..1
        """
        frame = self.desktop_bgr.copy()

        # 1. Desktop icon hover / selected box + click ripple
        hover_row = state.get("hover_row")
        click_row = state.get("click_row")
        if hover_row is not None or click_row is not None:
            row = click_row if click_row is not None else hover_row
            x0, y0 = ICON_X - 14, ICON_Y0 + row * ICON_DY - 4
            x1, y1 = x0 + ICON_TILE_W + 28, y0 + ICON_TILE_H - 2
            ov = frame[y0:y1, x0:x1].astype(np.float32)
            if click_row is not None:
                col = np.array([255.0, 175.0, 96.0], np.float32)  # BGR Windows selection cyan-blue
                ov = ov * 0.70 + col * 0.30
                bdr_c = (255, 205, 96)
            else:
                col = np.array([255.0, 255.0, 255.0], np.float32)
                ov = ov * 0.86 + col * 0.14
                bdr_c = (210, 220, 235)
            frame[y0:y1, x0:x1] = np.clip(ov, 0, 255).astype(np.uint8)
            cv2.rectangle(frame, (x0, y0), (x1 - 1, y1 - 1), bdr_c, 1, cv2.LINE_AA)

        rip = state.get("click_ripple", 0.0)
        if rip > 0.005 and state.get("cursor") is not None:
            cx, cy = int(round(state["cursor"][0])), int(round(state["cursor"][1]))
            rad = int(round(10 + rip * 44))
            alpha_r = (1.0 - rip) * 0.85
            tmp = frame.copy()
            cv2.circle(tmp, (cx, cy), rad, (255, 215, 130), 3, cv2.LINE_AA)
            cv2.circle(tmp, (cx, cy), max(4, rad // 2), (255, 240, 210), 2, cv2.LINE_AA)
            frame = cv2.addWeighted(tmp, alpha_r, frame, 1.0 - alpha_r, 0)

        # 2. Active Taskbar indicator glow
        app = state.get("active_app")
        win_alpha = state.get("win_alpha", 0.0)
        if app is not None and win_alpha > 0.05:
            ax = self.tb_app_x[app["key"]]
            # Highlight pill behind taskbar icon + glowing bottom indicator bar
            ov = frame[H16 - 48 : H16 - 6, ax - 22 : ax + 22].astype(np.float32)
            ov = ov * (1.0 - 0.16 * win_alpha) + 255.0 * (0.16 * win_alpha)
            frame[H16 - 48 : H16 - 6, ax - 22 : ax + 22] = np.clip(ov, 0, 255).astype(np.uint8)
            b, g, r = app["accent"][2], app["accent"][1], app["accent"][0]
            cv2.line(frame, (ax - 9, H16 - 5), (ax + 9, H16 - 5), (b, g, r), 3, cv2.LINE_AA)

        # 3. Application Window + Aemeath Boot / Loop Overlay
        if app is not None and win_alpha > 0.01:
            mode = app["mode"]
            win_scale = state.get("win_scale", 1.0)
            ov_alpha = state.get("overlay_alpha", 1.0)
            kind = state.get("mode_kind", "intro")

            if kind == "intro":
                vid_bgr = self.cache.intro_at(mode, state.get("intro_t", 0.0))
                if ov_alpha >= 0.995:
                    win_bgr = vid_bgr.copy()
                else:
                    mock = self.mockups_bgr[app["key"]]
                    win_bgr = cv2.addWeighted(vid_bgr, ov_alpha, mock, 1.0 - ov_alpha, 0)
            elif kind == "crossfade":
                # Smooth handoff from intro -> loop while overlay fades from 1.0 -> residual (~0.36)
                vid_i = self.cache.intro_at(mode, state.get("intro_t", 14.0))
                vid_l = self.cache.loop_at(mode, state.get("loop_t", 0.0))
                cf = state.get("cf_loop", 0.0)
                vid_bgr = cv2.addWeighted(vid_l, cf, vid_i, 1.0 - cf, 0)
                mock = self.mockups_bgr[app["key"]]
                win_bgr = cv2.addWeighted(vid_bgr, ov_alpha, mock, 1.0 - ov_alpha, 0)
            else:  # loop reveal
                vid_l = self.cache.loop_at(mode, state.get("loop_t", 0.0))
                mock = self.mockups_bgr[app["key"]]
                win_bgr = cv2.addWeighted(vid_l, ov_alpha, mock, 1.0 - ov_alpha, 0)

            # Optional beat flash inside window
            fl = state.get("flash_alpha", 0.0)
            if fl > 0.005:
                flash_col = np.array([255.0, 232.0, 250.0], np.float32)
                win_bgr = np.clip(win_bgr.astype(np.float32) * (1.0 - fl * 0.35) + flash_col * (fl * 0.72), 0, 255).astype(np.uint8)

            # Live 思源宋体 subtitle overlay
            sub_a = state.get("sub_alpha", 0.0)
            if sub_a > 0.01:
                alpha_blend_bgr(win_bgr, self.sub_rgba, 0, 0, opacity=sub_a)

            # Thin bright Windows 11 window border
            alpha_blend_bgr(win_bgr, self.win_border_rgba, 0, 0, opacity=1.0)

            # Composite window with scale-in spring + drop shadow onto desktop
            if abs(win_scale - 1.0) < 0.003 and win_alpha >= 0.995:
                alpha_blend_bgr(frame, self.win_shadow_rgba, WIN_X - self.sh_pad, WIN_Y - self.sh_pad, opacity=1.0)
                roi = frame[WIN_Y : WIN_Y + WIN_H, WIN_X : WIN_X + WIN_W].astype(np.float32)
                m = self.win_mask_f
                frame[WIN_Y : WIN_Y + WIN_H, WIN_X : WIN_X + WIN_W] = np.clip(
                    roi * (1.0 - m) + win_bgr.astype(np.float32) * m, 0, 255
                ).astype(np.uint8)
            else:
                sw = max(32, int(round(WIN_W * win_scale)))
                sh = max(24, int(round(WIN_H * win_scale)))
                # Origin interpolates from icon center toward final window center!
                cx_t = WIN_X + WIN_W * 0.5
                cy_t = WIN_Y + WIN_H * 0.5
                origin_k = clamp((win_scale - 0.15) / 0.85)
                cx = app["tile_cx"] * (1.0 - origin_k) + cx_t * origin_k
                cy = app["tile_cy"] * (1.0 - origin_k) + cy_t * origin_k
                wx = int(round(cx - sw * 0.5))
                wy = int(round(cy - sh * 0.5))

                win_s = cv2.resize(win_bgr, (sw, sh), interpolation=cv2.INTER_LINEAR)
                mask_s = cv2.resize(self.win_mask_f[:, :, 0], (sw, sh), interpolation=cv2.INTER_LINEAR) * win_alpha
                # Clip to frame
                x0, y0 = max(0, wx), max(0, wy)
                x1, y1 = min(W16, wx + sw), min(H16, wy + sh)
                if x0 < x1 and y0 < y1:
                    sx0, sy0 = x0 - wx, y0 - wy
                    sx1, sy1 = sx0 + (x1 - x0), sy0 + (y1 - y0)
                    m_roi = mask_s[sy0:sy1, sx0:sx1, None]
                    dst = frame[y0:y1, x0:x1].astype(np.float32)
                    src = win_s[sy0:sy1, sx0:sx1].astype(np.float32)
                    frame[y0:y1, x0:x1] = np.clip(dst * (1.0 - m_roi) + src * m_roi, 0, 255).astype(np.uint8)

            # Note: Floating Mode Pill is composited exclusively in compose_16_9 (9:16 has its own top badge!)

        # 4. Crisp Windows 11 Mouse Cursor on top
        cur = state.get("cursor")
        if cur is not None:
            cx = int(round(cur[0])) - self.cursor_hot[0]
            cy = int(round(cur[1])) - self.cursor_hot[1]
            alpha_blend_bgr(frame, self.cursor_rgba, cx, cy, opacity=1.0)

        return frame

    def compose_16_9(self, desktop_bgr, state):
        """Apply subtle cinematic camera motion for 16:9 + floating mode pill + optional Outro Card fade."""
        cam_cx, cam_cy, cam_z = state.get("cam16", (W16 * 0.5, H16 * 0.5, 1.0))
        if abs(cam_z - 1.0) > 0.002:
            out = apply_camera_zoom_bgr(desktop_bgr, cam_cx, cam_cy, cam_z, W16, H16)
        else:
            out = desktop_bgr.copy()

        app = state.get("active_app")
        pa = state.get("pill_alpha", 0.0) * state.get("win_alpha", 0.0)
        if app is not None and pa > 0.01:
            pill = self.mode_pills[app["key"]]
            px = W16 - pill.shape[1] - 36
            py = 18
            alpha_blend_bgr(out, pill, px, py, opacity=pa)

        oa = state.get("outro_alpha", 0.0)
        if oa > 0.005:
            # Soft glowing cosmic Mode C background bokeh behind Outro Card
            bg_c = cv2.resize(self.cache.loop_at("c", state.get("outro_t", 0.0)), (W16, H16), interpolation=cv2.INTER_LINEAR)
            bg_c = cv2.GaussianBlur(bg_c, (0, 0), 14)
            bg_c = (bg_c.astype(np.float32) * 0.45).astype(np.uint8)
            out = cv2.addWeighted(bg_c, oa, out, 1.0 - oa, 0)
            alpha_blend_bgr(out, self.outro_16, 0, 0, opacity=oa)
        return out

    def compose_9_16(self, desktop_bgr, state, audio_level=0.0):
        """Bespoke 1080x1920 Douyin vertical showcase with 100%-uncropped 16:10 hero viewport + top title + dock + live bars."""
        # 1. Ambient blurred background infused with live scene colors
        small = cv2.resize(desktop_bgr, (90, 160), interpolation=cv2.INTER_AREA)
        blur = cv2.GaussianBlur(small, (0, 0), 9)
        bg = cv2.resize(blur, (W9, H9), interpolation=cv2.INTER_LINEAR)
        canvas = (bg.astype(np.float32) * 0.24 + np.array([18.0, 9.0, 11.0], np.float32)).clip(0, 255).astype(np.uint8)

        oa = state.get("outro_alpha", 0.0)
        if oa < 0.995:
            # 2. Center Hero Stage Viewport (1024 x 640 = 16:10 so the entire 1536x864 window fits 100% uncropped!)
            vw, vh = 1024, 640
            vx = (W9 - vw) // 2
            vy = 492
            vcx, vcy, vz = state.get("cam9", (W16 * 0.5, H16 * 0.5, 1.22))
            view = apply_camera_zoom_bgr(desktop_bgr, vcx, vcy, vz, vw, vh)

            # Soft glowing border around center viewport
            app = state.get("active_app")
            acc = app["accent"] if (app is not None and state.get("win_alpha", 0.0) > 0.15) else (120, 210, 255)
            cv2.rectangle(canvas, (vx - 4, vy - 4), (vx + vw + 4, vy + vh + 4), (acc[2], acc[1], acc[0]), 4, cv2.LINE_AA)
            canvas[vy : vy + vh, vx : vx + vw] = view

            # 3. Top Header
            hdr_key = app["key"] if (app is not None and state.get("win_alpha", 0.0) > 0.15) else "desktop"
            alpha_blend_bgr(canvas, self.v9_headers[hdr_key], 0, 24, opacity=1.0)

            # 4. Live Audio Equalizer Bars between viewport & dock (y=1185..1255)
            n_bars = 29
            bar_w = 14
            gap = 14
            total_bw = n_bars * (bar_w + gap) - gap
            bx0 = (W9 - total_bw) // 2
            t_glob = state.get("t_glob", 0.0)
            for bi in range(n_bars):
                dist_c = abs(bi - (n_bars - 1) * 0.5) / ((n_bars - 1) * 0.5)
                shape = max(0.18, 1.0 - 0.72 * (dist_c ** 1.4))
                wave = 0.55 + 0.45 * math.sin(t_glob * 11.5 + bi * 0.68)
                bh = int(round(8 + (audio_level * 62.0 * shape * wave)))
                bh = min(58, max(6, bh))
                bx = bx0 + bi * (bar_w + gap)
                by = 1236 - bh // 2
                u = bi / float(n_bars - 1)
                r = int(255 * (1 - u) + 110 * u)
                g = int(134 * (1 - u) + 230 * u)
                b = int(202 * (1 - u) + 255 * u)
                cv2.rectangle(canvas, (bx, by), (bx + bar_w, by + bh), (b, g, r), -1)

            # 5. Bottom 4-AI Dock (centered nicely above Douyin caption safe area)
            act_k = app["key"] if (app is not None and state.get("win_alpha", 0.0) > 0.15) else None
            alpha_blend_bgr(canvas, self.v9_dock_cache[act_k], 0, 1280, opacity=1.0)

        if oa > 0.005:
            bg_c = cv2.resize(self.cache.loop_at("c", state.get("outro_t", 0.0)), (W9, H9), interpolation=cv2.INTER_LINEAR)
            bg_c = cv2.GaussianBlur(bg_c, (0, 0), 16)
            bg_c = (bg_c.astype(np.float32) * 0.42).astype(np.uint8)
            canvas = cv2.addWeighted(bg_c, oa, canvas, 1.0 - oa, 0)
            alpha_blend_bgr(canvas, self.outro_9, 0, 0, opacity=oa)

        return canvas


# ───────────────────────── TIMELINE CHOREOGRAPHERS ─────────────────────────

def cursor_glide(p0, p1, u):
    """Natural human-like slight curved bezier glide from p0 -> p1."""
    s = smootherstep(0.0, 1.0, u)
    # Gentle arc perpendicular to motion
    mx = (p0[0] + p1[0]) * 0.5 + (p1[1] - p0[1]) * 0.10
    my = (p0[1] + p1[1]) * 0.5 - (p1[0] - p0[0]) * 0.08
    x = (1 - s) ** 2 * p0[0] + 2 * (1 - s) * s * mx + s ** 2 * p1[0]
    y = (1 - s) ** 2 * p0[1] + 2 * (1 - s) * s * my + s ** 2 * p1[1]
    return (x, y)


def build_short_timeline(t):
    """
    Compact Beat-Synced Showcase (25.20s total) synced 1:1 to aemeath_original_22s.mp3:
      Act 1 (0.00 - 7.80s): DeepSeek Harness -> Mode A (Drop #1 at 4.50s -> Starlight Wings!)
      Act 2 (7.80 - 14.30s): Antigravity -> Mode B (Click on 8.75s beat, Mecha Burst dead-on 10.50s climax!)
      Act 3 (14.30 - 21.80s): Codex -> Mode C (Paper Plane -> Salvation Wings -> Voyager Loop!)
      Outro (21.80 - 25.20s): Grand 4-in-1 AI Showcase + GitHub Repo
    """
    st = {"t_glob": t, "outro_alpha": 0.0, "pill_alpha": 0.0, "sub_alpha": 0.0, "flash_alpha": 0.0}
    win_cx, win_cy = WIN_X + WIN_W * 0.5, WIN_Y + WIN_H * 0.5

    # ACT 1: DeepSeek Harness (Mode A)
    if t < 7.80:
        app = APPS[0]
        p_start = (780.0, 460.0)
        p_icon = (float(app["tile_cx"]), float(app["tile_cy"]))
        if t < 1.22:
            # Mouse glides to DeepSeek icon, hovers, double-clicks at 0.98 & 1.11
            u = clamp((t - 0.10) / 0.80)
            st["cursor"] = cursor_glide(p_start, p_icon, u)
            if t >= 0.72:
                st["hover_row"] = 0
            if t >= 0.98:
                st["click_row"] = 0
                st["click_ripple"] = clamp((t - 0.98) / 0.34)
            z16 = 1.0 + 0.12 * smoothstep(0.25, 1.05, t)
            st["cam16"] = (W16 * 0.5 * (1 - 0.35 * (z16 - 1) / 0.12) + p_icon[0] * 0.35 * (z16 - 1) / 0.12,
                           H16 * 0.5 * (1 - 0.15 * (z16 - 1) / 0.12) + p_icon[1] * 0.15 * (z16 - 1) / 0.12, z16)
            # 9:16 zooms closely onto desktop left icons!
            st["cam9"] = (320.0, 290.0, 2.25)
        else:
            st["active_app"] = app
            # Spring open 1.22 -> 1.46, smooth close 7.55 -> 7.80
            if t < 1.46:
                u = (t - 1.22) / 0.24
                st["win_scale"] = 0.22 + 0.78 * ease_out_back(u, 0.85)
                st["win_alpha"] = smoothstep(0.0, 0.45, u)
                st["cursor"] = p_icon
                st["click_row"] = 0
                st["click_ripple"] = clamp((t - 1.11) / 0.30)
            elif t > 7.56:
                u = (t - 7.56) / 0.24
                st["win_scale"] = 1.0 - 0.35 * smoothstep(0.0, 1.0, u)
                st["win_alpha"] = 1.0 - smoothstep(0.0, 1.0, u)
            else:
                st["win_scale"] = 1.0
                st["win_alpha"] = 1.0
            st["pill_alpha"] = smoothstep(1.35, 1.65, t) * (1.0 - smoothstep(7.45, 7.65, t))

            # Beat-synced Mode A playback (1.0x real speed!)
            if t < 4.50:
                st["mode_kind"] = "intro"
                st["intro_t"] = 1.22 + (t - 1.22)  # 1.22s -> 4.50s (fluorescent line art -> neon scan!)
                st["overlay_alpha"] = 1.0
            elif t < 6.45:
                st["mode_kind"] = "intro"
                st["intro_t"] = 10.45 + (t - 4.50)  # 10.45s -> 12.40s (Starlight Wings Climax right on 4.50s Drop!)
                st["overlay_alpha"] = 1.0
                st["flash_alpha"] = (1.0 - smoothstep(4.50, 4.78, t)) * 0.85
                st["sub_alpha"] = smoothstep(4.62, 4.95, t) * (1.0 - smoothstep(6.15, 6.45, t))
            else:
                # 6.45 -> 7.80: Smooth fade out revealing live DeepSeek Harness UI + Mode A loop!
                st["mode_kind"] = "crossfade"
                st["intro_t"] = 12.40 + (t - 6.45) * 0.9
                st["loop_t"] = t - 6.45
                st["cf_loop"] = smoothstep(6.45, 6.95, t)
                st["overlay_alpha"] = 1.0 - 0.65 * smootherstep(6.45, 7.05, t)

            # Camera settles smoothly onto app window
            k = smoothstep(1.22, 1.60, t)
            st["cam16"] = (W16 * 0.5, H16 * 0.5, 1.12 * (1 - k) + 1.00 * k)
            st["cam9"] = (320.0 * (1 - k) + win_cx * k, 290.0 * (1 - k) + (win_cy + 16) * k, 2.25 * (1 - k) + 1.22 * k)

    # ACT 2: Antigravity (Mode B)
    elif t < 14.30:
        app = APPS[1]
        p_prev = (float(APPS[0]["tile_cx"]), float(APPS[0]["tile_cy"]))
        p_icon = (float(app["tile_cx"]), float(app["tile_cy"]))
        if t < 8.88:
            u = clamp((t - 7.85) / 0.72)
            st["cursor"] = cursor_glide(p_prev, p_icon, u)
            if t >= 8.40:
                st["hover_row"] = 1
            if t >= 8.62:
                st["click_row"] = 1
                st["click_ripple"] = clamp((t - 8.62) / 0.34)
            z16 = 1.00 + 0.12 * smoothstep(7.80, 8.65, t)
            st["cam16"] = (W16 * 0.5 * 0.65 + p_icon[0] * 0.35, H16 * 0.5 * 0.85 + p_icon[1] * 0.15, z16)
            k_z = smoothstep(7.80, 8.15, t)
            st["cam9"] = (win_cx * (1 - k_z) + 320.0 * k_z, (win_cy + 16) * (1 - k_z) + 330.0 * k_z, 1.22 * (1 - k_z) + 2.25 * k_z)
        else:
            st["active_app"] = app
            if t < 9.12:
                u = (t - 8.88) / 0.24
                st["win_scale"] = 0.22 + 0.78 * ease_out_back(u, 0.85)
                st["win_alpha"] = smoothstep(0.0, 0.45, u)
                st["cursor"] = p_icon
                st["click_row"] = 1
                st["click_ripple"] = clamp((t - 8.75) / 0.30)
            elif t > 14.06:
                u = (t - 14.06) / 0.24
                st["win_scale"] = 1.0 - 0.35 * smoothstep(0.0, 1.0, u)
                st["win_alpha"] = 1.0 - smoothstep(0.0, 1.0, u)
            else:
                st["win_scale"] = 1.0
                st["win_alpha"] = 1.0
            st["pill_alpha"] = smoothstep(9.00, 9.28, t) * (1.0 - smoothstep(13.95, 14.15, t))

            # Beat-synced Mode B: Idol smile -> Pixel-heart Glitch Tear -> Exostrider Mecha Burst DEAD-ON 10.50s Climax!
            if t < 9.65:
                st["mode_kind"] = "intro"
                st["intro_t"] = 7.45 + (t - 8.88)  # 7.45 -> 8.22s (Idol stage smile!)
                st["overlay_alpha"] = 1.0
            elif t < 12.65:
                st["mode_kind"] = "intro"
                st["intro_t"] = 9.60 + (t - 9.65)  # 9.60 -> 12.60s! Hits 10.45s Mecha Burst right at t=10.50s!
                st["overlay_alpha"] = 1.0
                if 10.45 <= t <= 10.75:
                    st["flash_alpha"] = (1.0 - smoothstep(10.48, 10.75, t)) * 0.55
                st["sub_alpha"] = smoothstep(10.58, 10.92, t) * (1.0 - smoothstep(12.30, 12.62, t))
            else:
                # 12.65 -> 14.30: Smooth reveal of live Antigravity IDE + Mode B Exostrider loop!
                st["mode_kind"] = "crossfade"
                st["intro_t"] = 12.60 + (t - 12.65) * 0.9
                st["loop_t"] = t - 12.65
                st["cf_loop"] = smoothstep(12.65, 13.15, t)
                st["overlay_alpha"] = 1.0 - 0.65 * smootherstep(12.65, 13.25, t)

            k = smoothstep(8.88, 9.24, t)
            st["cam16"] = (W16 * 0.5, H16 * 0.5, 1.12 * (1 - k) + 1.00 * k)
            st["cam9"] = (320.0 * (1 - k) + win_cx * k, 330.0 * (1 - k) + (win_cy + 16) * k, 2.25 * (1 - k) + 1.22 * k)

    # ACT 3: Codex (Mode C)
    elif t < 21.80:
        app = APPS[2]
        p_prev = (float(APPS[1]["tile_cx"]), float(APPS[1]["tile_cy"]))
        p_icon = (float(app["tile_cx"]), float(app["tile_cy"]))
        if t < 15.32:
            u = clamp((t - 14.35) / 0.68)
            st["cursor"] = cursor_glide(p_prev, p_icon, u)
            if t >= 14.88:
                st["hover_row"] = 2
            if t >= 15.08:
                st["click_row"] = 2
                st["click_ripple"] = clamp((t - 15.08) / 0.34)
            z16 = 1.00 + 0.12 * smoothstep(14.30, 15.10, t)
            st["cam16"] = (W16 * 0.5 * 0.65 + p_icon[0] * 0.35, H16 * 0.5 * 0.85 + p_icon[1] * 0.15, z16)
            k_z = smoothstep(14.30, 14.65, t)
            st["cam9"] = (win_cx * (1 - k_z) + 320.0 * k_z, (win_cy + 16) * (1 - k_z) + 410.0 * k_z, 1.22 * (1 - k_z) + 2.25 * k_z)
        else:
            st["active_app"] = app
            if t < 15.56:
                u = (t - 15.32) / 0.24
                st["win_scale"] = 0.22 + 0.78 * ease_out_back(u, 0.85)
                st["win_alpha"] = smoothstep(0.0, 0.45, u)
                st["cursor"] = p_icon
                st["click_row"] = 2
                st["click_ripple"] = clamp((t - 15.21) / 0.30)
            else:
                st["win_scale"] = 1.0
                st["win_alpha"] = 1.0
            st["pill_alpha"] = smoothstep(15.44, 15.72, t) * (1.0 - smoothstep(21.40, 21.75, t))

            # Beat-synced Mode C: Paper Plane soaring -> Salvation Wings Climax -> Voyager Loop!
            if t < 17.55:
                st["mode_kind"] = "intro"
                st["intro_t"] = 1.60 + (t - 15.32)  # 1.60 -> 3.83s (Paper Plane!)
                st["overlay_alpha"] = 1.0
            elif t < 20.05:
                st["mode_kind"] = "intro"
                st["intro_t"] = 10.20 + (t - 17.55)  # 10.20 -> 12.70s (Salvation wings & blade climax!)
                st["overlay_alpha"] = 1.0
                if t < 17.82:
                    st["flash_alpha"] = (1.0 - smoothstep(17.55, 17.82, t)) * 0.65
                st["sub_alpha"] = smoothstep(17.68, 18.02, t) * (1.0 - smoothstep(19.70, 20.02, t))
            else:
                # 20.05 -> 21.80: Smooth reveal of live Codex UI + Mode C Voyager starlight loop!
                st["mode_kind"] = "crossfade"
                st["intro_t"] = 12.70 + (t - 20.05) * 0.8
                st["loop_t"] = t - 20.05
                st["cf_loop"] = smoothstep(20.05, 20.55, t)
                st["overlay_alpha"] = 1.0 - 0.64 * smootherstep(20.05, 20.68, t)

            k = smoothstep(15.32, 15.68, t)
            st["cam16"] = (W16 * 0.5, H16 * 0.5, 1.12 * (1 - k) + 1.00 * k)
            st["cam9"] = (320.0 * (1 - k) + win_cx * k, 410.0 * (1 - k) + (win_cy + 16) * k, 2.25 * (1 - k) + 1.22 * k)

    # GRAND 4-IN-1 OUTRO CARD (21.80 - 25.20s)
    else:
        app = APPS[2]
        st["active_app"] = app
        st["win_scale"] = 1.0
        st["win_alpha"] = 1.0
        st["mode_kind"] = "loop"
        st["loop_t"] = t - 20.05
        st["overlay_alpha"] = 0.36
        st["cam16"] = (W16 * 0.5, H16 * 0.5, 1.00)
        st["cam9"] = (win_cx, win_cy + 16, 1.22)
        st["outro_alpha"] = smootherstep(21.80, 22.45, t)
        st["outro_t"] = t - 21.80

    return st


def build_full_timeline(t):
    """
    Full 3-Mode Showcase (57.00s total) playing EVERY complete 14.50s intro.mp4 with full audio & live 思源宋体 subtitles:
      Act 1 (0.00 - 17.80s): DeepSeek Harness -> Complete 14.50s Mode A + 1.90s Live UI Reveal
      Act 2 (17.80 - 35.55s): Antigravity     -> Complete 14.50s Mode B + 1.90s Live UI Reveal
      Act 3 (35.55 - 53.30s): Codex           -> Complete 14.50s Mode C + 1.90s Live UI Reveal
      Outro (53.30 - 57.00s): Grand 4-in-1 AI Showcase + GitHub Repo
    """
    st = {"t_glob": t, "outro_alpha": 0.0, "pill_alpha": 0.0, "sub_alpha": 0.0, "flash_alpha": 0.0}
    win_cx, win_cy = WIN_X + WIN_W * 0.5, WIN_Y + WIN_H * 0.5

    acts = [
        (0.00, 1.40, 17.80, APPS[0], (780.0, 460.0), 1.12, 1.25, 290.0),
        (17.80, 19.15, 35.55, APPS[1], (float(APPS[0]["tile_cx"]), float(APPS[0]["tile_cy"])), 18.85, 18.98, 330.0),
        (35.55, 36.90, 53.30, APPS[2], (float(APPS[1]["tile_cx"]), float(APPS[1]["tile_cy"])), 36.60, 36.73, 410.0),
    ]

    for idx, (t0, t_open, t_end, app, p_start, c1, c2, v9_y) in enumerate(acts):
        if t < t_end:
            p_icon = (float(app["tile_cx"]), float(app["tile_cy"]))
            if t < t_open:
                u = clamp((t - (t0 + 0.08)) / max(0.3, c1 - t0 - 0.16))
                st["cursor"] = cursor_glide(p_start, p_icon, u)
                if t >= c1 - 0.24:
                    st["hover_row"] = app["row"]
                if t >= c1:
                    st["click_row"] = app["row"]
                    st["click_ripple"] = clamp((t - c1) / 0.34)
                z16 = 1.00 + 0.12 * smoothstep(t0 + 0.10, c1, t)
                st["cam16"] = (W16 * 0.5 * 0.65 + p_icon[0] * 0.35, H16 * 0.5 * 0.85 + p_icon[1] * 0.15, z16)
                k_z = smoothstep(t0, t0 + 0.35, t) if idx > 0 else 1.0
                st["cam9"] = (win_cx * (1 - k_z) + 320.0 * k_z, (win_cy + 16) * (1 - k_z) + v9_y * k_z, 1.22 * (1 - k_z) + 2.25 * k_z)
            else:
                dt = t - t_open  # 0.00 -> 16.40s
                st["active_app"] = app
                is_last = idx == 2
                if dt < 0.24:
                    u = dt / 0.24
                    st["win_scale"] = 0.22 + 0.78 * ease_out_back(u, 0.85)
                    st["win_alpha"] = smoothstep(0.0, 0.45, u)
                    st["cursor"] = p_icon
                    st["click_row"] = app["row"]
                    st["click_ripple"] = clamp((t - c2) / 0.30)
                elif (not is_last) and t > t_end - 0.24:
                    u = (t - (t_end - 0.24)) / 0.24
                    st["win_scale"] = 1.0 - 0.35 * smoothstep(0.0, 1.0, u)
                    st["win_alpha"] = 1.0 - smoothstep(0.0, 1.0, u)
                else:
                    st["win_scale"] = 1.0
                    st["win_alpha"] = 1.0
                st["pill_alpha"] = smoothstep(0.15, 0.45, dt) * (1.0 - smoothstep(t_end - 0.35, t_end - 0.12, t))

                # Exact real AemeathAntigravityBoot.cs timing!
                # 0.00..12.60: full 1.00 intro, 12.60..14.50: quintic fade to 0.35 residual alpha, 14.50..16.40: loop.mp4 reveal!
                if dt < 14.50:
                    st["mode_kind"] = "intro"
                    st["intro_t"] = dt
                    if dt < 12.60:
                        st["overlay_alpha"] = 1.0
                    else:
                        st["overlay_alpha"] = 1.0 - 0.65 * smootherstep(12.60, 14.50, dt)
                    # Exact real subtitle timing: 4.65s..12.65s with 0.45s fade!
                    if 4.65 <= dt <= 12.65:
                        st["sub_alpha"] = clamp(min((dt - 4.65) / 0.45, (12.65 - dt) / 0.45))
                else:
                    st["mode_kind"] = "loop"
                    st["loop_t"] = dt - 14.50
                    st["overlay_alpha"] = 0.35

                k = smoothstep(0.0, 0.38, dt)
                st["cam16"] = (W16 * 0.5, H16 * 0.5, 1.12 * (1 - k) + 1.00 * k)
                st["cam9"] = (320.0 * (1 - k) + win_cx * k, v9_y * (1 - k) + (win_cy + 16) * k, 2.25 * (1 - k) + 1.22 * k)
            return st

    # GRAND 4-IN-1 OUTRO (53.30 -> 57.00s)
    st["active_app"] = APPS[2]
    st["win_scale"] = 1.0
    st["win_alpha"] = 1.0
    st["mode_kind"] = "loop"
    st["loop_t"] = t - (36.90 + 14.50)
    st["overlay_alpha"] = 0.35
    st["cam16"] = (W16 * 0.5, H16 * 0.5, 1.00)
    st["cam9"] = (win_cx, win_cy + 16, 1.22)
    st["outro_alpha"] = smootherstep(53.30, 53.95, t)
    st["outro_t"] = t - 53.30
    return st


# ───────────────────────── AUDIO TRACK BUILDERS ─────────────────────────

def build_short_audio(ffmpeg_bin, out_wav):
    dur = 25.20
    buf = np.zeros((int(round(dur * SR)), 2), dtype=np.float32)
    rng = np.random.default_rng(20261127)
    music = decode_audio_stereo(ffmpeg_bin, AUDIO_22S)
    # Smooth gentle fade-in on first 0.35s so it glides naturally over desktop hook
    fi_n = int(0.35 * SR)
    music[:fi_n] *= np.linspace(0.0, 1.0, fi_n, dtype=np.float32)[:, None]
    mix_at(buf, music, 0.0, gain=0.92)

    click = synth_mouse_click(rng)
    for tc in (0.98, 1.11, 8.62, 8.75, 15.08, 15.21):
        mix_at(buf, click, tc, gain=1.05)

    whoosh_open = synth_whoosh(0.20, 280.0, 960.0, gain=0.11)
    whoosh_close = synth_whoosh(0.18, 720.0, 260.0, gain=0.08)
    for to in (1.22, 8.88, 15.32):
        mix_at(buf, whoosh_open, to, gain=1.0)
    for tc in (7.56, 14.06):
        mix_at(buf, whoosh_close, tc, gain=1.0)

    mix_at(buf, synth_outro_chime(3.3), 21.85, gain=0.85)
    save_wav(out_wav, buf)
    return buf


def build_full_audio(ffmpeg_bin, out_wav):
    dur = 57.00
    buf = np.zeros((int(round(dur * SR)), 2), dtype=np.float32)
    rng = np.random.default_rng(20261128)
    intro_wav = decode_audio_stereo(ffmpeg_bin, AUDIO_14S5)
    # Mix full 14.50s boot audio cleanly for each of the 3 acts!
    for t_open in (1.40, 19.15, 36.90):
        mix_at(buf, intro_wav, t_open, gain=0.92)

    click = synth_mouse_click(rng)
    for tc in (1.12, 1.25, 18.85, 18.98, 36.60, 36.73):
        mix_at(buf, click, tc, gain=1.05)

    whoosh_open = synth_whoosh(0.20, 280.0, 960.0, gain=0.11)
    whoosh_close = synth_whoosh(0.18, 720.0, 260.0, gain=0.08)
    for to in (1.40, 19.15, 36.90):
        mix_at(buf, whoosh_open, to, gain=1.0)
    for tc in (17.56, 35.31):
        mix_at(buf, whoosh_close, tc, gain=1.0)

    mix_at(buf, synth_outro_chime(3.5), 53.35, gain=0.90)
    save_wav(out_wav, buf)
    return buf


# ───────────────────────── ENCODER & DRIVER ─────────────────────────

def start_encoder(ffmpeg_bin, out_mp4, w, h, audio_wav):
    cmd = [
        ffmpeg_bin, "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "pipe:0",
        "-i", audio_wav,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-profile:v", "high", "-level", "4.1",
        "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-crf", "17", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), "-ac", "2",
        "-movflags", "+faststart", "-shortest",
        out_mp4,
    ]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def render_edit(ffmpeg_bin, composer, edit_name, dur_sec, timeline_fn, audio_buf, wav_path, out_16, out_9):
    print(f"\n[Render] {edit_name} ({dur_sec:.2f}s -> 16:9 + 9:16 simultaneous dual-encode)...")
    t0 = time.time()
    n_frames = int(round(dur_sec * FPS))
    p16 = start_encoder(ffmpeg_bin, out_16, W16, H16, wav_path)
    p9 = start_encoder(ffmpeg_bin, out_9, W9, H9, wav_path)

    # Precompute smooth per-frame audio RMS for 9:16 equalizer bars
    win_s = int(SR / FPS)
    rms_arr = np.zeros(n_frames, dtype=np.float32)
    for fi in range(n_frames):
        s0 = fi * win_s
        seg = audio_buf[s0 : s0 + win_s]
        rms_arr[fi] = float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0
    # Smooth RMS envelope
    smooth_rms = 0.0
    for fi in range(n_frames):
        t = fi / float(FPS)
        smooth_rms = smooth_rms * 0.55 + clamp(rms_arr[fi] * 3.4, 0.0, 1.0) * 0.45
        st = timeline_fn(t)
        desk = composer.render_desktop_frame(st)
        f16 = composer.compose_16_9(desk, st)
        f9 = composer.compose_9_16(desk, st, audio_level=smooth_rms)
        p16.stdin.write(f16.tobytes())
        p9.stdin.write(f9.tobytes())
        if (fi + 1) % 150 == 0 or fi == n_frames - 1:
            print(f"  {edit_name}: {fi + 1}/{n_frames} frames ({time.time() - t0:.1f}s)")

    p16.stdin.close()
    p9.stdin.close()
    rc16, rc9 = p16.wait(), p9.wait()
    if rc16 != 0 or rc9 != 0:
        raise RuntimeError(f"ffmpeg failed: rc16={rc16}, rc9={rc9}")
    print(f"[Done] {edit_name} finished in {time.time() - t0:.1f}s!")


def render_preview_stills(composer, out_dir):
    """Render key verification stills before full video encoding."""
    os.makedirs(out_dir, exist_ok=True)
    checks = [
        ("01_desktop_click_deepseek", 1.04),
        ("02_modeA_boot_sub", 5.20),
        ("03_modeA_deepseek_reveal", 7.30),
        ("04_modeB_antigravity_mecha", 10.90),
        ("05_modeB_antigravity_reveal", 13.70),
        ("06_modeC_codex_plane", 16.50),
        ("07_modeC_codex_reveal", 21.10),
        ("08_outro_4in1", 23.60),
    ]
    for name, ts in checks:
        st = build_short_timeline(ts)
        desk = composer.render_desktop_frame(st)
        f16 = composer.compose_16_9(desk, st)
        f9 = composer.compose_9_16(desk, st, audio_level=0.72)
        cv2.imwrite(os.path.join(out_dir, f"{name}_16x9.jpg"), f16, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        cv2.imwrite(os.path.join(out_dir, f"{name}_9x16.jpg"), f9, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    # Build two neat contact sheets (4x2 for 16:9, 4x2 for 9:16) for instant visual review
    tiles16 = [cv2.resize(cv2.imread(os.path.join(out_dir, f"{n}_16x9.jpg")), (640, 360)) for n, _ in checks]
    sheet16 = np.vstack([np.hstack(tiles16[:4]), np.hstack(tiles16[4:])])
    cv2.imwrite(os.path.join(out_dir, "sheet_16x9.jpg"), sheet16, [int(cv2.IMWRITE_JPEG_QUALITY), 92])

    tiles9 = [cv2.resize(cv2.imread(os.path.join(out_dir, f"{n}_9x16.jpg")), (360, 640)) for n, _ in checks]
    sheet9 = np.vstack([np.hstack(tiles9[:4]), np.hstack(tiles9[4:])])
    cv2.imwrite(os.path.join(out_dir, "sheet_9x16.jpg"), sheet9, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    print("[Preview] Saved contact sheets to", out_dir)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview-only", action="store_true", help="Render keyframe contact sheets only")
    ap.add_argument("--only", choices=["short", "full", "all"], default="all")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    ffmpeg_bin = find_ffmpeg()
    cache = ModeMediaCache()
    cache.load_all()
    composer = PromoComposer(cache)

    preview_dir = r"C:\Users\yang2\.gemini\antigravity\brain\d2cd8584-0e12-4d6e-836f-4885a4bb1d96\scratch\promo_preview"
    if args.preview_only:
        render_preview_stills(composer, preview_dir)
        return

    wav_short = os.path.join(preview_dir, "audio_short.wav")
    wav_full = os.path.join(preview_dir, "audio_full.wav")
    os.makedirs(preview_dir, exist_ok=True)

    if args.only in ("short", "all"):
        buf_s = build_short_audio(ffmpeg_bin, wav_short)
        render_edit(
            ffmpeg_bin, composer, "紧凑卡点版", 25.20, build_short_timeline, buf_s, wav_short,
            os.path.join(OUT_DIR, "爱弥斯AI开机动画_宣传片_紧凑卡点版_横屏16x9.mp4"),
            os.path.join(OUT_DIR, "爱弥斯AI开机动画_宣传片_紧凑卡点版_竖屏9x16抖音版.mp4"),
        )

    if args.only in ("full", "all"):
        buf_f = build_full_audio(ffmpeg_bin, wav_full)
        render_edit(
            ffmpeg_bin, composer, "完整三模式版", 57.00, build_full_timeline, buf_f, wav_full,
            os.path.join(OUT_DIR, "爱弥斯AI开机动画_宣传片_完整三模式_横屏16x9.mp4"),
            os.path.join(OUT_DIR, "爱弥斯AI开机动画_宣传片_完整三模式_竖屏9x16抖音版.mp4"),
        )


if __name__ == "__main__":
    main()
