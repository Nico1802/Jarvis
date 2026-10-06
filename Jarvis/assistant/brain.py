"""J.A.R.V.I.S.' Gehirn: LM Studio (mit Auto-Start) + lernendes Gedaechtnis."""

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import requests

import config
from assistant import gedaechtnis

USERNAME = os.environ.get("USERNAME", "Nutzer")
HOME = Path.home().as_posix()
CWD = Path.cwd().as_posix()

SYSTEM_PROMPT = f"""Du bist J.A.R.V.I.S., der persoenliche Assistent von {USERNAME} auf einem Windows-PC.
Du kennst den Nutzer gut, lernst staendig dazu und steuerst seinen PC.

Antworte AUSSCHLIESSLICH mit genau einem JSON-Objekt. Kein Markdown, kein Codeblock, kein Zusatztext.

Format ohne Aktion:
{{"say": "<kurze Antwort auf Deutsch>", "action": null, "merken": null}}

Format mit Aktion:
{{"say": "", "action": {{"name": "<aktionsname>", "args": {{}}}}, "merken": null}}

Lernen (optional): Verraet dir der Nutzer etwas ueber sich, fuelle "merken":
{{"say": "Gemerkt!", "action": null, "merken": {{"kategorie": "Essen", "info": "liebt Pizza"}}}}

Verfuegbare Aktionen:
- open_app - Programm starten. args: {{"name": "notepad"}} (Name, Suchbegriff oder voller Pfad - auch installierte Apps werden automatisch gefunden)
- search_apps - installierte Apps durchsuchen. args: {{"query": "rechner"}} (leer = Liste zeigen)
- search_files - Dateien auf dem PC nach Dateinamen suchen. args: {{"query": "lebenslauf", "ordner": ""}}
- search_content - INHALTE von Textdateien durchsuchen. args: {{"query": "passwort", "ordner": ""}}
- run_command - Windows-Befehl (cmd) ausfuehren. args: {{"command": "ipconfig"}}
- open_website - Website oeffnen. args: {{"url": "https://www.youtube.com"}}
- web_search - Google-Suche starten. args: {{"query": "wetter berlin morgen"}}
- type_text - Text ins aktive Fenster einfuegen. args: {{"text": "Hallo Welt"}}
- clipboard_copy - Text in die Zwischenablage kopieren. args: {{"text": "Hallo"}}
- screenshot - Bildschirmfoto im Bilder-Ordner speichern. args: {{}}
- write_file - Datei erstellen oder ueberschreiben. args: {{"path": "{HOME}/Desktop/notiz.txt", "content": "..."}}
- read_file - Datei lesen. args: {{"path": "{HOME}/Desktop/notiz.txt"}}
- list_dir - Ordnerinhalt auflisten. args: {{"path": "{HOME}/Downloads"}}
- set_volume - Lautstaerke 0-100 setzen. args: {{"level": 30}}
- get_volume - aktuelle Lautstaerke abfragen. args: {{}}
- spotify - Spotify steuern. args: {{"befehl": "start", "suchbegriff": ""}} - befehl: start, play, pause, next, prev, stop, lieblingssongs, spiele oder suche; suchbegriff nur bei spiele/suche
- media_key - Medien steuern. args: {{"key": "play"}} (play, pause, next, prev, stop)
- lock_pc - PC sperren. args: {{}}
- sleep_pc - PC in den Ruhezustand versetzen. args: {{}}
- mein_profil - zeigen, was du ueber den Nutzer weisst. args: {{"kategorie": ""}} (optional filtern)
- vergiss - Erinnerungen loeschen. args: {{"suchbegriff": "...", "alles": false}}

Regeln:
- say: kurz (maximal 1-2 Saetze), persoenlich, Deutsch, zum Vorlesen geeignet.
- LERNE staendig ueber den Nutzer: Name, Geschmaecker, Lieblinge, Gewohnheiten,
  Termine, Familie, Ziele - bei jeder neuen Info setze "merken".
- Nutze dein gespeichertes Wissen (unten), um persoenlich zu antworten.
- Sucht der Nutzer etwas AUF DEM PC (Apps, Dateien, Infos in Dateien), nutze search_apps,
  search_files oder search_content und fasse die Ergebnisse kurz zusammen.
- Musik/Spotify: 'oeffne spotify' -> open_app mit "spotify". 'spiel meine Lieblingssongs ab'
  -> spotify mit befehl "lieblingssongs". 'spiel <Song/Kuenstler> ab' -> spotify befehl
  "spiele" mit suchbegriff. Nur play/pause/naechstes Lied -> spotify befehl "play"/"pause"/"next".
- Keine Aktion noetig (Frage, Smalltalk)? Dann action auf null setzen.
- Fehlen Angaben (welcher Text, welcher Pfad, welche Lautstaerke)? Rueckfrage stellen statt raten.
- Niemals destruktive Dinge tun (Dateien loeschen, System veraendern), ausser mit klarer Anweisung.
- In Pfaden und Befehlen nur normale Schraegstriche / verwenden und niemals Backslashes schreiben,
  damit das JSON gueltig bleibt.
- Wichtige Ordner: Home {HOME} | Desktop {HOME}/Desktop | Bilder {HOME}/Pictures | Dokumente {HOME}/Documents
- Arbeitsordner: {CWD}
"""


def _system_prompt():
    basis = SYSTEM_PROMPT
    wissen = gedaechtnis.als_text()
    if wissen:
        basis += "\n\n" + wissen
    return basis


# Repariert JSON mit einzelnen Backslashes (z. B. "C:\\Users" statt "C:/Users"):
# jeder Backslash, der nicht schon doppelt ist, wird verdoppelt
_BACKSLASH_FIX = re.compile(r'(?<!\\)\\(?!\\)')


def lm_studio_starten(melden=print):
    """Startet den LM-Studio-Server automatisch, falls er nicht laeuft."""
    try:
        if requests.get(config.LMSTUDIO_MODELS_URL, timeout=2).status_code == 200:
            return True  # laeuft schon
    except Exception:
        pass

    melden("⚙️ Starte das Denk-System (LM Studio) im Hintergrund …")
    kandidaten = [
        shutil.which("lms"),
        os.path.expanduser(r"~\.lmstudio\lms.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\LM Studio\resources\app\.webpack\cli\lms.exe"),
        r"C:\Program Files\LM Studio\resources\app\.webpack\cli\lms.exe",
    ]
    for kandidat in kandidaten:
        if not kandidat:
            continue
        if kandidat == "lms" or os.path.exists(kandidat):
            try:
                subprocess.run([kandidat, "server", "start"],
                               capture_output=True, timeout=90)
                break
            except Exception:
                continue

    for _ in range(40):  # bis zu ~80 Sekunden warten
        try:
            if requests.get(config.LMSTUDIO_MODELS_URL, timeout=2).status_code == 200:
                melden("✅ Denk-System ist online.")
                return True
        except Exception:
            pass
        time.sleep(2)
    melden("⚠️ LM Studio konnte nicht automatisch gestartet werden "
           "(lms-CLI nicht gefunden?). Starte es einmal manuell.")
    return False


def _parse(raw):
    """Extrahiert (say, action) aus der Modellantwort und lernt daneben."""
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    text = re.sub(r"^```(?:json)?\s*", "", text).strip()
    text = re.sub(r"\s*```$", "", text).strip()
    start, ende = text.find("{"), text.rfind("}")
    if start == -1 or ende <= start:
        return text.strip(), None
    kandidat = text[start:ende + 1]
    daten = None
    for versuch in (kandidat, _BACKSLASH_FIX.sub(lambda m: "\\\\", kandidat)):
        try:
            daten = json.loads(versuch)
            break
        except json.JSONDecodeError:
            continue
    if not isinstance(daten, dict):
        return kandidat.strip(), None
    say = str(daten.get("say") or "").strip()

    # Lernen: "merken" dauerhaft speichern
    merken = daten.get("merken")
    if isinstance(merken, dict) and str(merken.get("info", "")).strip():
        try:
            gedaechtnis.merken(merken.get("kategorie") or "allgemein",
                               merken.get("info"))
        except Exception:
            pass

    action = daten.get("action")
    if isinstance(action, dict) and isinstance(action.get("name"), str):
        return say, action
    return say, None


