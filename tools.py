"""
tools.py — Definisi schema tools (dikirim ke API) dan implementasinya.
Tools tersedia: read_file, write_file, edit_file, list_dir,
                search_in_files, web_search, create_dir, open_app, run_command
"""

import os, re, subprocess
from pathlib import Path

import requests

from config import (
    check_path, yn,
    MAX_FILE_BYTES, MAX_SEARCH_CHARS,
    ALLOWED_ROOT,
    DIM, R, RED, GREEN, YELLOW, MAGENTA,
)

# ─── Schema (dikirim ke API) ──────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Baca isi file teks. Gunakan untuk melihat kode, config, atau dokumen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path absolut atau relatif ke file"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Tulis atau buat file baru. Untuk membuat file baru atau menimpa seluruh isi file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":    {"type": "string", "description": "Path file yang akan ditulis"},
                    "content": {"type": "string", "description": "Isi file yang akan ditulis"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit bagian tertentu dari file: ganti old_str dengan new_str. Gunakan untuk patch kode tanpa menulis ulang seluruh file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":    {"type": "string", "description": "Path file yang akan diedit"},
                    "old_str": {"type": "string", "description": "Teks yang akan diganti (harus unik dalam file)"},
                    "new_str": {"type": "string", "description": "Teks pengganti"},
                },
                "required": ["path", "old_str", "new_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "Tampilkan isi direktori (file dan subfolder).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":      {"type": "string",  "description": "Path direktori, default '.'"},
                    "recursive": {"type": "boolean", "description": "Tampilkan subfolder secara rekursif, default false"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_in_files",
            "description": "Cari teks/pattern dalam file di suatu direktori.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern":   {"type": "string", "description": "Teks atau regex yang dicari"},
                    "directory": {"type": "string", "description": "Direktori yang dicari, default '.'"},
                    "extension": {"type": "string", "description": "Filter ekstensi, contoh: .py .js (opsional)"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Cari informasi di internet menggunakan DuckDuckGo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Query pencarian"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_dir",
            "description": "Buat direktori baru (beserta parent jika perlu).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path direktori yang akan dibuat"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Buka aplikasi atau file di sistem operasi. Bisa membuka aplikasi (Chrome, Notepad, VSCode, dll), folder, atau URL di browser default.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Nama aplikasi, path file/folder, atau URL (https://...)"},
                    "args":   {"type": "array", "items": {"type": "string"}, "description": "Argumen tambahan opsional"},
                },
                "required": ["target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Jalankan perintah shell/terminal. Selalu meminta konfirmasi user sebelum eksekusi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string",  "description": "Perintah shell yang akan dijalankan"},
                    "cwd":     {"type": "string",  "description": "Direktori tempat menjalankan command"},
                    "timeout": {"type": "integer", "description": "Batas waktu eksekusi dalam detik, default 60"},
                },
                "required": ["command"],
            },
        },
    },
]

# ─── Implementasi ─────────────────────────────────────────────────────────────

def tool_read_file(path: str) -> str:
    p, err = check_path(path)
    if err: return err
    if not p.exists():  return f"❌ File tidak ditemukan: {p}"
    if not p.is_file(): return f"❌ Bukan file: {p}"
    size = p.stat().st_size
    if size > MAX_FILE_BYTES:
        return f"❌ File terlalu besar ({size:,} bytes). Maksimum {MAX_FILE_BYTES:,} bytes."
    try:
        content  = p.read_text(encoding="utf-8", errors="replace")
        lines    = content.splitlines()
        numbered = "\n".join(f"{i+1:>4} | {l}" for i, l in enumerate(lines))
        return f"📄 {p} ({len(lines)} baris)\n\n{numbered}"
    except Exception as e:
        return f"❌ Gagal membaca: {e}"


def tool_write_file(path: str, content: str) -> str:
    p, err = check_path(path)
    if err: return err
    exists = p.exists()
    if not yn(f"AI ingin {'menimpa' if exists else 'membuat'} file: {p}"):
        return "❌ Dibatalkan oleh user."
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"✅ File {'ditimpa' if exists else 'dibuat'}: {p} ({content.count(chr(10))+1} baris)"
    except Exception as e:
        return f"❌ Gagal menulis: {e}"


