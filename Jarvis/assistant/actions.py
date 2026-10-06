"""Hier passiert die echte PC-Steuerung.

Jede Funktion ist eine "Aktion", die die KI per Name aufrufen kann.
Neue Aktion ergaenzen:
    1. Funktion hier schreiben (gibt (erfolg, nachricht) zurueck)
    2. Unten in ACTIONS eintragen
    3. In assistant/brain.py im SYSTEM_PROMPT beschreiben
"""

import inspect
import json
import os
import re
import shutil
import subprocess
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import pyautogui
import pyperclip

pyautogui.FAILSAFE = True


def _text(wert, standard=""):
    return str(wert).strip() if wert is not None else standard


def _bilder_ordner():
    for kandidat in ("~/Pictures", "~/OneDrive/Pictures", "~/OneDrive/Bilder", "~/Bilder"):
        p = Path(kandidat).expanduser()
        if p.exists():
            return p
    return Path.home()


# ---------------- Programme & Web ----------------

_STARTMENUE_ORDNER = [
    Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "Microsoft/Windows/Start Menu/Programs",
    Path(os.environ.get("AppData", "")) / "Microsoft/Windows/Start Menu/Programs",
]
_APP_INDEX = None   # {"Name": pfad_zur_verknuepfung}
_UWP_INDEX = None   # {"Name": appid_von_store_apps}


def _normalisiere(text):
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def _app_index():
    """Alle installierten Programme (Startmenue-Verknuepfungen), gecacht."""
    global _APP_INDEX
    if _APP_INDEX is None:
        index = {}
        for ordner in _STARTMENUE_ORDNER:
            if not ordner.exists():
                continue
            try:
                for pfad in ordner.rglob("*.lnk"):
                    if pfad.stem and pfad.stem not in index:
                        index[pfad.stem] = str(pfad)
            except Exception:
                pass
        _APP_INDEX = index
    return _APP_INDEX


def _uwp_index():
    """Windows-Store-/System-Apps via PowerShell (Get-StartApps), gecacht."""
    global _UWP_INDEX
    if _UWP_INDEX is None:
        index = {}
        try:
            ergebnis = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-StartApps | ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=25,
                encoding="utf-8", errors="replace")
            daten = json.loads(ergebnis.stdout or "[]")
            if isinstance(daten, dict):
                daten = [daten]
            for app in daten:
                name, appid = app.get("Name"), app.get("AppID")
                if name and appid and "!" in str(appid):
                    index[str(name)] = str(appid)
        except Exception:
            pass
        _UWP_INDEX = index
    return _UWP_INDEX


def _finde_app(suchbegriff):
    """Sucht installierte Apps; liefert (art, (name, wert)) oder (None, None)."""
    q = _normalisiere(suchbegriff)
    if not q:
        return None, None
    treffer = []
    for name, pfad in _app_index().items():
        n = _normalisiere(name)
        if q in n:
            treffer.append((len(n) - len(q), name, pfad, "lnk"))
    for name, appid in _uwp_index().items():
        n = _normalisiere(name)
        if q in n and "!" in appid:
            treffer.append((len(n) - len(q), name, appid, "uwp"))
    if not treffer:
        return None, None
    treffer.sort()
    _, name, wert, art = treffer[0]
    return art, (name, wert)


def open_app(name=""):
    name = _text(name).strip('"')
    if not name:
        return False, "Es wurde kein Programmname angegeben."
    pfad = Path(name)
    # 1) Ist es ein echter Pfad oder eine Datei?
    if pfad.exists():
        os.startfile(str(pfad))
        return True, f"'{pfad.name}' wurde geoeffnet."
    # 2) Bekanntes Programm im System-PATH (notepad, calc, cmd, ...)?
    ort = shutil.which(name) or shutil.which(name + ".exe")
    if ort:
        subprocess.Popen([ort])
        return True, f"'{name}' wurde gestartet."
    # 3) Installierte Apps durchsuchen (Startmenue + Store-Apps)
    art, treffer = _finde_app(name)
    if art == "lnk":
        app_name, lnk_pfad = treffer
        os.startfile(lnk_pfad)
        return True, f"'{app_name}' wurde gestartet."
    if art == "uwp":
        app_name, appid = treffer
        subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{appid}"])
        return True, f"'{app_name}' wurde gestartet."
    # 4) Letzter Versuch: Windows-'start'
    subprocess.Popen(f'start "" "{name}"', shell=True)
    return True, f"'{name}' wurde gestartet."


