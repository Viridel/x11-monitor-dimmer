from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

APP_NAME = "X11 Monitor Dimmer"
CONFIG_DIR = Path.home() / ".config" / "x11-monitor-dimmer"
CONFIG_FILE = CONFIG_DIR / "config.json"
RUNTIME_DIR = Path("/tmp/x11-monitor-dimmer")
PIDFILE = RUNTIME_DIR / "app.pid"

MIN_BRIGHTNESS = 20
MAX_BRIGHTNESS = 100
MIN_DEFAULT = 40
MAX_CUSTOM_NAME = 12
DEFAULT_SLOTS = (1, 2)
QUICK_BRIGHTNESS_LEVELS = (90, 80, 70, 60, 50, 40, 30, 20)

BASELINE_WIDTH = 3840
MIN_SCALE = 0.65
MAX_SCALE = 1.00


def _new_config():
    return {
        "monitors": {},
        "ui_host_output": None,
        "default_names": {},
    }


def load_config():
    if not CONFIG_FILE.exists():
        return _new_config()

    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return _new_config()

    if not isinstance(cfg, dict):
        return _new_config()

    if not isinstance(cfg.get("monitors"), dict):
        cfg["monitors"] = {}
    if not isinstance(cfg.get("default_names"), dict):
        cfg["default_names"] = {}
    cfg.setdefault("ui_host_output", None)

    # sync_sliders is intentionally ignored by the redesigned UI, but an
    # existing key is harmless and is left untouched for backwards safety.
    return cfg


def save_config(cfg):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, sort_keys=True), encoding="utf-8")


def parse_xrandr():
    result = subprocess.run(["xrandr", "--query"], capture_output=True, text=True, check=True)
    monitors = []
    pattern = re.compile(r"^(\S+) connected( primary)? (\d+)x(\d+)\+(\d+)\+(\d+)")
    for line in result.stdout.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        output, primary, w, h, x, y = match.groups()
        monitors.append(
            {
                "output": output,
                "primary": bool(primary),
                "width": int(w),
                "height": int(h),
                "x": int(x),
                "y": int(y),
            }
        )
    return monitors


def already_running():
    try:
        if PIDFILE.exists():
            pid = int(PIDFILE.read_text(encoding="utf-8").strip())
            os.kill(pid, 0)
            return pid
    except Exception:
        return None
    return None
