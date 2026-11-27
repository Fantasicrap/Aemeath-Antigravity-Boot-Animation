# -*- coding: utf-8 -*-
"""Render 30fps 1280x720 WPF-safe MP4s & Antigravity plugin WebP assets for all 3 Aemeath modes
using 100% OFFICIAL KURO GAMES Wuthering Waves footage (zero AI-generated art):
  - combat_showcase.mp4 : Resonator Combat Showcase | Aemeath
  - pv_blessing.mp4     : Resonator Showcase | Aemeath - GRADUATION SHOW (祝福)
  - ep_paper_plane.mp4  : EP3.1 - Aemeath - "Paper Plane" (纸飞机)
  - short_salvation.mp4 : Cinematic Short | Salvation (拯救)

Preserves all audio-synced slicing (14.5s《于电子星海轻歌》), sakura-pink fluorescent line art,
cyber pink-cyan neon holographic scan, Electronic Ghost Glitch tears, unobstructed starlight flares,
and seamless 8.0s loop / 16.0s loop-x2 handoff for Windows WPF overlay + Antigravity MCP App plugin.
"""
import argparse
import math
import os
import shutil
import subprocess

import cv2
import imageio_ffmpeg
import numpy as np
from PIL import Image

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOOTAGE_DIR = os.path.join(REPO_ROOT, "tools", "official_footage")
KF_DIR = os.path.join(REPO_ROOT, "tools", "keyframes")
AUDIO_WAV = os.path.join(REPO_ROOT, "tools", "source_audio", "aemeath_boot_14s5.wav")
OUT_BASE = os.path.join(REPO_ROOT, "windows-overlay", "assets")
PLUG_ASSETS = os.path.join(REPO_ROOT, "antigravity-plugin", "assets_src")
PREVIEW_DIR = os.path.join(REPO_ROOT, "docs", "preview")

W, H, FPS = 1280, 720, 30
INTRO_SEC = 14.5
LOOP_SEC = 8.0


def find_ffmpeg():
    env_bin = os.environ.get("FFMPEG_BIN")
    if env_bin and os.path.exists(env_bin):
        return env_bin
    sys_ff = shutil.which("ffmpeg")
    if sys_ff:
        return sys_ff
    return imageio_ffmpeg.get_ffmpeg_exe()


def clamp(v, a=0.0, b=1.0):
    return a if v < a else (b if v > b else v)


def smooth(a, b, x):
    t = clamp((x - a) / max(1e-6, (b - a)))
    return t * t * (3.0 - 2.0 * t)


