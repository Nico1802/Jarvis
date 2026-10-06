"""Das J.A.R.V.I.S.-Fenster: futuristische HUD-Oberflaeche v3.

- Animierter HUD-Ring mit Radar-Sweep, Orbit-Punkten und pulsierendem Kern
- Zustandsfarben: Bereit (cyan) / Hoeren (amber) / Denken (gruen) / Sprechen (violett)
- Gradient-Kopfzeile mit Uhr und Status-LEDs, CPU/RAM-Anzeige, Laufschrift-Ticker
- Schnellaktionen, Lautstaerkeregler, Chatverlauf, Texteingabe mit Verlauf
"""

import math
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, scrolledtext

import config
from assistant import actions
from assistant.audio import MicError
from assistant.tts import Sprecher

# ------------------------- Farbschema -------------------------
BG = "#04060c"
PANEL = "#080d16"
RAHMEN = "#0d2436"
KNOPF = "#0d3a52"
CYAN = "#00d4ff"
CYAN_BLASS = "#7fe3ff"
CYAN_DIM = "#0a5f7f"
CYAN_DUNKEL = "#073545"
TEXT = "#cfefff"
TEXT_DIM = "#57748a"
AMBER = "#ffb020"
GRUEN = "#2bff9a"
ROT = "#ff5d5d"
VIOLETT = "#9aa8ff"

ZUSTANDS_FARBEN = {
    "bereit": CYAN,
    "höre": AMBER,
    "denke": GRUEN,
    "spreche": VIOLETT,
    "fehler": ROT,
}

STATUS_ZUSTAND = (
    ("denke", "denke"),
    ("führe", "denke"),
    ("höre", "höre"),
    ("hoere", "höre"),
    ("spreche", "spreche"),
    ("bereit", "bereit"),
    ("fehler", "fehler"),
)

TICKER_TEXT = ("J.A.R.V.I.S. SYSTEM ONLINE   ///   LOKALES GEHIRN MIT AUTO-START   ///   "
               "LERNENDES GEDAECHTNIS   ///   ELEVENLABS + EDGE AUDIO   ///   "
               "VOLLER PC-ZUGRIFF   ///   SPOTIFY-STEUERUNG   ///   ")


def _zustand_fuer(text):
    t = str(text).lower()
    for schluesel, zustand in STATUS_ZUSTAND:
        if schluesel in t:
            return zustand
    return None


class KopfLeiste(tk.Canvas):
    """Gradient-Kopfzeile mit Titel, Uhr und Status-LED."""

    def __init__(self, master, breite=540, hoehe=64):
        super().__init__(master, width=breite, height=hoehe, bg=BG,
                         highlightthickness=0)
        for x in range(breite):
            anteil = x / breite
            r = int(6 + 10 * anteil)
            g = int(10 + 24 * anteil)
            b = int(18 + 36 * anteil)
            self.create_line(x, 0, x, hoehe, fill=f"#{r:02x}{g:02x}{b:02x}")
        self.create_line(0, hoehe - 1, breite, hoehe - 1, fill=RAHMEN)
        self.create_text(16, 8, text="J.A.R.V.I.S.", font=("Consolas", 20, "bold"),
                         fill=CYAN, anchor="nw")
        self.create_text(16, 40, text="Just A Rather Very Intelligent System",
                         font=("Consolas", 8), fill=TEXT_DIM, anchor="nw")
        self.uhr = self.create_text(breite - 16, 10, text="--:--:--",
                                    font=("Consolas", 15), fill=CYAN_BLASS, anchor="ne")
        self.lm_led = self.create_text(breite - 16, 38, text="● LM PRÜFE …",
                                       font=("Consolas", 9), fill=TEXT_DIM, anchor="ne")

    def setze_uhr(self, text):
        self.itemconfig(self.uhr, text=text)

    def setze_lm(self, zustand):
        if zustand == "online":
            self.itemconfig(self.lm_led, text="● LM ONLINE", fill=GRUEN)
        elif zustand == "cloud":
            self.itemconfig(self.lm_led, text="☁ CLOUD-MODUS", fill=AMBER)
        else:
            self.itemconfig(self.lm_led, text="● LM OFFLINE", fill=ROT)


