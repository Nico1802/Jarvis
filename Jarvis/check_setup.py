"""Prüft, ob alles für Jarvis bereit ist:  python check_setup.py"""

import importlib
import sys

import config

PIP_NAMEN = {
    "speech_recognition": "SpeechRecognition",
    "sounddevice": "sounddevice",
    "numpy": "numpy",
    "pyttsx3": "pyttsx3",
    "requests": "requests",
    "pyautogui": "PyAutoGUI",
    "pyperclip": "pyperclip",
    "pycaw": "pycaw",
}


def main():
    print("=" * 60)
    print("Setup-Check für JARVIS")
    print("=" * 60)

    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    status = "✅" if sys.version_info >= (3, 9) else "❌ (mindestens Python 3.9 empfohlen)"
    print(f"\nPython-Version: {version}  {status}")

    print("\n1) Python-Bibliotheken:")
    fehlen = []
    for modul, pip_name in PIP_NAMEN.items():
        try:
            importlib.import_module(modul)
            print(f"   ✅ {modul}")
        except Exception:
            print(f"   ❌ {modul}   ->  pip install {pip_name}")
            fehlen.append(pip_name)
    if fehlen:
        print("   -> Alles installieren:  pip install -r requirements.txt")

    print("\n2) LM Studio (das 'Gehirn'):")
    try:
        import requests
        r = requests.get("http://localhost:1234/v1/models", timeout=4)
        modelle = [m.get("id", "?") for m in r.json().get("data", [])]
        print("   ✅ Server erreichbar unter http://localhost:1234")
        print(f"   Geladene Modelle: {', '.join(modelle) or '(keine)'}")
        if not modelle:
            print("   -> In LM Studio ein Modell laden, z. B. 'Qwen2.5-7B-Instruct'.")
    except Exception:
        print("   ⚠️ Server läuft gerade nicht - ABER: Jarvis startet ihn automatisch,")
        print("      sobald du deinen ersten Befehl gibst (Auto-Start in config.py).")

    print("\n   Sprachausgabe über ElevenLabs:")
    try:
        if config.ELEVENLABS_ENABLED and config.ELEVENLABS_API_KEY:
            maske = config.ELEVENLABS_API_KEY[:6] + "..." + config.ELEVENLABS_API_KEY[-4:]
            print("   ✅ aktiv - Jarvis spricht mit einer naturgetreuen ElevenLabs-Stimme")
            print(f"      Modell: {config.ELEVENLABS_MODEL} | Stimme: {config.ELEVENLABS_VOICE_ID}")
            print(f"      Schlüssel: {maske}")
            print("      (Muss mit 'sk_' beginnen! Bei Fehlern: Edge-Fallback-Stimme)")
        else:
            print("   - kein Schlüssel - Jarvis nutzt die Edge-Stimme")
        if getattr(config, "EDGE_TTS_ENABLED", True):
            print(f"   ✅ Fallback aktiv: Edge-Stimme '{config.EDGE_TTS_VOICE}' (kostenlos)")
        if config.CLOUD_API_KEY:
            print(f"   Cloud-LLM zusätzlich aktiv: {config.CLOUD_BASE_URL}")
    except Exception as exc:
        print(f"   ❌ {exc}")

    print("\n3) Sprachausgabe (TTS):")
    try:
        import pyttsx3
        engine = pyttsx3.init()
        stimmen = engine.getProperty("voices")
        deutsche = [
            v.name for v in stimmen
            if "german" in (v.name or "").lower() or "de-de" in (v.id or "").lower()
        ]
        hinweis = ", ".join(deutsche) if deutsche else "keine deutsche Stimme gefunden (nutzt Standard)"
        print(f"   ✅ pyttsx3 funktioniert. Deutsche Stimme: {hinweis}")
    except Exception as exc:
        print(f"   ❌ {exc}")

    print("\n4) Mikrofon (sounddevice):")
    try:
        import sounddevice as sd
        alle = sd.query_devices()
        eingaben = [d for d in alle if d.get("max_input_channels", 0) > 0]
        standard = sd.default.device[0]
        name = alle[standard]["name"] if standard is not None and 0 <= standard < len(alle) else "?"
        print(f"   ✅ {len(eingaben)} Eingabegerät(e). Standard: {name}")
    except Exception as exc:
        print(f"   ❌ {exc}")

    print("\n5) Sprech-Test (Sprache -> Text, braucht Internet):")
    antwort = input("   Jetzt etwas sagen? [Enter = ja, n = überspringen] ").strip().lower()
    if antwort != "n":
        try:
            import speech_recognition as sr
            from assistant.audio import MicRecorder
            print("   🎙️  Sag jetzt etwas, z. B. 'Hallo Jarvis' ...")
            aufnahme = MicRecorder().record(wait_seconds=5, max_seconds=6)
            if aufnahme is None:
                print("   ⚠️ Nichts gehört - näher ans Mikrofon und lauter sprechen.")
            else:
                roh, rate = aufnahme
                text = sr.Recognizer().recognize_google(
                    sr.AudioData(roh, rate, 2), language="de-DE")
                print(f"   ✅ Erkannt: '{text}'")
        except Exception as exc:
            name = type(exc).__name__
            if name == "RequestError":
                print("   ❌ Google-Spracherkennung nicht erreichbar - Internet prüfen.")
            elif name == "UnknownValueError":
                print("   ⚠️ Aufgenommen, aber nicht verstanden. Nochmal probieren.")
            else:
                print(f"   ❌ {exc}")

    print("\nFertig! Wenn alles ✅ ist:  python main.py   (das Jarvis-Fenster öffnet sich)")
    print("Zum Testen ohne Mikrofon:  python main.py --text")


if __name__ == "__main__":
    main()
