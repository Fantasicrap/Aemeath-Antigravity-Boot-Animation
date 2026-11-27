# -*- coding: utf-8 -*-
"""Zero-Node single-file bundler for the Aemeath (爱弥斯) Antigravity MCP App plugin.

Inlines all 3 modes' WebP assets, 14.5s《于电子星海轻歌》MP3 audio, official @modelcontextprotocol/ext-apps
SDK runtime, and frontend scripts into one self-contained intro.html (< 10 MiB MCP App limit).
"""
import base64
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(HERE, "assets_src")
SRC_DIR = os.path.join(HERE, "src")

IMAGE_KEYS = [
    "a_line", "a_neon", "a_closed", "a_open", "a_climax",
    "b_line", "b_neon", "b_idol", "b_mecha",
    "c_plane", "c_blessing", "c_salvation", "c_voyager",
]


def b64_uri(path, mime):
    with open(path, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode('ascii')}"


def main():
    asset_map = {}
    for key in IMAGE_KEYS:
        p = os.path.join(ASSETS_DIR, f"{key}.webp")
        if not os.path.exists(p):
            raise FileNotFoundError(f"Missing plugin asset: {p} (run tools/render_aemeath_boot.py first)")
        asset_map[key] = b64_uri(p, "image/webp")

    mp3_path = os.path.join(ASSETS_DIR, "aemeath_boot_14s5.mp3")
    if not os.path.exists(mp3_path):
        raise FileNotFoundError(f"Missing audio asset: {mp3_path}")
    asset_map["bootAudio"] = b64_uri(mp3_path, "audio/mpeg")

    asset_script = "window.__AEMEATH_ASSETS__=" + json.dumps(asset_map, separators=(",", ":")) + ";"

    with open(os.path.join(SRC_DIR, "mcp_ext_apps_sdk.js"), "r", encoding="utf-8") as f:
        mcp_sdk = f.read()

    bundle_parts = []
    for name in ("bridge.js", "aemeath_fx.js", "aemeath_sfx.js", "aemeath_director.js"):
        with open(os.path.join(SRC_DIR, name), "r", encoding="utf-8") as f:
            bundle_parts.append(f.read())
    bundle_js = "\n".join(bundle_parts).replace("</script", "<\\/script")

    with open(os.path.join(SRC_DIR, "intro.html"), "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("/*__ASSETS__*/", asset_script, 1)
    html = html.replace("/*__MCP_SDK__*/", mcp_sdk, 1)
    html = html.replace("/*__BUNDLE__*/", bundle_js, 1)

    out_path = os.path.join(HERE, "intro.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    sz = os.path.getsize(out_path)
    print(f"Built {out_path}: {sz / 1024:.1f} KiB ({sz / 1048576:.2f} MiB)")
    if sz >= 10 * 1048576:
        raise RuntimeError("intro.html exceeds Antigravity 10 MiB MCP App limit!")


if __name__ == "__main__":
    main()