class Laufschrift(tk.Canvas):
    """Endlos durchlaufender Ticker am unteren Rand."""

    def __init__(self, master, breite=540, text=TICKER_TEXT):
        super().__init__(master, width=breite, height=20, bg=PANEL,
                         highlightthickness=0)
        self.breite = breite
        self.x = breite
        self.item = self.create_text(0, 10, text=text, font=("Consolas", 9),
                                     fill=TEXT_DIM, anchor="w")
        self.textbreite = tkfont.Font(font=("Consolas", 9)).measure(text)
        self._laufen()

    def _laufen(self):
        try:
            self.x -= 1
            if self.x < -self.textbreite:
                self.x = self.breite
            self.coords(self.item, self.x, 10)
        except tk.TclError:
            return
        self.after(40, self._laufen)


class HudRing(tk.Canvas):
    """Animierter HUD-Ring mit Radar-Sweep, Orbit-Punkten und pulsierendem Kern."""

    def __init__(self, master, groesse=260):
        super().__init__(master, width=groesse, height=groesse,
                         bg=BG, highlightthickness=0, bd=0)
        self.groesse = groesse
        self.z = groesse / 2
        self.winkel = 0.0
        self.zustand = "bereit"
        self._boegen = []
        self._elemente_bauen()
        self._animieren()

    def _elemente_bauen(self):
        z = self.z
        # statische Grundringe
        self.create_oval(z-128, z-128, z+128, z+128, outline=CYAN_DUNKEL, width=2)
        self.create_oval(z-124, z-124, z+124, z+124, outline="#0a2e40", width=1)

        # Striche rundum (zwei Reihen)
        for grad in range(0, 360, 6):
            lang = (grad % 30 == 0)
            a = math.radians(grad)
            for r1, r2 in (((110, 120), ) if lang else ((115, 120), )):
                self.create_line(z + r1*math.cos(a), z + r1*math.sin(a),
                                 z + r2*math.cos(a), z + r2*math.sin(a),
                                 fill=CYAN_DIM if lang else "#0a2e40", width=2)

        # rotierende Boegen: (radius, extent, farbe, dicke, geschwindigkeit, phase)
        boegen = [
            (126, 70, CYAN, 3, 1.4, 0),
            (126, 18, CYAN, 3, 1.4, 180),
            (106, 130, "#12b8de", 2, -0.9, 0),
            (106, 26, "#12b8de", 2, -0.9, 190),
            (86, 210, CYAN_DUNKEL, 2, 0.6, 0),
            (86, 34, CYAN_DIM, 2, 0.6, 260),
            (66, 46, CYAN_DIM, 2, -2.0, 0),
        ]
        for radius, extent, farbe, dicke, speed, phase in boegen:
            item = self.create_arc(z - radius, z - radius, z + radius, z + radius,
                                   start=phase, extent=extent, style="arc",
                                   outline=farbe, width=dicke)
            self._boegen.append((item, speed, phase))

        # Radar-Sweep: Linie + nachziehende Spur
        self._radar = self.create_line(z, z, z, z - 126, fill="#4de8ff", width=2)
        self._radar_spur = []
        for extent, farbe in ((12, "#0a6b8f"), (26, "#085270"), (40, "#063a52")):
            item = self.create_arc(z-126, z-126, z+126, z+126, start=0,
                                   extent=extent, style="arc", outline=farbe, width=5)
            self._radar_spur.append((item, extent))

        # Orbit-Punkte
        self._punkte = []
        for radius, speed in ((116, 2.4), (96, -1.6), (76, 3.0)):
            punkt = self.create_oval(z-3, z-3, z+3, z+3, fill=CYAN_BLASS, outline="")
            self._punkte.append((punkt, radius, speed))

        # pulsierender Kern + Schrift
        self._puls = self.create_oval(z-52, z-52, z+52, z+52, outline=CYAN, width=2)
        self._kern = self.create_oval(z-43, z-43, z+43, z+43,
                                      outline=CYAN_DIM, width=1, fill="#050d15")
        self.create_text(z, z - 5, text="JARVIS", font=("Consolas", 18, "bold"),
                         fill="#08405a")  # Glow-Schatten
        self._titel = self.create_text(z, z - 6, text="JARVIS",
                                       font=("Consolas", 18, "bold"), fill=CYAN)
        self._unterzeile = self.create_text(z, z + 15, text="BEREIT",
                                            font=("Consolas", 9), fill=TEXT_DIM)
        self._systemzeile = self.create_text(z, z + 31, text="SYSTEME ONLINE",
                                             font=("Consolas", 7), fill=CYAN_DIM)

    def setze_zustand(self, name=None, unterzeile=None):
        if name in ZUSTANDS_FARBEN:
            self.zustand = name
        if unterzeile:
            self.itemconfig(self._unterzeile, text=str(unterzeile).upper()[:30])

    def setze_systemzeile(self, text):
        try:
            self.itemconfig(self._systemzeile, text=str(text).upper()[:30])
        except tk.TclError:
            pass

    def _animieren(self):
        try:
            self.winkel = (self.winkel + 1.4) % 360
            t = time.time()
            z = self.z

            # Kern pulsiert in Groesse und Helligkeit
            tempo = 7.0 if self.zustand == "höre" else 2.2
            puls = 1.0 + 0.07 * math.sin(t * tempo)
            r = 52 * puls
            self.coords(self._puls, z - r, z - r, z + r, z + r)
            hell = (math.sin(t * 2.2) + 1) / 2
            self.itemconfig(self._kern, fill=f"#{int(5 + 9*hell):02x}"
                                             f"#{int(13 + 30*hell):02x}"
                                             f"#{int(21 + 45*hell):02x}")

            farbe = ZUSTANDS_FARBEN.get(self.zustand, CYAN)
            self.itemconfig(self._puls, outline=farbe)
            self.itemconfig(self._titel, fill=farbe)

            # rotierende Boegen
            for item, speed, phase in self._boegen:
                self.itemconfig(item, start=(self.winkel * speed + phase) % 360)

            # Radar-Sweep
            radar = (self.winkel * 3) % 360
            a = math.radians(radar)
            self.coords(self._radar, z, z, z + 126*math.cos(a), z + 126*math.sin(a))
            for item, extent in self._radar_spur:
                self.itemconfig(item, start=(radar - extent) % 360)

            # Orbit-Punkte
            for punkt, radius, speed in self._punkte:
                b = math.radians(self.winkel * speed)
                px, py = z + radius*math.cos(b), z + radius*math.sin(b)
                self.coords(punkt, px - 3, py - 3, px + 3, py + 3)
        except tk.TclError:
            return  # Fenster geschlossen
        self.after(40, self._animieren)


