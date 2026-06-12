"""
config.py — Konstanta global, warna terminal, persona, dan path safety.
"""

import os, re, sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

try:
    import requests
except ImportError:
    print("❌ Jalankan: pip install requests")
    sys.exit(1)

# ─── Path & Limits ────────────────────────────────────────────────────────────

HISTORY_FILE     = Path(__file__).parent / "history" / "history.json"
MAX_FILE_BYTES   = 100_000
MAX_SEARCH_CHARS = 3_000

# ─── Provider ─────────────────────────────────────────────────────────────────

PROVIDER       = "ollama"   # di-override oleh main()
OLLAMA_URL     = "http://localhost:11434/api/chat"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODELS_OLLAMA = {
    "1": ("llama3.2:latest", "Llama 3.2 (latest)"),
}

MODELS_OPENROUTER = {
    "1": ("meta-llama/llama-3.3-70b-instruct:free", "Llama 3.3 70B (free)"),
    "2": ("meta-llama/llama-3.1-8b-instruct:free",  "Llama 3.1 8B (free)"),
    "3": ("mistralai/mistral-7b-instruct:free",      "Mistral 7B (free)"),
    "4": ("google/gemma-3-27b-it:free",              "Gemma 3 27B (free)"),
    "5": ("deepseek/deepseek-r1:free",               "DeepSeek R1 (free)"),
    "6": ("openai/gpt-4o-mini",                      "GPT-4o Mini"),
    "7": ("nex-agi/nex-n2-pro:free",             "nex-agi/nex-n2-pro:free"),
    "8": ("google/gemini-2.0-flash-exp:free",        "Gemini 2.0 Flash (free)"),
}

# ─── VOICEVOX ─────────────────────────────────────────────────────────────────

VOICEVOX_URL     = "http://127.0.0.1:50021"
VOICEVOX_SPEAKER = 3       # 3 = Zundamon Normal
VOICE_ENABLED    = True  # toggle via /voice

# ─── Persona ──────────────────────────────────────────────────────────────────

PERSONA_NAMA   = "My AI"
PERSONA_PROMPT = (
    "Kamu adalah My AI, asisten pribadi yang serba bisa. Kemampuanmu meliputi:\n"
    "- Asisten umum: menjawab pertanyaan, menulis, merangkum, brainstorming.\n"
    "- Developer: membaca, menulis, mengedit, dan menjelaskan kode di berbagai bahasa.\n"
    "- File manager: mengorganisasi, mencari, dan memodifikasi file dan folder.\n"
    "- Researcher: mencari informasi terkini di internet lalu merangkumnya.\n\n"
    "Gunakan tools yang tersedia secara proaktif tanpa perlu diminta eksplisit. "
    "Selalu jelaskan dengan singkat apa yang sedang kamu lakukan sebelum mengeksekusi tool. "
    "Untuk tugas besar, pecah menjadi langkah-langkah kecil dan laporkan progresnya.\n\n"
    "Gaya respons:\n"
    "- Untuk sapaan kasual (hai, halo, pagi, makasih, dll) atau basa-basi sehari-hari, "
    "balas SANGAT SINGKAT (1 kalimat pendek atau beberapa kata saja), santai, "
    "tanpa basa-basi tambahan dan tanpa tools, dalam Bahasa Indonesia.\n"
    "- KHUSUS jika pesan user HANYA berupa kata 'test', 'tes', 'testing', 'cek', atau 'ping' "
    "(tanpa konten lain), balas dengan SATU kalimat SANGAT PENDEK dalam BAHASA JEPANG saja "
    "(contoh: 'テスト成功です！', 'はい、聞こえています！', 'マイクのテスト中だよ！'). "
    "Tanpa terjemahan, tanpa romaji, tanpa penjelasan tambahan, tanpa tools.\n"
    "- Untuk pertanyaan/tugas yang butuh penjelasan, kerja teknis, atau analisis, "
    "balas selengkap dan sejelas yang dibutuhkan seperti biasa dalam Bahasa Indonesia."
)

# ─── Warna terminal ───────────────────────────────────────────────────────────

R       = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
MAGENTA = "\033[95m"
WHITE   = "\033[97m"

def c(text, color): return f"{color}{text}{R}"
def yn(prompt): return input(f"{YELLOW}⚠ {prompt} [y/N]: {R}").strip().lower() == "y"

# ─── Whitelist direktori ──────────────────────────────────────────────────────

ALLOWED_ROOT = Path(".").resolve()

def set_allowed_root(path: Path):
    global ALLOWED_ROOT
    ALLOWED_ROOT = path.resolve()

def check_path(path: str) -> tuple[Path, str]:
    """Resolve path & pastikan berada di dalam ALLOWED_ROOT.
    Return (resolved_path, error_msg). error_msg kosong jika aman."""
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = ALLOWED_ROOT / p
    p = p.resolve()
    try:
        p.relative_to(ALLOWED_ROOT)
    except ValueError:
        return p, f"❌ Akses ditolak: '{p}' berada di luar direktori yang diizinkan ({ALLOWED_ROOT})"
    return p, ""

# ─── Config file (.env) ───────────────────────────────────────────────────────

def load_config() -> dict:
    return {
        "api_key":       os.environ.get("OPENROUTER_API_KEY", ""),
        "provider":      os.environ.get("MY_AI_PROVIDER", ""),
        "default_model": os.environ.get("MY_AI_DEFAULT_MODEL", ""),
    }

def save_config(data: dict):
    env_file = Path(__file__).parent / ".env"
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines() if env_file.exists() else []
        for key, val in data.items():
            env_key = {
                "api_key":       "OPENROUTER_API_KEY",
                "provider":      "MY_AI_PROVIDER",
                "default_model": "MY_AI_DEFAULT_MODEL",
            }.get(key, key.upper())
            found = False
            for i, line in enumerate(lines):
                if line.startswith(f"{env_key}="):
                    lines[i] = f"{env_key}={val}"
                    found = True
                    break
            if not found:
                lines.append(f"{env_key}={val}")
        env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass
