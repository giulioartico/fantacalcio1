"""Costruisce la mail: una distinta di gara, non un report.

Vincoli dei client di posta: solo tabelle, stili inline, niente flex/grid,
font di sistema. Il colore forte è speso in un punto solo, il modulo.
"""

import datetime as dt
from zoneinfo import ZoneInfo

from optimizer import NOMI_RUOLO, RUOLI

ROMA = ZoneInfo("Europe/Rome")

INCHIOSTRO = "#132A32"
CARTA = "#FFFFFF"
FONDO = "#E8E4DC"
RIGA = "#DAD5CB"
TENUE = "#6E6A63"
ALLARME = "#A6362F"
OK = "#2E6F4E"

SERIF = "Georgia, 'Times New Roman', serif"
SANS = "Helvetica, Arial, sans-serif"

GIORNI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
MESI = [
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
]


def _data_italiana(d: dt.datetime) -> str:
    d = d.astimezone(ROMA)
    return f"{GIORNI[d.weekday()]} {d.day} {MESI[d.month - 1]}, ore {d:%H:%M}"


def _campo_avversario(g: dict) -> str:
    if not g.get("avversario"):
        return "non gioca"
    dove = "in casa con" if g.get("in_casa") else "in trasferta a"
    return f"{dove} {g['avversario']}"


def _riga_giocatore(g: dict, numero: int | None = None) -> str:
    colore_tit = ALLARME if g["titolarita"] < 60 else (OK if g["titolarita"] >= 85 else INCHIOSTRO)
    prefisso = (
        f'<span style="color:{TENUE};font-family:{SANS};font-size:12px;">{numero}.</span> '
        if numero
        else ""
    )
    return f"""
    <tr>
      <td style="padding:9px 0 9px 0;border-bottom:1px solid {RIGA};vertical-align:top;">
        <div style="font-family:{SERIF};font-size:16px;color:{INCHIOSTRO};line-height:1.25;">
          {prefisso}{g['nome']}
        </div>
        <div style="font-family:{SANS};font-size:12px;color:{TENUE};padding-top:3px;line-height:1.45;">
          {g['squadra']}, {_campo_avversario(g)}<br>{g['nota']}
        </div>
      </td>
      <td style="padding:9px 0 9px 12px;border-bottom:1px solid {RIGA};text-align:right;vertical-align:top;white-space:nowrap;">
        <div style="font-family:{SANS};font-size:15px;color:{colore_tit};">{g['titolarita']:.0f}%</div>
        <div style="font-family:{SANS};font-size:11px;color:{TENUE};padding-top:3px;">attesi {g['ev']:.2f}</div>
      </td>
    </tr>"""


def _sezione(titolo: str, righe: str, sottotitolo: str = "") -> str:
    sotto = (
        f'<div style="font-family:{SANS};font-size:12px;color:{TENUE};padding-top:2px;">{sottotitolo}</div>'
        if sottotitolo
        else ""
    )
    return f"""
    <tr><td style="padding:26px 28px 0 28px;">
      <div style="font-family:{SANS};font-size:13px;color:{INCHIOSTRO};font-weight:bold;">{titolo}</div>
      {sotto}
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:8px;">{righe}</table>
    </td></tr>"""


