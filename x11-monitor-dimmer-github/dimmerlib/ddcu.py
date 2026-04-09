from __future__ import annotations

import json
import re
import subprocess
from typing import Any


def _run(cmd: list[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cmd": cmd,
        }
    except Exception as exc:
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "cmd": cmd,
        }


def _decode_mfg_id(byte1: int, byte2: int) -> str:
    word = (byte1 << 8) | byte2
    chars = [
        chr(((word >> 10) & 0x1F) + 64),
        chr(((word >> 5) & 0x1F) + 64),
        chr((word & 0x1F) + 64),
    ]
    return "".join(chars)


def _clean_descriptor_text(raw: bytes) -> str:
    text = raw.split(b"\x0a", 1)[0].split(b"\x00", 1)[0]
    return text.decode("ascii", errors="ignore").strip()


def _parse_edid(edid_hex: str) -> dict[str, Any]:
    info: dict[str, Any] = {
        "edid_found": False,
        "manufacturer_id": None,
        "product_code": None,
        "binary_serial": None,
        "manufacture_week": None,
        "manufacture_year": None,
        "monitor_name": None,
        "serial_text": None,
        "preferred_name": None,
    }

    edid_hex = "".join(edid_hex.split()).strip()
    if not edid_hex:
        return info

    try:
        blob = bytes.fromhex(edid_hex)
    except Exception:
        return info

    if len(blob) < 128:
        return info

    info["edid_found"] = True
    info["manufacturer_id"] = _decode_mfg_id(blob[8], blob[9])
    info["product_code"] = blob[10] | (blob[11] << 8)
    info["binary_serial"] = int.from_bytes(blob[12:16], "little")
    info["manufacture_week"] = blob[16]
    info["manufacture_year"] = 1990 + blob[17]

    for off in range(54, 126, 18):
        desc = blob[off:off + 18]
        if len(desc) < 18:
            continue
        if desc[0:3] != b"\x00\x00\x00":
            continue

        tag = desc[3]
        if tag == 0xFC:
            info["monitor_name"] = _clean_descriptor_text(desc[5:18]) or None
        elif tag == 0xFF:
            info["serial_text"] = _clean_descriptor_text(desc[5:18]) or None

    info["preferred_name"] = (
        info["monitor_name"]
        or info["manufacturer_id"]
        or "Unknown Display"
    )
    return info


def _parse_xrandr_verbose(stdout: str) -> list[dict[str, Any]]:
    displays: list[dict[str, Any]] = []

    current_output: str | None = None
    current_line: str | None = None
    current_edid_lines: list[str] = []
    collecting_edid = False

    section_start_re = re.compile(r"^(\S+)\s+(connected|disconnected)\b")

    def finalize():
        nonlocal current_output, current_line, current_edid_lines, collecting_edid

        if current_output is None or current_line is None:
            current_output = None
            current_line = None
            current_edid_lines = []
            collecting_edid = False
            return

        if " connected" not in current_line:
            current_output = None
            current_line = None
            current_edid_lines = []
            collecting_edid = False
            return

        edid_info = _parse_edid("".join(current_edid_lines))
        displays.append(
            {
                "output": current_output,
                "connected": True,
                "xrandr_header": current_line.strip(),
                **edid_info,
            }
        )

        current_output = None
        current_line = None
        current_edid_lines = []
        collecting_edid = False

    for raw_line in stdout.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()

        m = section_start_re.match(line)
        if m:
            finalize()
            current_output = m.group(1)
            current_line = line
            current_edid_lines = []
            collecting_edid = False
            continue

        if current_output is None:
            continue

        if stripped == "EDID:":
            collecting_edid = True
            current_edid_lines = []
            continue

        if collecting_edid:
            if re.fullmatch(r"[0-9a-fA-F]+", stripped) and len(stripped) % 2 == 0:
                current_edid_lines.append(stripped)
                continue
            collecting_edid = False

    finalize()
    return displays


def resolve_display_models() -> dict[str, Any]:
    result = _run(["xrandr", "--verbose"])

    report: dict[str, Any] = {
        "xrandr_ok": result["ok"],
        "displays": [],
        "output_model_map": {},
        "notes": [],
    }

    if not result["ok"]:
        report["notes"].append("xrandr --verbose failed.")
        report["stderr"] = result["stderr"]
        return report

    displays = _parse_xrandr_verbose(result["stdout"])
    report["displays"] = displays
    report["output_model_map"] = {
        d["output"]: d["preferred_name"]
        for d in displays
        if d.get("connected")
    }

    if not displays:
        report["notes"].append("No connected displays were parsed from xrandr --verbose.")
    else:
        report["notes"].append(f"Resolved {len(displays)} connected display(s) from EDID.")

    return report


def main() -> int:
    print(json.dumps(resolve_display_models(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
