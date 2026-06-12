"""
history.py — Manajemen history chat: load, save, tampilkan, resume sesi.
"""

import json

from config import (
    HISTORY_FILE,
    BOLD, DIM, R, CYAN, YELLOW, WHITE,
)


def load_history() -> list:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_history(history: list):
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_FILE.write_text(
            json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def show_history(history: list):
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


def list_sessions(history: list) -> list:
    """Tampilkan sesi yang bisa di-resume. Return list referensi sesi yang ditampilkan."""
    if not history:
        print(f"\n{YELLOW}Belum ada sesi tersimpan.{R}\n")
        return []
    shown = history[-15:]
    print(f"\n{BOLD}{'─'*56}{R}")
    print(f"{BOLD}  💬 Sesi tersimpan (ketik nomor untuk resume){R}")
    print(f"{BOLD}{'─'*56}{R}")
    for i, e in enumerate(shown, 1):
        ts   = e.get("timestamp", "")[:16].replace("T", " ")
        msg  = e.get("user_first", "")[:38]
        mdl  = e.get("model", "").split("/")[-1][:20]
        nmsg = len([m for m in e.get("messages", []) if m.get("role") in ("user", "assistant")])
        print(f"  {CYAN}{i:>2}{R}. {WHITE}{msg:<38}{R}  {DIM}{ts}  {mdl}  ({nmsg} pesan){R}")
    print(f"{BOLD}{'─'*56}{R}")
    return shown


def load_session_messages(entry: dict, system_msg: dict) -> list:
    """Bangun ulang list messages dari entry history, diawali system_msg.
    Tool messages & bare tool_calls di-skip agar tidak membingungkan model."""
    restored = [system_msg]
    for m in entry.get("messages", []):
        if m.get("role") == "tool":
            continue
        if m.get("role") == "assistant" and m.get("tool_calls") and not m.get("content"):
            continue
        restored.append({k: v for k, v in m.items() if k in ("role", "content")})
    return restored