def search_apps(query=""):
    """Durchsucht alle installierten Apps (Startmenue + Store)."""
    q = _text(query)
    alle = sorted(set(list(_app_index()) + list(_uwp_index())), key=str.lower)
    if q:
        nq = _normalisiere(q)
        treffer = [n for n in alle if nq in _normalisiere(n)]
    else:
        treffer = alle
    if not treffer:
        return True, (f"Keine installierte App passt zu '{q}'. "
                      f"Insgesamt sind {len(alle)} Apps installiert.")
    treffer = treffer[:20]
    return True, (f"{len(treffer)} passende App(s): " + ", ".join(treffer)
                  + f". Insgesamt {len(alle)} installierte Apps.")


_SUCH_ORDNER = ["Desktop", "Documents", "Downloads", "Pictures", "Videos", "Music",
                "OneDrive/Desktop", "OneDrive/Documents", "OneDrive/Downloads",
                "OneDrive/Pictures", "OneDrive/Bilder", "OneDrive/Dokumente"]


def _such_ordner(ordner):
    angabe = _text(ordner)
    if angabe:
        p = Path(angabe).expanduser()
        if p.exists():
            return [p]
    home = Path.home()
    return [home / rel for rel in _SUCH_ORDNER if (home / rel).exists()]


def search_files(query="", ordner=""):
    """Durchsucht den PC nach Dateien mit einem Suchbegriff im Dateinamen."""
    such = _text(query)
    if not such:
        return False, "Es wurde kein Suchbegriff angegeben."
    q = such.lower()
    treffer = []
    geprueft = 0
    abbrechen = False
    for start in _such_ordner(ordner):
        for wurzel, verzeichnisse, dateien in os.walk(start):
            verzeichnisse[:] = [v for v in verzeichnisse
                                if not v.startswith((".", "$"))]
            for d in dateien:
                geprueft += 1
                if q in d.lower():
                    treffer.append(os.path.join(wurzel, d))
                    if len(treffer) >= 15:
                        abbrechen = True
                        break
            if abbrechen or geprueft >= 20000:
                break
        if abbrechen or geprueft >= 20000:
            break
    if not treffer:
        return True, (f"Keine Datei mit '{such}' im Namen gefunden "
                      f"({geprueft} Dateien durchsucht).")
    mehr = " (Es konnten nicht alle Ordner durchsucht werden.)" if geprueft >= 20000 else ""
    return True, (f"{len(treffer)} Datei(en) mit '{such}' im Namen: "
                  + " | ".join(treffer[:15]) + mehr)


_TEXT_ENDUNGEN = {".txt", ".md", ".csv", ".log", ".ini", ".cfg", ".json",
                  ".xml", ".py", ".html", ".htm", ".yml", ".yaml", ".srt"}


