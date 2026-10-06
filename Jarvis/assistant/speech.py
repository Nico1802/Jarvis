"""Sprachschnittstelle: Mikrofon rein (sounddevice + Google), Antworten raus (ElevenLabs)."""

import speech_recognition as sr

import config
from assistant.audio import MicError, MicRecorder
from assistant.tts import Sprecher


def _konsole_status(name, wert=None):
    if name == "kalibriere":
        print("🎙️  Prüfe Umgebungsgeräusch ...")
    elif name == "hoere":
        print("🎙️  Höre zu ... (sag 'Jarvis' und danach deinen Befehl)")
    elif name == "schwelle":
        print(f"   (Mikrofon-Schwelle: {wert:.0f})")


class Speech:
    def __init__(self):
        self.recorder = MicRecorder()
        self.erkennung = sr.Recognizer()
        self.sprecher = Sprecher()

    def listen(self, on_state=None, stop_event=None):
        """Nimmt eine Aeusserung auf; liefert Text in Kleinbuchstaben oder None."""
        if on_state is None:
            on_state = _konsole_status
        try:
            aufnahme = self.recorder.record(
                on_state=on_state,
                stop_event=stop_event,
                wait_seconds=config.LISTEN_TIMEOUT,
                max_seconds=config.PHRASE_TIME_LIMIT,
                silence_seconds=config.MIC_SILENCE_SECONDS,
            )
        except MicError:
            raise
        if aufnahme is None:
            return None
        roh, rate = aufnahme
        audio = sr.AudioData(roh, rate, 2)
        try:
            text = self.erkennung.recognize_google(audio, language=config.LANGUAGE)
        except sr.UnknownValueError:
            return None
        except sr.RequestError:
            print("⚠️ Spracherkennung (Google) nicht erreichbar - Internetverbindung pruefen.")
            return None
        text = text.lower().strip()
        if text:
            print(f"👤 Du: {text}")
        return text

    def say(self, text):
        """Gibt Text im Terminal aus und liest ihn laut vor."""
        print(f"🤖 Jarvis: {text}")
        if not config.SPEAK_ENABLED:
            return
        quelle = self.sprecher.sprich(text)
        if quelle != "keine":
            print(f"🔊 Sprachausgabe: {quelle}")
