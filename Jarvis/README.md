# 🤖 JARVIS – dein persönlicher KI-Assistent (Windows)

Jarvis hört dich, versteht dich (auf Deutsch) und **steuert deinen PC**: Programme öffnen,
Befehle ausführen, Dateien schreiben, Screenshots machen, Lautstärke regeln und vieles mehr.
Die Antworten spricht er vor. Das "Gehirn" läuft **lokal** in LM Studio – privat und kostenlos.

## Was Jarvis kann

| Sag z. B. | Was passiert |
|---|---|
| „Jarvis, öffne Notepad" | Startet ein Programm – auch Store-Apps und installierte Programme werden automatisch gefunden |
| „Jarvis, welche Apps habe ich installiert?" / „such die App Steam" | Durchsucht alle installierten Apps (Startmenü + Store) |
| „Jarvis, such auf meinem PC eine Datei mit 'Lebenslauf' im Namen" | Durchsucht Desktop, Dokumente, Downloads, Bilder u. v. m. |
| „Jarvis, in welcher Datei steht mein WLAN-Passwort?" | Durchsucht die **Inhalte** von Textdateien auf dem PC |
| „Jarvis, wie ist das Wetter in Berlin?" | Öffnet die Google-Suche |
| „Jarvis, öffne youtube.com" | Öffnet eine Website |
| „Jarvis, mach einen Screenshot" | Speichert ein Bild in deinem Bilder-Ordner |
| „Jarvis, schreib 'Einkaufen: Milch' in eine Notiz auf dem Desktop" | Erstellt/beschreibt Dateien |
| „Jarvis, wie viele Dateien sind in Downloads?" | Liest Ordner aus, beantwortet Fragen dazu |
| „Jarvis, tippe Hallo Welt" | Fügt Text ins aktive Fenster ein |
| „Jarvis, öffne Spotify" | Findet & startet Spotify |
| „Jarvis, spiel meine Lieblingssongs ab" | Öffnet Spotify → Liked Songs → startet die Wiedergabe |
| „Jarvis, spiel 'Blinding Lights' ab" | Sucht den Song in Spotify und spielt ihn ab |
| „Jarvis, Lautstärke auf 30" / „nächstes Lied" / „pausiere" | Systemsteuerung |
| „Jarvis, zeig mir alle laufenden Prozesse" | Führt Windows-Befehle aus (Rückfrage bei Riskantem) |
| Fragen & Smalltalk | „Jarvis, erzähl mir einen Witz" |

## So funktioniert es

```
 🎙️ Mikrofon → Spracherkennung (Google, kostenlos) → LM Studio (lokal, entscheidet)
     → assistant/actions.py steuert deinen PC → 🔊 Antwort wird vorgelesen
```

- **Gehirn**: LM Studio läuft lokal auf deinem PC – privat und kostenlos.
- **Stimme**: Jarvis antwortet mit einer naturgetreuen **ElevenLabs-Stimme** (API-Schlüssel in
  `config.py`); bei Fehlern oder leeren Credits springt automatisch die Windows-Stimme ein.
- **Spracherkennung**: nutzt Googles kostenlosen Dienst → dafür wird **Internet** benötigt.
- **Oberfläche**: das Jarvis-Fenster zeigt Status, Verlauf und nimmt auch getippte Befehle.

## Voraussetzungen