def search_content(query="", ordner=""):
    """Durchsucht die INHALTE von Textdateien auf dem PC."""
    such = _text(query).lower()
    if not such:
        return False, "Es wurde kein Suchbegriff angegeben."
    treffer = []
    geprueft = 0
    abbrechen = False
    for start in _such_ordner(ordner):
        for wurzel, verzeichnisse, dateien in os.walk(start):
            verzeichnisse[:] = [v for v in verzeichnisse
                                if not v.startswith((".", "$"))]
            for d in dateien:
                if geprueft >= 3000 or len(treffer) >= 8:
                    abbrechen = True
                    break
                pfad = os.path.join(wurzel, d)
                if os.path.splitext(d)[1].lower() not in _TEXT_ENDUNGEN:
                    continue
                try:
                    if os.path.getsize(pfad) > 2_000_000:
                        continue
                    with open(pfad, "r", encoding="utf-8", errors="ignore") as f:
                        for i, zeile in enumerate(f, 1):
                            if such in zeile.lower():
                                treffer.append(f"{pfad} (Zeile {i}): {zeile.strip()[:150]}")
                                break
                except Exception:
                    pass
                geprueft += 1
            if abbrechen:
                break
        if abbrechen:
            break
    if not treffer:
        return True, (f"Keine Datei mit dem Inhalt '{such}' gefunden "
                      f"({geprueft} Textdateien durchsucht).")
    return True, (f"{len(treffer)} Treffer fuer '{such}': " + " | ".join(treffer))


def run_command(command=""):
    command = _text(command)
    if not command:
        return False, "Es wurde kein Befehl angegeben."
    try:
        ergebnis = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return False, "Der Befehl wurde nach 60 Sekunden abgebrochen."
    ausgabe = ((ergebnis.stdout or "") + "\n" + (ergebnis.stderr or "")).strip()
    ausgabe = (ausgabe[:900] + (" ..." if len(ausgabe) > 900 else "")) or "(keine Ausgabe)"
    erfolg = ergebnis.returncode == 0
    return erfolg, f"Exit-Code {ergebnis.returncode}. Ausgabe: {ausgabe}"


def open_website(url=""):
    url = _text(url)
    if not url:
        return False, "Es wurde keine Adresse angegeben."
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    if not re.match(r"^https?://[A-Za-z0-9.\-]+", url):
        return False, f"'{url}' sieht nicht wie eine gueltige Adresse aus."
    webbrowser.open(url)
    return True, f"Die Website {url} wird geoeffnet."


def web_search(query=""):
    query = _text(query)
    if not query:
        return False, "Es wurde kein Suchbegriff angegeben."
    webbrowser.open("https://www.google.com/search?q=" + quote_plus(query))
    return True, f"Die Google-Suche nach '{query}' wurde geoeffnet."


# ---------------- Text & Eingaben ----------------

def type_text(text=""):
    text = str(text) if text is not None else ""
    if not text:
        return False, "Es wurde kein Text angegeben."
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "v")
    return True, "Der Text wurde in das aktive Fenster eingefuegt."


def clipboard_copy(text=""):
    text = str(text) if text is not None else ""
    if not text:
        return False, "Es wurde kein Text angegeben."
    pyperclip.copy(text)
    return True, "Der Text liegt jetzt in der Zwischenablage."


def screenshot():
    ziel = _bilder_ordner() / f"Screenshot_{datetime.now():%Y-%m-%d_%H%M%S}.png"
    pyautogui.screenshot(str(ziel))
    return True, f"Screenshot gespeichert unter {ziel}."


# ---------------- Dateien & Ordner ----------------

def write_file(path="", content=""):
    pfad = _text(path)
    if not pfad:
        return False, "Es wurde kein Dateipfad angegeben."
    ziel = Path(pfad).expanduser()
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(str(content or ""), encoding="utf-8")
    return True, f"Die Datei {ziel} wurde gespeichert."


def read_file(path=""):
    pfad = _text(path)
    if not pfad:
        return False, "Es wurde kein Dateipfad angegeben."
    ziel = Path(pfad).expanduser()
    if not ziel.is_file():
        return False, f"Die Datei {ziel} existiert nicht."
    inhalt = ziel.read_text(encoding="utf-8", errors="replace")[:1200]
    return True, f"Inhalt von {ziel}: {inhalt}"


