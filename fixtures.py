"""Trova la prossima giornata di Serie A e l'ora del primo calcio d'inizio.

Tre sorgenti gratuite, provate in ordine:
  1. football-data.org   chiave gratuita, solo email, nessuna carta (consigliata)
  2. TheSportsDB         nessuna chiave, funziona subito
  3. cache locale        l'ultimo calendario salvato, che copre alcune settimane
"""

import datetime as dt
import json
import os

import requests

TIMEOUT = 30
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(BASE, "state", "calendario.json")
SERIE_A_SPORTSDB = "4332"


def _ora(iso: str) -> dt.datetime:
    d = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc)


def _raggruppa(partite: list):
    """Da una lista piatta di partite a una lista di giornate ordinate."""
    per_giornata = {}
    for p in partite:
        per_giornata.setdefault(p["giornata"], []).append(p)
    giornate = []
    for numero, elenco in per_giornata.items():
        elenco.sort(key=lambda p: _ora(p["inizio"]))
        giornate.append({"giornata": numero, "partite": elenco})
    giornate.sort(key=lambda g: _ora(g["partite"][0]["inizio"]))
    return giornate


def _prima_futura(giornate):
    adesso = dt.datetime.now(dt.timezone.utc)
    for g in giornate:
        partite = sorted(g["partite"], key=lambda p: _ora(p["inizio"]))
        inizio = _ora(partite[0]["inizio"])
        if inizio > adesso:
            return {
                "giornata": g["giornata"],
                "primo_calcio_inizio": inizio,
                "partite": partite,
            }
    return None


def _salva_cache(giornate):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "aggiornato": dt.datetime.now(dt.timezone.utc).isoformat(),
                "giornate": giornate,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )


def _da_cache():
    try:
        with open(CACHE, encoding="utf-8") as f:
            return _prima_futura(json.load(f).get("giornate", []))
    except (FileNotFoundError, ValueError, KeyError):
        return None


def _da_football_data(token: str):
    r = requests.get(
        "https://api.football-data.org/v4/competitions/SA/matches",
        params={"status": "SCHEDULED,TIMED"},
        headers={"X-Auth-Token": token},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    partite = [
        {
            "giornata": m["matchday"],
            "casa": m["homeTeam"]["name"],
            "trasferta": m["awayTeam"]["name"],
            "inizio": _ora(m["utcDate"]).isoformat(),
        }
        for m in r.json().get("matches", [])
    ]
    return _raggruppa(partite) if partite else []


def _da_sportsdb():
    """Senza chiave: TheSportsDB espone le prossime partite di ogni campionato."""
    chiave = os.getenv("THESPORTSDB_KEY", "3")
    r = requests.get(
        f"https://www.thesportsdb.com/api/v1/json/{chiave}/eventsnextleague.php",
        params={"id": SERIE_A_SPORTSDB},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    partite = []
    for e in r.json().get("events") or []:
        data, ora = e.get("dateEvent"), (e.get("strTime") or "00:00:00")[:8]
        if not data:
            continue
        partite.append(
            {
                "giornata": int(e.get("intRound") or 0),
                "casa": e.get("strHomeTeam", ""),
                "trasferta": e.get("strAwayTeam", ""),
                "inizio": _ora(f"{data}T{ora}+00:00").isoformat(),
            }
        )
    return _raggruppa(partite) if partite else []


def prossima_giornata():
    token = os.getenv("FOOTBALL_DATA_TOKEN", "").strip()
    sorgenti = []
    if token:
        sorgenti.append(("football-data.org", lambda: _da_football_data(token)))
    sorgenti.append(("TheSportsDB", _da_sportsdb))

    for nome, sorgente in sorgenti:
        try:
            giornate = sorgente()
            prossima = _prima_futura(giornate)
            if prossima:
                _salva_cache(giornate)
                print(f"Calendario da {nome}: giornata {prossima['giornata']}.")
                return prossima
            print(f"{nome} non ha partite future.")
        except Exception as e:  # noqa: BLE001
            print(f"{nome} non disponibile: {e}")

    in_cache = _da_cache()
    if in_cache:
        print(f"Calendario dalla cache locale: giornata {in_cache['giornata']}.")
        return in_cache

    raise RuntimeError(
        "Nessuna sorgente di calendario disponibile. Imposta FOOTBALL_DATA_TOKEN "
        "con una chiave gratuita di football-data.org."
    )


def avversario_di(squadra: str, giornata: dict):
    s = squadra.lower()
    for p in giornata["partite"]:
        if s in p["casa"].lower() or p["casa"].lower() in s:
            return p["trasferta"], True
        if s in p["trasferta"].lower() or p["trasferta"].lower() in s:
            return p["casa"], False
    return None, None


if __name__ == "__main__":
    print(json.dumps(prossima_giornata(), indent=2, default=str, ensure_ascii=False))