1. **Python 3.10 oder neuer** → [python.org/downloads](https://www.python.org/downloads/)
   („Add Python to PATH" anhaken!)
2. **VS Code** mit der Erweiterung **Python**
3. **LM Studio** + ein geladenes Modell

## Einrichtung (einmalig, ca. 5 Minuten)

Ordner in VS Code öffnen (**Datei → Ordner öffnen**), Terminal öffnen
(**Terminal → Neues Terminal**) und ausführen:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

> Tipp: Wenn VS Code fragt, welchen Interpreter du nutzen willst → **.venv** auswählen.

### LM Studio vorbereiten (vor jedem Start)

1. LM Studio öffnen
2. Ein Modell laden – Empfehlungen:
   - **Qwen2.5-7B-Instruct** (gut, ~8 GB RAM)
   - **Llama-3.1-8B-Instruct**
   - Schwächerer PC: **Qwen2.5-3B-Instruct** oder **Llama-3.2-3B-Instruct**
3. Links auf **Developer** → oben **Start Server** (Port 1234)

Jarvis findet das geladene Modell **automatisch**. Mehrere Modelle gleichzeitig?
Dann in [config.py](config.py) bei `LMSTUDIO_MODEL` die gewünschte ID eintragen.

## Prüfen & Starten

```powershell
python check_setup.py   # prüft Bibliotheken, Mikrofon, TTS und LM Studio
python main.py          # das Jarvis-Fenster öffnet sich
```

Weitere Startarten: `python main.py --voice` (nur Konsole mit Mikrofon),
`python main.py --text` (nur Tastatur, zum Testen). In VS Code reicht **F5**
(dort kannst du den Modus wählen), oder Doppelklick auf **start_assistent.bat** –
bzw. auf **„Assistent starten.bat" auf deinem Desktop**.

## Das Jarvis-Fenster (HUD)

Im Zentrum rotiert ein **animierter HUD-Ring**, der die Farbe wechselt:
🔵 cyan = bereit · 🟠 amber = hört zu · 🟢 grün = denkt nach · 🟣 violett = spricht · 🔴 rot = Fehler.

- **Schnellaktionen** (laufen sofort, ohne Sprachmodell): 📸 Screenshot · 🕒 Uhrzeit ·
  🔋 Akku · ▶️ Musik · 🌐 YouTube
- **🔊 Lautstärkeregler** steuert direkt die Systemlautstärke
- **Status-LEDs**: LM Studio online/offline und Mikrofonstatus, dazu eine Uhr
- **Sprache**: sag **„Jarvis"** und danach deinen Befehl. Nur „Jarvis" → er fragt „Ja?".
  Der Knopf **„👁 Immer zuhören"** aktiviert das Wake-Wort dauerhaft; **„🎙️ Sprechen"**
  hört einmal sofort zu (ohne Wake-Wort).
- **Tastatur**: Befehl tippen + Enter; mit **↑ / ↓** kommst du an frühere Befehle.
- **Beenden**: „Jarvis, beenden" sagen/tippen oder das Fenster schließen.

## ☁️ Cloud-Gehirn (optional)

Jarvis denkt **lokal** mit LM Studio. Optional kann er bei ausgeschaltetem LM Studio auf eine
OpenAI-kompatible Cloud-API ausweichen – dafür in `config.py` einen LLM-Schlüssel bei
`CLOUD_API_KEY` eintragen (z. B. von Together, Groq, OpenRouter oder DeepSeek) plus passender
`CLOUD_BASE_URL` und `CLOUD_MODEL`. Die LED oben rechts zeigt: `● LM ONLINE` /
`☁ CLOUD-MODUS` / `● LM OFFLINE`.

## 🔊 Sprachausgabe mit ElevenLabs

Jarvis' Antworten werden mit **ElevenLabs** gesprochen (sehr naturgetreu, versteht Deutsch).
In `config.py` anpassbar:

```python
ELEVENLABS_API_KEY   = "dein-elevenlabs-schluessel"
ELEVENLABS_VOICE_ID  = "pNInz6obpgDQGcFmaJgB"   # "Adam" - tief, assistenten-artig
ELEVENLABS_MODEL     = "eleven_flash_v2_5"       # schnell & mehrsprachig
ELEVENLABS_ENABLED   = True                      # False = nur Windows-Stimme
```

- Andere Stimmen: die ID findest du in deinem ElevenLabs-Dashboard unter **Voices**.
- Sind die Credits aufgebraucht oder offline, springt **automatisch die Windows-Stimme** ein.

> ⚠️ Behandle API-Schlüssel wie Passwörter: nicht weitergeben, nicht öffentlich posten.

## 🔒 Sicherheit

Jarvis hat **echte** Kontrolle über deinen PC. Dafür gibt es Schutz:

- Riskante Befehle (Löschen, Installationen, …) werden **nur nach Rückfrage** ausgeführt –
  ein Ja/Nein-Fenster erscheint (bzw. Jarvis fragt im Sprachmodus „Ja oder nein?").
- Ganz gefährliche Befehle (Formatieren, Registry-Änderungen, `shutdown`, …) sind in
  [assistant/safety.py](assistant/safety.py) **komplett blockiert**.
- Bestehende Dateien werden nur mit deiner Bestätigung überschrieben.
- `CONFIRM_RISKY` in `config.py` auf `False` setzen = ohne Rückfragen (nicht empfohlen).

## Selbst erweitern

Neue Fähigkeit (z. B. E-Mails, Erinnerungen, Wetter):

1. Neue Funktion in [assistant/actions.py](assistant/actions.py) schreiben –
   sie gibt `(erfolg: bool, nachricht: str)` zurück.
2. In das `ACTIONS`-Verzeichnis am Ende der Datei eintragen.
3. Die Aktion im `SYSTEM_PROMPT` in [assistant/brain.py](assistant/brain.py) beschreiben.

Oder frag einfach mich – ich kann Jarvis für dich erweitern.

## Fehlerbehebung

| Problem | Lösung |
|---|---|
| Jarvis versteht dich nicht | Konsole zeigt die **Mikrofon-Schwelle** (z. B. „Schwelle: 280"). Bei viel Umgebungsgeräusch `MIC_THRESHOLD` in `config.py` erhöhen (z. B. 600), bei leisem Mikrofon senken (z. B. 120). Mikrofon in Windows-Einstellungen als Standard setzen |
| „Mikrofon konnte nicht geöffnet werden" | Läuft Discord/Teams/OBS mit dem Mikrofon? Anderes Gerät in `config.py` bei `MIC_DEVICE` eintragen (Name) |
| „Ich erreiche LM Studio nicht" | LM Studio → **Developer** → **Start Server**. Anderer Port? → `LMSTUDIO_URL` in `config.py` anpassen |
| Antwortet wirres Zeug | Anderes (besseres) Modell laden, z. B. Qwen2.5-7B-Instruct |
| Sprachausgabe klingt englisch | Windows-Einstellungen → Zeit & Sprache → Sprache → Deutsch (Sprachpaket) installieren |
| Spracherkennung geht nicht | Internetverbindung prüfen (Google-Dienst); Test mit `python check_setup.py` |

## Ausbau-Ideen

- 🗣️ Spracherkennung komplett offline mit `faster-whisper`
- 🌙 Offline-Wake-Wort mit `openWakeWord`
- ⏰ Erinnerungen & Timer, 🌦️ Wetter-API, 📧 E-Mails, 🖱️ Maussteuerung