def list_dir(path=""):
    ziel = Path(_text(path) or ".").expanduser()
    if not ziel.exists():
        return False, f"Der Pfad {ziel} existiert nicht."
    eintraege = sorted(ziel.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
    namen = [f"[Ordner] {e.name}" if e.is_dir() else e.name for e in eintraege[:40]]
    rest = f" ... und {len(eintraege) - 40} weitere" if len(eintraege) > 40 else ""
    return True, f"Inhalt von {ziel}: {', '.join(namen) or '(leer)'}{rest}"


# ---------------- System ----------------

def set_volume(level=50):
    try:
        stufe = max(0, min(100, int(level)))
    except (TypeError, ValueError):
        return False, "Die Lautstaerke muss eine Zahl zwischen 0 und 100 sein."
    try:
        from ctypes import POINTER, cast
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        geraet = AudioUtilities.GetSpeakers()
        schnittstelle = geraet.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        lautstaerke = cast(schnittstelle, POINTER(IAudioEndpointVolume))
        lautstaerke.SetMasterVolumeLevelScalar(stufe / 100.0, None)
        return True, f"Die Lautstaerke wurde auf {stufe} Prozent gesetzt."
    except Exception as exc:
        return False, f"Lautstaerke konnte nicht geaendert werden: {exc}"


_MEDIA_TASTEN = {"play": 0xB3, "pause": 0xB3, "next": 0xB0, "prev": 0xB1, "stop": 0xB2}


def get_volume():
    """Liefert die aktuelle System-Lautstaerke (0-100) oder None."""
    try:
        from ctypes import POINTER, cast
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        geraet = AudioUtilities.GetSpeakers()
        schnittstelle = geraet.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        lautstaerke = cast(schnittstelle, POINTER(IAudioEndpointVolume))
        return int(round(lautstaerke.GetMasterVolumeLevelScalar() * 100))
    except Exception:
        return None


def _taste_druecken(vk):
    """Drueckt eine virtuelle Taste systemweit (z. B. Medien-Tasten)."""
    import ctypes
    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
    ctypes.windll.user32.keybd_event(vk, 0, 2, 0)


def media_key(key="play"):
    taste = _text(key).lower()
    vk = _MEDIA_TASTEN.get(taste)
    if vk is None:
        return False, f"Unbekannte Medientaste '{taste}'. Erlaubt: play, pause, next, prev, stop."
    _taste_druecken(vk)
    return True, "Medienbefehl gesendet."


def _spotify_installiert():
    if _finde_app("spotify")[0]:
        return True
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "spotify"):
            return True
    except OSError:
        return False


def _spotify_fokus_und_enter():
    """Holt das Spotify-Fenster nach vorn und bestaetigt den ersten Treffer."""
    try:
        import pygetwindow as gw
        fenster = [f for f in gw.getAllWindows()
                   if "spotify" in (f.title or "").lower()]
        if fenster:
            try:
                fenster[0].activate()
            except Exception:
                pass
            time.sleep(1.0)
            pyautogui.press("enter")
            time.sleep(1.5)
            pyautogui.press("enter")
    except Exception:
        pass


def spotify(befehl="start", suchbegriff=""):
    """Steuert Spotify: App starten, Wiedergabe, Lieblingssongs, Songs suchen."""
    befehl = _text(befehl).lower()
    if not _spotify_installiert():
        return False, "Spotify ist auf diesem PC nicht installiert."

    if befehl in ("start", "oeffnen", "open"):
        subprocess.Popen('start "" "spotify:"', shell=True)
        return True, "Spotify wird geoeffnet."

    medien = {"play": "play", "pause": "pause", "weiter": "next",
              "next": "next", "zurueck": "prev", "prev": "prev", "stop": "stop"}
    if befehl in medien:
        return media_key(medien[befehl])

    begriff = _text(suchbegriff)
    if befehl in ("lieblingssongs", "liked", "favoriten", "lieblingslieder"):
        subprocess.Popen('start "" "spotify:collection:tracks"', shell=True)
        time.sleep(6)
        _taste_druecken(0xB3)  # Play/Pause: startet die Wiedergabe
        return True, ("Spotify zeigt deine Lieblingssongs (Liked Songs) "
                      "und die Wiedergabe wurde gestartet.")

    if befehl in ("spiele", "spiel", "suche", "search"):
        if not begriff:
            return False, "Es wurde kein Song- oder Suchbegriff angegeben."
        import urllib.parse
        subprocess.Popen('start "" "spotify:search:'
                         + urllib.parse.quote(begriff) + '"', shell=True)
        time.sleep(4)
        _spotify_fokus_und_enter()
        return True, (f"Spotify hat nach '{begriff}' gesucht und versucht, "
                      "den ersten Treffer abzuspielen.")

    return False, (f"Unbekannter Spotify-Befehl '{befehl}'. Erlaubt: start, play, "
                   "pause, next, prev, stop, suche, spiele, lieblingssongs.")