def smoother(a, b, x):
    t = clamp((x - a) / max(1e-6, (b - a)))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def fast_bloom(layer, sigma):
    small = cv2.resize(layer, (W // 6, H // 6), interpolation=cv2.INTER_AREA)
    blur = cv2.GaussianBlur(small, (0, 0), max(0.8, sigma * 0.18))
    return cv2.resize(blur, (W, H), interpolation=cv2.INTER_LINEAR)


def crop_16_9(fr, crop_bot=0.0, x_bias=0.5, crop_top=0.0):
    """Aspect-preserving 16:9 crop & high-quality resize to 1280x720 (removes any top/bottom caption strip)."""
    h0, w0 = fr.shape[:2]
    y_top = int(round(h0 * crop_top)) if crop_top > 0.0 else 0
    y_bot = int(round(h0 * (1.0 - crop_bot))) if crop_bot > 0.0 else h0
    if y_top > 0 or y_bot < h0:
        fr = fr[y_top:y_bot, :]
        h0, w0 = fr.shape[:2]
    target_ar = W / float(H)
    cur_ar = w0 / float(h0)
    if cur_ar > target_ar + 1e-4:
        tw = int(round(h0 * target_ar))
        x0 = int(round((w0 - tw) * x_bias))
        x0 = max(0, min(w0 - tw, x0))
        fr = fr[:, x0 : x0 + tw]
    elif cur_ar < target_ar - 1e-4:
        th = int(round(w0 / target_ar))
        y0 = max(0, (h0 - th) // 2)
        fr = fr[y0 : y0 + th, :]
    return cv2.resize(fr, (W, H), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)


class ClipBank:
    """Caches decoded official HD clips in memory for ultra-fast, frame-accurate sampling."""

    def __init__(self):
        self._cache = {}

    def load_segment(self, filename, t_start, t_end, crop_bot=0.0, x_bias=0.5, crop_top=0.0):
        key = (filename, round(t_start, 3), round(t_end, 3), round(crop_bot, 3), round(x_bias, 2), round(crop_top, 3))
        if key in self._cache:
            return self._cache[key]
        path = os.path.join(FOOTAGE_DIR, filename)
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            raise FileNotFoundError(f"Cannot open official footage: {path}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        f0 = max(0, int(round(t_start * fps)))
        f1 = max(f0 + 1, int(round(t_end * fps)))
        cap.set(cv2.CAP_PROP_POS_FRAMES, f0)
        frames = []
        for _ in range(f1 - f0 + 1):
            ok, fr = cap.read()
            if not ok:
                break
            frames.append(crop_16_9(fr, crop_bot=crop_bot, x_bias=x_bias, crop_top=crop_top).astype(np.uint8))
        cap.release()
        if not frames:
            raise RuntimeError(f"No frames decoded from {filename} [{t_start}, {t_end}]")
        self._cache[key] = frames
        return frames

    def sample(self, frames, norm_u, ping_pong=False):
        """Sample frame smoothly with linear temporal interpolation for silky slow-mo."""
        u = clamp(norm_u, 0.0, 1.0)
        if ping_pong:
            u = u * 2.0 if u <= 0.5 else (1.0 - u) * 2.0
        n = len(frames)
        if n == 1:
            return frames[0].astype(np.float32)
        pos = u * (n - 1)
        i0 = int(math.floor(pos))
        i1 = min(n - 1, i0 + 1)
        frac = pos - i0
        if frac < 1e-3 or i0 == i1:
            return frames[i0].astype(np.float32)
        return frames[i0].astype(np.float32) * (1.0 - frac) + frames[i1].astype(np.float32) * frac

    def grab_frame(self, filename, ts, crop_bot=0.0, x_bias=0.5, crop_top=0.0):
        frames = self.load_segment(filename, ts, ts + 0.05, crop_bot=crop_bot, x_bias=x_bias, crop_top=crop_top)
        return frames[0].astype(np.float32)


def save_webp(bgr_f32, out_path, quality=84):
    rgb = cv2.cvtColor(np.clip(bgr_f32, 0, 255).astype(np.uint8), cv2.COLOR_BGR2RGB)
    Image.fromarray(rgb).save(out_path, format="WEBP", quality=quality, method=6)


def save_png(bgr_f32, out_path):
    rgb = cv2.cvtColor(np.clip(bgr_f32, 0, 255).astype(np.uint8), cv2.COLOR_BGR2RGB)
    Image.fromarray(rgb).save(out_path, format="PNG")


def save_jpg(bgr_f32, out_path, quality=94):
    rgb = cv2.cvtColor(np.clip(bgr_f32, 0, 255).astype(np.uint8), cv2.COLOR_BGR2RGB)
    Image.fromarray(rgb).save(out_path, format="JPEG", quality=quality)


def scharr_mag(ch):
    gx = cv2.Scharr(ch, cv2.CV_32F, 1, 0) / 32.0
    gy = cv2.Scharr(ch, cv2.CV_32F, 0, 1) / 32.0
    return np.hypot(gx, gy)


def build_derived_layers(img_bgr, head_cx=0.50, head_cy=0.44):
    """Extract sakura-pink fluorescent line art & cyber pink-cyan holographic neon aura from official frame."""
    rgb = img_bgr[..., ::-1] / 255.0
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]

    # Soft vignette so edges fade cleanly into pitch-black #000000 cosmos
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    nx, ny = xx / W, yy / H
    vig = np.clip(1.0 - np.hypot((nx - head_cx) / 0.62, (ny - head_cy) / 0.62) ** 2.2, 0.0, 1.0)
    subject_mask = cv2.GaussianBlur((lum > 0.08).astype(np.float32), (0, 0), 7.0)
    subject_mask = np.clip((subject_mask - 0.08) / 0.30, 0.0, 1.0) * (0.25 + 0.75 * vig)

    grad = np.maximum(scharr_mag(lum), 0.78 * np.maximum(scharr_mag(rgb[..., 0]), scharr_mag(rgb[..., 2])))
    valley = np.clip(cv2.GaussianBlur(lum, (0, 0), 1.8) - lum, 0.0, 1.0)
    lines = np.clip(grad * 3.1 + valley * 4.4, 0.0, 1.0) * subject_mask
    lines = np.clip((lines - 0.12) / 0.76, 0.0, 1.0) ** 0.85

    line_glow = cv2.GaussianBlur(lines, (0, 0), 2.4)
    l_int = np.clip(lines * 1.18 + line_glow * 0.50, 0.0, 1.0)[..., None]
    pink_tint = np.array([228.0, 178.0, 255.0], np.float32)
    line_col = pink_tint * (1.0 - lines[..., None] * 0.55) + 255.0 * (lines[..., None] * 0.55)
    line_art = np.clip(line_col * l_int, 0, 255).astype(np.float32)

    rim_blur = cv2.GaussianBlur(lines, (0, 0), 7.5)
    cyan_mix = np.clip(1.0 - ny * 1.8, 0.0, 1.0)
    neon_b = np.clip(img_bgr[..., 0] * 0.72 + rim_blur * (185.0 + 70.0 * cyan_mix) + lines * 185.0, 0, 255)
    neon_g = np.clip(img_bgr[..., 1] * 0.50 + rim_blur * (105.0 + 110.0 * cyan_mix) + lines * 165.0, 0, 255)
    neon_r = np.clip(img_bgr[..., 2] * 0.86 + rim_blur * (235.0 - 85.0 * cyan_mix) + lines * 210.0, 0, 255)
    neon_aura = np.stack([neon_b, neon_g, neon_r], axis=-1) * subject_mask[..., None]

    head_r = np.hypot((nx - head_cx) * (W / H), (ny - head_cy))
    return line_art, neon_aura, head_r, xx, yy


def apply_camera_zoom(img_bgr, scale=1.0, tx=0.0, ty=0.0, cx=0.5, cy=0.5):
    if abs(scale - 1.0) < 1e-4 and abs(tx) < 0.05 and abs(ty) < 0.05:
        return img_bgr
    px, py = cx * W, cy * H
    M = np.array(
        [[scale, 0.0, (1.0 - scale) * px + tx], [0.0, scale, (1.0 - scale) * py + ty]],
        dtype=np.float32,
    )
    return cv2.warpAffine(img_bgr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def apply_digital_glitch(frame, strength, seed):
    if strength <= 0.01:
        return frame
    rng = np.random.default_rng(seed)
    out = frame.copy()
    shift = int(round(3 + strength * 18))
    if shift > 0:
        out[:, shift:, 2] = frame[:, :-shift, 2]
        out[:, :-shift, 0] = frame[:, shift:, 0]
    n_bands = int(4 + strength * 14)
    for _ in range(n_bands):
        y0 = int(rng.integers(0, H - 6))
        bh = int(rng.integers(3, max(6, int(12 + strength * 36))))
        y1 = min(H, y0 + bh)
        dx = int(rng.integers(-int(12 + strength * 58), int(12 + strength * 58)))
        if dx != 0:
            out[y0:y1] = np.roll(out[y0:y1], dx, axis=1)
        if rng.random() < 0.35 * strength:
            col = np.array([255.0, 235.0, 95.0], np.float32) if rng.random() < 0.55 else np.array([205.0, 95.0, 255.0], np.float32)
            out[y0 : min(y1, y0 + 4)] = np.clip(out[y0 : min(y1, y0 + 4)] * 0.4 + col * 0.75, 0, 255)
    if strength > 0.25:
        out[::4] *= 1.0 - 0.14 * strength
    return np.clip(out, 0, 255)


def add_holo_scanline(frame, y_norm, intensity):
    if intensity <= 0.01 or y_norm < -0.05 or y_norm > 1.05:
        return frame
    iy = int(clamp(y_norm, 0.0, 0.999) * H)
    layer = np.zeros_like(frame)
    th = max(2, int(4 + intensity * 6))
    y0, y1 = max(0, iy - th), min(H, iy + th + 1)
    layer[y0:y1, :] = np.array([255.0, 228.0, 145.0], np.float32)
    glow = fast_bloom(layer, 14) * np.array([1.0, 0.78, 0.92], np.float32)
    return np.clip(frame + (layer * 0.85 + glow * 1.15) * intensity, 0, 255)


def add_star_flare(frame, cx, cy, size, intensity, tint_bgr=(0.82, 0.76, 1.0), anamorphic=0.0, v_scale=1.0):
    if intensity <= 0.005:
        return frame
    layer = np.zeros_like(frame)
    ix, iy = int(cx), int(cy)
    r_v, r_h = int(size * 1.15 * v_scale), int(size * 1.38)
    if r_v > 4:
        pts_v = np.array([[ix, iy - r_v], [ix + max(2, int(size * 0.042)), iy], [ix, iy + r_v], [ix - max(2, int(size * 0.042)), iy]], np.int32)
        cv2.fillConvexPoly(layer, pts_v, (245, 245, 255), cv2.LINE_AA)
    pts_h = np.array([[ix - r_h, iy], [ix, iy - max(2, int(size * 0.038))], [ix + r_h, iy], [ix, iy + max(2, int(size * 0.038))]], np.int32)
    cv2.fillConvexPoly(layer, pts_h, (245, 245, 255), cv2.LINE_AA)
    cv2.circle(layer, (ix, iy), max(3, int(size * 0.10)), (255, 255, 255), -1, cv2.LINE_AA)
    if anamorphic > 0.01:
        th = max(2, int(2 + anamorphic * 5))
        bw = int(W * 0.48)
        x0, x1 = max(0, ix - bw), min(W, ix + bw)
        pts_b = np.array([[x0, iy], [ix, max(0, iy - th)], [x1, iy], [ix, min(H - 1, iy + th)]], np.int32)
        cv2.fillConvexPoly(layer, pts_b, (235 * anamorphic, 210 * anamorphic, 255 * anamorphic), cv2.LINE_AA)
    tint = np.array(tint_bgr, np.float32)
    added = (layer * 0.78 + fast_bloom(layer, 10) * 0.88 * tint + fast_bloom(layer, 28) * 0.72 * tint) * intensity
    return np.clip(frame + added, 0, 255)


def add_cosmic_motes(frame, phase, motes, opacity=1.0):
    if opacity <= 0.01:
        return frame
    layer = np.zeros_like(frame)
    for mx0, my0, rad, k_spd, ph0, ctype in motes:
        x = int((mx0 * W + 18.0 * math.sin((phase * k_spd + ph0) * 2.0 * math.pi)) % W)
        y = int(((my0 - phase * k_spd) % 1.0) * H)
        tw = (0.35 + 0.65 * (0.5 + 0.5 * math.sin((phase * 2.0 + ph0) * 2.0 * math.pi))) * opacity
        if ctype == 0:
            col = (int(210 * tw), int(155 * tw), int(255 * tw))
        elif ctype == 1:
            col = (int(255 * tw), int(235 * tw), int(125 * tw))
        else:
            col = (int(165 * tw), int(235 * tw), int(255 * tw))
        cv2.circle(layer, (x, y), max(1, int(rad)), col, -1, cv2.LINE_AA)
    return np.clip(frame + layer * 0.74 + fast_bloom(layer, 6) * 0.55, 0, 255)


def start_ffmpeg(ffmpeg_bin, out_mp4, audio_wav=None):
    cmd = [
        ffmpeg_bin, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "bgr24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    ]
    if audio_wav:
        cmd += ["-i", audio_wav]
    cmd += [
        "-c:v", "libx264", "-profile:v", "baseline", "-level", "3.1",
        "-preset", "fast", "-crf", "16",
        "-bf", "0", "-g", "15", "-keyint_min", "15", "-sc_threshold", "0",
        "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
        "-movflags", "+faststart",
    ]
    if audio_wav:
        cmd += ["-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k", "-shortest"]
    cmd += [out_mp4]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def make_loop_x2(ffmpeg_bin, out_dir):
    loop_x2 = os.path.join(out_dir, "loop-x2.mp4")
    list_txt = os.path.join(out_dir, "_concat.txt")
    with open(list_txt, "w", encoding="utf-8") as f:
        f.write("file 'loop.mp4'\nfile 'loop.mp4'\n")
    subprocess.run(
        [ffmpeg_bin, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", list_txt, "-c", "copy", "-movflags", "+faststart", loop_x2],
        check=True,
    )
    os.remove(list_txt)


def make_motes(seed, count=42):
    rng = np.random.default_rng(seed)
    return [(rng.random(), rng.random(), 1.1 + rng.random() * 2.1, 1 if i % 3 else 2, rng.random(), i % 3) for i in range(count)]


# ───────────────────────── MODE A: 官方原片 · 星海睁眼觉醒 ─────────────────────────

def render_mode_a(ffmpeg_bin, bank):
    print("[Mode A] Rendering 官方原片 · 星海睁眼觉醒 ...")
    out_dir = os.path.join(OUT_BASE, "a")
    os.makedirs(out_dir, exist_ok=True)

    # Official Kuro Games clips (100% subtitle-free!)
    seg_ep_closed = bank.load_segment("ep_paper_plane.mp4", 216.0, 224.2)      # Gentle closed-eyes smile + cyan wing glow
    seg_eye_open = bank.load_segment("short_salvation.mp4", 250.9, 253.2)      # Official closed -> golden star-eyes opening!
    seg_wing_rise = bank.load_segment("ep_paper_plane.mp4", 227.5, 234.0)      # Pure-white angelic starlight wings awakening
    seg_wing_loop = bank.load_segment("ep_paper_plane.mp4", 230.0, 234.0)      # Calm glowing wings in deep dark cosmos

    kf_closed = bank.grab_frame("short_salvation.mp4", 251.1)
    kf_open = bank.grab_frame("short_salvation.mp4", 252.8)
    kf_climax = bank.grab_frame("ep_paper_plane.mp4", 231.5)
    line_art, neon_aura, head_r, xx, yy = build_derived_layers(kf_closed, head_cx=0.50, head_cy=0.45)

    # Save official keyframes & plugin WebPs
    save_jpg(kf_closed, os.path.join(KF_DIR, "a_closed.jpg"))
    save_jpg(kf_open, os.path.join(KF_DIR, "a_open.jpg"))
    save_jpg(kf_climax, os.path.join(KF_DIR, "a_climax.jpg"))
    save_webp(kf_closed, os.path.join(PLUG_ASSETS, "a_closed.webp"), quality=84)
    save_webp(kf_open, os.path.join(PLUG_ASSETS, "a_open.webp"), quality=84)
    save_webp(kf_climax, os.path.join(PLUG_ASSETS, "a_climax.webp"), quality=84)
    save_webp(line_art, os.path.join(PLUG_ASSETS, "a_line.webp"), quality=82)
    save_webp(neon_aura, os.path.join(PLUG_ASSETS, "a_neon.webp"), quality=82)

    motes = make_motes(202601, 44)
    PINK_GOLD = (0.78, 0.80, 1.0)
    CYAN_WHITE = (1.0, 0.92, 0.72)

    def loop_frame_a(phase):
        frame = bank.sample(seg_wing_loop, phase, ping_pong=True)
        breath = 0.14 + 0.12 * (0.5 + 0.5 * math.sin(phase * 2.0 * math.pi))
        frame = add_star_flare(frame, W * 0.24, H * 0.30, 110, breath * 0.42, tint_bgr=CYAN_WHITE)
        frame = add_star_flare(frame, W * 0.76, H * 0.30, 110, breath * 0.42, tint_bgr=PINK_GOLD)
        return add_cosmic_motes(frame, phase, motes, opacity=0.72)

    total_intro = int(round(INTRO_SEC * FPS))
    proc = start_ffmpeg(ffmpeg_bin, os.path.join(out_dir, "intro.mp4"), audio_wav=AUDIO_WAV)
    for fi in range(total_intro):
        t = fi / FPS
        phase = ((t - INTRO_SEC) / LOOP_SEC) % 1.0

        if t < 4.45:
            # Beat 1-2: Pure black void -> official Aemeath pink-white fluorescent line art -> cyber neon scan
            r_lim = 0.18 + smooth(0.0, 2.20, t) * 0.28 + smooth(2.20, 4.35, t) * 1.15
            rad_mask = np.clip((r_lim - head_r) / 0.14, 0.0, 1.0)[..., None]
            op_line = smooth(0.10, 0.85, t) * (1.0 - smooth(3.05, 4.45, t) * 0.40)
            op_neon = smooth(2.05, 4.10, t)
            base = line_art * rad_mask * op_line + neon_aura * rad_mask * op_neon
            frame = apply_camera_zoom(np.clip(base, 0, 255), scale=1.03 - 0.03 * smooth(0.0, 4.45, t))
            if 1.85 <= t <= 4.35:
                sp = clamp((t - 1.85) / 2.50)
                frame = add_holo_scanline(frame, 0.12 + sp * 0.78, math.sin(sp * math.pi) * 0.52)
            frame = add_cosmic_motes(frame, phase, motes, opacity=smooth(1.6, 4.2, t) * 0.56)
        elif t < 8.85:
            # Beat 3: Materialize into official EP3.1 closed-eyes smiling Aemeath with glowing cyan wings!
            u = clamp((t - 4.45) / 4.40)
            vid = bank.sample(seg_ep_closed, u)
            mat = smooth(4.45, 5.15, t)
            frame = neon_aura * (1.0 - mat) + vid * mat if mat < 0.999 else vid
            if 4.45 <= t <= 6.20:
                fg = math.sin(clamp((t - 4.45) / 1.75) * math.pi)
                frame = add_star_flare(frame, W * 0.18, H * 0.42, 165, fg * 0.72, tint_bgr=CYAN_WHITE)
                frame = add_star_flare(frame, W * 0.82, H * 0.42, 165, fg * 0.72, tint_bgr=PINK_GOLD)
            frame = add_cosmic_motes(frame, phase, motes, opacity=0.62)
        elif t < 10.45:
            # Beat 4: Electronic Ghost Glitch flash -> OFFICIAL closed-to-open golden star-eyes close-up!
            u = clamp((t - 8.85) / 1.60)
            frame = bank.sample(seg_eye_open, u)
            if 8.85 <= t <= 9.20:
                gs = (1.0 - smooth(8.85, 9.20, t)) * 0.85
                frame = apply_digital_glitch(frame, gs, fi * 7 + 11)
            elif 10.05 <= t <= 10.45:
                gs = smooth(10.05, 10.42, t) * 0.90
                frame = apply_digital_glitch(frame, gs, fi * 13 + 3)
                flash = smooth(10.22, 10.45, t)
                frame = np.clip(frame * (1.0 - flash * 0.45) + np.array([245.0, 225.0, 255.0], np.float32) * (flash * 0.82), 0, 255)
            frame = add_cosmic_motes(frame, phase, motes, opacity=0.70)
        else:
            # Beat 5-6: 10.50s Ultimate Climax -> Official Starlight Wings Awakening -> seamless handoff to loop_a!
            if t < 12.60:
                u = clamp((t - 10.45) / 2.15)
                frame = bank.sample(seg_wing_rise, u * 0.55)
                frame = add_cosmic_motes(frame, phase, motes, opacity=0.75)
                if 10.45 <= t <= 12.40:
                    bp = clamp((t - 10.45) / 1.95)
                    burst = smooth(0.0, 0.14, bp) * ((1.0 - smooth(0.14, 1.0, bp)) ** 1.30)
                    frame = add_star_flare(frame, W * 0.23, H * 0.34, 240, burst * 0.88, tint_bgr=CYAN_WHITE)
                    frame = add_star_flare(frame, W * 0.77, H * 0.34, 240, burst * 0.88, tint_bgr=PINK_GOLD)
                    frame = add_star_flare(frame, W * 0.50, H * 0.55, 130, burst * 0.58, tint_bgr=PINK_GOLD, anamorphic=burst * 0.78, v_scale=0.32)
                    after = 1.0 - smooth(10.45, 10.75, t)
                    if after > 0.01:
                        frame = np.clip(frame + np.array([230.0, 215.0, 255.0], np.float32) * (after * 0.48), 0, 255)
            else:
                # 12.60..14.50s: Smooth crossfade into exact phase of loop_frame_a so 14.50s -> loop.mp4 is 100% seamless!
                xf = smoother(12.60, 13.45, t)
                loop_f = loop_frame_a(phase)
                if xf < 0.999:
                    u = clamp((t - 10.45) / 3.20)
                    rise_f = add_cosmic_motes(bank.sample(seg_wing_rise, min(1.0, 0.55 + u * 0.45)), phase, motes, opacity=0.72)
                    frame = rise_f * (1.0 - xf) + loop_f * xf
                else:
                    frame = loop_f

        if fi == int(1.6 * FPS):
            save_png(frame, os.path.join(PREVIEW_DIR, "modeA_01_line.png"))
        elif fi == int(9.9 * FPS):
            save_png(frame, os.path.join(PREVIEW_DIR, "modeA_02_eyes.png"))
        elif fi == int(11.1 * FPS):
            save_png(frame, os.path.join(PREVIEW_DIR, "modeA_03_climax.png"))
        proc.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())

    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed on mode A intro.mp4")

    total_loop = int(round(LOOP_SEC * FPS))
    proc2 = start_ffmpeg(ffmpeg_bin, os.path.join(out_dir, "loop.mp4"))
    for fi in range(total_loop):
        proc2.stdin.write(np.clip(loop_frame_a(fi / total_loop), 0, 255).astype(np.uint8).tobytes())
    proc2.stdin.close()
    if proc2.wait() != 0:
        raise RuntimeError("ffmpeg failed on mode A loop.mp4")
    make_loop_x2(ffmpeg_bin, out_dir)
    print("[Mode A] Done.")


# ───────────────────────── MODE B: 官方原片 · 双形态切换（电子幽灵 × 隧者机兵） ─────────────────────────

def render_mode_b(ffmpeg_bin, bank):
    print("[Mode B] Rendering 官方原片 · 双形态切换（电子幽灵 × 隧者机兵） ...")
    out_dir = os.path.join(OUT_BASE, "b")
    os.makedirs(out_dir, exist_ok=True)

    # Official Kuro Games footage (crop_bot=0.095 cleanly removes any tiny bottom English captions!)
    seg_appear = bank.load_segment("combat_showcase.mp4", 16.0, 19.6, crop_bot=0.095)
    seg_idol = bank.load_segment("pv_blessing.mp4", 195.2, 199.6, crop_top=0.11, x_bias=0.72)
    seg_heart_glitch = bank.load_segment("combat_showcase.mp4", 68.4, 69.9, crop_bot=0.095)
    seg_mecha_charge = bank.load_segment("combat_showcase.mp4", 62.1, 63.6, crop_bot=0.095)
    seg_mecha_ult = bank.load_segment("combat_showcase.mp4", 73.5, 75.4, crop_bot=0.10)
    seg_mecha_loop = bank.load_segment("ep_paper_plane.mp4", 206.0, 213.6, crop_bot=0.0)

    kf_scan = bank.grab_frame("combat_showcase.mp4", 19.2, crop_bot=0.095)
    kf_idol = bank.grab_frame("pv_blessing.mp4", 196.2, crop_top=0.11, x_bias=0.72)
    kf_mecha = bank.grab_frame("combat_showcase.mp4", 63.0, crop_bot=0.095)
    kf_mecha_dark = bank.grab_frame("ep_paper_plane.mp4", 209.0)
    b_line, b_neon, _, _, yy = build_derived_layers(kf_scan, head_cx=0.52, head_cy=0.46)

    save_jpg(kf_idol, os.path.join(KF_DIR, "b_idol.jpg"))
    save_jpg(kf_mecha, os.path.join(KF_DIR, "b_mecha.jpg"))
    save_jpg(kf_mecha_dark, os.path.join(KF_DIR, "b_mecha_loop.jpg"))
    save_webp(kf_idol, os.path.join(PLUG_ASSETS, "b_idol.webp"), quality=84)
    save_webp(kf_mecha, os.path.join(PLUG_ASSETS, "b_mecha.webp"), quality=84)
    save_webp(b_line, os.path.join(PLUG_ASSETS, "b_line.webp"), quality=82)
    save_webp(b_neon, os.path.join(PLUG_ASSETS, "b_neon.webp"), quality=82)

    motes = make_motes(202602, 46)
    FUSION_PINK = (0.74, 0.68, 1.0)
    CYAN_CORE = (1.0, 0.90, 0.64)

    def loop_frame_b(phase):
        # Seamless crossfaded official colossal Exostrider in pitch-black space (zero lyrics/subtitles!)
        frame = bank.sample(seg_mecha_loop, phase, ping_pong=True)
        pulse = 0.16 + 0.14 * (0.5 + 0.5 * math.sin(phase * 2.0 * math.pi))
        frame = add_star_flare(frame, W * 0.28, H * 0.66, 95, pulse * 0.48, tint_bgr=FUSION_PINK)
        frame = add_star_flare(frame, W * 0.54, H * 0.42, 110, pulse * 0.42, tint_bgr=CYAN_CORE)
        return add_cosmic_motes(frame, phase, motes, opacity=0.76)

    total_intro = int(round(INTRO_SEC * FPS))
    proc = start_ffmpeg(ffmpeg_bin, os.path.join(out_dir, "intro.mp4"), audio_wav=AUDIO_WAV)
    for fi in range(total_intro):
        t = fi / FPS
        phase = ((t - INTRO_SEC) / LOOP_SEC) % 1.0

        if t < 4.45:
            # Beat 1-2: Holographic terminal scanline reconstructs official Aemeath + Exostrider silhouette
            scan_y = smooth(0.05, 4.10, t) * 1.08
            scan_mask = np.clip((scan_y - yy / H) / 0.12, 0.0, 1.0)[..., None]
            op_line = smooth(0.08, 0.80, t) * (1.0 - smooth(3.05, 4.45, t) * 0.42)
            op_neon = smooth(1.90, 4.15, t)
            base = b_line * scan_mask * op_line + b_neon * scan_mask * op_neon
            frame = add_holo_scanline(np.clip(base, 0, 255), scan_y, (1.0 - smooth(3.75, 4.45, t)) * 0.82)
            if (2.20 <= t <= 2.48) or (3.85 <= t <= 4.15):
                frame = apply_digital_glitch(frame, 0.36, fi + 5)
            frame = add_cosmic_motes(frame, phase, motes, opacity=smooth(1.4, 4.1, t) * 0.62)
        elif t < 6.65:
            # Beat 3a: Official Combat Showcase digital matrix materialization!
            u = clamp((t - 4.45) / 2.20)
            vid = bank.sample(seg_appear, u)
            mat = smooth(4.45, 4.95, t)
            frame = b_neon * (1.0 - mat) + vid * mat if mat < 0.999 else vid
            frame = add_cosmic_motes(frame, phase, motes, opacity=0.66)
        elif t < 8.85:
            # Beat 3b: Official Graduation Show Fleet Snowfluff stage smile!
            u = clamp((t - 6.65) / 2.20)
            vid = bank.sample(seg_idol, u)
            xf = smooth(6.65, 7.00, t)
            if xf < 0.999:
                prev = bank.sample(seg_appear, 1.0)
                frame = prev * (1.0 - xf) + vid * xf
            else:
                frame = vid
            frame = add_cosmic_motes(frame, phase, motes, opacity=0.66)
        elif t < 10.45:
            # Beat 4: Electronic Ghost Glitch Tear + Official Pink Pixel-Heart Surge + Mecha Flash!
            gp = clamp((t - 8.85) / 1.60)
            if t < 9.95:
                frame = bank.sample(seg_heart_glitch, clamp((t - 8.85) / 1.10))
            else:
                frame = bank.sample(seg_mecha_ult, clamp((t - 9.95) / 0.50) * 0.35)
            g_str = 0.45 + 0.55 * math.sin(gp * math.pi) + (0.40 if t > 10.0 else 0.0)
            frame = apply_digital_glitch(frame, min(1.0, g_str), fi * 13 + 7)
            flash = smooth(10.20, 10.45, t)
            if flash > 0.01:
                frame = np.clip(frame * (1.0 - flash * 0.50) + np.array([245.0, 218.0, 255.0], np.float32) * (flash * 0.88), 0, 255)
        elif t < 12.25:
            # Beat 5: 10.50s Ultimate Drop -> Official Exostrider Mecha Wing-Spread Charge + Starburst Ultimate!
            if t < 11.40:
                u = clamp((t - 10.45) / 0.95)
                frame = bank.sample(seg_mecha_charge, u)
            else:
                u = clamp((t - 11.40) / 0.85)
                frame = bank.sample(seg_mecha_ult, 0.35 + u * 0.65)
            bp = clamp((t - 10.45) / 1.80)
            burst = smooth(0.0, 0.14, bp) * ((1.0 - smooth(0.14, 1.0, bp)) ** 1.35)
            frame = add_star_flare(frame, W * 0.24, H * 0.45, 200, burst * 0.78, tint_bgr=CYAN_CORE)
            frame = add_star_flare(frame, W * 0.78, H * 0.45, 200, burst * 0.78, tint_bgr=FUSION_PINK)
            after = 1.0 - smooth(10.45, 10.75, t)
            if after > 0.01:
                frame = np.clip(frame + np.array([225.0, 205.0, 255.0], np.float32) * (after * 0.45), 0, 255)
            frame = add_cosmic_motes(frame, phase, motes, opacity=0.76)
        else:
            # Beat 6: 12.25s secondary climax beat -> dissolve cleanly into dark-space Exostrider loop!
            xf = smoother(12.25, 13.00, t)
            loop_f = loop_frame_b(phase)
            if xf < 0.999:
                ult_end = bank.sample(seg_mecha_ult, 1.0)
                frame = ult_end * (1.0 - xf) + loop_f * xf
                exhale = math.sin(xf * math.pi)
                frame = np.clip(frame + np.array([235.0, 215.0, 255.0], np.float32) * (exhale * 0.35), 0, 255)
            else:
                frame = loop_f

        if fi == int(7.4 * FPS):
            save_png(frame, os.path.join(PREVIEW_DIR, "modeB_01_idol.png"))
        elif fi == int(10.9 * FPS):
            save_png(frame, os.path.join(PREVIEW_DIR, "modeB_02_mecha.png"))
        elif fi == int(13.5 * FPS):
            save_png(frame, os.path.join(PREVIEW_DIR, "modeB_03_loop.png"))
        proc.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())

    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed on mode B intro.mp4")

    total_loop = int(round(LOOP_SEC * FPS))
    proc2 = start_ffmpeg(ffmpeg_bin, os.path.join(out_dir, "loop.mp4"))
    for fi in range(total_loop):
        proc2.stdin.write(np.clip(loop_frame_b(fi / total_loop), 0, 255).astype(np.uint8).tobytes())
    proc2.stdin.close()
    if proc2.wait() != 0:
        raise RuntimeError("ffmpeg failed on mode B loop.mp4")
    make_loop_x2(ffmpeg_bin, out_dir)
    print("[Mode B] Done.")


# ───────────────────────── MODE C: 官方原片多幕混剪 · 纸飞机 / 祝福 / 拯救 / 远航星 ─────────────────────────

def render_mode_c(ffmpeg_bin, bank):
    print("[Mode C] Rendering 官方原片多幕混剪 · 纸飞机 / 祝福 / 拯救 / 远航星 ...")
    out_dir = os.path.join(OUT_BASE, "c")
    os.makedirs(out_dir, exist_ok=True)

    # All 4 iconic official videos woven into one emotional 14.5s montage (zero subtitles!)
    seg_plane = bank.load_segment("ep_paper_plane.mp4", 22.8, 30.0)
    seg_bless1 = bank.load_segment("pv_blessing.mp4", 230.2, 233.6, crop_top=0.11, x_bias=0.75)
    seg_bless2 = bank.load_segment("pv_blessing.mp4", 239.2, 241.0, crop_top=0.11, x_bias=0.60)
    seg_salv_arc = bank.load_segment("short_salvation.mp4", 226.2, 227.9, crop_bot=0.095)
    seg_salv_eyes = bank.load_segment("short_salvation.mp4", 251.3, 253.0)
    seg_salv_wings = bank.load_segment("short_salvation.mp4", 259.6, 261.0)
    seg_salv_blade = bank.load_segment("short_salvation.mp4", 277.2, 279.0)
    seg_voyager = bank.load_segment("short_salvation.mp4", 253.7, 255.55)

    kf_plane = bank.grab_frame("ep_paper_plane.mp4", 26.5)
    kf_bless = bank.grab_frame("pv_blessing.mp4", 232.0, crop_top=0.11, x_bias=0.75)
    kf_salv = bank.grab_frame("short_salvation.mp4", 278.0)
    kf_voy = bank.grab_frame("short_salvation.mp4", 254.8)

    save_jpg(kf_plane, os.path.join(KF_DIR, "c_plane.jpg"))
    save_jpg(kf_bless, os.path.join(KF_DIR, "c_blessing.jpg"))
    save_jpg(kf_salv, os.path.join(KF_DIR, "c_salvation.jpg"))
    save_jpg(kf_voy, os.path.join(KF_DIR, "c_voyager.jpg"))
    save_webp(kf_plane, os.path.join(PLUG_ASSETS, "c_plane.webp"), quality=84)
    save_webp(kf_bless, os.path.join(PLUG_ASSETS, "c_blessing.webp"), quality=84)
    save_webp(kf_salv, os.path.join(PLUG_ASSETS, "c_salvation.webp"), quality=84)
    save_webp(kf_voy, os.path.join(PLUG_ASSETS, "c_voyager.webp"), quality=84)

    motes = make_motes(202603, 44)
    WARM_GOLD = (0.72, 0.88, 1.0)
    ROSE_PINK = (0.84, 0.76, 1.0)
    CYAN_STAR = (1.0, 0.92, 0.70)

    def loop_frame_c(phase):
        # Official Salvation deep golden-stardust cosmos vigil (Aemeath floating beside Exostrider)
        frame = bank.sample(seg_voyager, phase, ping_pong=True)
        tw = 0.18 + 0.14 * (0.5 + 0.5 * math.sin(phase * 2.0 * math.pi))
        frame = add_star_flare(frame, W * 0.22, H * 0.26, 115, tw * 0.55, tint_bgr=WARM_GOLD)
        return add_cosmic_motes(frame, phase, motes, opacity=0.72)

    total_intro = int(round(INTRO_SEC * FPS))
    proc = start_ffmpeg(ffmpeg_bin, os.path.join(out_dir, "intro.mp4"), audio_wav=AUDIO_WAV)
    for fi in range(total_intro):
        t = fi / FPS
        phase = ((t - INTRO_SEC) / LOOP_SEC) % 1.0

        if t < 4.55:
            # Beat 1: Official EP3.1 Paper Plane soaring past Aemeath
            fade_in = smoother(0.0, 1.25, t)
            u = clamp(t / 4.55)
            frame = bank.sample(seg_plane, u) * fade_in
            frame = add_cosmic_motes(frame, phase, motes, opacity=fade_in * 0.55)
            xf = smooth(4.15, 4.55, t)
            if xf > 0.005:
                b0 = bank.sample(seg_bless1, 0.0)
                frame = frame * (1.0 - xf) + b0 * xf
                bloom_k = math.sin(xf * math.pi)
                frame = np.clip(frame + np.array([215.0, 200.0, 255.0], np.float32) * (bloom_k * 0.30), 0, 255)
        elif t < 8.85:
            # Beat 2: Official PV《祝福》Graduation Show singing + tender smile
            if t < 6.95:
                frame = bank.sample(seg_bless1, clamp((t - 4.55) / 2.40))
            else:
                u2 = clamp((t - 6.95) / 1.90)
                v2 = bank.sample(seg_bless2, u2)
                xf = smooth(6.95, 7.25, t)
                frame = bank.sample(seg_bless1, 1.0) * (1.0 - xf) + v2 * xf if xf < 0.999 else v2
            frame = add_cosmic_motes(frame, phase, motes, opacity=0.62)
            if t >= 8.55:
                frame = apply_digital_glitch(frame, smooth(8.55, 8.85, t) * 0.92, fi * 7 + 3)
        elif t < 12.50:
            # Beat 3: Official Animated Short《拯救》Forced Resonance Climax!
            if t < 9.65:
                frame = bank.sample(seg_salv_arc, clamp((t - 8.85) / 0.80))
                if t < 9.15:
                    frame = apply_digital_glitch(frame, (1.0 - smooth(8.85, 9.15, t)) * 0.85, fi * 11 + 2)
            elif t < 10.45:
                frame = bank.sample(seg_salv_eyes, clamp((t - 9.65) / 0.80))
                if t >= 10.12:
                    frame = apply_digital_glitch(frame, smooth(10.12, 10.45, t) * 0.82, fi * 17 + 9)
            elif t < 11.40:
                frame = bank.sample(seg_salv_wings, clamp((t - 10.45) / 0.95))
            else:
                frame = bank.sample(seg_salv_blade, clamp((t - 11.40) / 1.10))

            if 10.42 <= t <= 12.20:
                dp = clamp((t - 10.42) / 1.78)
                burst = smooth(0.0, 0.14, dp) * ((1.0 - smooth(0.14, 1.0, dp)) ** 1.25)
                frame = add_star_flare(frame, W * 0.20, H * 0.36, 210, burst * 0.82, tint_bgr=CYAN_STAR)
                frame = add_star_flare(frame, W * 0.82, H * 0.36, 210, burst * 0.82, tint_bgr=WARM_GOLD)
            frame = add_cosmic_motes(frame, phase, motes, opacity=0.78)

            xf2 = smoother(11.95, 12.50, t)
            if xf2 > 0.005:
                voy = loop_frame_c(phase)
                frame = frame * (1.0 - xf2) + voy * xf2
                exhale = math.sin(xf2 * math.pi)
                frame = np.clip(frame + np.array([225.0, 232.0, 255.0], np.float32) * (exhale * 0.34), 0, 255)
        else:
            # Beat 4: Official 《远航星》 Deep Stardust Vigil seamlessly entering loop_c!
            frame = loop_frame_c(phase)

        if fi == int(2.4 * FPS):
            save_png(frame, os.path.join(PREVIEW_DIR, "modeC_01_plane.png"))
        elif fi == int(11.7 * FPS):
            save_png(frame, os.path.join(PREVIEW_DIR, "modeC_02_salvation.png"))
        elif fi == int(13.6 * FPS):
            save_png(frame, os.path.join(PREVIEW_DIR, "modeC_03_voyager.png"))
        proc.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())

    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed on mode C intro.mp4")

    total_loop = int(round(LOOP_SEC * FPS))
    proc2 = start_ffmpeg(ffmpeg_bin, os.path.join(out_dir, "loop.mp4"))
    for fi in range(total_loop):
        proc2.stdin.write(np.clip(loop_frame_c(fi / total_loop), 0, 255).astype(np.uint8).tobytes())
    proc2.stdin.close()
    if proc2.wait() != 0:
        raise RuntimeError("ffmpeg failed on mode C loop.mp4")
    make_loop_x2(ffmpeg_bin, out_dir)
    print("[Mode C] Done.")


def main():
    ap = argparse.ArgumentParser(description="Render all 3 Aemeath boot animation modes using 100% official footage.")
    ap.add_argument("--modes", default="a,b,c", help="Comma-separated modes to render: a,b,c")
    args = ap.parse_args()

    os.makedirs(KF_DIR, exist_ok=True)
    os.makedirs(PLUG_ASSETS, exist_ok=True)
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    ff = find_ffmpeg()
    print("Using ffmpeg:", ff)

    bank = ClipBank()
    modes = [m.strip().lower() for m in args.modes.split(",") if m.strip()]
    if "a" in modes:
        render_mode_a(ff, bank)
    if "b" in modes:
        render_mode_b(ff, bank)
    if "c" in modes:
        render_mode_c(ff, bank)
    print("All official-footage Aemeath modes rendered successfully.")


if __name__ == "__main__":
    main()
