#!/usr/bin/env python3
"""Implementasi tools untuk My AI CLI."""

import re
import requests
from pathlib import Path
from config import MAX_FILE_BYTES, MAX_SEARCH_CHARS
from utils import c, yn, R, MAGENTA, DIM

def tool_read_file(path: str) -> str:
    """Baca isi file teks."""
    p = Path(path).expanduser().resolve()
    if not p.exists():    return f"❌ File tidak ditemukan: {p}"
    if not p.is_file():   return f"❌ Bukan file: {p}"
    size = p.stat().st_size
    if size > MAX_FILE_BYTES:
        return f"❌ File terlalu besar ({size:,} bytes). Maksimum {MAX_FILE_BYTES:,} bytes."
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        lines   = content.splitlines()
        numbered = "\n".join(f"{i+1:>4} | {l}" for i, l in enumerate(lines))
        return f"📄 {p} ({len(lines)} baris)\n\n{numbered}"
    except Exception as e:
        return f"❌ Gagal membaca: {e}"

def tool_write_file(path: str, content: str) -> str:
    """Tulis atau buat file baru."""
    p = Path(path).expanduser().resolve()
    exists = p.exists()
    action = "menimpa" if exists else "membuat"
    if not yn(f"AI ingin {action} file: {p}"):
        return "❌ Dibatalkan oleh user."
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        lines = content.count("\n") + 1
        return f"✅ File {'ditimpa' if exists else 'dibuat'}: {p} ({lines} baris)"
    except Exception as e:
        return f"❌ Gagal menulis: {e}"

def tool_edit_file(path: str, old_str: str, new_str: str) -> str:
    """Edit bagian tertentu dari file."""
    p = Path(path).expanduser().resolve()
    if not p.exists(): return f"❌ File tidak ditemukan: {p}"
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"❌ Gagal membaca: {e}"
    count = content.count(old_str)
    if count == 0:  return "❌ Teks yang dicari tidak ditemukan dalam file."
    if count > 1:   return f"❌ Teks ditemukan {count}x (harus unik). Perjelas konteks teks yang akan diganti."
    preview_old = old_str[:120].replace("\n", "↵ ")
    preview_new = new_str[:120].replace("\n", "↵ ")
    print(f"\n  {DIM}Dari:{R} {c(preview_old, 'red')}")
    print(f"  {DIM}Ke  :{R} {c(preview_new, 'green')}")
    if not yn(f"AI ingin edit file: {p}"):
        return "❌ Dibatalkan oleh user."
    try:
        new_content = content.replace(old_str, new_str, 1)
        p.write_text(new_content, encoding="utf-8")
        return f"✅ File diedit: {p}"
    except Exception as e:
        return f"❌ Gagal menulis: {e}"

def tool_list_dir(path: str = ".", recursive: bool = False) -> str:
    """Tampilkan isi direktori."""
    p = Path(path).expanduser().resolve()
    if not p.exists():   return f"❌ Path tidak ditemukan: {p}"
    if not p.is_dir():   return f"❌ Bukan direktori: {p}"
    try:
        entries = []
        if recursive:
            for item in sorted(p.rglob("*")):
                rel  = item.relative_to(p)
                icon = "📁" if item.is_dir() else "📄"
                size = f"  {item.stat().st_size:>8,} B" if item.is_file() else ""
                entries.append(f"{icon} {rel}{size}")
        else:
            for item in sorted(p.iterdir()):
                icon = "📁" if item.is_dir() else "📄"
                size = f"  {item.stat().st_size:>8,} B" if item.is_file() else ""
                entries.append(f"{icon} {item.name}{size}")
        if not entries: return f"📂 {p} (kosong)"
        return f"📂 {p} ({len(entries)} item)\n\n" + "\n".join(entries)
    except Exception as e:
        return f"❌ Gagal: {e}"

def tool_search_in_files(pattern: str, directory: str = ".", extension: str = "") -> str:
    """Cari teks/pattern dalam file di direktori."""
    base = Path(directory).expanduser().resolve()
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
                        rel = fpath.relative_to(base)
                        results.append(f"{rel}:{i}: {line.strip()}")
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
    """Cari informasi di internet menggunakan DuckDuckGo."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url     = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        resp    = requests.get(url, headers=headers, timeout=10)
        raw     = resp.text
        results = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', raw, re.DOTALL)
        titles  = re.findall(r'class="result__a"[^>]*>(.*?)</a>', raw, re.DOTALL)
        def clean(s): return re.sub(r'<[^>]+>', '', s).strip()
        items   = []
        for t, r in zip(titles[:5], results[:5]):
            items.append(f"• {clean(t)}\n  {clean(r)}")
        if not items:
            return f"🌐 Tidak ada hasil untuk: {query}"
        return f"🌐 Hasil web search: '{query}'\n\n" + "\n\n".join(items)
    except Exception as e:
        return f"❌ Web search gagal: {e}"

def tool_create_dir(path: str) -> str:
    """Buat direktori baru."""
    p = Path(path).expanduser().resolve()
    if p.exists(): return f"ℹ️ Direktori sudah ada: {p}"
    if not yn(f"AI ingin membuat direktori: {p}"):
        return "❌ Dibatalkan oleh user."
    try:
        p.mkdir(parents=True, exist_ok=True)
        return f"✅ Direktori dibuat: {p}"
    except Exception as e:
        return f"❌ Gagal: {e}"

# Pemetaan tool
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
                "required": ["path"]
            }
        }
    },
    # ... (lanjutkan dengan definisi tools lain seperti di original code)
]

TOOL_MAP = {
    "read_file":       lambda a: tool_read_file(**a),
    "write_file":      lambda a: tool_write_file(**a),
    "edit_file":       lambda a: tool_edit_file(**a),
    "list_dir":        lambda a: tool_list_dir(**a),
    "search_in_files": lambda a: tool_search_in_files(**a),
    "web_search":      lambda a: tool_web_search(**a),
    "create_dir":      lambda a: tool_create_dir(**a),
}