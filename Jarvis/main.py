"""
JARVIS - persönlicher KI-Assistent mit Sprachsteuerung (Windows).

Start im Terminal:
    python main.py            Jarvis-Fenster öffnet sich (Empfehlung)
    python main.py --voice    Konsole mit Mikrofon (ohne Fenster)
    python main.py --text     Nur Tastatur, zum Testen (ohne Mikrofon)

Setup-Prüfung vorher:  python check_setup.py
"""

import re
import sys
from pathlib import Path

try:
    import config
    from assistant import actions, safety
    from assistant.brain import Brain
except ImportError as exc:
    print("Es fehlen noch Bibliotheken. Führe im Projektordner aus:")
    print("    pip install -r requirements.txt")
    print(f"Details: {exc}")
    raise SystemExit(1)

JA_MUSTER = r"\b(ja|ok(ay)?|bitte|mach|los)\b"
NEIN_MUSTER = r"\b(nein|ne|nicht|abbruch|abbrechen|stop|stopp|warte)\b"


class SpeechUI:
    """Konsole mit Mikrofon (--voice)."""

    def __init__(self, speech):
        self.speech = speech

    def say(self, text):
        self.speech.say(text)

    def status(self, text):
        pass  # in der Konsole stehen Statuszeilen schon im Log

    def ask_yes_no(self, frage):
        self.speech.say(frage + " Sag ja oder nein.")
        for _ in range(3):
            antwort = self.speech.listen()
            if not antwort:
                self.speech.say("Sag bitte ja oder nein.")
                continue
            if re.search(JA_MUSTER, antwort):
                return True
            if re.search(NEIN_MUSTER, antwort):
                return False
            self.speech.say("Ich brauche ein klares Ja oder Nein.")
        return False


class TextInputUI:
    """Nur Tastatur (--text)."""

    def say(self, text):
        print(f"🤖 Jarvis: {text}")

    def status(self, text):
        pass

    def ask_yes_no(self, frage):
        print(f"❓ {frage}")
        for _ in range(3):
            antwort = input("Antwort (ja/nein): ").strip().lower()
            if re.search(JA_MUSTER, antwort):
                return True
            if re.search(NEIN_MUSTER, antwort):
                return False
            print("Bitte mit ja oder nein antworten.")
        return False


def process_command(text, ui, brain):
    """Ein Befehl: Modell fragen -> Aktion ausführen -> Ergebnis vorlesen."""
    say, action = brain.ask(text)

    if action is None:
        ui.say(say or "Da bin ich mir nicht sicher.")
        return

    name = action.get("name", "?")
    args = action.get("args") or {}
    print(f"🔧 Aktion: {name} {args}")
    ui.status(f"⚙️ Führe aus: {name}")

    # --- Sicherheitsprüfungen ---
    if name == "run_command":
        command = str(args.get("command", ""))
        blocked, risky = safety.check(command)
        if blocked:
            ui.say("Diesen Befehl führe ich aus Sicherheitsgründen nicht aus.")
            return
        if risky and config.CONFIRM_RISKY:
            if not ui.ask_yes_no(f"Soll ich diesen Befehl wirklich ausführen: {command}?"):
                ui.say("Alles klar, abgebrochen.")
                return

    if name == "sleep_pc" and config.CONFIRM_RISKY:
        if not ui.ask_yes_no("Soll der PC wirklich in den Ruhezustand gehen?"):
            ui.say("Okay, ich lasse ihn an.")
            return

    if name == "write_file" and config.CONFIRM_RISKY:
        ziel = Path(str(args.get("path", "")).strip())
        if ziel.name and ziel.exists() and ziel.is_file() and ziel.stat().st_size > 0:
            if not ui.ask_yes_no(f"Die Datei {ziel.name} existiert schon. Überschreiben?"):
                ui.say("Okay, ich habe nichts verändert.")
                return

    # --- Ausführen ---
    erfolg, ergebnis = actions.handle(action)
    print(("✅ " if erfolg else "❌ ") + ergebnis)
    logge = getattr(ui, "log_system", None)
    if logge:
        logge(f"Aktion '{name}' {'erfolgreich ausgeführt' if erfolg else 'fehlgeschlagen'}")

    # --- Ergebnis dem Modell zurückmelden, damit es kurz zusammenfasst ---
    bericht = (
        f"[Systembericht] Die Aktion '{name}' war "
        f"{'erfolgreich' if erfolg else 'NICHT erfolgreich'}. Ergebnis: {ergebnis}. "
        "Gib dem Nutzer jetzt eine kurze Rückmeldung auf Deutsch. Keine weitere Aktion starten."
    )
    final_say, _ = brain.ask(bericht)
    ui.say(final_say or ergebnis)


def extract_after_wake_word(text):
    lower = text.lower()
    if config.WAKE_WORD in lower:
        rest = lower.split(config.WAKE_WORD, 1)[1]
        return rest.strip(" ,.!?").strip() or None
    return None


def wait_for_followup(speech):
    """Nach dem nackten Wake-Wort: auf den eigentlichen Befehl warten."""
    for _ in range(3):
        text = speech.listen()
        if text:
            return extract_after_wake_word(text) or text
    speech.say("Dann bis später!")
    return None


def run_gui():
    try:
        from assistant.gui import JarvisApp
        from assistant.speech import Speech
    except Exception as exc:
        print(f"⚠️ Das Jarvis-Fenster konnte nicht geladen werden: {exc}")
        print("   Tipp: pip install -r requirements.txt   oder   python main.py --text")
        return
    try:
        speech = Speech()
    except Exception as exc:
        print(f"⚠️ Mikrofon-System nicht bereit: {exc}")
        print("   Jarvis startet trotzdem - nutze das Textfeld im Fenster.")
        speech = None
    brain = Brain()
    app = JarvisApp(speech, brain, process_command)
    app.run()


def run_voice():
    from assistant.speech import Speech

    try:
        speech = Speech()
    except Exception as exc:
        print(f"⚠️ Sprachsystem konnte nicht starten: {exc}")
        print("   Tipp: pip install -r requirements.txt   oder   python main.py --text")
        return
    ui = SpeechUI(speech)
    brain = Brain()
    ui.say(f"Jarvis bereit! Sag {config.WAKE_WORD} und danach deinen Befehl.")
    try:
        while True:
            text = speech.listen()
            if not text or config.WAKE_WORD not in text:
                continue
            command = extract_after_wake_word(text)
            if not command:
                ui.say("Ja?")
                command = wait_for_followup(speech)
                if not command:
                    continue
            if command in config.EXIT_WORDS:
                ui.say("Auf Wiedersehen! Bis bald.")
                break
            process_command(command, ui, brain)
    except KeyboardInterrupt:
        pass
    print("\nJarvis beendet.")


def run_text():
    ui = TextInputUI()
    brain = Brain()
    ui.say("Textmodus aktiv. Befehl eintippen ('beenden' zum Stoppen).")
    while True:
        try:
            text = input("🧑 Du: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text in config.EXIT_WORDS:
            ui.say("Auf Wiedersehen! Bis bald.")
            break
        process_command(text, ui, brain)


def main():
    print("=" * 62)
    print("  JARVIS - Dein persönlicher KI-Assistent (Windows)")
    print("=" * 62)
    if "--text" in sys.argv:
        run_text()
    elif "--voice" in sys.argv:
        run_voice()
    else:
        run_gui()


if __name__ == "__main__":
    main()
