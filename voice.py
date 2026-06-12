"""
voice.py — VOICEVOX Text-to-Speech.
Membutuhkan aplikasi VOICEVOX berjalan di http://127.0.0.1:50021
https://voicevox.hiroshiba.jp/
"""

import re, sys, subprocess
from pathlib import Path

import requests

import config
from config import DIM, R

_TEMP_VOICE_FILE = Path(__file__).parent / "history" / "_voice_tmp.wav"


def voicevox_check() -> bool:
    """Cek apakah server VOICEVOX berjalan."""
    try:
        r = requests.get(f"{config.VOICEVOX_URL}/version", timeout=3)
        return r.ok
    except Exception:
        return False


def voicevox_speakers() -> list:
    """Ambil daftar speaker/karakter yang tersedia."""
    try:
        r = requests.get(f"{config.VOICEVOX_URL}/speakers", timeout=5)
        if not r.ok:
            return []
        out = []
        for sp in r.json():
            for style in sp.get("styles", []):
                out.append((style["id"], f"{sp['name']} - {style['name']}"))
        return out
    except Exception:
        return []


def _clean_text_for_tts(text: str) -> str:
    """Buang markdown/simbol yang tidak enak didengar TTS."""
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`([^`]*)`', r'\1', text)
    text = re.sub(r'[*_#>~\[\]()]', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\n+', '. ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _play_audio_file(path: Path):
    """Putar file audio secara cross-platform (blocking)."""
    system = sys.platform
    try:
        if system.startswith("win"):
            import winsound
            winsound.PlaySound(str(path), winsound.SND_FILENAME)
        elif system == "darwin":
            subprocess.run(["afplay", str(path)], check=False)
        else:
            for player in (["paplay"], ["aplay"], ["ffplay", "-nodisp", "-autoexit"]):
                if subprocess.run(["which", player[0]], capture_output=True).returncode == 0:
                    subprocess.run(player + [str(path)], check=False,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
    except Exception as e:
        print(f"  {DIM}(gagal memutar audio: {e}){R}")


def speak_text(text: str) -> str:
    """Sintesis teks via VOICEVOX, mainkan audio lokal, dan kirim ke avatar browser
    (jika avatar server berjalan) untuk lip-sync. Return pesan status."""
    text = _clean_text_for_tts(text)
    if not text:
        return "ℹ️ Tidak ada teks untuk dibacakan."

    try:
        q = requests.post(
            f"{config.VOICEVOX_URL}/audio_query",
            params={"text": text, "speaker": config.VOICEVOX_SPEAKER},
            timeout=15,
        )
        q.raise_for_status()

        s = requests.post(
            f"{config.VOICEVOX_URL}/synthesis",
            params={"speaker": config.VOICEVOX_SPEAKER},
            json=q.json(),
            timeout=30,
        )
        s.raise_for_status()

        _TEMP_VOICE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _TEMP_VOICE_FILE.write_bytes(s.content)

        # Kirim ke avatar browser (jika ada) untuk lip-sync — tidak blocking jika gagal
        try:
            import avatar_server
            if avatar_server.is_running():
                avatar_server.broadcast_audio(s.content)
        except Exception:
            pass

        _play_audio_file(_TEMP_VOICE_FILE)
        return "✅ Suara diputar."
    except requests.exceptions.ConnectionError:
        return ("❌ Tidak bisa terhubung ke VOICEVOX. "
                "Pastikan aplikasi VOICEVOX terbuka (server di :50021).")
    except Exception as e:
        return f"❌ TTS gagal: {e}"
