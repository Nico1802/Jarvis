"""Sicherheitsnetze: blockierte und riskante Befehle erkennen.

Der Assistent hat echte Kontrolle über deinen PC. Diese Listen sorgen dafür,
dass ganz gefährliche Befehle nie ausgeführt werden und riskante nur nach
einer Rückfrage.
"""

import re

# Niemals ausführen (harte Blockade):
BLOCKED_PATTERNS = [
    r"\bformat(\.com)?\b",
    r"\bdiskpart\b",
    r"\bbcdedit\b",
    r"\bdel\s+(/q\s+)?(/s|/f)",
    r"\b(rd|rmdir)\s+/s\b",
    r"remove-item\b[^|;&]*-(recurse|force)",
    r"\brm\s+-[rf]{1,2}\b",
    r"\bcipher\s+/w\b",
    r"\bshutdown\b",
    r"\b(stop|restart)-computer\b",
    r"\breg(\.exe)?\s+(add|delete)\b",
    r"\bvssadmin\b",
    r"\bwevtutil\s+cl\b",
]

# Nur nach Rückfrage ausführen:
RISKY_PATTERNS = [
    r"\btaskkill\b",
    r"\bnetsh\b",
    r"\bsc(\.exe)?\s+(config|delete|stop|start)\b",
    r"\bpowershell\b",
    r"\bpwsh\b",
    r"\bwinget\s+(install|uninstall)\b",
    r"\bchoco\s+(install|uninstall)\b",
    r"\bpip\s+(install|uninstall)\b",
    r"\bnpm\s+(install|uninstall|rm)\b",
    r"\b(remove-item|del|erase|rm)\b",
    r"\binvoke-(webrequest|expression)\b",
    r"\bstart-process\b",
    r"\bschtasks\b",
    r"\b(icacls|takeown|attrib)\b",
    r"\bnet\s+(user|localgroup)\b",
    r"\bcurl\b",
]


def check(command):
    """Liefert (blocked, risky) fuer einen Befehls-String."""
    cmd = (command or "").lower()
    blocked = any(re.search(muster, cmd) for muster in BLOCKED_PATTERNS)
    risky = blocked or any(re.search(muster, cmd) for muster in RISKY_PATTERNS)
    return blocked, risky
