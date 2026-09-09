"""Raccolta notizie senza costi.

Invece di pagare uno strumento di ricerca, interroghiamo i feed RSS di Google News:
sono pubblici, gratuiti, senza chiave e senza limiti pratici per questo uso.
Ogni feed restituisce i titoli delle ultime notizie italiane sull'argomento chiesto,
che è esattamente ciò che serve: "probabili formazioni", infortuni, squalifiche.
"""

import time
import urllib.parse
import xml.etree.ElementTree as ET
from html import unescape

import requests

FEED = "https://news.google.com/rss/search"
TIMEOUT = 15
PAUSA = 0.25  # cortesia verso il servizio


def _pulisci(testo: str) -> str:
    testo = unescape(testo or "")
    # i titoli di Google News finiscono con " - Testata": la testata serve a valutare la fonte
    return " ".join(testo.split())


def cerca(query: str, giorni: int = 4, massimo: int = 8) -> list:
    """Restituisce una lista di titoli recenti per la query indicata."""
    params = {
        "q": f"{query} when:{giorni}d",
        "hl": "it",
        "gl": "IT",
        "ceid": "IT:it",
    }
    url = f"{FEED}?{urllib.parse.urlencode(params)}"
    try:
        r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        radice = ET.fromstring(r.content)
    except Exception as e:  # noqa: BLE001
        print(f"  feed non raggiungibile per '{query}': {e}")
        return []

    titoli = []
    for item in radice.iter("item"):
        titolo = _pulisci(item.findtext("title", ""))
        data = _pulisci(item.findtext("pubDate", ""))[:16]
        if titolo:
            titoli.append(f"[{data}] {titolo}")
        if len(titoli) >= massimo:
            break
    return titoli


def raccogli(rosa: dict, giornata: dict) -> str:
    """Costruisce il dossier di notizie da dare al modello.

    Tre livelli: probabili formazioni per squadra, infortuni e squalifiche per squadra,
    e una ricerca mirata per ogni giocatore della rosa.
    """
    squadre = sorted({g["squadra"] for g in rosa["giocatori"]})
    blocchi = []

    print(f"Raccolgo notizie su {len(squadre)} squadre e {len(rosa['giocatori'])} giocatori...")

    for squadra in squadre:
        righe = cerca(f"probabili formazioni {squadra}", giorni=4)
        time.sleep(PAUSA)
        righe += cerca(f"{squadra} infortunati squalificati", giorni=5)
        time.sleep(PAUSA)
        if righe:
            blocchi.append(f"### {squadra}\n" + "\n".join(dict.fromkeys(righe)))

    for g in rosa["giocatori"]:
        righe = cerca(f'"{g["nome"]}" {g["squadra"]}', giorni=6, massimo=5)
        time.sleep(PAUSA)
        if righe:
            blocchi.append(f"### Giocatore: {g['nome']}\n" + "\n".join(righe))

    dossier = "\n\n".join(blocchi)
    print(f"Raccolti {len(dossier)} caratteri di notizie.")
    return dossier


if __name__ == "__main__":
    for riga in cerca("probabili formazioni Inter"):
        print(riga)
