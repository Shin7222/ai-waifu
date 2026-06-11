#!/usr/bin/env python3
"""Manajemen history percakapan."""

import json
import datetime
from pathlib import Path
from config import HISTORY_FILE
from utils import c, R, BOLD, CYAN, DIM, WHITE, YELLOW


# 🔥 BASE DIR = tempat kamu menjalankan program
BASE_DIR = Path.cwd()
HISTORY_DIR = BASE_DIR / "history"
HISTORY_DIR.mkdir(exist_ok=True)


# =========================
# JSON HISTORY
# =========================

def load_history() -> list:
    """Muat history dari file JSON."""
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except:
            return []
    return []


def save_history(history: list):
    """Simpan history ke file JSON."""
    try:
        HISTORY_FILE.write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except:
        pass


def clear_json_history():
    """Hapus isi history JSON."""
    if HISTORY_FILE.exists():
        HISTORY_FILE.write_text("[]", encoding="utf-8")
        print(f"{c('✓ History JSON dikosongkan', 'yellow')}")
    else:
        print("File history tidak ditemukan.")


# =========================
# DISPLAY HISTORY
# =========================

def show_history(history: list):
    """Tampilkan history percakapan."""
    if not history:
        print(f"\n{YELLOW}Belum ada history.{R}\n")
        return

    print(f"\n{BOLD}{'─'*56}{R}")
    print(f"{BOLD}  📋 History{R}")
    print(f"{BOLD}{'─'*56}{R}")

    for i, e in enumerate(history[-15:], 1):
        ts  = e.get("timestamp", "")[:16].replace("T", " ")
        msg = e.get("user_first", "")[:38]
        mdl = e.get("model", "").split("/")[-1][:20]

        print(f"  {DIM}{i:>2}.{R} {WHITE}{msg:<38}{R}  {DIM}{ts}  {mdl}{R}")

    print(f"{BOLD}{'─'*56}{R}\n")


# =========================
# TXT SAVE
# =========================

def save_to_txt(messages: list, persona: str, model: str):
    """Simpan percakapan ke file teks di folder history."""
    
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fn = HISTORY_DIR / f"chat_{ts}.txt"

    lines = [
        f"My AI Chat — {ts}",
        f"Persona: {persona}",
        f"Model: {model}",
        f"{'─'*50}\n"
    ]

    for m in messages:
        role = m.get("role", "")

        if role == "system":
            continue

        if role == "tool":
            lines.append(f"[Tool Result]:\n{m.get('content','')}\n")

        elif role == "assistant":
            content = m.get("content") or ""
            tc = m.get("tool_calls")

            if tc:
                lines.append(
                    f"AI (tool call): {json.dumps(tc, ensure_ascii=False)[:200]}\n"
                )

            if content:
                lines.append(f"AI:\n{content}\n")

        else:
            lines.append(f"Kamu:\n{m.get('content','')}\n")

    fn.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n{c('✓ Disimpan ke: ' + str(fn.resolve()), 'green')}\n")


# =========================
# DELETE HISTORY
# =========================

def clear_txt_history():
    """Hapus semua file txt di folder history."""
    
    if not HISTORY_DIR.exists():
        print("Folder history belum ada.")
        return

    files = list(HISTORY_DIR.glob("chat_*.txt"))

    for f in files:
        f.unlink()

    print(f"{c(f'✓ {len(files)} file history dihapus', 'yellow')}")


def clear_all_history():
    """Hapus semua history (JSON + TXT)."""
    clear_json_history()
    clear_txt_history()
    print(f"{c('✓ Semua history berhasil dihapus', 'red')}")