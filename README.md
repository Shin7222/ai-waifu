# My AI CLI

## Install
```bash
pip install -r requirements.txt --break-system-packages
```

## Jalankan
```bash
python main.py
```

## Struktur
- config.py      — konstanta, warna, persona, path safety, .env
- voice.py        — VOICEVOX TTS + broadcast lipsync ke avatar
- tools.py        — tools AI (file, search, shell, dll)
- api.py          — Ollama & OpenRouter streaming + agentic loop
- history.py      — load/save/resume sesi chat
- ui.py           — pilih model, help, export chat
- avatar_server.py— server Live2D avatar (Flask + WebSocket)
- web/            — halaman avatar Live2D (index.html + model/)
- main.py         — entry point

## Avatar Live2D
Ketik `/avatar` di CLI untuk membuka avatar di browser.
Klik sekali di window avatar agar audio bisa diputar (browser autoplay policy).
Saat `/voice on` aktif, setiap balasan AI akan disuarakan VOICEVOX
dan mulut avatar akan bergerak sesuai amplitude audio (lip-sync).

## .env (dibuat otomatis)
- OPENROUTER_API_KEY
- MY_AI_PROVIDER (ollama / openrouter)
- MY_AI_DEFAULT_MODEL
