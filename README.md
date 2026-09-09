# Agente fantacalcio

Ogni giorno controlla quando comincia la prossima giornata di Serie A. Se si gioca domani,
raccoglie le notizie (probabili formazioni, infortuni, squalifiche), calcola la formazione
migliore per la tua rosa e ti manda una mail. Negli altri giorni non fa niente.

Gira su GitHub Actions e **non costa nulla**: nessun servizio a pagamento, nessuna carta di
credito richiesta in nessun passaggio.

## Come funziona

1. **Calendario** — trova la prossima giornata e l'ora del primo calcio d'inizio, da
   football-data.org o da TheSportsDB, entrambi gratuiti.
2. **Notizie** — interroga i feed RSS di Google News: due ricerche per ogni squadra della
   tua rosa (probabili formazioni, infortuni e squalifiche) e una per ogni giocatore. Sono
   feed pubblici, senza chiave e senza costi.
3. **Lettura** — un modello gratuito legge i titoli raccolti e li trasforma in dati: per
   ogni giocatore probabilità di partire titolare, stato, avversario, voto e bonus attesi,
   più una riga di spiegazione. Il predefinito è Gemini Flash nel piano gratuito di Google
   AI Studio, che dà 1.500 richieste al giorno senza carta di credito. Qui ne serve **una a
   giornata**.
4. **Conti** — i numeri li fa il codice, non il modello. Per ogni modulo ammesso calcola il
   punteggio atteso dell'undici, tiene conto del modificatore di difesa e sceglie la
   combinazione migliore. Il valore di un giocatore è
   `probabilità di giocare × fantavoto atteso + probabilità di panchina × 5.4`, così le
   scommesse rischiose vengono penalizzate da sole.
5. **Mail** — arriva il giorno prima con modulo, undici, panchina in ordine di ingresso e
   la lista di chi tenere d'occhio.

La divisione fra il punto 2 e il punto 3 è la ragione per cui l'agente è gratuito. Gli
strumenti di ricerca integrati nei modelli si pagano a query; i feed RSS no. Al modello
resta solo da leggere e sintetizzare, un lavoro che i modelli gratuiti di fascia Flash
svolgono bene.

## Installazione (una volta sola, 15 minuti)

### 1. Metti il progetto su GitHub

Crea un repository e caricaci questa cartella. Se lo fai **pubblico** i minuti di Actions
sono illimitati; se lo fai privato hai 2.000 minuti al mese, e qui ne servono una trentina.
In entrambi i casi le chiavi restano protette nei secret, non nel codice.

### 2. Compila la tua rosa

Apri `config/rosa.yaml` e sostituisci l'esempio con i tuoi giocatori (nome, squadra, ruolo).
In `config/lega.yaml` controlla i moduli ammessi e se la tua lega usa il modificatore di difesa.

### 3. Prendi le chiavi (tutte gratuite)

- **Gemini**: vai su aistudio.google.com, accedi con l'account Google e crea una chiave API.
  Non serve la carta, il piano gratuito non scade.
- **Mail**: se usi Gmail attiva la verifica in due passaggi e genera una *password per le
  app* di 16 caratteri. La password normale non funziona via SMTP.
- **football-data.org** (facoltativo ma consigliato): registrazione con la sola email, ti
  arriva un token. Rende il calendario più affidabile. Senza, si usa TheSportsDB.

### 4. Inserisci i segreti su GitHub

Nel repository: `Settings` → `Secrets and variables` → `Actions` → `New repository secret`.

| Nome | Valore |
|---|---|
| `GEMINI_API_KEY` | la chiave di Google AI Studio |
| `MAIL_TO` | dove vuoi ricevere la formazione |
| `SMTP_USER` | l'indirizzo da cui parte la mail |
| `SMTP_PASS` | la password per le app |
| `SMTP_HOST` | `smtp.gmail.com` (o quello del tuo provider) |
| `SMTP_PORT` | `587` |
| `FOOTBALL_DATA_TOKEN` | facoltativo |

