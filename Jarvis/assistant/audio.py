"""Mikrofon-Aufnahme mit sounddevice (kein PyAudio noetig - laeuft auf jedem Python).

record() kalibriert kurz das Umgebungsgeraeusch, wartet, bis du sprichst,
nimmt auf und beendet automatisch nach einer kurzen Stille.
"""

import numpy as np
import sounddevice as sd

import config


class MicError(Exception):
    """Mikrofon konnte nicht geoeffnet werden."""


def _rms(raw):
    """Mittlere Lautstaerke (Pegel) eines int16-Audio-Stuecks."""
    arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    if arr.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(arr * arr)))


class MicRecorder:
    def __init__(self, blocksize=1024):
        self.blocksize = blocksize

    def _oeffne(self):
        """Oeffnet das Mikrofon; probiert mehrere Einstellungen aus."""
        versuche = [
            {"samplerate": 16000, "channels": 1},   # ideal
            {"samplerate": None, "channels": 1},    # Standardrate des Mikrofons
            {"samplerate": None, "channels": None}  # ganz normale Standardeinstellung
        ]
        for einstellung in versuche:
            try:
                stream = sd.RawInputStream(
                    samplerate=einstellung["samplerate"],
                    blocksize=self.blocksize,
                    dtype="int16",
                    channels=einstellung["channels"],
                    device=config.MIC_DEVICE,
                )
                stream.start()
                return stream
            except Exception:
                continue
        eingaben = [
            d["name"] for d in sd.query_devices()
            if d.get("max_input_channels", 0) > 0
        ]
        hinweis = ", ".join(eingaben[:5]) or "keine Eingabegeraete gefunden"
        raise MicError(
            "Mikrofon konnte nicht geoeffnet werden. "
            f"Gefundene Eingabegeraete: {hinweis}. "
            "Laueft ein anderes Programm (Discord/Teams) mit dem Mikrofon?"
        )

    def record(self, on_state=None, stop_event=None,
               wait_seconds=6.0, max_seconds=15.0, silence_seconds=0.9):
        """Liefert (rohdaten, samplerate) oder None (nichts gesagt / abgebrochen)."""
        stream = self._oeffne()
        rate = int(stream.samplerate or 16000)
        kan = int(stream.channels or 1)
        schritt = self.blocksize / rate
        try:
            # 1) Umgebungsgeraeusch messen -> Schwelle fuer "das ist Sprache"
            if on_state:
                on_state("kalibriere")
            messungen = []
            dauer = 0.0
            while dauer < 0.35:
                if stop_event is not None and stop_event.is_set():
                    return None
                daten, _ = stream.read(self.blocksize)
                messungen.append(_rms(bytes(daten)))
                dauer += schritt
            mittel = sum(messungen) / len(messungen) if messungen else 0.0
            if config.MIC_THRESHOLD > 0:
                schwelle = float(config.MIC_THRESHOLD)
            else:
                schwelle = max(mittel * config.MIC_THRESHOLD_FACTOR,
                               config.MIC_THRESHOLD_FLOOR)
            if on_state:
                on_state("schwelle", schwelle)

            # 2) Auf Sprechen warten und aufnehmen
            if on_state:
                on_state("hoere")
            puffern = []
            gesprochen = False
            stille = 0.0
            dauer = 0.0
            while True:
                if stop_event is not None and stop_event.is_set():
                    return None
                daten, _ = stream.read(self.blocksize)
                stueck = bytes(daten)
                dauer += schritt
                if not gesprochen:
                    puffern.append(stueck)
                    if _rms(stueck) >= schwelle:
                        gesprochen = True
                        puffern = puffern[-8:]  # etwas Vorlauf behalten
                        stille = 0.0
                    elif dauer >= wait_seconds:
                        return None
                else:
                    puffern.append(stueck)
                    if _rms(stueck) < schwelle:
                        stille += schritt
                        if stille >= silence_seconds:
                            break
                    else:
                        stille = 0.0
                    if dauer >= max_seconds:
                        break

            roh = b"".join(puffern)
            # Stereo -> Mono (die Spracherkennung will Mono)
            if kan > 1 and roh:
                arr = np.frombuffer(roh, dtype=np.int16).reshape(-1, kan).astype(np.float32)
                roh = arr.mean(axis=1).astype(np.int16).tobytes()
            if len(roh) < rate // 4:  # weniger als ~0,25 s Sprache
                return None
            return roh, rate
        finally:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
