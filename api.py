"""
api.py — Komunikasi dengan AI provider: Ollama (lokal) dan OpenRouter (cloud).

Fungsi utama:
  call_api_stream()  — generator stream chunk ternormalisasi
  process_response() — agentic loop: stream → tool call → stream lagi
"""

import json, time

import requests

from flask import request, jsonify

import config
from config import (
    PROVIDER, OLLAMA_URL, OPENROUTER_URL,
    BOLD, DIM, R, CYAN, YELLOW, MAGENTA,
)
from tools import TOOLS, TOOL_MAP


# ─── Dispatcher ───────────────────────────────────────────────────────────────

def call_api_stream(model: str, messages: list, api_key: str = "", use_tools: bool = True):
    """Generator: yield chunk ternormalisasi dari provider aktif.
    Setiap chunk: {"message": {"content": str, "tool_calls"?: list}, "done": bool}
    """
    if config.PROVIDER == "openrouter":
        yield from _stream_openrouter(model, messages, api_key, use_tools)
    else:
        yield from _stream_ollama(model, messages, use_tools)


# ─── Ollama ───────────────────────────────────────────────────────────────────

def _stream_ollama(model: str, messages: list, use_tools: bool = True):
    """Stream NDJSON dari Ollama — format asli sudah cocok, pass-through langsung."""
    body = {
        "model":    model,
        "messages": messages,
        "stream":   True,
        "options":  {"num_predict": 4096},
    }
    if use_tools:
        body["tools"] = TOOLS

    resp = requests.post(OLLAMA_URL, json=body, timeout=120, stream=True)
    if not resp.ok:
        raise ValueError(f"HTTP {resp.status_code}: {resp.text[:300]}")

    for line in resp.iter_lines():
        if not line:
            continue
        try:
            yield json.loads(line.decode("utf-8"))
        except json.JSONDecodeError:
            continue


# ─── OpenRouter ───────────────────────────────────────────────────────────────

