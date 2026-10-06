"""J.A.R.V.I.S.' Langzeit-Gedaechtnis.

Speichert dauerhaft Fakten ueber den Nutzer (Geschmaecker, Gewohnheiten,
Fakten, Termine ...) in gedaechtnis.json - ueber Neustarts hinweg.
"""

import json
import time
from pathlib import Path

DATEI = Path(__file__).resolve().parent.parent / "gedaechtnis.json"


def _laden():
    try:
        daten = json.loads(DATEI.read_text(encoding="utf-8"))
        return daten if isinstance(daten, list) else []
    except Exception:
        return []


def _speichern(eintraege):
    try:
        DATEI.write_text(json.dumps(eintraege, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    except Exception as exc:
        print(f"⚠️ Gedaechtnis konnte nicht gespeichert werden: {exc}")


def merken(kategorie, info):
    """Speichert eine neue Erinnerung ueber den Nutzer."""
    eintraege = _laden()
    eintraege.append({
        "kategorie": str(kategorie)[:40].strip() or "allgemein",
        "info": str(info)[:300].strip(),
        "zeit": time.strftime("%d.%m.%Y %H:%M"),
    })
    _speichern(eintraege[-250:])  # Gedaechtnis nicht unendlich wachsen lassen
    return True


def alle():
    return _laden()


def vergessen(suchbegriff="", alles=False):
    """Loescht Erinnerungen. Liefert die Anzahl geloeschter Eintraege."""
    eintraege = _laden()
    if alles:
        anzahl = len(eintraege)
        _speichern([])
        return anzahl
    suchbegriff = str(suchbegriff).lower()
    behalten = [e for e in eintraege
                if suchbegriff not in (e["info"] + " " + e["kategorie"]).lower()]
    geloescht = len(eintraege) - len(behalten)
    _speichern(behalten)
    return geloescht


def als_text(max_anzahl=40):
    """Das Gedaechtnis als Textblock fuer den System-Prompt."""
    eintraege = _laden()
    if not eintraege:
        return ""
    zeilen = []
    for eintrag in eintraege[-max_anzahl:]:
        zeilen.append(f"- [{eintrag['kategorie']}] {eintrag['info']} ({eintrag['zeit']})")
    kopf = f"GESPEICHERTES WISSEN UEBER DEN NUTZER ({len(eintraege)} Eintraege, nutze es fuer persoenliche Antworten):"
    return kopf + "\n" + "\n".join(zeilen)
