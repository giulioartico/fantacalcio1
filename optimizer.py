"""Sceglie il modulo migliore, l'undici titolare e l'ordine della panchina.

La matematica sta qui, non nel modello: Claude fornisce le stime sui giocatori,
questo modulo fa i conti in modo deterministico e ripetibile.
"""

from itertools import combinations

RUOLI = ["P", "D", "C", "A"]
NOMI_RUOLO = {"P": "Portiere", "D": "Difensori", "C": "Centrocampisti", "A": "Attaccanti"}

STATI_ESCLUSI = {"infortunato", "squalificato", "non convocato"}

# Tabella del modificatore di difesa (media voto di portiere + 3 migliori difensori).
# Se la tua lega usa una tabella diversa, cambiala qui: è l'unico punto che la definisce.
TABELLA_MODIFICATORE = [
    (7.25, 6),
    (7.00, 5),
    (6.75, 4),
    (6.50, 3),
    (6.25, 2),
    (6.00, 1),
    (5.50, 0),
    (5.00, -1),
    (4.50, -3),
    (0.00, -5),
]


def valore_atteso(g: dict, pesi: dict) -> float:
    """Fantavoto atteso, pesato sulla probabilità di scendere in campo."""
    p = max(0.0, min(100.0, g["titolarita"])) / 100.0
    if g["stato"] in STATI_ESCLUSI:
        return 0.0
    fantavoto = g["voto_atteso"] + g["bonus_atteso"]
    return p * fantavoto + (1 - p) * pesi["valore_senza_voto"]


def voto_atteso_puro(g: dict, pesi: dict) -> float:
    """Come sopra ma senza bonus/malus: serve al modificatore di difesa."""
    p = max(0.0, min(100.0, g["titolarita"])) / 100.0
    if g["stato"] in STATI_ESCLUSI:
        return 0.0
    return p * g["voto_atteso"] + (1 - p) * pesi["valore_senza_voto"]


def bonus_modificatore(portiere: dict, difensori: list, pesi: dict) -> float:
    if len(difensori) < 4:
        return 0.0
    voti_d = sorted((voto_atteso_puro(d, pesi) for d in difensori), reverse=True)[:3]
    media = (voto_atteso_puro(portiere, pesi) + sum(voti_d)) / 4
    for soglia, bonus in TABELLA_MODIFICATORE:
        if media >= soglia:
            return float(bonus)
    return 0.0


def _schierabili(analisi: list, pesi: dict) -> list:
    out = []
    for g in analisi:
        g = dict(g)
        g["ev"] = valore_atteso(g, pesi)
        g["disponibile"] = g["stato"] not in STATI_ESCLUSI
        out.append(g)
    return out


def scegli_formazione(analisi: list, lega: dict) -> dict:
    pesi = lega["pesi"]
    soglia = pesi.get("soglia_titolarita_minima", 0)
    peso_mod = pesi.get("peso_modificatore", 1.0)
    usa_mod = bool(lega.get("modificatore_difesa"))

    tutti = _schierabili(analisi, pesi)
    disponibili = [g for g in tutti if g["disponibile"]]

    per_ruolo = {}
    for r in RUOLI:
        pool = [g for g in disponibili if g["ruolo"] == r]
        pool.sort(key=lambda g: g["ev"], reverse=True)
        # Chi è sotto la soglia di titolarità va in fondo, ma resta utilizzabile
        # se la rosa non offre alternative.
        sicuri = [g for g in pool if g["titolarita"] >= soglia]
        rischiosi = [g for g in pool if g["titolarita"] < soglia]
        per_ruolo[r] = sicuri + rischiosi

    migliore = None
    for modulo in lega["moduli"]:
        try:
            nd, nc, na = (int(x) for x in modulo.split("-"))
        except ValueError:
            continue
        richiesti = {"P": 1, "D": nd, "C": nc, "A": na}
        if any(len(per_ruolo[r]) < n for r, n in richiesti.items()):
            continue

        centrocampo = per_ruolo["C"][:nc]
        attacco = per_ruolo["A"][:na]
        base = sum(g["ev"] for g in centrocampo + attacco)

        opzioni_p = per_ruolo["P"] if usa_mod else per_ruolo["P"][:1]
        pool_d = per_ruolo["D"][:9] if usa_mod else per_ruolo["D"]

        for portiere in opzioni_p:
            combos = (
                combinations(pool_d, nd)
                if usa_mod and nd >= 4
                else [tuple(per_ruolo["D"][:nd])]
            )
            for difesa in combos:
                difesa = list(difesa)
                punteggio = base + portiere["ev"] + sum(d["ev"] for d in difesa)
                mod = bonus_modificatore(portiere, difesa, pesi) if usa_mod else 0.0
                totale = punteggio + peso_mod * mod
                if migliore is None or totale > migliore["punteggio"]:
                    migliore = {
                        "modulo": modulo,
                        "punteggio": totale,
                        "fantapunti_attesi": punteggio,
                        "modificatore": mod,
                        "titolari": {
                            "P": [portiere],
                            "D": difesa,
                            "C": centrocampo,
                            "A": attacco,
                        },
                    }

    if migliore is None:
        raise RuntimeError(
            "Nessun modulo schierabile con i giocatori disponibili: "
            "controlla la rosa o allarga la lista dei moduli."
        )

    titolari_nomi = {
        g["nome"] for gruppo in migliore["titolari"].values() for g in gruppo
    }
    panchina = {}
    for r in RUOLI:
        resto = [
            g
            for g in per_ruolo[r]
            if g["nome"] not in titolari_nomi and g["ev"] > 0
        ]
        panchina[r] = resto[: lega.get("panchina_max", 8)]

    indisponibili = [g for g in tutti if not g["disponibile"]]
    allarmi = [
        g
        for g in tutti
        if g["disponibile"]
        and (g["stato"] == "in dubbio" or g["titolarita"] < soglia)
    ]

    migliore["panchina"] = panchina
    migliore["indisponibili"] = indisponibili
    migliore["allarmi"] = sorted(allarmi, key=lambda g: g["titolarita"])
    return migliore
