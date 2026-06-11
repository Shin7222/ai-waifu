#!/usr/bin/env python3
"""Fungsi utilitas umum."""

# Definisi Warna
R="\033[0m"
BOLD="\033[1m"
DIM="\033[2m"
CYAN="\033[96m"
GREEN="\033[92m"
YELLOW="\033[93m"
RED="\033[91m"
MAGENTA="\033[95m"
WHITE="\033[97m"

def c(text, color):
    """Berikan warna pada teks."""
    colors = {
        'cyan': CYAN,
        'green': GREEN,
        'yellow': YELLOW, 
        'red': RED,
        'magenta': MAGENTA,
        'white': WHITE,
        'default': R
    }
    return f"{colors.get(color, R)}{text}{R}"

def yn(prompt):
    """Prompt konfirmasi ya/tidak."""
    return input(f"{YELLOW}⚠ {prompt} [y/N]: {R}").strip().lower() == "y"

def help_text():
    """Tampilkan teks bantuan."""
    print(f"""
{BOLD}Perintah:{R}
  {c('/clear', 'cyan')}    — Reset konteks percakapan
  {c('/history', 'cyan')}  — Lihat history chat
  {c('/persona', 'cyan')}  — Ganti persona
  {c('/model', 'cyan')}    — Ganti model AI
  {c('/cwd', 'cyan')}      — Tampilkan & ganti working directory
  {c('/tools', 'cyan')}    — Lihat tools yang tersedia
  {c('/save', 'cyan')}     — Export percakapan ke .txt
  {c('/apikey', 'cyan')}   — Ganti & simpan API key
  {c('/info', 'cyan')}     — Info model & persona aktif
  {c('/help', 'cyan')}     — Pesan ini
  {c('/exit', 'cyan')}     — Keluar

{BOLD}Tips:{R}
  Kamu bisa langsung bilang ke AI:
  {DIM}"baca file main.py"{R}
  {DIM}"cari semua fungsi yang pakai requests di folder ini"{R}
  {DIM}"buat file config.json dengan isi ..."{R}
  {DIM}"cari di internet cara install flask"{R}
""")