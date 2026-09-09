"""Dati finti per provare l'agente senza chiavi API e senza inviare mail."""

import datetime as dt
import random

NOTE = [
    "Titolare fisso, ha giocato tutte le ultime partite.",
    "Ballottaggio aperto secondo le probabili formazioni.",
    "Rientrato in gruppo, il tecnico lo ha convocato.",
    "In grande forma, due bonus nelle ultime tre.",
    "Turnover possibile dopo la coppa infrasettimanale.",
    "Avversario in difficoltà, occasione ghiotta.",
]


def giornata_finta():
    inizio = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=22)
    return {
        "giornata": 7,
        "primo_calcio_inizio": inizio,
        "partite": [
            {"casa": "Inter", "trasferta": "Napoli", "inizio": inizio.isoformat()},
            {
                "casa": "Juventus",
                "trasferta": "Lazio",
                "inizio": (inizio + dt.timedelta(hours=3)).isoformat(),
            },
        ],
    }


def analisi_finta(rosa):
    random.seed(7)
    fuori = {"Kempf", "Colombo"}
    out = []
    for g in rosa["giocatori"]:
        titolare = random.choice([95, 88, 75, 60, 45, 30])
        stato = "ok"
        if g["nome"] in fuori:
            stato, titolare = random.choice(["infortunato", "squalificato"]), 0
        elif titolare < 55:
            stato = "in dubbio"
        bonus = {"P": 0.0, "D": 0.15, "C": 0.45, "A": 0.9}[g["ruolo"]]
        out.append(
            {
                "nome": g["nome"],
                "ruolo": g["ruolo"],
                "squadra": g["squadra"],
                "titolarita": titolare,
                "stato": stato,
                "avversario": random.choice(["Napoli", "Lazio", "Torino", "Roma"]),
                "in_casa": random.choice([True, False]),
                "difficolta_avversario": random.randint(1, 5),
                "voto_atteso": round(random.uniform(5.6, 6.9), 2),
                "bonus_atteso": round(bonus * random.uniform(0.4, 1.6), 2),
                "nota": random.choice(NOTE),
                "trovato": True,
            }
        )
    return out