def tool_edit_file(path: str, old_str: str, new_str: str) -> str:
    p, err = check_path(path)
    if err: return err
    if not p.exists(): return f"❌ File tidak ditemukan: {p}"
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"❌ Gagal membaca: {e}"
    count = content.count(old_str)
    if count == 0: return "❌ Teks yang dicari tidak ditemukan dalam file."
    if count > 1:  return f"❌ Teks ditemukan {count}x (harus unik). Perjelas konteks teks yang akan diganti."
    print(f"\n  {DIM}Dari:{R} {RED}{old_str[:120].replace(chr(10), '↵ ')}{R}")
    print(f"  {DIM}Ke  :{R} {GREEN}{new_str[:120].replace(chr(10), '↵ ')}{R}")
    if not yn(f"AI ingin edit file: {p}"):
        return "❌ Dibatalkan oleh user."
    try:
        p.write_text(content.replace(old_str, new_str, 1), encoding="utf-8")
        return f"✅ File diedit: {p}"
    except Exception as e:
        return f"❌ Gagal menulis: {e}"


def tool_list_dir(path: str = ".", recursive: bool = False) -> str:
    p, err = check_path(path)
    if err: return err
    if not p.exists():  return f"❌ Path tidak ditemukan: {p}"
    if not p.is_dir():  return f"❌ Bukan direktori: {p}"
    try:
        entries = []
        items   = sorted(p.rglob("*")) if recursive else sorted(p.iterdir())
        for item in items:
            icon = "📁" if item.is_dir() else "📄"
            rel  = item.relative_to(p) if recursive else Path(item.name)
            size = f"  {item.stat().st_size:>8,} B" if item.is_file() else ""
            entries.append(f"{icon} {rel}{size}")
        return f"📂 {p} ({len(entries)} item)\n\n" + "\n".join(entries) if entries else f"📂 {p} (kosong)"
    except Exception as e:
        return f"❌ Gagal: {e}"


