#!/usr/bin/env python3
"""
My AI CLI — OpenRouter + Tool Calling
Fitur: baca/tulis file, edit kode, web search, akses folder
"""

import os
import sys
import re
from pathlib import Path
import datetime

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # python-dotenv tidak terinstall, skip

try:
    import requests
except ImportError:
    print("❌ Jalankan: pip install requests")
    sys.exit(1)

from config import (
    MODELS, 
    PERSONA_NAMA, 
    PERSONA_PROMPT, 
    load_config, 
    save_config
)
from utils import (
    c, yn, help_text, 
    YELLOW, RED, GREEN, CYAN, DIM, R, BOLD
)
from api import process_response
from history import load_history, save_history, show_history, save_to_txt

def pilih_model(default_model: str = "") -> tuple:
    """Pilih model AI."""
    # Cari nomor default dari config
    default_key = "1"
    for k,(mid,_) in MODELS.items():
        if mid == default_model:
            default_key = k
            break

    print(f"{BOLD}Pilih model:{R}")
    for k,(mid,desc) in MODELS.items():
        marker = f"  {GREEN}← tersimpan{R}" if mid == default_model else ""
        print(f"  {CYAN}{k}{R}. {desc}  {DIM}({mid}){R}{marker}")
    print(f"  {CYAN}6{R}. Ketik model ID sendiri\n")
    while True:
        p = input(f"{DIM}Pilih [1-6, default={default_key}]: {R}").strip() or default_key
        if p in MODELS:
            mid, desc = MODELS[p]
            save_config({"default_model": mid})
            print(f"\n{GREEN}✓ {desc}{R}\n")
            return mid, desc
        elif p == "6":
            mid = input("Model ID: ").strip()
            if mid:
                save_config({"default_model": mid})
                print(f"\n{GREEN}✓ {mid}{R}\n")
                return mid, mid
        else:
            print(f"{RED}Tidak valid.{R}")

