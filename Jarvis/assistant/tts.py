"""Sprachausgabe mit Fallback-Kette:

1. ElevenLabs  - naturgetreue Stimme (API-Schluessel in config.py)
2. Edge-TTS    - kostenlose natuerliche Microsoft-Stimme (kein Schluessel noetig)
3. SAPI        - alte Windows-Stimme (bei manchen Windows-Updates kaputt)

sprich() gibt den Text als Sprache aus und liefert zurueck, welche Quelle
genutzt wurde ("ElevenLabs", "Edge" oder "SAPI").
"""

import time

import numpy as np
import requests
import sounddevice as sd

import config


class Sprecher:
    def __init__(self):
        self._elfehler = 0  # ElevenLabs nach 2 Fehlern automatisch deaktivieren

    # ---------------- 1) ElevenLabs ----------------

    def _elevenlabs(self, text):
        url = (f"https://api.elevenlabs.io/v1/text-to-speech/"
               f"{config.ELEVENLABS_VOICE_ID}?output_format=pcm_44100")
        antwort = requests.post(
            url,
            headers={
                "xi-api-key": config.ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
            json={"text": text, "model_id": config.ELEVENLABS_MODEL},
            timeout=60,
        )
        if antwort.status_code != 200:
            raise RuntimeError(f"HTTP {antwort.status_code}: {antwort.text[:100]}")
        if not antwort.content:
            raise RuntimeError("Leere Antwort erhalten.")
        audio = np.frombuffer(antwort.content, dtype=np.int16)
        sd.play(audio, 44100)
        sd.wait()

    # ---------------- 2) Edge-TTS (kostenlos, natuerlich) ----------------

    def _edge_holen(self, text):
        import asyncio
        import edge_tts
        async def _laden():
            verbindung = edge_tts.Communicate(text, config.EDGE_TTS_VOICE)
            mp3 = bytearray()
            async for teil in verbindung.stream():
                if teil["type"] == "audio":
                    mp3.extend(teil["data"])
            return bytes(mp3)
        return asyncio.run(_laden())

    @staticmethod
    def _spiele_mp3(mp3):
        import miniaudio
        dekodiert = miniaudio.decode(mp3)
        arr = np.array(dekodiert.samples, dtype=np.int16)
        if dekodiert.nchannels > 1:
            arr = arr.reshape(-1, dekodiert.nchannels).mean(axis=1).astype(np.int16)
        sd.play(arr, dekodiert.sample_rate)
        sd.wait()

    # ---------------- 3) SAPI (alte Windows-Stimme) ----------------

    @staticmethod
    def _sapi(text):
        try:
            import pythoncom
            pythoncom.CoInitialize()
            import win32com.client
            stimme = win32com.client.Dispatch("SAPI.SpVoice")
        except Exception:
            from comtypes.client import CreateObject
            stimme = CreateObject("SAPI.SpVoice")
        stimme.Speak(str(text), 0)

    # ---------------- Oeffentliche Schnittstelle ----------------

    def sprich(self, text):
        """Spielt den Text als Sprache ab. Liefert die genutzte Quelle."""
        text = str(text).strip()
        if not text:
            return "keine"

        # 1) ElevenLabs
        if (config.ELEVENLABS_ENABLED and config.ELEVENLABS_API_KEY
                and self._elfehler < 2):
            try:
                self._elevenlabs(text)
                self._elfehler = 0
                return "ElevenLabs"
            except Exception as exc:
                self._elfehler += 1
                print(f"⚠️ ElevenLabs nicht verfügbar ({exc})"
                      + (" - ElevenLabs wird fuer diese Sitzung deaktiviert."
                         if self._elfehler >= 2 else ""))

        # 2) Edge-TTS
        mp3 = b""
        if getattr(config, "EDGE_TTS_ENABLED", True):
            try:
                mp3 = self._edge_holen(text)
            except Exception as exc:
                print(f"⚠️ Edge-TTS nicht verfügbar ({exc})")
        if mp3:
            try:
                self._spiele_mp3(mp3)
                return "Edge"
            except Exception as exc:
                print(f"⚠️ MP3-Wiedergabe fehlgeschlagen ({exc})")

        # 3) SAPI (letzter Versuch)
        try:
            self._sapi(text)
            return "SAPI"
        except Exception as exc:
            print(f"⚠️ Auch die Windows-Stimme funktioniert nicht: {exc}")
            return "keine (nur Text)"
