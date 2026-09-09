"""Invio della mail via SMTP. Funziona con Gmail, Outlook, Aruba, qualunque provider."""

import os
import smtplib
from email.message import EmailMessage


def invia_mail(oggetto: str, html: str, testo: str, destinatario: str = ""):
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    porta = int(os.getenv("SMTP_PORT", "587"))
    utente = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASS", "")
    mittente = os.getenv("MAIL_FROM", utente)
    a = os.getenv("MAIL_TO", "") or destinatario

    mancanti = [n for n, v in (("SMTP_USER", utente), ("SMTP_PASS", password)) if not v]
    if mancanti:
        raise RuntimeError(f"Variabili SMTP mancanti: {', '.join(mancanti)}")
    if not a:
        raise RuntimeError("Nessun destinatario: imposta MAIL_TO o 'destinatario' in lega.yaml.")

    msg = EmailMessage()
    msg["Subject"] = oggetto
    msg["From"] = mittente
    msg["To"] = a
    msg.set_content(testo)
    msg.add_alternative(html, subtype="html")

    with smtplib.SMTP(host, porta, timeout=60) as s:
        s.starttls()
        s.login(utente, password)
        s.send_message(msg)
    print(f"Mail inviata a {a}")