def tool_search_in_files(pattern: str, directory: str = ".", extension: str = "") -> str:
    base, err = check_path(directory)
    if err: return err
    if not base.exists(): return f"❌ Direktori tidak ditemukan: {base}"
    results = []
    glob = f"*{extension}" if extension else "*"
    try:
        files = [f for f in base.rglob(glob) if f.is_file() and f.stat().st_size < MAX_FILE_BYTES]
        for fpath in sorted(files)[:50]:
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
                for i, line in enumerate(text.splitlines(), 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        results.append(f"{fpath.relative_to(base)}:{i}: {line.strip()}")
            except Exception:
                continue
        if not results:
            return f"🔍 Tidak ada hasil untuk '{pattern}' di {base}"
        out = "\n".join(results[:80])
        if len(out) > MAX_SEARCH_CHARS:
            out = out[:MAX_SEARCH_CHARS] + "\n... (terpotong)"
        return f"🔍 {len(results)} hasil untuk '{pattern}':\n\n{out}"
    except Exception as e:
        return f"❌ Error pencarian: {e}"


def tool_web_search(query: str) -> str:
    headers = {
        "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    # Coba HTML scrape dulu (hasil lebih kaya)
    try:
        url  = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        results = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
        titles  = re.findall(r'class="result__a"[^>]*>(.*?)</a>',       resp.text, re.DOTALL)
        clean   = lambda s: re.sub(r'<[^>]+>', '', s).strip()
        items   = [f"• {clean(t)}\n  {clean(r)}" for t, r in zip(titles[:5], results[:5]) if clean(t) or clean(r)]
        if items:
            return f"🌐 Hasil web search: '{query}'\n\n" + "\n\n".join(items)
    except requests.exceptions.RequestException:
        pass

    # Fallback: DuckDuckGo Instant Answer API
    try:
        resp = requests.get("https://api.duckduckgo.com/", params={
            "q": query, "format": "json", "no_html": "1", "skip_disambig": "1"
        }, headers=headers, timeout=10)
        resp.raise_for_status()
        data  = resp.json()
        items = []
        if data.get("AbstractText"):
            items.append(f"• {data.get('Heading', query)}\n  {data['AbstractText']}")
        for topic in data.get("RelatedTopics", [])[:5]:
            if isinstance(topic, dict) and topic.get("Text"):
                items.append(f"• {topic['Text']}")
        if items:
            return f"🌐 Hasil web search: '{query}'\n\n" + "\n\n".join(items[:5])
        return f"🌐 Tidak ada hasil untuk: {query}"
    except requests.exceptions.ConnectionError as e:
        return f"❌ Web search gagal: tidak bisa terhubung ke internet.\nDetail: {e}"
    except requests.exceptions.Timeout:
        return "❌ Web search gagal: timeout, coba lagi."
    except Exception as e:
        return f"❌ Web search gagal: {e}"


def tool_create_dir(path: str) -> str:
    p, err = check_path(path)
    if err: return err
    if p.exists(): return f"ℹ️ Direktori sudah ada: {p}"
    if not yn(f"AI ingin membuat direktori: {p}"):
        return "❌ Dibatalkan oleh user."
    try:
        p.mkdir(parents=True, exist_ok=True)
        return f"✅ Direktori dibuat: {p}"
    except Exception as e:
        return f"❌ Gagal: {e}"


def tool_open_app(target: str, args: list = None) -> str:
    import shutil, platform
    args   = args or []
    system = platform.system()

    ALIASES = {
        "notepad": "notepad.exe", "explorer": "explorer.exe",
        "cmd": "cmd.exe", "powershell": "powershell.exe",
        "calc": "calc.exe", "paint": "mspaint.exe", "taskmgr": "taskmgr.exe",
        "chrome":  "google-chrome" if system != "Windows" else "chrome",
        "firefox": "firefox", "code": "code", "vscode": "code",
        "cursor": "cursor", "sublime": "subl", "vim": "vim", "nano": "nano",
    }
    resolved = ALIASES.get(target.lower(), target)

    if target.startswith(("http://", "https://")):
        import webbrowser
        webbrowser.open(target)
        return f"✅ Membuka URL di browser: {target}"

    p = Path(target).expanduser()
    if p.exists():
        if system == "Windows":   os.startfile(str(p))
        elif system == "Darwin":  subprocess.Popen(["open", str(p)])
        else:                     subprocess.Popen(["xdg-open", str(p)])
        return f"✅ Membuka: {p}"

    try:
        if system == "Windows":
            subprocess.Popen(["start", "", resolved] + args, shell=True)
        elif system == "Darwin":
            subprocess.Popen(["open", "-a", resolved] + args)
        else:
            if not shutil.which(resolved):
                return f"❌ Aplikasi tidak ditemukan: {resolved}"
            subprocess.Popen([resolved] + args)
        return f"✅ Membuka aplikasi: {resolved}" + (f" dengan argumen: {args}" if args else "")
    except Exception as e:
        return f"❌ Gagal membuka '{target}': {e}"


MAX_CMD_OUTPUT = 5_000

def tool_run_command(command: str, cwd: str = "", timeout: int = 60) -> str:
    if cwd:
        run_dir, err = check_path(cwd)
        if err: return err
        if not run_dir.is_dir():
            return f"❌ Direktori tidak ditemukan: {run_dir}"
    else:
        run_dir = ALLOWED_ROOT

    timeout = min(max(int(timeout or 60), 1), 300)
    print(f"\n  {DIM}Perintah:{R}   {YELLOW}{command}{R}")
    print(f"  {DIM}Direktori:{R}  {run_dir}")
    if not yn("AI ingin menjalankan perintah shell di atas"):
        return "❌ Dibatalkan oleh user."

    try:
        result = subprocess.run(
            command, shell=True, cwd=str(run_dir),
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        out    = ((result.stdout or "") + (result.stderr or "")).strip() or "(tidak ada output)"
        if len(out) > MAX_CMD_OUTPUT:
            out = out[:MAX_CMD_OUTPUT] + f"\n... (terpotong, total {len(out):,} karakter)"
        status = "✅" if result.returncode == 0 else f"⚠️ exit code {result.returncode}"
        return f"{status}\n$ {command}\n\n{out}"
    except subprocess.TimeoutExpired:
        return f"❌ Perintah timeout setelah {timeout} detik: {command}"
    except Exception as e:
        return f"❌ Gagal menjalankan perintah: {e}"


# ─── Dispatch map ─────────────────────────────────────────────────────────────

TOOL_MAP = {
    "read_file":       lambda a: tool_read_file(**a),
    "write_file":      lambda a: tool_write_file(**a),
    "edit_file":       lambda a: tool_edit_file(**a),
    "list_dir":        lambda a: tool_list_dir(**a),
    "search_in_files": lambda a: tool_search_in_files(**a),
    "web_search":      lambda a: tool_web_search(**a),
    "create_dir":      lambda a: tool_create_dir(**a),
    "open_app":        lambda a: tool_open_app(**a),
    "run_command":     lambda a: tool_run_command(**a),
}