### 5. Prova subito

Vai su `Actions` → `Formazione fantacalcio` → `Run workflow`, spunta **forza** e avvia.
Ti arriva la mail anche se la giornata non è domani. Da lì in poi va da solo.

## Provare in locale

```bash
pip install -r requirements.txt

python src/main.py --prova        # dati finti, nessuna chiave, salva state/anteprima.html
python src/main.py --calendario   # controlla solo che il calendario si scarichi
python src/main.py --notizie      # stampa le notizie raccolte, senza chiamare il modello
python src/main.py --modelli      # elenca i modelli disponibili per il fornitore scelto
python src/main.py --forza        # giro completo con mail vera
```

I primi tre comandi non chiamano nessun modello, quindi sono il modo più rapido per capire
dove si è rotto qualcosa.

## Cambiare fornitore del modello

Il predefinito è Gemini. Se un giorno il piano gratuito cambia, si passa a un altro con due
variabili, senza toccare il codice:

| Fornitore | Variabili | Note |
|---|---|---|
| Gemini | `LLM_PROVIDER=gemini`, `GEMINI_API_KEY` | 1.500 richieste al giorno, gratis |
| Groq | `LLM_PROVIDER=groq`, `GROQ_API_KEY` | piano gratuito, molto veloce |
| OpenRouter | `LLM_PROVIDER=openrouter`, `OPENROUTER_API_KEY` | modelli con suffisso `:free` |
| Anthropic | `LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY` | a pagamento, analisi più accurata |

Se il nome di un modello non esiste più ricevi un errore 404: `python src/main.py --modelli`
ti stampa quelli disponibili, poi imposti `LLM_MODEL` con quello giusto.

## Cose che vorrai cambiare

| Voglio... | File |
|---|---|
| aggiungere o togliere giocatori | `config/rosa.yaml` |
| cambiare moduli o disattivare il modificatore | `config/lega.yaml` |
| essere più o meno prudente sui ballottaggi | `pesi` in `config/lega.yaml` |
| cambiare l'orario della mail | il `cron` in `.github/workflows/fantacalcio.yml` |
| usare un'altra tabella del modificatore | `TABELLA_MODIFICATORE` in `src/optimizer.py` |
| cercare notizie su altre fonti o con altre query | `src/news.py` |
| cambiare cosa chiede l'agente al modello | `PROMPT` in `src/scout.py` |

## Limiti da conoscere

- La qualità è più bassa della versione a pagamento con ricerca integrata. Qui il modello
  legge i titoli delle notizie, non gli articoli interi: prende bene infortuni, squalifiche
  e ballottaggi dichiarati, coglie meno le sfumature. Per un giocatore di cui non si parla,
  la stima è prudente e la mail te lo dice invece di inventare.
- I feed RSS possono cambiare formato o non rispondere. Se un feed salta, l'agente lo
  segnala nei log e va avanti con quello che ha.
- Le probabili formazioni del giorno prima cambiano: un allenatore può stravolgere tutto in
  conferenza stampa. Prima del calcio d'inizio dai comunque un'occhiata.
- Il Mantra è supportato solo in versione semplificata, con i ruoli ricondotti a P/D/C/A.
- La formazione va inserita a mano sull'app della tua lega: l'agente consiglia, non schiera.
- GitHub spegne i workflow programmati dopo 60 giorni senza attività sul repository. Il
  commit automatico della cache basta a tenerlo sveglio, ma se ricevi una mail del tipo
  "this workflow will be disabled soon", apri Actions e riattivalo con un clic.
- L'orario dei cron su GitHub è indicativo: la mail può arrivare con qualche decina di
  minuti di ritardo. La finestra di invio è larga apposta, quindi non salta mai una giornata.
- Sul piano gratuito di Gemini, Google può usare i contenuti inviati per addestrare i propri
  modelli. Qui viaggiano solo nomi di calciatori e titoli di giornale, ma è giusto saperlo.
