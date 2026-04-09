#!/bin/bash
set -e

APP="/home/media/.local/bin/dimmer-app.py"

PIDS="$(pgrep -f "python3 $APP" || true)"

if [ -z "$PIDS" ]; then
    echo "X11 Monitor Dimmer is not running."
    exit 0
fi

echo "$PIDS" | xargs -r kill
