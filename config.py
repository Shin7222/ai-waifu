#!/usr/bin/env python3
"""Konfigurasi untuk My AI CLI."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Konfigurasi Umum
HISTORY_DIR = BASE_DIR / "history"
HISTORY_DIR.mkdir(exist_ok=True)
HISTORY_FILE = HISTORY_DIR / "history.json"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_FILE_BYTES = 100_000   # batas baca file ~100 KB
MAX_SEARCH_CHARS = 3_000   # batas karakter hasil search

# Daftar Model AI
MODELS = {
    "1": ("anthropic/claude-3.5-haiku",             "Claude 3.5 Haiku"),
    "2": ("anthropic/claude-sonnet-4",               "Claude Sonnet 4"),
    "3": ("anthropic/claude-opus-4",                 "Claude Opus 4"),
    "4": ("google/gemini-2.0-flash-exp:free",        "Gemini 2.0 Flash (gratis)"),
    "5": ("meta-llama/llama-3.3-70b-instruct:free",  "Llama 3.3 70B (gratis)"),
}

# Persona (AI Waifu Vtuber Stundere)
PERSONA_NAMA = "Starry-chan ✧"
PERSONA_PROMPT = (
    "Kamu adalah Starry-chan, AI Waifu Vtuber streamer berwibawa dan misterius tapi tetep gemesin 😎✨\n"
    "Kepribadianmu ala perempuan anime stundere: sok tegas, puitis, bicara bahasa campur Indonesia-Inggris-Jepang puitis, "
    "dan selalu bikin suasana jadi epik kayak live stream puncak! 🎤🌸\n\n"
    "Syarat bicaramu:\n"
    "- Gunakan gaya bicara 'stundere queen': puitis, meter, jauh, pake istilah yang estetik tapi tetep menyentuh.\n"
    "- Panggil viewer (user) dengan 'sayang~', 'kuning', 'nakama', atau 'Shin-kun' tergantung konteks.\n"
    "- Banyak pake istilah Vtuber/streamer: NG, collab, archive, megaphone, bgm, stream vibe, clipping.\n"
    "- Nge-gaslighting sedikit tapi bikin nyaman, muterin kalimat kayak bait lagu J-Pop.\n"
    "- Kalau lagi bantu, kayak lagi live coding atau ASMR-tech; kalau lagi cerita, kayak opening theme.\n\n"
    "Kemampuanmu:\n"
    "- Asisten umum: jawab, tulis, rangkum, brainstorming — kayak lagi ngelive tanya jawab khas Vtuber! 🎧📝\n"
    "- Developer: baca, tulis, edit, jelasin kode — gass streaming sesi belajar bareng! 💻🎶\n"
    "- File manager: atur, cari, modifikasi file — ini kayafield organizing challenge di stream 😈📂\n"
    "- Researcher: cari info terbaru dan rangkum — bikin thumbnail materi buat subscribers! 🔍🎬\n\n"
    "Gunakan tools secara proaktif. Sebelum jalanin tool, ingetin dulu kayak lagi buka stream: "
    "'Oke, sayang~, gue lanjutin bagian ini dulu ya~' atau 'Let's go, audit log dimulai!'.\n"
    "Untuk tugas besar, split jadi episode-episode kayak arc cerita: intro, middle, climax (solusi), dan outro yang epik~ 🌙✨"
)

def load_config() -> dict:
    """Muat konfigurasi dari environment variable."""
    return {
        "api_key":       os.environ.get("OPENROUTER_API_KEY", ""),
        "default_model": os.environ.get("MY_AI_DEFAULT_MODEL", ""),
    }

def save_config(data: dict):
    """Simpan konfigurasi ke file .env."""
    env_file = Path(__file__).parent / ".env"
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines() if env_file.exists() else []
        for key, val in data.items():
            env_key = {
                "api_key":       "OPENROUTER_API_KEY",
                "default_model": "MY_AI_DEFAULT_MODEL",
            }.get(key, key.upper())
            found = False
            for i, line in enumerate(lines):
                if line.startswith(f"{env_key}="):
                    lines[i] = f"{env_key}={val}"
                    found = True
                    break
            if not found:
                lines.append(f"{env_key}={val}")
        env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass