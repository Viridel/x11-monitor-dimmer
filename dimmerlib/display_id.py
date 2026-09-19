from __future__ import annotations

import re
import subprocess
from typing import Any


def _run_xrandr_verbose() -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["xrandr", "--verbose"],
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as exc:
        return {
            "ok": False,
            "stdout": "",
            "stderr": str(exc),
        }


def _clean_descriptor_text(raw: bytes) -> str:
    text = raw.split(b"\x0a", 1)[0].split(b"\x00", 1)[0]
    return text.decode("ascii", errors="ignore").strip()


def _parse_edid_name(edid_hex: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "edid_found": False,
        "monitor_name": None,
    }

    edid_hex = "".join(edid_hex.split()).strip()
    if not edid_hex:
        return result

    try:
        blob = bytes.fromhex(edid_hex)
    except Exception:
        return result

    if len(blob) < 128:
        return result

    result["edid_found"] = True

    for offset in range(54, 126, 18):
        descriptor = blob[offset:offset + 18]
        if len(descriptor) < 18:
            continue
        if descriptor[0:3] != b"\x00\x00\x00":
            continue
        if descriptor[3] != 0xFC:
            continue

        name = _clean_descriptor_text(descriptor[5:18])
        if name:
            result["monitor_name"] = name
            break

    return result


def _parse_xrandr_verbose(stdout: str) -> list[dict[str, Any]]:
    displays: list[dict[str, Any]] = []

    current_output: str | None = None
    current_header: str | None = None
    current_edid_lines: list[str] = []
    collecting_edid = False

    section_start_re = re.compile(r"^(\S+)\s+(connected|disconnected)\b")

    def finalize() -> None:
        nonlocal current_output, current_header, current_edid_lines, collecting_edid

        if current_output is not None and current_header is not None and " connected" in current_header:
            edid = _parse_edid_name("".join(current_edid_lines))
            displays.append(
                {
                    "output": current_output,
                    "connected": True,
                    "xrandr_header": current_header.strip(),
                    **edid,
                }
            )

        current_output = None
        current_header = None
        current_edid_lines = []
        collecting_edid = False

    for raw_line in stdout.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()

        match = section_start_re.match(line)
        if match:
            finalize()
            current_output = match.group(1)
            current_header = line
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



def fallback_display_name(position: int) -> str:
    try:
        position = int(position)
    except Exception:
        position = 1
    if position < 1:
        position = 1
    return f"Display #{position}"

def resolve_display_names() -> dict[str, Any]:
    command = _run_xrandr_verbose()
    report: dict[str, Any] = {
        "xrandr_ok": command["ok"],
        "displays": [],
        "output_name_map": {},
        "notes": [],
    }

    if not command["ok"]:
        report["notes"].append("xrandr --verbose failed.")
        report["stderr"] = command["stderr"]
        return report

    displays = _parse_xrandr_verbose(command["stdout"])
    report["displays"] = displays
    report["output_name_map"] = {
        display["output"]: display["monitor_name"]
        for display in displays
        if display.get("connected") and display.get("monitor_name")
    }

    if not displays:
        report["notes"].append("No connected displays were parsed from xrandr --verbose.")
    else:
        resolved = len(report["output_name_map"])
        report["notes"].append(
            f"Parsed {len(displays)} connected display(s); {resolved} supplied a usable EDID model name."
        )

    return report