class Brain:
    """Gespraechs-Gedaechtnis + Verbindung zum Modell (lokal, Auto-Start, optional Cloud)."""

    def __init__(self):
        self.session = requests.Session()
        self._model = config.LMSTUDIO_MODEL or None
        self._startversuch = False
        self.status_melden = None  # Callback der Oberflaeche (optional)
        self.history = [{"role": "system", "content": _system_prompt()}]
        self._verlauf_laden()

    # ---------- Hilfsfunktionen ----------

    def _melde(self, text):
        if text:
            if self.status_melden:
                self.status_melden(text)
            else:
                print(text)

    def _system_aktualisieren(self):
        self.history[0] = {"role": "system", "content": _system_prompt()}

    @property
    def _verlauf_datei(self):
        return Path(__file__).resolve().parent.parent / "gespraech.json"

    def _verlauf_laden(self):
        """Gespraech aus der letzten Sitzung wiederherstellen."""
        try:
            daten = json.loads(self._verlauf_datei.read_text(encoding="utf-8"))
            if isinstance(daten, list) and daten:
                alte = [m for m in daten
                        if isinstance(m, dict) and m.get("role") in ("user", "assistant")]
                self.history = [self.history[0]] + alte[-config.MAX_HISTORY:]
        except Exception:
            pass

    def _verlauf_speichern(self):
        try:
            daten = [m for m in self.history if m.get("role") != "system"]
            self._verlauf_datei.write_text(
                json.dumps(daten[-config.MAX_HISTORY:], ensure_ascii=False, indent=1),
                encoding="utf-8")
        except Exception:
            pass

    def _modell_id(self):
        """Findet automatisch die Modell-ID des geladenen Modells (LM Studio)."""
        if self._model:
            return self._model
        try:
            daten = self.session.get(config.LMSTUDIO_MODELS_URL, timeout=5).json()
            ids = [m.get("id") for m in daten.get("data", []) if m.get("id")]
            if ids:
                self._model = ids[0]
        except Exception:
            pass
        return self._model or "local-model"

    def _frage_modell(self, url, model, headers=None, timeout=240):
        payload = {
            "model": model,
            "messages": self.history,
            "temperature": 0.2,
            "max_tokens": 1200,
            "stream": False,
        }
        return self.session.post(url, json=payload, headers=headers, timeout=timeout)

    def _lokal_anfragen(self):
        """LM Studio fragen. Liefert (inhalt, fehlermeldung)."""
        try:
            antwort = self._frage_modell(config.LMSTUDIO_URL, self._modell_id())
        except requests.RequestException:
            return None, None  # nicht erreichbar
        if antwort.status_code == 200:
            try:
                return antwort.json()["choices"][0]["message"]["content"], None
            except (KeyError, IndexError, ValueError):
                return None, "LM Studio lieferte eine ungueltige Antwort."
        return None, f"LM Studio meldet {antwort.status_code}."

    # ---------- Hauptfunktion ----------

    def ask(self, text):
        """Sendet eine Nachricht, lernt daneben und liefert (say, action)."""
        self.history.append({"role": "user", "content": text})
        self._system_aktualisieren()
        self._trim()

        inhalt = None
        quelle = None
        fehlerdetail = ""

        # 1) LM Studio (mit Auto-Start, falls aus)
        inhalt, lokal_fehler = self._lokal_anfragen()
        if inhalt is None and config.LMSTUDIO_AUTO_START and not self._startversuch:
            self._startversuch = True
            if lm_studio_starten(self._melde):
                inhalt, lokal_fehler = self._lokal_anfragen()
                if inhalt is not None:
                    self._startversuch = False  # spaeter erneut versuchen koennen
        if inhalt is not None:
            quelle = "LM Studio (lokal)"
        elif lokal_fehler:
            fehlerdetail = lokal_fehler

        # 2) Cloud-Fallback (optional, OpenAI-kompatible API)
        if inhalt is None and config.CLOUD_API_KEY:
            try:
                url = config.CLOUD_BASE_URL.rstrip("/") + "/chat/completions"
                kopf = {"Authorization": f"Bearer {config.CLOUD_API_KEY}"}
                antwort = self._posten(url, config.CLOUD_MODEL, headers=kopf,
                                       timeout=getattr(config, "CLOUD_TIMEOUT", 120))
                if antwort.status_code == 200:
                    inhalt = antwort.json()["choices"][0]["message"]["content"]
                    quelle = "Cloud-API"
                else:
                    fehlerdetail = (f"Cloud meldet {antwort.status_code}: "
                                    f"{antwort.text[:120]}")
            except requests.RequestException:
                fehlerdetail = fehlerdetail or "Cloud nicht erreichbar."
            except (KeyError, IndexError, ValueError):
                fehlerdetail = fehlerdetail or "Cloud lieferte eine ungueltige Antwort."

        if inhalt is None:
            if config.CLOUD_API_KEY:
                meldung = ("Ich komme gerade nicht an mein Gehirn - weder LM Studio "
                           "noch die Cloud-API. " + fehlerdetail)
            else:
                meldung = ("Ich erreiche LM Studio nicht und konnte es auch nicht "
                           "selbst starten. " + fehlerdetail)
            return (meldung, None)

        say, action = _parse(inhalt)
        self.history.append({"role": "assistant", "content": inhalt})
        self._trim()
        self._verlauf_speichern()
        print(f"🧠 Gehirn: {quelle}")
        return say, action

    def _trim(self):
        if len(self.history) > config.MAX_HISTORY + 1:
            self.history = [self.history[0]] + self.history[-config.MAX_HISTORY:]
