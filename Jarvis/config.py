"""Zentrale Einstellungen - hier kannst du alles anpassen."""

# --- Das "Gehirn": LM Studio (laeuft komplett lokal auf deinem PC) ---
# LM Studio oeffnen -> links "Developer" -> oben "Start Server" (Port 1234).
LMSTUDIO_URL = "http://localhost:1234/v1/chat/completions"
LMSTUDIO_MODELS_URL = "http://localhost:1234/v1/models"
# Wenn du MEHRERE Modelle geladen hast und ein bestimmtes nutzen willst,
# trage hier die Modell-ID ein (z. B. "qwen2.5-7b-instruct").
# Leer lassen = Jarvis nimmt automatisch das geladene Modell.
LMSTUDIO_MODEL = ""
# Jarvis startet LM Studio automatisch im Hintergrund, wenn es nicht laeuft.
LMSTUDIO_AUTO_START = True

# --- Cloud-Gehirn (optional): antwortet, wenn LM Studio aus ist ---
# OpenAI-kompatible API (z. B. Together, Groq, OpenRouter, DeepSeek).
# Schluessel hier eintragen; leer = Jarvis denkt nur mit LM Studio.
CLOUD_API_KEY = ""
CLOUD_BASE_URL = "https://api.together.xyz/v1"
CLOUD_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
CLOUD_TIMEOUT = 120

# --- Sprachausgabe: ElevenLabs (sehr naturgetreue Stimme) ---
# Jarvis spricht mit ElevenLabs; bei Fehlern (z. B. Credits alle)
# springt automatisch die lokale Windows-Stimme ein.
ELEVENLABS_API_KEY = "5d21d4bc786d2fad7a6bf93966d5e59c3cfb8b9f886438b8d928ecfcec7beebc"
ELEVENLABS_VOICE_ID = "pNInz6obpgDQGcFmaJgB"   # "Adam" - tief, assistenten-artig
ELEVENLABS_MODEL = "eleven_flash_v2_5"          # schnell & versteht Deutsch
ELEVENLABS_ENABLED = True

# Fallback-Stimme (kostenlos, kein Schluessel noetig) - natuerliche Microsoft-Stimme
EDGE_TTS_ENABLED = True
EDGE_TTS_VOICE = "de-DE-ConradNeural"   # Alternativen: de-DE-KatjaNeural, de-DE-AmalaNeural, ...

# --- Sprache ---
LANGUAGE = "de-DE"      # Sprache der Spracherkennung
WAKE_WORD = "jarvis"    # Aktivierungswort (kleingeschrieben, einfach halten!)
SPEAK_ENABLED = True    # Antworten vorlesen?

# --- Mikrofon (Stille-Erkennung) ---
MIC_DEVICE = None            # None = Standard-Mikrofon von Windows
MIC_SILENCE_SECONDS = 0.9    # so viel Stille beendet die Aufnahme automatisch
MIC_THRESHOLD = 0            # 0 = Schwelle automatisch berechnen; sonst fester Mindestpegel
MIC_THRESHOLD_FACTOR = 2.5   # auto: Schwelle = Umgebungspegel * Faktor
MIC_THRESHOLD_FLOOR = 250.0  # auto: Mindest-Schwelle

# --- Verhalten ---
CONFIRM_RISKY = True    # Bei riskanten Befehlen vorher nachfragen
LISTEN_TIMEOUT = 6      # Sekunden warten, bis du zu sprechen beginnst
PHRASE_TIME_LIMIT = 15  # Maximale Laenge einer Eingabe in Sekunden
MAX_HISTORY = 12        # Behaltene Nachrichten im Gespraechsverlauf

# --- Beenden ---
EXIT_WORDS = {"beenden", "exit", "quit", "tschuess", "tschüss",
              "auf wiedersehen", "gute nacht"}
