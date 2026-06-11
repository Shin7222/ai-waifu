"""
ui.py — Fungsi UI: pemilihan model, help text, export chat ke .txt.
"""

import json, datetime
from pathlib import Path

import requests

import config
from config import (
    PROVIDER, MODELS_OLLAMA, MODELS_OPENROUTER,
    save_config,
    BOLD, DIM, R, CYAN, GREEN, RED, YELLOW,
)


def fetch_ollama_models() -> list:
    """Ambil daftar model yang sudah di-pull di Ollama lokal."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if not resp.ok:
            return []
        return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        return []


def pilih_model(default_model: str = "") -> tuple:
    """Tampilkan daftar model sesuai provider aktif, return (model_id, model_desc)."""
    if config.PROVIDER == "openrouter":
        options = dict(MODELS_OPENROUTER)
        label   = "OpenRouter"
        note    = "(cloud — butuh API key)"
    else:
        detected = fetch_ollama_models()
        if detected:
            options = {str(i): (name, name) for i, name in enumerate(detected, 1)}
            note    = "(terdeteksi dari 'ollama list')"
        else:
            options = dict(MODELS_OLLAMA)
            note    = "(fallback — Ollama tidak terdeteksi)"
        label = "Ollama"

    custom_key  = str(len(options) + 1)
    default_key = next((k for k, (mid, _) in options.items() if mid == default_model), "1")

    print(f"{BOLD}Pilih model {CYAN}[{label}]{R}:{R}")
    print(f"  {DIM}{note}{R}")
    for k, (mid, desc) in options.items():
        marker = f"  {GREEN}← tersimpan{R}" if mid == default_model else ""
        print(f"  {CYAN}{k}{R}. {desc}{marker}")
    print(f"  {CYAN}{custom_key}{R}. Ketik model ID sendiri\n")

    while True:
        p = input(f"{DIM}Pilih [1-{custom_key}, default={default_key}]: {R}").strip() or default_key
        if p in options:
            mid, desc = options[p]
            save_config({"default_model": mid})
            print(f"\n{GREEN}✓ {desc}{R}\n")
            return mid, desc
        elif p == custom_key:
            mid = input("Model ID (contoh: mistralai/mixtral-8x7b-instruct): ").strip()
            if mid:
                save_config({"default_model": mid})
                print(f"\n{GREEN}✓ {mid}{R}\n")
                return mid, mid
        else:
            print(f"{RED}Tidak valid.{R}")


def save_to_txt(messages: list, persona: str, model: str):
    """Export percakapan ke file .txt."""
    ts    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fn    = Path(f"my_ai_chat_{ts}.txt")
    lines = [f"My AI Chat — {ts}\nPersona: {persona}\nModel: {model}\n{'─'*50}\n"]
    for m in messages:
        role = m.get("role", "")
        if role == "system":
            continue
        if role == "tool":
            lines.append(f"[Tool Result]:\n{m.get('content', '')}\n")
        elif role == "assistant":
            content = m.get("content") or ""
            tc      = m.get("tool_calls")
            if tc:      lines.append(f"AI (tool call): {json.dumps(tc, ensure_ascii=False)[:200]}\n")
            if content: lines.append(f"AI:\n{content}\n")
        else:
            lines.append(f"Kamu:\n{m.get('content', '')}\n")
    fn.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{GREEN}✓ Disimpan ke: {fn.resolve()}{R}\n")


def help_text():
    print(f"""
{BOLD}Perintah:{R}
  {CYAN}/clear{R}    — Reset konteks percakapan
  {CYAN}/history{R}  — Lihat history chat
  {CYAN}/sessions{R} — Lihat & lanjutkan (resume) sesi lama
  {CYAN}/voice{R}    — VOICEVOX TTS: /voice on | off | list | set <id>
  {CYAN}/persona{R}  — Info persona aktif
  {CYAN}/model{R}    — Ganti model AI
  {CYAN}/cwd{R}      — Tampilkan & ganti working directory
  {CYAN}/tools{R}    — Lihat tools yang tersedia
  {CYAN}/save{R}     — Export percakapan ke .txt
  {CYAN}/apikey{R}   — Set/ganti OpenRouter API key
  {CYAN}/info{R}     — Info provider, model & persona aktif
  {CYAN}/help{R}     — Pesan ini
  {CYAN}/exit{R}     — Keluar

{BOLD}Tips:{R}
  {DIM}"baca file main.py"{R}
  {DIM}"cari semua fungsi yang pakai requests di folder ini"{R}
  {DIM}"buat file config.json dengan isi ..."{R}
  {DIM}"cari di internet cara install flask"{R}

{BOLD}Provider:{R}
  {CYAN}Ollama{R}      — Model lokal. Butuh: ollama serve
  {CYAN}OpenRouter{R}  — 300+ model cloud (termasuk gratis). Butuh: API key dari openrouter.ai/keys
""")