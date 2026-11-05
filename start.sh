#!/usr/bin/env bash
# Linux / macOS launcher. Mirrors start.bat.
#
#   ./start.sh                       # local: loopback, auto port, opens browser
#   SAHARA_HOST=0.0.0.0 ./start.sh   # LAN server (e.g. on magus); debug off, no browser
#   SAHARA_PORT=5000 ./start.sh      # pin a port instead of auto-picking 5000-5100
set -euo pipefail
cd "$(dirname "$0")"
if [ -d venv ]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
fi
exec python app.py
