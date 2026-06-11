#!/usr/bin/env python3
"""Modul untuk berinteraksi dengan OpenRouter API."""

import json
import requests
from config import OPENROUTER_URL
from tools import TOOLS, TOOL_MAP

def call_api(api_key: str, model: str, messages: list, use_tools: bool = True) -> dict:
    """Panggil OpenRouter API untuk mendapatkan respons AI."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "https://my-ai-cli",
        "X-Title":       "My AI CLI",
    }
    body = {"model": model, "messages": messages, "max_tokens": 4096}
    if use_tools:
        body["tools"] = TOOLS

    resp = requests.post(OPENROUTER_URL, headers=headers, json=body, timeout=120)
    if resp.status_code == 401: raise ValueError("API key tidak valid.")
    if resp.status_code == 402: raise ValueError("Saldo OpenRouter habis.")
    if resp.status_code == 429: raise ValueError("Rate limit. Tunggu sebentar.")
    if not resp.ok:             raise ValueError(f"HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json()

def process_response(api_key: str, model: str, messages: list) -> str:
    """Proses respons API secara agentic, menangani tool calls."""
    while True:
        data    = call_api(api_key, model, messages)
        choice  = data["choices"][0]
        message = choice["message"]
        finish  = choice.get("finish_reason", "")

        # Tambah respons assistant ke messages
        messages.append(message)

        # Kalau tidak ada tool call → kembalikan teks
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            return message.get("content") or ""

        # Eksekusi semua tool calls
        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            try:
                fn_args = json.loads(tc["function"]["arguments"])
            except Exception:
                fn_args = {}

            # Tampilkan apa yang AI lakukan
            print(f"\n  🔧 {fn_name}({', '.join(f'{k}={repr(v)[:60]}' for k,v in fn_args.items())})")

            if fn_name in TOOL_MAP:
                result = TOOL_MAP[fn_name](fn_args)
            else:
                result = f"❌ Tool tidak dikenal: {fn_name}"

            # Tampilkan preview hasil
            preview = result[:200].replace("\n", " ")
            print(f"  → {preview}{'...' if len(result)>200 else ''}\n")

            # Kirim hasil tool ke messages
            messages.append({
                "role":         "tool",
                "tool_call_id": tc["id"],
                "content":      result,
            })