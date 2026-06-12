#!/usr/bin/env python3
"""
main.py — Entry point My AI CLI.
Jalankan: python main.py

Struktur proyek:
  config.py   — konstanta, warna, persona, path safety, load/save config
  voice.py    — VOICEVOX TTS
  tools.py    — definisi & implementasi tools AI
  api.py      — Ollama & OpenRouter streaming + agentic loop
  history.py  — load/save/tampilkan history & sessions
  ui.py       — pilih model, help text, save to txt
  main.py     — (ini) provider setup & command loop
"""

import os, re, datetime
from pathlib import Path

import requests

import config
from config import (
    load_config, save_config,
    set_allowed_root, PERSONA_NAMA, PERSONA_PROMPT,
    BOLD, DIM, R, CYAN, GREEN, YELLOW, RED,
    yn,
)
from api      import process_response
from history  import load_history, save_history, show_history, list_sessions, load_session_messages
from tools    import TOOLS
from ui       import pilih_model, save_to_txt, help_text
from voice    import voicevox_check, voicevox_speakers
import voice
import avatar_server


def _setup_provider(cfg: dict) -> tuple[str, str]:
    """Pilih provider & siapkan API key. Return (provider, api_key)."""
    saved_provider = cfg.get("provider", "")
    ollama_ok      = False

    try:
        ping      = requests.get("http://localhost:11434/api/tags", timeout=3)
        ollama_ok = ping.ok
    except Exception:
        pass

    print(f"{BOLD}Pilih provider:{R}")
    ollama_mark = f"  {GREEN}← terdeteksi{R}" if ollama_ok else f"  {DIM}(tidak berjalan){R}"
    or_mark     = f"  {GREEN}← tersimpan{R}" if saved_provider == "openrouter" else ""
    ol_mark     = (f"  {GREEN}← tersimpan{R}" if saved_provider == "ollama" else "") + ollama_mark
    print(f"  {CYAN}1{R}. Ollama  (lokal){ol_mark}")
    print(f"  {CYAN}2{R}. OpenRouter (cloud){or_mark}\n")

    default_prov = "1" if (saved_provider == "ollama" or not saved_provider) else "2"
    prov_input   = input(f"{DIM}Pilih [1/2, default={default_prov}]: {R}").strip() or default_prov

    if prov_input == "2":
        config.PROVIDER = "openrouter"
        save_config({"provider": "openrouter"})
        print(f"\n{GREEN}✓ Provider: OpenRouter{R}")

        api_key = cfg.get("api_key", "")
        if api_key:
            masked = api_key[:8] + "…" + api_key[-4:]
            print(f"  {DIM}API key tersimpan: {masked}{R}")
            if input(f"  Ganti API key? [y/N]: ").strip().lower() == "y":
                api_key = input(f"  Masukkan OPENROUTER_API_KEY baru: ").strip()
                if api_key:
                    save_config({"api_key": api_key})
                    print(f"  {GREEN}✓ API key disimpan.{R}")
        else:
            print(f"\n  {YELLOW}⚠ OPENROUTER_API_KEY belum diset.{R}")
            print(f"  Daftar gratis di {CYAN}https://openrouter.ai/keys{R}")
            api_key = input(f"  Masukkan API key (kosongkan=skip): ").strip()
            if api_key:
                save_config({"api_key": api_key})
                print(f"  {GREEN}✓ API key disimpan ke .env{R}")
            else:
                print(f"  {DIM}Lanjut tanpa API key (akan error saat memanggil model).{R}")
        print()
        return "openrouter", api_key

    else:
        config.PROVIDER = "ollama"
        save_config({"provider": "ollama"})
        if ollama_ok:
            print(f"{GREEN}✓ Provider: Ollama (terhubung){R}")
        else:
            print(f"{YELLOW}⚠ Provider: Ollama — server tidak terdeteksi. Jalankan: ollama serve{R}")
            if not yn("Tetap lanjutkan?"):
                return "ollama", ""
        print()
        return "ollama", ""


