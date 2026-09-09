"""Agente fantacalcio.

Gira una volta al giorno. Se la prossima giornata comincia entro le prossime ~30 ore,
legge le notizie, calcola la formazione migliore e manda la mail. Altrimenti non fa nulla.

  python src/main.py              esecuzione normale
  python src/main.py --forza      ignora la finestra temporale e manda comunque
  python src/main.py --prova      dati finti, nessuna chiamata esterna: salva anteprima.html
  python src/main.py --calendario controlla solo che il calendario si scarichi
  python src/main.py --notizie    stampa le notizie raccolte, senza chiamare il modello
  python src/main.py --modelli    elenca i modelli disponibili per il fornitore scelto
"""

import datetime as dt
import json
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mailer import invia_mail  # noqa: E402
from optimizer import scegli_formazione  # noqa: E402
from render import render_email  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Finestra di invio: la mail parte solo se il primo calcio d'inizio è
# fra 12 e 30 ore. Con un'esecuzione al giorno significa una sola mail per giornata,
# sempre il giorno prima.
ORE_MIN = float(os.getenv("ORE_MIN", "12"))
ORE_MAX = float(os.getenv("ORE_MAX", "30"))


def carica(nome):
    with open(os.path.join(BASE, "config", nome), encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    forza = "--forza" in sys.argv or os.getenv("FORCE_RUN", "").lower() in ("1", "true", "yes")
    prova = "--prova" in sys.argv

    if "--modelli" in sys.argv:
        import llm

        llm.elenca_modelli()
        return

    rosa = carica("rosa.yaml")
    lega = carica("lega.yaml")

    if "--notizie" in sys.argv:
        import news

        print(news.raccogli(rosa, {"giornata": 0, "partite": []})[:4000])
        return

    if "--calendario" in sys.argv:
        from fixtures import prossima_giornata

        g = prossima_giornata()
        print(json.dumps(g, indent=2, default=str, ensure_ascii=False))
        return

    if prova:
        from prova import giornata_finta, analisi_finta

        giornata = giornata_finta()
        analisi = analisi_finta(rosa)
    else:
        from fixtures import prossima_giornata
        from scout import analizza_rosa

        giornata = prossima_giornata()
        adesso = dt.datetime.now(dt.timezone.utc)
        ore = (giornata["primo_calcio_inizio"] - adesso).total_seconds() / 3600
        print(f"Prossima giornata: {giornata['giornata']}, fra {ore:.1f} ore.")

        if not forza and not (ORE_MIN < ore <= ORE_MAX):
            print("Non è ancora il giorno prima. Nessuna mail inviata.")
            return

        print("Leggo le notizie e analizzo la rosa...")
        analisi = analizza_rosa(rosa, giornata)

    form = scegli_formazione(analisi, lega)
    print(f"Modulo scelto: {form['modulo']} ({form['fantapunti_attesi']:.1f} punti attesi)")

    html, testo = render_email(giornata, form, lega)
    oggetto = f"Formazione {form['modulo']} — giornata {giornata['giornata']}"

    os.makedirs(os.path.join(BASE, "state"), exist_ok=True)
    with open(os.path.join(BASE, "state", "anteprima.html"), "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(BASE, "state", "ultima_analisi.json"), "w", encoding="utf-8") as f:
        json.dump(analisi, f, indent=2, ensure_ascii=False)

    if prova:
        print("Modalità prova: anteprima salvata in state/anteprima.html, nessuna mail inviata.")
        print()
        print(testo)
        return

    invia_mail(oggetto, html, testo, destinatario=lega.get("destinatario", ""))


if __name__ == "__main__":
    main()