def _stream_openrouter(model: str, messages: list, api_key: str, use_tools: bool = True):
    """Stream SSE dari OpenRouter, dinormalisasi ke format yang sama dengan Ollama.

    Error handling:
      429 → auto-retry hingga MAX_RETRIES kali dengan backoff
      400 + tools → retry sekali tanpa tools (model tidak support tool calling)
      402 → raise dengan pesan jelas (kredit habis)
    """
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY belum diset. Jalankan /apikey untuk mengisinya.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "https://github.com/my-ai-cli",
        "X-Title":       "My AI CLI",
    }

    MAX_RETRIES = 4
    _use_tools  = use_tools

    for attempt in range(MAX_RETRIES + 1):
        body = {
            "model":      model,
            "messages":   messages,
            "stream":     True,
            "max_tokens": 4096,
        }
        if _use_tools:
            body["tools"] = TOOLS

        resp = requests.post(OPENROUTER_URL, json=body, headers=headers, timeout=120, stream=True)

        # 429: rate limit — tunggu lalu retry
        if resp.status_code == 429:
            if attempt >= MAX_RETRIES:
                raise ValueError(
                    f"Rate limit (429) setelah {MAX_RETRIES} percobaan. "
                    "Coba lagi nanti atau ganti model (/model)."
                )
            try:
                retry_after = float(
                    resp.json().get("error", {}).get("metadata", {})
                               .get("retry_after_seconds", 0) or 0
                )
            except Exception:
                retry_after = 0
            wait = max(retry_after, 5 * (attempt + 1))
            print(f"\n  {YELLOW}⏳ Rate limit (429). Menunggu {wait:.0f}s lalu retry "
                  f"({attempt+1}/{MAX_RETRIES})…{R}", flush=True)
            time.sleep(wait)
            continue

        # 400 + tools → retry tanpa tools
        if resp.status_code == 400 and _use_tools:
            print(f"\n  {YELLOW}⚠ Model tidak mendukung tool calling (400). "
                  f"Retry tanpa tools…{R}", flush=True)
            _use_tools = False
            continue

        # 402: kredit habis
        if resp.status_code == 402:
            try:
                msg = resp.json().get("error", {}).get("message", "")
            except Exception:
                msg = ""
            raise ValueError(
                f"❌ Kredit OpenRouter tidak cukup (402).\n"
                f"  {msg}\n"
                f"  → Top-up di: https://openrouter.ai/settings/credits\n"
                f"  → Atau ganti ke model gratis (/model)."
            )

        # Error lain
        if not resp.ok:
            raise ValueError(f"HTTP {resp.status_code}: {resp.text[:400]}")

        break  # berhasil → lanjut parsing SSE
    else:
        raise ValueError("Semua percobaan gagal.")

    # Parsing SSE — kumpulkan tool_call delta per-chunk lalu flush sekaligus
    accumulated: dict = {}  # index → {id, type, function:{name, arguments}}

    for raw_line in resp.iter_lines():
        if not raw_line:
            continue
        line = raw_line.decode("utf-8").strip()

        if line == "data: [DONE]":
            if accumulated:
                yield {"message": {"content": "", "tool_calls": _finalize_tool_calls(accumulated)}, "done": False}
            yield {"message": {"content": ""}, "done": True}
            return

        if not line.startswith("data: "):
            continue
        try:
            data = json.loads(line[6:])
        except json.JSONDecodeError:
            continue

        choice = (data.get("choices") or [{}])[0]
        delta  = choice.get("delta", {})

        text_piece = delta.get("content") or ""

        for tc_delta in (delta.get("tool_calls") or []):
            idx = tc_delta.get("index", 0)
            if idx not in accumulated:
                accumulated[idx] = {"id": tc_delta.get("id", ""), "type": "function",
                                    "function": {"name": "", "arguments": ""}}
            acc = accumulated[idx]
            fn  = tc_delta.get("function", {})
            if fn.get("name"):      acc["function"]["name"]      += fn["name"]
            if fn.get("arguments"): acc["function"]["arguments"] += fn["arguments"]
            if tc_delta.get("id"):  acc["id"] = tc_delta["id"]

        is_done = choice.get("finish_reason") in ("stop", "tool_calls", "length")
        yield {"message": {"content": text_piece}, "done": False}

        if is_done:
            if accumulated:
                yield {"message": {"content": "", "tool_calls": _finalize_tool_calls(accumulated)}, "done": False}
            yield {"message": {"content": ""}, "done": True}
            return


def _finalize_tool_calls(accumulated: dict) -> list:
    """Ubah dict index→fragment menjadi list tool_calls standar."""
    result = []
    for idx in sorted(accumulated):
        tc  = accumulated[idx]
        raw = tc["function"]["arguments"]
        try:
            args = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            args = {"_raw": raw}
        result.append({
            "id":   tc.get("id", f"call_{idx}"),
            "type": "function",
            "function": {"name": tc["function"]["name"], "arguments": args},
        })
    return result


# ─── Agentic loop ─────────────────────────────────────────────────────────────

def process_response(api_key: str, model: str, messages: list) -> str:
    """Loop: stream teks → eksekusi tool calls → stream lagi, hingga tidak ada tool call."""
    from voice import speak_text  # import lokal untuk hindari circular

    while True:
        full_content  = ""
        tool_calls    = []
        printed_label = False

        for chunk in call_api_stream(model, messages, api_key):
            msg   = chunk.get("message", {})
            piece = msg.get("content", "")

            if piece:
                if not printed_label:
                    print(f"\n{CYAN}{BOLD}AI ▸{R} ", end="", flush=True)
                    printed_label = True
                print(piece, end="", flush=True)
                full_content += piece

            if msg.get("tool_calls"):
                tool_calls = msg["tool_calls"]

            if chunk.get("done"):
                break

        if printed_label:
            print()  # newline setelah streaming selesai

        assistant_msg = {"role": "assistant", "content": full_content}
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)

        # Tidak ada tool call → selesai
        if not tool_calls:
            if config.VOICE_ENABLED and full_content.strip():
                status = speak_text(full_content)
                if status.startswith("❌"):
                    print(f"  {DIM}{status}{R}")
            return ""

        # Eksekusi tool calls
        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            fn_args = tc["function"].get("arguments", {})
            if isinstance(fn_args, str):
                try:
                    fn_args = json.loads(fn_args)
                except Exception:
                    fn_args = {}

            print(f"\n  {MAGENTA}🔧 {fn_name}{R}({DIM}"
                  + ", ".join(f"{k}={repr(v)[:60]}" for k, v in fn_args.items())
                  + f"{R})")

            result  = TOOL_MAP[fn_name](fn_args) if fn_name in TOOL_MAP else f"❌ Tool tidak dikenal: {fn_name}"
            preview = result[:200].replace("\n", " ")
            print(f"  {DIM}→ {preview}{'...' if len(result) > 200 else ''}{R}\n")

            messages.append({"role": "tool", "content": result})


