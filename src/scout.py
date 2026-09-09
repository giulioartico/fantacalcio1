"""Lo scout: raccoglie le notizie gratis e le fa interpretare al modello.

La divisione dei compiti è voluta. La ricerca la facciamo noi con i feed RSS, che
non costano niente; al modello resta solo il lavoro di lettura e sintesi, che qualsiasi
modello gratuito di fascia Flash svolge bene. È il motivo per cui l'agente gira a costo zero.
"""

import llm
import news

PROMPT = """Sei uno scout di fantacalcio. Devi valutare una rosa in vista della \
{giornata}ª giornata di Serie A.

Partite della giornata:
{partite}

Rosa da analizzare ({n} giocatori):
{rosa}

Qui sotto trovi i titoli delle notizie italiane più recenti su queste squadre e su questi \
giocatori, raccolti dalla stampa sportiva. Usali come fonte principale.

--- NOTIZIE ---
{notizie}
--- FINE NOTIZIE ---

Per OGNI giocatore della rosa restituisci un oggetto con questi campi:
- "nome": esattamente come scritto nella rosa
- "titolarita": probabilità in percentuale (0-100) che parta titolare
- "stato": uno tra "ok", "in dubbio", "infortunato", "squalificato", "non convocato"
- "avversario": squadra avversaria in questa giornata (o null se la squadra riposa)
- "in_casa": true se gioca in casa, false in trasferta, null se non gioca
- "difficolta_avversario": da 1 (avversario facile) a 5 (avversario proibitivo)
- "voto_atteso": voto base stimato senza bonus/malus, tipicamente tra 5.0 e 7.0
- "bonus_atteso": bonus/malus netti attesi (gol, assist, rigori, cartellini). Circa 0.8-1.0 \
per un attaccante titolare pericoloso, 0.3-0.5 per un centrocampista offensivo, 0.1 per un \
difensore, valori negativi se rischia cartellini
- "nota": una frase breve in italiano con il motivo principale (massimo 15 parole)

Regole importanti:
- Se le notizie non dicono niente su un giocatore, NON inventare: metti titolarita 50, \
stato "ok" e nota "Nessuna notizia recente, stima prudente".
- Se le notizie parlano di infortunio, squalifica o ballottaggio, tienine conto e citalo \
nella nota.
- Se la squadra del giocatore non gioca in questa giornata, metti titolarita 0 e stato \
"non convocato".
- Attenzione agli omonimi e alle notizie vecchie: la data è all'inizio di ogni titolo.

Rispondi SOLO con un array JSON, senza testo introduttivo, senza spiegazioni e senza \
backtick. Formato:
[{{"nome": "...", "titolarita": 85, "stato": "ok", "avversario": "...", "in_casa": true, \
"difficolta_avversario": 3, "voto_atteso": 6.2, "bonus_atteso": 0.8, "nota": "..."}}]"""


def analizza_rosa(rosa: dict, giornata: dict) -> list:
    giocatori = rosa["giocatori"]
    dossier = news.raccogli(rosa, giornata)

    prompt = PROMPT.format(
        giornata=giornata["giornata"],
        partite="\n".join(
            f"- {p['casa']} - {p['trasferta']} ({p['inizio'][:16].replace('T', ' ')})"
            for p in giornata["partite"]
        ),
        rosa="\n".join(f"- {g['nome']} ({g['ruolo']}, {g['squadra']})" for g in giocatori),
        n=len(giocatori),
        notizie=dossier or "Nessuna notizia recuperata.",
    )

    analisi = llm.chiedi(prompt)
    if isinstance(analisi, dict):
        analisi = analisi.get("giocatori", analisi.get("rosa", []))

    per_nome = {a.get("nome", "").lower(): a for a in analisi}
    completa = []
    for g in giocatori:
        a = per_nome.get(g["nome"].lower(), {})
        completa.append(
            {
                "nome": g["nome"],
                "ruolo": g["ruolo"],
                "squadra": g["squadra"],
                "titolarita": float(a.get("titolarita", 50) or 0),
                "stato": a.get("stato", "ok") or "ok",
                "avversario": a.get("avversario"),
                "in_casa": a.get("in_casa"),
                "difficolta_avversario": a.get("difficolta_avversario"),
                "voto_atteso": float(a.get("voto_atteso", 6.0) or 6.0),
                "bonus_atteso": float(a.get("bonus_atteso", 0.0) or 0.0),
                "nota": a.get("nota", "Nessuna notizia recente, stima prudente."),
                "trovato": bool(a),
            }
        )

    mancanti = [g["nome"] for g in completa if not g["trovato"]]
    if mancanti:
        print(f"Il modello non ha valutato: {', '.join(mancanti)} (usati valori prudenti).")
    return completa