def mein_profil(kategorie=""):
    """Zeigt, was Jarvis ueber den Nutzer gespeichert hat."""
    from assistant import gedaechtnis
    eintraege = gedaechtnis.alle()
    kategorie = _text(kategorie).lower()
    if kategorie:
        eintraege = [e for e in eintraege if kategorie in e["kategorie"].lower()]
    if not eintraege:
        return True, "Ich habe noch nichts ueber dich gespeichert."
    zeilen = [f"[{e['kategorie']}] {e['info']} ({e['zeit']})"
              for e in eintraege[-25:]]
    return True, (f"Ich kenne {len(eintraege)} Dinge ueber dich. Die letzten: "
                  + " | ".join(zeilen))


def vergiss(suchbegriff="", alles=False):
    """Loescht Erinnerungen ueber den Nutzer."""
    from assistant import gedaechtnis
    if alles:
        anzahl = gedaechtnis.vergessen(alles=True)
        return True, (f"Ich habe mein gesamtes Gedaechtnis geloescht "
                      f"({anzahl} Eintraege). Wir fangen neu an.")
    suchbegriff = _text(suchbegriff)
    if not suchbegriff:
        return False, "Sag mir, was ich vergessen soll - oder 'alles'."
    anzahl = gedaechtnis.vergessen(suchbegriff=suchbegriff)
    if anzahl:
        return True, f"Ich habe {anzahl} Erinnerung(en) zu '{suchbegriff}' geloescht."
    return True, f"Ich habe keine Erinnerung zu '{suchbegriff}' gefunden."


def lock_pc():
    subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True, timeout=10)
    return True, "Der PC wird gesperrt."


def sleep_pc():
    # Hinweis: Ist der Ruhezustand deaktiviert, geht der PC in den Standby.
    subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True, timeout=10)
    return True, "Der PC geht in den Ruhezustand."


ACTIONS = {
    "open_app": open_app,
    "search_apps": search_apps,
    "search_files": search_files,
    "search_content": search_content,
    "run_command": run_command,
    "open_website": open_website,
    "web_search": web_search,
    "type_text": type_text,
    "clipboard_copy": clipboard_copy,
    "screenshot": screenshot,
    "write_file": write_file,
    "read_file": read_file,
    "list_dir": list_dir,
    "set_volume": set_volume,
    "get_volume": get_volume,
    "spotify": spotify,
    "mein_profil": mein_profil,
    "vergiss": vergiss,
    "media_key": media_key,
    "lock_pc": lock_pc,
    "sleep_pc": sleep_pc,
}


def handle(action):
    """Fuehrt eine Aktion der KI aus. Liefert (erfolg, nachricht)."""
    name = str(action.get("name", ""))
    funktion = ACTIONS.get(name)
    if funktion is None:
        return False, f"Unbekannte Aktion '{name}'."
    args = action.get("args") or {}
    if not isinstance(args, dict):
        args = {}
    erlaubt = set(inspect.signature(funktion).parameters)
    gefiltert = {k: v for k, v in args.items() if k in erlaubt}
    try:
        return funktion(**gefiltert)
    except Exception as exc:
        return False, f"Fehler bei '{name}': {exc}"