# ──────────────────────────────────────────────────────────────────────────────
# Avatar / Web API Helpers
# ──────────────────────────────────────────────────────────────────────────────

def process_response_api(api_key: str, model: str, messages: list):
    """
    Versi process_response untuk web/avatar.
    Tidak print ke terminal.
    Tidak speak otomatis.
    Mengembalikan dict.
    """

    while True:
        full_content = ""
        tool_calls = []

        for chunk in call_api_stream(model, messages, api_key):
            msg = chunk.get("message", {})

            full_content += msg.get("content", "")

            if msg.get("tool_calls"):
                tool_calls = msg["tool_calls"]

            if chunk.get("done"):
                break

        assistant_msg = {
            "role": "assistant",
            "content": full_content
        }

        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls

        messages.append(assistant_msg)

        if not tool_calls:
            return {
                "text": full_content,
                "emotion": detect_emotion(full_content),
                "tool_calls": []
            }

        for tc in tool_calls:

            fn_name = tc["function"]["name"]

            fn_args = tc["function"].get("arguments", {})

            if isinstance(fn_args, str):
                try:
                    fn_args = json.loads(fn_args)
                except Exception:
                    fn_args = {}

            result = (
                TOOL_MAP[fn_name](fn_args)
                if fn_name in TOOL_MAP
                else f"❌ Tool tidak dikenal: {fn_name}"
            )

            messages.append({
                "role": "tool",
                "content": result
            })


def ask_ai(message: str):

    messages = [
        {
            "role": "user",
            "content": message
        }
    ]

    api_key = getattr(config, "OPENROUTER_API_KEY", "")
    model = getattr(config, "MODEL", "llama3")

    print("DEBUG API_KEY =", repr(api_key))
    print("DEBUG MODEL   =", repr(model))
    print("DEBUG PROVIDER=", getattr(config, "PROVIDER", None))

    result = process_response_api(
        api_key,
        model,
        messages
    )

    # ── TTS: synthesize via VOICEVOX & broadcast ke browser ────────────────
    text = result.get("text", "")
    if text.strip():
        try:
            from voice import synthesize_wav
            import avatar_server

            wav_bytes = synthesize_wav(text)
            if wav_bytes:
                avatar_server.broadcast_audio(wav_bytes)
                avatar_server.broadcast_expression(result.get("emotion", "normal"))
            else:
                print("DEBUG TTS: synthesize_wav returned empty (cek VOICEVOX_URL / VOICEVOX app)")
        except Exception as e:
            print("DEBUG TTS ERROR:", e)

    return result


def detect_emotion(text: str):
    """
    Deteksi emosi sederhana.
    """

    t = text.lower()

    if any(x in t for x in [
        "senang",
        "bahagia",
        "gembira",
        "hehe",
        "haha"
    ]):
        return "happy"

    if any(x in t for x in [
        "sedih",
        "kecewa",
        "duka"
    ]):
        return "sad"

    if any(x in t for x in [
        "marah",
        "kesal",
        "geram"
    ]):
        return "angry"

    return "normal"