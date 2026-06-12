#!/bin/bash
# run.sh — Jalankan My AI CLI dari folder manapun (klik 2x atau ./run.sh)

cd "$(dirname "$0")"

if command -v gnome-terminal &> /dev/null; then
    gnome-terminal -- bash -c "python3 main.py; exec bash"
elif command -v konsole &> /dev/null; then
    konsole -e bash -c "python3 main.py; exec bash"
elif command -v xterm &> /dev/null; then
    xterm -e bash -c "python3 main.py; exec bash"
else
    python3 main.py
fi