class JarvisApp:
    def __init__(self, speech, brain, process_command):
        self.speech = speech          # kann None sein (dann nur Texteingabe)
        self.brain = brain
        self.sprecher = Sprecher()
        self._verarbeite = process_command

        self.jobs = queue.Queue()
        self.events_ui = queue.Queue()
        self.stop = threading.Event()
        self.beschaeftigt = threading.Event()
        self.begruessung_fertig = threading.Event()
        self._warte_auf_befehl = False
        self.mic_deaktivieren = False
        self.immer_flag = True
        self._verlauf = []
        self._verlauf_pos = -1

        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S.")
        self.root.configure(bg=BG)
        self._fenster_icon()
        self._fenster_platzieren()

        self.immer_zuhoeren = tk.BooleanVar(value=True)
        self._baue_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _fenster_icon(self):
        try:
            ico = r"C:\Users\nicos\Jarvis\jarvis.ico"
            if os.path.exists(ico):
                self.root.iconbitmap(ico)
                return
            from PIL import Image, ImageDraw, ImageTk
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.ellipse([4, 4, 60, 60], outline=(0, 212, 255, 255), width=4)
            d.ellipse([24, 24, 40, 40], fill=(0, 212, 255, 255))
            self._icon = ImageTk.PhotoImage(img)
            self.root.iconphoto(True, self._icon)
        except Exception:
            pass

    def _fenster_platzieren(self):
        breite, hoehe = 540, 780
        hoehe = min(hoehe, max(620, self.root.winfo_screenheight() - 90))
        x = max(0, (self.root.winfo_screenwidth() - breite) // 2)
        y = max(0, (self.root.winfo_screenheight() - hoehe) // 3)
        self.root.geometry(f"{breite}x{hoehe}+{x}+{y}")
        self.root.resizable(False, False)

    # ------------------------- Aufbau -------------------------

    def _baue_widgets(self):
        breite = 540

        # unten stehende Reihen ZUERST von unten packen:
        fussleiste = tk.Frame(self.root, bg=PANEL)
        fussleiste.pack(fill="x", side="bottom")
        self.mic_led = tk.Label(fussleiste, text="● MIC", font=("Consolas", 8),
                                bg=PANEL, fg=GRUEN)
        self.mic_led.pack(side="left", padx=(12, 8), pady=4)
        self.cpu_label = tk.Label(fussleiste, text="CPU -- %", font=("Consolas", 8),
                                  bg=PANEL, fg=TEXT_DIM)
        self.cpu_label.pack(side="left", padx=(0, 8))
        self.ram_label = tk.Label(fussleiste, text="RAM -- %", font=("Consolas", 8),
                                  bg=PANEL, fg=TEXT_DIM)
        self.ram_label.pack(side="left")
        tk.Label(fussleiste, text="J.A.R.V.I.S. v3.0 • lokal & privat",
                 font=("Consolas", 8), bg=PANEL, fg=TEXT_DIM).pack(side="right", padx=12)

        self.ticker = Laufschrift(self.root, breite=breite)

        fuss = tk.Frame(self.root, bg=BG)
        fuss.pack(fill="x", side="bottom", padx=16, pady=(4, 4))
        self.mic_button = tk.Button(fuss, text="🎙️  SPRECHEN", command=self._mic_klick,
                                    bg=KNOPF, fg=CYAN, relief="flat", bd=0,
                                    font=("Consolas", 12, "bold"), padx=18, pady=6,
                                    activebackground=CYAN_DUNKEL,
                                    activeforeground=CYAN_BLASS, cursor="hand2")
        self.mic_button.pack(side="left")
        self.immer_btn = tk.Button(fuss, text="👁 IMMER ZUHÖREN: AN",
                                   command=self._immer_umschalten, bg=KNOPF,
                                   fg=CYAN, relief="flat", bd=0,
                                   font=("Consolas", 9), padx=10, pady=6,
                                   activebackground=CYAN_DUNKEL,
                                   activeforeground=CYAN_BLASS, cursor="hand2")
        self.immer_btn.pack(side="left", padx=(8, 0))

        zeile = tk.Frame(self.root, bg=BG)
        zeile.pack(fill="x", side="bottom", padx=16, pady=(6, 4))
        self.eingabe = tk.Entry(zeile, font=("Consolas", 11), bg=PANEL, fg=TEXT,
                                insertbackground=CYAN, relief="flat",
                                highlightthickness=1, highlightbackground=RAHMEN,
                                highlightcolor=CYAN_DIM)
        self.eingabe.pack(side="left", fill="x", expand=True, ipady=7)
        self.eingabe.bind("<Return>", lambda _e: self._senden())
        self.eingabe.bind("<Up>", self._verlauf_zurueck)
        self.eingabe.bind("<Down>", self._verlauf_vor)
        tk.Button(zeile, text="SENDEN ▸", command=self._senden, bg=KNOPF,
                  fg=CYAN, relief="flat", bd=0, font=("Consolas", 10, "bold"),
                  padx=12, activebackground=CYAN_DUNKEL, activeforeground=CYAN,
                  cursor="hand2").pack(side="left", padx=(8, 0))

        vol_zeile = tk.Frame(self.root, bg=BG)
        vol_zeile.pack(fill="x", side="bottom", padx=16, pady=(4, 2))
        tk.Label(vol_zeile, text="🔊", font=("Consolas", 10),
                 bg=BG, fg=CYAN_BLASS).pack(side="left")
        self.volumen = tk.Scale(vol_zeile, from_=0, to=100, orient="horizontal",
                                showvalue=0, bg=BG, fg=TEXT_DIM,
                                troughcolor="#0c1a26", highlightthickness=0,
                                activebackground=CYAN, sliderrelief="flat",
                                length=230)
        self.volumen.set(50)
        self.volumen.bind("<ButtonRelease-1>", self._volumen_loslassen)
        self.volumen.pack(side="left", padx=8)
        self.vol_anzeige = tk.Label(vol_zeile, text="50 %", font=("Consolas", 9),
                                    bg=BG, fg=TEXT_DIM)
        self.vol_anzeige.pack(side="left")

        aktionen = tk.Frame(self.root, bg=BG)
        aktionen.pack(fill="x", side="bottom", padx=16)
        for text, name in (("📸 Shot", "screenshot"), ("🕒 Zeit", "uhrzeit"),
                           ("🔋 Akku", "akku"), ("▶️ Musik", "musik"),
                           ("🌐 YT", "youtube"), ("🧠 Profil", "profil")):
            tk.Button(aktionen, text=text, font=("Consolas", 9), bg=PANEL,
                      fg=CYAN_BLASS, relief="flat", bd=0, padx=7, pady=3,
                      highlightthickness=1, highlightbackground=RAHMEN,
                      activebackground=CYAN_DUNKEL, activeforeground=CYAN,
                      cursor="hand2",
                      command=lambda n=name: self.jobs.put(("direkt", n))
                      ).pack(side="left", padx=(0, 5))

        kopf = KopfLeiste(self.root, breite=breite)
        kopf.pack(side="top", fill="x")
        self.kopf = kopf

        self.ring = HudRing(self.root, groesse=260)
        self.ring.pack(side="top", pady=(4, 0))

        self.chat = scrolledtext.ScrolledText(
            self.root, wrap="word", state="disabled", font=("Consolas", 10),
            bg=PANEL, fg=TEXT, relief="flat", padx=10, pady=8, height=6,
            highlightthickness=1, highlightbackground=RAHMEN)
        self.chat.pack(fill="both", expand=True, padx=16, pady=8)
        self.chat.tag_configure("jarvis", foreground=CYAN_BLASS,
                                font=("Consolas", 10, "bold"))
        self.chat.tag_configure("du", foreground="#ffd479",
                                font=("Consolas", 10, "bold"))
        self.chat.tag_configure("system", foreground="#7f95a6")
        self.chat.tag_configure("warnung", foreground=ROT,
                                font=("Consolas", 10, "bold"))

    # ------------------- Meldungen zur Oberflaeche -------------------

    def _pump(self):
        try:
            self.immer_flag = bool(self.immer_zuhoeren.get())
        except tk.TclError:
            pass
        try:
            while True:
                n = self.events_ui.get_nowait()
                art = n[0]
                if art == "log":
                    self._log(n[1], n[2])
                elif art == "status":
                    self.ring.setze_zustand(_zustand_fuer(n[1]), n[1])
                elif art == "ring":
                    self.ring.setze_zustand(n[1], n[2] if len(n) > 2 else None)
                elif art == "frage":
                    frage, event, halter = n[1], n[2], n[3]
                    antwort = messagebox.askyesno("JARVIS - Rückfrage", frage,
                                                  parent=self.root)
                    halter["antwort"] = bool(antwort)
                    event.set()
                elif art == "lm":
                    self.kopf.setze_lm(n[1])
                elif art == "stats":
                    self.cpu_label.configure(text=f"CPU {n[1]:.0f} %")
                    self.ram_label.configure(text=f"RAM {n[2]:.0f} %")
                elif art == "systemzeile":
                    self.ring.setze_systemzeile(n[1])
                elif art == "volumen_setzen":
                    self.volumen.set(n[1])
                    self.vol_anzeige.configure(text=f"{n[1]} %")
                elif art == "mic_aus":
                    self.immer_zuhoeren.set(False)
                    self.mic_deaktivieren = True
                    self.mic_button.configure(state="disabled", text="🎙️ KEIN MIKROFON")
                    self.immer_btn.configure(state="disabled", text="👁 IMMER ZUHÖREN: AUS",
                                             fg=TEXT_DIM)
                    self.mic_led.configure(fg=ROT)
        except queue.Empty:
            pass
        if not self.stop.is_set():
            self.root.after(100, self._pump)

    def _log(self, rolle, text):
        self.chat.configure(state="normal")
        tag = {"🤖 Jarvis": "jarvis", "🧑 Du": "du", "⚠️": "warnung"}.get(rolle, "system")
        self.chat.insert("end", f"{rolle}: ", tag)
        self.chat.insert("end", f"{text}\n\n")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    # ----- Schnittstelle fuer process_command (laeuft im Arbeits-Thread) -----

    def say(self, text):
        text = str(text)
        self.events_ui.put(("log", "🤖 Jarvis", text))
        self.events_ui.put(("ring", "spreche", "Spreche …"))
        if config.SPEAK_ENABLED:
            try:
                quelle = self.sprecher.sprich(text)
                print(f"🔊 Sprachausgabe: {quelle}")
                if (quelle != "ElevenLabs" and config.ELEVENLABS_ENABLED
                        and not getattr(self, "_tts_fallback_gemeldet", False)):
                    self._tts_fallback_gemeldet = True
                    self.events_ui.put(
                        ("log", "⚠️",
                         "ElevenLabs nicht erreichbar (Schluessel muss mit 'sk_' beginnen) - "
                         "Jarvis nutzt die kostenlose Edge-Stimme. Details im Terminal."))
            except Exception as exc:
                self.events_ui.put(("log", "⚠️", f"Sprachausgabe-Fehler: {exc}"))
        self.events_ui.put(("ring", "bereit", "Bereit"))

    def ask_yes_no(self, frage):
        self.events_ui.put(("log", "❓ Rückfrage", frage))
        event = threading.Event()
        halter = {}
        self.events_ui.put(("frage", frage, event, halter))
        event.wait(timeout=180)
        return bool(halter.get("antwort"))

    def status(self, text):
        self.events_ui.put(("status", text))

    def log_system(self, text):
        self.events_ui.put(("log", "⚙️", str(text)))

    # ------------------------- Threads -------------------------

    @staticmethod
    def _com_init():
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass

    def _gui_mic_status(self, name, wert=None):
        texte = {
            "kalibriere": "Prüfe Umgebungsgeräusch …",
            "hoere": "🎙️ Ich höre zu … (sag 'Jarvis' + Befehl)",
        }
        if name == "schwelle":
            self.events_ui.put(("status", f"Ich höre zu … (Schwelle {wert:.0f})"))
        elif name in texte:
            self.events_ui.put(("status", texte[name]))

    def _lm_check_thread(self):
        import requests
        while not self.stop.is_set():
            zustand = "offline"
            try:
                if requests.get(config.LMSTUDIO_MODELS_URL,
                                timeout=3).status_code == 200:
                    zustand = "online"
            except Exception:
                pass
            if zustand == "offline" and config.CLOUD_API_KEY:
                zustand = "cloud"
            self.events_ui.put(("lm", zustand))
            self.stop.wait(30)

    def _stats_thread(self):
        import psutil
        while not self.stop.is_set():
            try:
                cpu = psutil.cpu_percent(interval=2)
                ram = psutil.virtual_memory().percent
                self.events_ui.put(("stats", cpu, ram))
            except Exception:
                self.stop.wait(3)

    def _mic_thread(self):
        self._com_init()
        if self.speech is None:
            self.events_ui.put(("log", "⚠️", "Kein Mikrofon verfügbar - bitte tippen."))
            self.events_ui.put(("mic_aus",))
            return
        # Kurz warten, bis die Begruessung durch ist (sonst hoert Jarvis sich selbst)
        self.begruessung_fertig.wait(timeout=8)
        while not self.stop.is_set():
            if (self.mic_deaktivieren or not self.immer_flag
                    or self.beschaeftigt.is_set()):
                self.stop.wait(0.3)
                continue
            try:
                text = self.speech.listen(on_state=self._gui_mic_status,
                                          stop_event=self.stop)
            except MicError:
                self.events_ui.put(
                    ("log", "⚠️",
                     "Mikrofon konnte nicht geöffnet werden - Immer-Zuhören ausgeschaltet."))
                self.events_ui.put(("mic_aus",))
                break
            if self.stop.is_set():
                break
            if not text:
                continue
            befehl = self._nach_wake_word(text)
            if befehl is None and not self._warte_auf_befehl:
                self._warte_auf_befehl = True
                self.events_ui.put(("log", "🤖 Jarvis", "Ja?"))
                continue
            if befehl is None:
                befehl = text
            self._warte_auf_befehl = False
            self.jobs.put(("text", befehl))

    def _worker(self):
        self._com_init()
        self.brain.status_melden = lambda s: self.events_ui.put(("status", s))
        self.jobs.put(("volumen_init", None))
        threading.Thread(target=self._stats_thread, daemon=True).start()
        self.say("Hallo! Ich bin Jarvis. Sag 'Jarvis' und deinen Befehl - oder tippe unten.")
        self.begruessung_fertig.set()
        while not self.stop.is_set():
            try:
                job = self.jobs.get(timeout=0.2)
            except queue.Empty:
                continue
            art = job[0]
            if art == "text":
                text = job[1]
                self.events_ui.put(("log", "🧑 Du", text))
                if text in config.EXIT_WORDS:
                    self.say("Auf Wiedersehen! Bis bald.")
                    self.stop.set()
                    try:
                        self.root.after(0, self._on_close)
                    except RuntimeError:
                        pass
                    break
                self.events_ui.put(("status", "💭 Denke nach …"))
                self.beschaeftigt.set()
                try:
                    self._verarbeite(text, self, self.brain)
                except Exception as exc:
                    self.events_ui.put(("log", "⚠️", f"Interner Fehler: {exc}"))
                finally:
                    self.beschaeftigt.clear()
                self.events_ui.put(("status", "Bereit"))
            elif art == "sprechen":
                if self.speech is None:
                    self.say("Ich habe kein Mikrofon. Tippe deinen Befehl einfach unten.")
                    continue
                self.events_ui.put(("status", "🎙️ Ich höre zu … (sprich jetzt)"))
                try:
                    text = self.speech.listen(on_state=self._gui_mic_status,
                                              stop_event=self.stop)
                except MicError as exc:
                    self.say(f"Mikrofon-Problem: {exc}")
                    continue
                if self.stop.is_set():
                    break
                if text:
                    self.jobs.put(("text", text))
                else:
                    self.events_ui.put(("log", "🤖 Jarvis",
                                        "Ich habe dich nicht verstanden."))
                    self.events_ui.put(("status", "Bereit"))
            elif art == "direkt":
                self.events_ui.put(("log", "⚡ Schnellaktion", job[1].capitalize()))
                self.beschaeftigt.set()
                try:
                    self._direkt_aktion(job[1])
                except Exception as exc:
                    self.events_ui.put(("log", "⚠️", f"Fehler: {exc}"))
                finally:
                    self.beschaeftigt.clear()
                self.events_ui.put(("status", "Bereit"))
            elif art == "volumen":
                ok, msg = actions.handle({"name": "set_volume",
                                          "args": {"level": job[1]}})
                self.events_ui.put(("log", "⚙️", msg))
            elif art == "volumen_init":
                wert = actions.get_volume()
                if wert is not None:
                    self.events_ui.put(("volumen_setzen", wert))

    def _direkt_aktion(self, name):
        """Schnellaktionen - laufen ohne Sprachmodell, sofort & zuverlaessig."""
        import webbrowser
        if name == "screenshot":
            ok, msg = actions.handle({"name": "screenshot"})
            self.say(msg if ok else f"Das hat nicht geklappt: {msg}")
        elif name == "uhrzeit":
            self.say(f"Es ist {time.strftime('%H:%M')} Uhr.")
        elif name == "akku":
            try:
                import psutil
                akku = psutil.sensors_battery()
                if akku is None:
                    self.say("Ich fand keinen Akku - der PC scheint am Strom zu hängen.")
                else:
                    zusatz = " und wird geladen" if akku.power_plugged else ""
                    self.say(f"Akku bei {round(akku.percent)} Prozent{zusatz}.")
            except Exception:
                self.say("Den Akku-Status konnte ich gerade nicht abrufen.")
        elif name == "musik":
            ok, msg = actions.handle({"name": "media_key", "args": {"key": "play"}})
            self.say("Medien-Wiedergabe umgeschaltet." if ok else msg)
        elif name == "youtube":
            webbrowser.open("https://www.youtube.com")
            self.say("YouTube wird geöffnet.")
        elif name == "profil":
            ok, msg = actions.handle({"name": "mein_profil"})
            self.say(msg)

    # ------------------------- Bedienung -------------------------

    def _senden(self):
        text = self.eingabe.get().strip()
        if text:
            self.eingabe.delete(0, "end")
            self._verlauf.append(text)
            self._verlauf_pos = -1
            self.jobs.put(("text", text))

    def _verlauf_zurueck(self, _e=None):
        if not self._verlauf:
            return
        self._verlauf_pos = min(self._verlauf_pos + 1, len(self._verlauf) - 1)
        self.eingabe.delete(0, "end")
        self.eingabe.insert(0, self._verlauf[-1 - self._verlauf_pos])

    def _verlauf_vor(self, _e=None):
        if not self._verlauf or self._verlauf_pos < 0:
            return
        self._verlauf_pos -= 1
        self.eingabe.delete(0, "end")
        if self._verlauf_pos >= 0:
            self.eingabe.insert(0, self._verlauf[-1 - self._verlauf_pos])

    def _mic_klick(self):
        self.jobs.put(("sprechen", None))

    def _immer_umschalten(self):
        neu = not self.immer_zuhoeren.get()
        self.immer_zuhoeren.set(neu)
        self.immer_btn.configure(
            text=f"👁 IMMER ZUHÖREN: {'AN' if neu else 'AUS'}",
            bg=KNOPF if neu else PANEL,
            fg=CYAN if neu else TEXT_DIM)
        self.mic_led.configure(fg=GRUEN if neu else TEXT_DIM)

    def _volumen_loslassen(self, _e=None):
        self.vol_anzeige.configure(text=f"{self.volumen.get()} %")
        self.jobs.put(("volumen", self.volumen.get()))

    @staticmethod
    def _nach_wake_word(text):
        lower = text.lower()
        if config.WAKE_WORD in lower:
            rest = lower.split(config.WAKE_WORD, 1)[1]
            return rest.strip(" ,.!?").strip() or None
        return None

    def _on_close(self):
        self.stop.set()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def run(self, auto_close_ms=None):
        threading.Thread(target=self._worker, daemon=True).start()
        threading.Thread(target=self._mic_thread, daemon=True).start()
        threading.Thread(target=self._lm_check_thread, daemon=True).start()
        self.root.after(100, self._pump)
        self.root.after(0, self._uhr_tick)
        if auto_close_ms:
            self.root.after(auto_close_ms, self._on_close)
        self.root.mainloop()

    def _uhr_tick(self):
        try:
            self.kopf.setze_uhr(time.strftime("%H:%M:%S"))
        except tk.TclError:
            return
        self.root.after(1000, self._uhr_tick)
