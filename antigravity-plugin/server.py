"""Minimal MCP stdio server that serves the Aemeath (爱弥斯) intro animation as an MCP App.

No third-party dependencies: speaks newline-delimited JSON-RPC 2.0 over stdio.
Persists user preferences (active mode A/B/C and custom subtitle lines) under --data_dir.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.environ.get("AEMEATH_INTRO_HTML") or os.path.join(HERE, "intro.html")
APP_URI = "ui://aemeath-intro/intro.html"
MIME = "text/html;profile=mcp-app"

DEFAULT_PREFS = {
    "mode": "a",
    "showSubtitle": True,
    "subtitlePrimary": "拯救世界的事，就交给我吧……",
    "subtitleSecondary": "Leave saving the world to me...",
    "soundEnabled": True,
}

DATA_DIR = HERE

TOOL_META = {
    "ui": {"resourceUri": APP_URI},
    "com.google.antigravity/ui": {
        "entrypoints": [
            {"type": "aux_pane", "title": "爱弥斯开场"},
            {"type": "global", "title": "爱弥斯开场"},
        ]
    },
}

APP_ONLY_META = {
    "ui": {"visibility": ["app"]},
}

TOOLS = [
    {
        "name": "open_aemeath_intro",
        "title": "爱弥斯开场动画",
        "description": (
            "Play the Wuthering Waves Aemeath (爱弥斯) opening animation with 14.5s "
            "Sing Among Digital Stars music, switchable between Mode A (one-take digital starlight awakening), "
            "Mode B (digital ghost to Exostrider mecha switch), and Mode C (multi-scene story montage), "
            "plus customizable subtitles."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["a", "b", "c"],
                    "description": "Optional animation preset: 'a' (星海觉醒), 'b' (隧者机兵), or 'c' (远航星忆).",
                },
                "subtitlePrimary": {
                    "type": "string",
                    "description": "Optional custom primary subtitle text.",
                },
                "subtitleSecondary": {
                    "type": "string",
                    "description": "Optional custom secondary subtitle text.",
                },
            },
            "additionalProperties": False,
        },
        "_meta": TOOL_META,
    },
    {
        "name": "save_aemeath_prefs",
        "title": "保存爱弥斯开场偏好",
        "description": "Persist user preferences (mode A/B/C, custom subtitle, sound toggle) for the Aemeath MCP App.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["a", "b", "c"]},
                "showSubtitle": {"type": "boolean"},
                "subtitlePrimary": {"type": "string"},
                "subtitleSecondary": {"type": "string"},
                "soundEnabled": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "_meta": APP_ONLY_META,
    },
    {
        "name": "get_aemeath_prefs",
        "title": "读取爱弥斯开场偏好",
        "description": "Read persisted user preferences for the Aemeath MCP App.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "_meta": APP_ONLY_META,
    },
]


def prefs_path():
    os.makedirs(DATA_DIR, exist_ok=True)
    return os.path.join(DATA_DIR, "aemeath_prefs.json")


def load_prefs():
    prefs = dict(DEFAULT_PREFS)
    p = prefs_path()
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                if raw.get("mode") in ("a", "b", "c"):
                    prefs["mode"] = raw["mode"]
                if isinstance(raw.get("showSubtitle"), bool):
                    prefs["showSubtitle"] = raw["showSubtitle"]
                if isinstance(raw.get("subtitlePrimary"), str):
                    prefs["subtitlePrimary"] = raw["subtitlePrimary"]
                if isinstance(raw.get("subtitleSecondary"), str):
                    prefs["subtitleSecondary"] = raw["subtitleSecondary"]
                if isinstance(raw.get("soundEnabled"), bool):
                    prefs["soundEnabled"] = raw["soundEnabled"]
        except Exception:
            pass
    return prefs


def save_prefs(updates):
    prefs = load_prefs()
    if isinstance(updates, dict):
        if updates.get("mode") in ("a", "b", "c"):
            prefs["mode"] = updates["mode"]
        if isinstance(updates.get("showSubtitle"), bool):
            prefs["showSubtitle"] = updates["showSubtitle"]
        if isinstance(updates.get("subtitlePrimary"), str):
            prefs["subtitlePrimary"] = updates["subtitlePrimary"][:160]
        if isinstance(updates.get("subtitleSecondary"), str):
            prefs["subtitleSecondary"] = updates["subtitleSecondary"][:200]
        if isinstance(updates.get("soundEnabled"), bool):
            prefs["soundEnabled"] = updates["soundEnabled"]
    try:
        with open(prefs_path(), "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return prefs


def read_html():
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        return f.read()


MODE_NAMES = {
    "a": "方案 A · 一镜到底（电子星海觉醒）",
    "b": "方案 B · 双形态切换（电子幽灵 × 隧者机兵）",
    "c": "方案 C · 多幕剧情（纸飞机 / 祝福 / 拯救 / 远航星）",
}


def handle(method, params):
    if method == "initialize":
        return {
            "protocolVersion": params.get("protocolVersion") or "2025-06-18",
            "capabilities": {"tools": {}, "resources": {}},
            "serverInfo": {"name": "aemeath-intro", "version": "1.0.0"},
        }
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if name == "open_aemeath_intro":
            prefs = save_prefs(args) if args else load_prefs()
            m_label = MODE_NAMES.get(prefs["mode"], prefs["mode"])
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"已打开爱弥斯开场动画（{m_label}｜台词：{prefs['subtitlePrimary']}）。",
                    }
                ],
                "structuredContent": {"prefs": prefs},
            }
        if name == "save_aemeath_prefs":
            prefs = save_prefs(args)
            return {
                "content": [{"type": "text", "text": "已保存偏好设置。"}],
                "structuredContent": {"prefs": prefs},
            }
        if name == "get_aemeath_prefs":
            prefs = load_prefs()
            return {
                "content": [{"type": "text", "text": "OK"}],
                "structuredContent": {"prefs": prefs},
            }
        raise LookupError("Unknown tool: %s" % name)
    if method == "resources/list":
        return {
            "resources": [
                {
                    "uri": APP_URI,
                    "name": "爱弥斯开场动画",
                    "mimeType": MIME,
                    "_meta": {"ui": {"prefersBorder": False}},
                }
            ]
        }
    if method == "resources/templates/list":
        return {"resourceTemplates": []}
    if method == "resources/read":
        if params.get("uri") != APP_URI:
            raise LookupError("Unknown resource: %s" % params.get("uri"))
        return {
            "contents": [
                {
                    "uri": APP_URI,
                    "mimeType": MIME,
                    "text": read_html(),
                    "_meta": {"ui": {"prefersBorder": False}},
                }
            ]
        }
    if method == "prompts/list":
        return {"prompts": []}
    raise NotImplementedError(method)


def send(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=True) + "\n")
    sys.stdout.flush()


def main():
    global DATA_DIR
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--data_dir", default=HERE)
    known, _ = ap.parse_known_args()
    if known.data_dir and known.data_dir != "${PLUGIN_DATA}":
        DATA_DIR = known.data_dir

    for raw in sys.stdin.buffer:
        line = raw.decode("utf-8", "replace").strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
            continue
        if "id" not in msg or "method" not in msg:
            continue
        mid = msg["id"]
        try:
            result = handle(msg["method"], msg.get("params") or {})
            send({"jsonrpc": "2.0", "id": mid, "result": result})
        except NotImplementedError as e:
            send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "Method not found: %s" % e}})
        except LookupError as e:
            send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": str(e)}})
        except Exception as e:
            send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": str(e)}})


if __name__ == "__main__":
    main()
