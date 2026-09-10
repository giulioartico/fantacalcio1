"""Un solo punto di contatto con il modello, con più fornitori intercambiabili.

Il predefinito è Gemini nel piano gratuito di Google AI Studio: nessuna carta di
credito, nessuna scadenza. Groq e OpenRouter hanno piani gratuiti equivalenti e
parlano lo stesso protocollo, quindi si cambia con una variabile d'ambiente.
Anthropic resta disponibile ma è a pagamento.
"""

import json
import os
import re
import time

import requests

TIMEOUT = 180

FORNITORI = {
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "modelli_url": "https://generativelanguage.googleapis.com/v1beta/openai/models",
        "chiave": "GEMINI_API_KEY",
        "modello": "gemini-2.5-flash",
        "gratis": True,
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "modelli_url": "https://api.groq.com/openai/v1/models",
        "chiave": "GROQ_API_KEY",
        "modello": "llama-3.3-70b-versatile",
        "gratis": True,
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "modelli_url": "https://openrouter.ai/api/v1/models",
        "chiave": "OPENROUTER_API_KEY",
        "modello": "meta-llama/llama-3.3-70b-instruct:free",
        "gratis": True,
    },
    "anthropic": {
        "url": "https://api.anthropic.com/v1/messages",
        "chiave": "ANTHROPIC_API_KEY",
        "modello": "claude-sonnet-5",
        "gratis": False,
    },
}


def _profilo():
    nome = os.getenv("LLM_PROVIDER", "gemini").lower()
    if nome not in FORNITORI:
        raise RuntimeError(
            f"Fornitore '{nome}' sconosciuto. Scegli tra: {', '.join(FORNITORI)}."
        )
    p = dict(FORNITORI[nome])
    p["nome"] = nome
    p["modello"] = os.getenv("LLM_MODEL") or p["modello"]
    p["api_key"] = os.getenv(p["chiave"], "").strip()
    if not p["api_key"]:
        raise RuntimeError(
            f"Manca la variabile {p['chiave']}. "
            f"Per il piano gratuito di Gemini prendi una chiave su aistudio.google.com."
        )
    return p


def estrai_json(testo: str):
    testo = re.sub(r"^```(?:json)?|```$", "", testo.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(testo)
    except json.JSONDecodeError:
        pass
    inizio = min((i for i in (testo.find("{"), testo.find("[")) if i != -1), default=-1)
    fine = max(testo.rfind("}"), testo.rfind("]"))
    if inizio == -1 or fine == -1:
        raise ValueError(f"Il modello non ha risposto in JSON:\n{testo[:800]}")
    return json.loads(testo[inizio : fine + 1])


# Errori temporanei del server: vale la pena riprovare invece di arrendersi subito.
CODICI_TEMPORANEI = {429, 500, 502, 503, 504}


def _con_ritentativi(url, headers, json, tentativi=3):
    ultimo = None
    for i in range(tentativi):
        r = requests.post(url, headers=headers, json=json, timeout=TIMEOUT)
        if r.status_code < 400 or r.status_code not in CODICI_TEMPORANEI:
            return r
        ultimo = r
        attesa = 5 * (i + 1)
        print(
            f"  Il server ha risposto {r.status_code} (errore temporaneo), "
            f"riprovo fra {attesa}s ({i + 1}/{tentativi})..."
        )
        time.sleep(attesa)
    return ultimo


def chiedi(prompt: str, max_token: int = 8000):
    """Manda il prompt al fornitore configurato e restituisce il JSON già parsato."""
    p = _profilo()

    if p["nome"] == "anthropic":
        r = _con_ritentativi(
            p["url"],
            headers={
                "x-api-key": p["api_key"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": p["modello"],
                "max_tokens": max_token,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        if r.status_code >= 400:
            raise RuntimeError(f"Errore {p['nome']} {r.status_code}: {r.text[:400]}")
        blocchi = r.json().get("content", [])
        testo = "\n".join(b.get("text", "") for b in blocchi if b.get("type") == "text")
        return estrai_json(testo)

    r = _con_ritentativi(
        p["url"],
        headers={
            "Authorization": f"Bearer {p['api_key']}",
            "Content-Type": "application/json",
        },
        json={
            "model": p["modello"],
            "max_tokens": max_token,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt}],
        },
    )
    if r.status_code >= 400:
        aiuto = ""
        if r.status_code == 404:
            aiuto = "  Il nome del modello potrebbe non esistere: prova `python src/main.py --modelli`."
        if r.status_code == 429:
            aiuto = "  Hai superato il limite giornaliero del piano gratuito: riprova domani."
        raise RuntimeError(f"Errore {p['nome']} {r.status_code}: {r.text[:400]}{aiuto}")

    dati = r.json()
    testo = dati["choices"][0]["message"]["content"]
    uso = dati.get("usage", {})
    if uso:
        print(
            f"Consumo: {uso.get('prompt_tokens', 0)} token in, "
            f"{uso.get('completion_tokens', 0)} token out "
            f"({p['nome']}, {'gratis' if p['gratis'] else 'a pagamento'})"
        )
    return estrai_json(testo)


def elenca_modelli():
    """Stampa i modelli disponibili per il fornitore configurato."""
    p = _profilo()
    if not p.get("modelli_url"):
        print(f"{p['nome']} non espone l'elenco dei modelli.")
        return
    r = requests.get(
        p["modelli_url"],
        headers={"Authorization": f"Bearer {p['api_key']}"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    for m in r.json().get("data", []):
        print(" ", m.get("id"))