def render_email(giornata: dict, form: dict, lega: dict):
    modulo = form["modulo"]
    scadenza = _data_italiana(giornata["primo_calcio_inizio"])

    corpo = ""
    for r in RUOLI:
        gruppo = form["titolari"][r]
        if not gruppo:
            continue
        righe = "".join(_riga_giocatore(g) for g in gruppo)
        corpo += _sezione(NOMI_RUOLO[r], righe)

    panchina_righe = ""
    for r in RUOLI:
        gruppo = form["panchina"].get(r, [])
        if not gruppo:
            continue
        panchina_righe += (
            f'<tr><td colspan="2" style="padding:14px 0 4px 0;font-family:{SANS};'
            f'font-size:11px;color:{TENUE};">{NOMI_RUOLO[r]}</td></tr>'
        )
        panchina_righe += "".join(
            _riga_giocatore(g, i) for i, g in enumerate(gruppo, start=1)
        )
    if panchina_righe:
        corpo += _sezione(
            "Panchina",
            panchina_righe,
            "Nell'ordine in cui conviene farli entrare, ruolo per ruolo.",
        )

    fuori = form["indisponibili"] + form["allarmi"]
    if fuori:
        avvisi = "".join(
            f"""<tr><td style="padding:7px 0;border-bottom:1px solid {RIGA};font-family:{SANS};font-size:13px;color:{INCHIOSTRO};line-height:1.45;">
              <span style="color:{ALLARME};">{g['stato']}</span> &nbsp;{g['nome']}
              <span style="color:{TENUE};"> — {g['nota']}</span>
            </td></tr>"""
            for g in fuori
        )
        corpo += _sezione("Da tenere d'occhio", avvisi)

    mod_txt = ""
    if form.get("modificatore"):
        segno = "+" if form["modificatore"] > 0 else ""
        mod_txt = f", modificatore difesa {segno}{form['modificatore']:.0f}"

    html = f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Formazione giornata {giornata['giornata']}</title></head>
<body style="margin:0;padding:0;background:{FONDO};">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{FONDO};padding:24px 12px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background:{CARTA};border:1px solid {RIGA};">

  <tr><td style="padding:30px 28px 24px 28px;background:{INCHIOSTRO};">
    <div style="font-family:{SANS};font-size:12px;color:#A9BCC2;">
      {lega.get('nome_lega', 'Fantacalcio')} &nbsp;|&nbsp; giornata {giornata['giornata']}
    </div>
    <div style="font-family:{SERIF};font-size:52px;color:#FFFFFF;letter-spacing:2px;padding:10px 0 6px 0;line-height:1;">
      {modulo}
    </div>
    <div style="font-family:{SANS};font-size:13px;color:#A9BCC2;line-height:1.5;">
      Si gioca da {scadenza}. Schiera prima di allora.
    </div>
  </td></tr>

  {corpo}

  <tr><td style="padding:26px 28px 30px 28px;">
    <div style="border-top:2px solid {INCHIOSTRO};padding-top:12px;font-family:{SANS};font-size:12px;color:{TENUE};line-height:1.6;">
      Totale atteso {form['fantapunti_attesi']:.1f} punti{mod_txt}.
      Le percentuali sono la probabilità stimata di partire titolare, i punti attesi
      tengono già conto del rischio panchina.
      Controlla gli ultimi aggiornamenti prima del calcio d'inizio.
    </div>
  </td></tr>

</table>
</td></tr></table>
</body></html>"""

    testo = [
        f"{lega.get('nome_lega', 'Fantacalcio')} — giornata {giornata['giornata']}",
        f"Modulo consigliato: {modulo}",
        f"Si gioca da {scadenza}.",
        "",
    ]
    for r in RUOLI:
        if form["titolari"][r]:
            testo.append(NOMI_RUOLO[r].upper())
            for g in form["titolari"][r]:
                testo.append(
                    f"  {g['nome']} ({g['squadra']}, {_campo_avversario(g)}) "
                    f"— {g['titolarita']:.0f}% titolare, attesi {g['ev']:.2f}. {g['nota']}"
                )
            testo.append("")
    testo.append("PANCHINA")
    for r in RUOLI:
        for i, g in enumerate(form["panchina"].get(r, []), start=1):
            testo.append(f"  {r}{i}. {g['nome']} — attesi {g['ev']:.2f}")
    if fuori:
        testo += ["", "DA TENERE D'OCCHIO"]
        for g in fuori:
            testo.append(f"  {g['nome']}: {g['stato']} — {g['nota']}")
    testo += ["", f"Totale atteso {form['fantapunti_attesi']:.1f} punti{mod_txt}."]

    return html, "\n".join(testo)
