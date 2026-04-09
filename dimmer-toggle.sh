#!/bin/bash
set -e

APP="/home/media/.local/bin/dimmer-app.py"

PID="$(pgrep -f "python3 $APP" || true)"

if [ -n "$PID" ]; then
    kill -USR1 "$PID"
    exit 0
fi

nohup python3 "$APP" >/dev/null 2>&1 &
disown