def main():
    """Fungsi utama untuk menjalankan My AI CLI."""
    print(f"\n{BOLD}{CYAN}{'═'*54}{R}")
    print(f"{BOLD}{CYAN}   🤖  My AI CLI  —  OpenRouter + Tools{R}")
    print(f"{BOLD}{CYAN}{'═'*54}{R}\n")

    cfg     = load_config()
    api_key = os.environ.get("OPENROUTER_API_KEY","").strip() or cfg.get("api_key","")
    if not api_key:
        print(f"{YELLOW}API key belum disimpan.{R}")
        print(f"{DIM}Daftar gratis: https://openrouter.ai/keys{R}\n")
        api_key = input("Masukkan OPENROUTER_API_KEY: ").strip()
        if not api_key:
            print(f"{RED}❌ API key diperlukan.{R}")
            return
        save_config({"api_key": api_key})
        env_path = Path(__file__).parent / ".env"
        print(f"{GREEN}✓ API key disimpan di {env_path}{R}\n")
    else:
        print(f"{DIM}API key loaded ✓{R}")

    default_model = cfg.get("default_model", "")
    model_id, model_desc = pilih_model(default_model)
    persona_nama, sys_prompt = PERSONA_NAMA, PERSONA_PROMPT

    cwd = Path(".").resolve()
    print(f"{DIM}Working directory: {cwd}{R}")
    print(f"{DIM}Ketik /help untuk melihat perintah.{R}\n")

    system_msg = {
        "role": "system",
        "content": (
            f"{sys_prompt}\n\n"
            f"Working directory saat ini: {cwd}\n"
            "Kamu memiliki akses ke tools: read_file, write_file, edit_file, "
            "list_dir, search_in_files, web_search, create_dir.\n"
            "Gunakan tools ini secara proaktif untuk membantu user. "
            "Sebelum menulis atau mengedit file, selalu jelaskan apa yang akan kamu lakukan. "
            "Untuk tugas besar, pecah menjadi langkah-langkah kecil."
        )
    }
    messages     = [system_msg]
    all_history  = load_history()

    while True:
        try:
            user_input = input(f"\n{BOLD}Kamu ▸{R} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n\n{YELLOW}Sampai jumpa!{R}\n")
            break

        if not user_input: 
            continue

        if user_input.startswith("/"):
            cmd = user_input.lower().split()[0]

            if cmd == "/app":
                from my_ai_cli.apps import run_app, list_apps
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    run_app(parts[1])
                else:
                    apps = [a.replace('.py', '') for a in list_apps()]
                    print(f"\n{BOLD}Aplikasi tersedia:{R}")
                    for a in apps:
                        print(f"  - {a}")
                    print(f"\nCara gunakan: /app <nama_app>\n")
                continue

            elif cmd == "/exit":
                print(f"\n{YELLOW}Sampai jumpa!{R}\n")
                break

            elif cmd == "/clear":
                messages = [system_msg]
                print(f"\n{GREEN}✓ Konteks dihapus.{R}")

            elif cmd == "/history":
                show_history(all_history)

            elif cmd == "/persona":
                print(f"\n{DIM}Persona tunggal aktif: {CYAN}{PERSONA_NAMA}{R}\n")

            elif cmd == "/model":
                default_model = cfg.get("default_model", "")
                model_id, model_desc = pilih_model(default_model)
                messages = [system_msg]
                print(f"{DIM}Konteks direset.{R}")

            elif cmd == "/cwd":
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    new_cwd = Path(parts[1]).expanduser().resolve()
                    if new_cwd.is_dir():
                        os.chdir(new_cwd)
                        cwd = new_cwd
                        system_msg["content"] = re.sub(
                            r"Working directory saat ini: .*",
                            f"Working directory saat ini: {cwd}",
                            system_msg["content"]
                        )
                        print(f"\n{GREEN}✓ Pindah ke: {cwd}{R}")
                    else:
                        print(f"\n{RED}❌ Direktori tidak ditemukan: {new_cwd}{R}")
                else:
                    print(f"\n  Working directory: {CYAN}{cwd}{R}")
                    new_path = input(f"  Ganti ke (kosongkan=batal): ").strip()
                    if new_path:
                        new_cwd = Path(new_path).expanduser().resolve()
                        if new_cwd.is_dir():
                            os.chdir(new_cwd)
                            cwd = new_cwd
                            system_msg["content"] = re.sub(
                                r"Working directory saat ini: .*",
                                f"Working directory saat ini: {cwd}",
                                system_msg["content"]
                            )
                            print(f"{GREEN}✓ Pindah ke: {cwd}{R}")
                        else:
                            print(f"{RED}❌ Tidak ditemukan.{R}")

            elif cmd == "/tools":
                from .tools import TOOLS
                print(f"\n{BOLD}Tools tersedia:{R}")
                for t in TOOLS:
                    fn = t["function"]
                    print(f"  {CYAN}{fn['name']}{R} — {fn['description']}")
                print()

            elif cmd == "/save":
                chat = [m for m in messages if m["role"] != "system"]
                if chat: 
                    save_to_txt(messages, persona_nama, model_id)
                else: 
                    print(f"\n{YELLOW}Belum ada percakapan.{R}")

            elif cmd == "/apikey":
                new_key = input(f"  Masukkan API key baru: ").strip()
                if new_key:
                    api_key = new_key
                    save_config({"api_key": new_key})
                    print(f"\n{GREEN}✓ API key diperbarui dan disimpan.{R}\n")
                else:
                    print(f"\n{YELLOW}Dibatalkan.{R}\n")

            elif cmd == "/info":
                print(f"\n  Model  : {CYAN}{model_desc}{R}  {DIM}({model_id}){R}")
                print(f"  Persona: {CYAN}{PERSONA_NAMA}{R}")
                print(f"  CWD    : {CYAN}{cwd}{R}\n")

            elif cmd == "/help":
                help_text()
            else:
                print(f"\n{RED}Tidak dikenal. Ketik /help.{R}")
            continue

        # ── Kirim ke API ──
        messages.append({"role": "user", "content": user_input})
        print(f"\n{DIM}Berpikir...{R}", end="\r", flush=True)

        try:
            reply = process_response(api_key, model_id, messages)
        except ValueError as e:
            print(f"\n{RED}❌ {e}{R}\n")
            messages.pop()
            continue
        except requests.exceptions.ConnectionError:
            print(f"\n{RED}❌ Tidak bisa terhubung. Cek internet.{R}\n")
            messages.pop()
            continue
        except Exception as e:
            print(f"\n{RED}❌ Error: {e}{R}\n")
            messages.pop()
            continue

        print(" " * 30, end="\r")
        if reply:
            print(f"\n{CYAN}{BOLD}AI ▸{R} {reply}\n")

        # Simpan history
        chat_msgs = [
            m for m in messages 
            if m["role"] not in ("system","tool") and not m.get("tool_calls")
        ]
        first_user = next((m["content"] for m in chat_msgs if m["role"]=="user"), "")
        entry = {
            "timestamp":  datetime.datetime.now().isoformat(),
            "persona":    persona_nama,
            "model":      model_id,
            "user_first": first_user,
            "messages":   [m for m in messages if m["role"] != "system"],
        }
        if len(chat_msgs) <= 2:
            all_history.append(entry)
        elif all_history:
            all_history[-1] = entry
        save_history(all_history)

def cli():
    """Entry point untuk CLI."""
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Sampai jumpa!{R}\n")

if __name__ == "__main__":
    cli()