def main():
    print(f"\n{BOLD}{CYAN}{'═'*54}{R}")
    print(f"{BOLD}{CYAN}   🤖  My AI CLI  —  Ollama / OpenRouter + Tools{R}")
    print(f"{BOLD}{CYAN}{'═'*54}{R}\n")

    cfg = load_config()

    provider, api_key = _setup_provider(cfg)

    default_model        = cfg.get("default_model", "")
    model_id, model_desc = pilih_model(default_model)
    persona_nama         = PERSONA_NAMA
    sys_prompt           = PERSONA_PROMPT

    cwd = Path(".").resolve()
    set_allowed_root(cwd)
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
        ),
    }
    messages            = [system_msg]
    all_history         = load_history()
    current_session_idx = None

    # ── Command loop ──────────────────────────────────────────────────────────
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

            if cmd == "/exit":
                print(f"\n{YELLOW}Sampai jumpa!{R}\n")
                break

            elif cmd == "/clear":
                messages            = [system_msg]
                current_session_idx = None
                print(f"\n{GREEN}✓ Konteks dihapus.{R}")

            elif cmd == "/history":
                show_history(all_history)

            elif cmd == "/sessions":
                shown = list_sessions(all_history)
                if shown:
                    sel = input(f"  {DIM}Nomor sesi (kosongkan=batal): {R}").strip()
                    if sel.isdigit() and 1 <= int(sel) <= len(shown):
                        entry               = shown[int(sel) - 1]
                        messages            = load_session_messages(entry, system_msg)
                        current_session_idx = all_history.index(entry)
                        n = len([m for m in messages if m["role"] in ("user", "assistant")])
                        print(f"\n{GREEN}✓ Sesi dilanjutkan ({n} pesan dimuat).{R}")
                    else:
                        print(f"\n{YELLOW}Dibatalkan.{R}")

            elif cmd == "/persona":
                print(f"\n{DIM}Persona tunggal aktif: {CYAN}{PERSONA_NAMA}{R}\n")

            elif cmd == "/model":
                model_id, model_desc = pilih_model(cfg.get("default_model", ""))
                messages             = [system_msg]
                current_session_idx  = None
                print(f"{DIM}Konteks direset. Provider: {'OpenRouter' if config.PROVIDER == 'openrouter' else 'Ollama'}{R}")

            elif cmd == "/cwd":
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    new_cwd = Path(parts[1]).expanduser().resolve()
                    if new_cwd.is_dir():
                        os.chdir(new_cwd)
                        cwd = new_cwd
                        set_allowed_root(cwd)
                        system_msg["content"] = re.sub(
                            r"Working directory saat ini: .*",
                            f"Working directory saat ini: {cwd}",
                            system_msg["content"],
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
                            set_allowed_root(cwd)
                            system_msg["content"] = re.sub(
                                r"Working directory saat ini: .*",
                                f"Working directory saat ini: {cwd}",
                                system_msg["content"],
                            )
                            print(f"{GREEN}✓ Pindah ke: {cwd}{R}")
                        else:
                            print(f"{RED}❌ Tidak ditemukan.{R}")

            elif cmd == "/tools":
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
                if config.PROVIDER == "ollama":
                    print(f"\n{YELLOW}Ollama berjalan lokal, tidak memerlukan API key.{R}")
                    print(f"{DIM}Untuk menggunakan OpenRouter, restart dan pilih provider OpenRouter.{R}\n")
                else:
                    parts = user_input.split(maxsplit=1)
                    if len(parts) > 1:
                        new_key = parts[1].strip()
                    else:
                        masked  = api_key[:8] + "…" + api_key[-4:] if api_key else "(belum diset)"
                        print(f"\n  API key saat ini: {DIM}{masked}{R}")
                        new_key = input(f"  Masukkan OPENROUTER_API_KEY baru (kosongkan=batal): ").strip()
                    if new_key:
                        api_key = new_key
                        save_config({"api_key": api_key})
                        print(f"\n{GREEN}✓ API key disimpan.{R}\n")
                    else:
                        print(f"\n{YELLOW}Dibatalkan.{R}\n")

            elif cmd == "/voice":
                parts = user_input.split(maxsplit=1)
                arg   = parts[1].lower() if len(parts) > 1 else ""

                if arg == "on":
                    if not voicevox_check():
                        print(f"\n{RED}❌ VOICEVOX tidak terdeteksi di {config.VOICEVOX_URL}.{R}")
                        print(f"{DIM}Buka aplikasi VOICEVOX terlebih dahulu, lalu coba lagi.{R}\n")
                    else:
                        config.VOICE_ENABLED = True
                        print(f"\n{GREEN}✓ Voice aktif. Setiap balasan AI akan dibacakan.{R}\n")
                elif arg == "off":
                    config.VOICE_ENABLED = False
                    print(f"\n{GREEN}✓ Voice nonaktif.{R}\n")
                elif arg == "list":
                    speakers = voicevox_speakers()
                    if not speakers:
                        print(f"\n{RED}❌ Tidak bisa ambil daftar speaker. VOICEVOX terbuka?{R}\n")
                    else:
                        print(f"\n{BOLD}Speaker VOICEVOX tersedia:{R}")
                        for sid, name in speakers:
                            mark = f"  {GREEN}← aktif{R}" if sid == config.VOICEVOX_SPEAKER else ""
                            print(f"  {CYAN}{sid:>3}{R}  {name}{mark}")
                        print(f"\n{DIM}Ganti dengan: /voice set <id>{R}\n")
                elif arg.startswith("set"):
                    sub = user_input.split()
                    if len(sub) >= 3 and sub[2].isdigit():
                        config.VOICEVOX_SPEAKER = int(sub[2])
                        print(f"\n{GREEN}✓ Speaker diubah ke ID {config.VOICEVOX_SPEAKER}.{R}")
                        print(f"{DIM}Lihat nama: /voice list{R}\n")
                    else:
                        print(f"\n{YELLOW}Pakai: /voice set <id_speaker>{R}\n")
                else:
                    status    = f"{GREEN}AKTIF{R}" if config.VOICE_ENABLED else f"{DIM}nonaktif{R}"
                    connected = f"{GREEN}terhubung{R}" if voicevox_check() else f"{RED}tidak terhubung{R}"
                    print(f"\n  Voice   : {status}")
                    print(f"  VOICEVOX: {connected}  {DIM}({config.VOICEVOX_URL}){R}")
                    print(f"  Speaker : {config.VOICEVOX_SPEAKER}")
                    print(f"\n{DIM}Pakai: /voice on | off | list | set <id>{R}\n")

            elif cmd == "/info":
                voice_status = f"{GREEN}ON{R}" if config.VOICE_ENABLED else f"{DIM}OFF{R}"
                prov_label   = f"{CYAN}OpenRouter{R}" if config.PROVIDER == "openrouter" else f"{CYAN}Ollama{R}"
                print(f"\n  Provider: {prov_label}")
                print(f"  Model   : {CYAN}{model_desc}{R}  {DIM}({model_id}){R}")
                print(f"  Persona : {CYAN}{PERSONA_NAMA}{R}")
                print(f"  CWD     : {CYAN}{cwd}{R}")
                print(f"  Voice   : {voice_status}\n")

            elif cmd == "/avatar":
                ok = avatar_server.start_server(open_browser=True)
                if ok:
                    print(f"\n{GREEN}✓ Avatar dibuka di http://{avatar_server.HOST}:{avatar_server.PORT}{R}")
                    print(f"{DIM}Klik di window/tab avatar sekali agar audio bisa diputar (browser autoplay policy).{R}\n")
                else:
                    print(f"\n{RED}❌ Gagal start avatar server. Pastikan sudah: pip install flask flask-sock{R}\n")

            elif cmd == "/help":
                help_text()

            else:
                print(f"\n{RED}Tidak dikenal. Ketik /help.{R}")
            continue

        # ── Kirim ke AI ───────────────────────────────────────────────────────
        messages.append({"role": "user", "content": user_input})

        try:
            process_response(api_key, model_id, messages)
        except ValueError as e:
            print(f"\n{RED}❌ {e}{R}\n")
            messages.pop()
            continue
        except requests.exceptions.ConnectionError:
            if config.PROVIDER == "openrouter":
                print(f"\n{RED}❌ Tidak bisa terhubung ke OpenRouter. Cek koneksi internet.{R}\n")
            else:
                print(f"\n{RED}❌ Tidak bisa terhubung ke Ollama. Pastikan 'ollama serve' berjalan.{R}\n")
            messages.pop()
            continue
        except Exception as e:
            print(f"\n{RED}❌ Error: {e}{R}\n")
            messages.pop()
            continue

        print()

        # Simpan ke history
        chat_msgs  = [m for m in messages if m["role"] not in ("system", "tool") and not m.get("tool_calls")]
        first_user = next((m["content"] for m in chat_msgs if m["role"] == "user"), "")
        entry = {
            "timestamp":  datetime.datetime.now().isoformat(),
            "persona":    persona_nama,
            "model":      model_id,
            "user_first": first_user,
            "messages":   [m for m in messages if m["role"] != "system"],
        }
        if current_session_idx is not None and 0 <= current_session_idx < len(all_history):
            entry["user_first"]                  = all_history[current_session_idx].get("user_first", first_user)
            all_history[current_session_idx]      = entry
        elif len(chat_msgs) <= 2:
            all_history.append(entry)
            current_session_idx = len(all_history) - 1
        elif all_history:
            all_history[-1] = entry
        save_history(all_history)


if __name__ == "__main__":
    main()
