# Kraft-analyse

Dashboard for analyse av det norske kraftsystemet: sammenhengen mellom
produksjon, pris, magasinfylling og vær i Norge (NO1-NO5) sammenlignet med
utvalgte europeiske prisområder (DE, DK1, DK2, NL, SE).

## Status

Første leveranse (steg 1 av flere):

- [x] Repo-struktur (`ingest/`, `backend/`, `frontend/`, `db/`, `docs/`)
- [x] Ingest-script som henter dagens spotpriser for NO1-NO5 + DE/DK1/DK2/NL/SE3 fra ENTSO-E
- [x] Enkel graf over prisene siste 7 dager
- [x] FastAPI-backend for spotprisdataene
- [x] Ingest + backend for produksjonsmiks per sone
- [x] Ingest + backend for import/eksport-flyt på utenlandskabler
- [x] Ingest + backend for magasinfylling (NVE)
- [x] Ingest + backend for værdata (MET Norway)
- [x] Korrelasjonsanalyse (backend)
- [x] Interaktivt frontend-dashboard
- [x] Prisprediksjonsmodell (gradient boosting, neste dags pris per sone)

## Repo-struktur

```
Kraft-analyse-/
├── ingest/           # Python: henter data fra ENTSO-E/Statnett og lagrer i DB/CSV
│   ├── entsoe/
│   │   ├── client.py            # ENTSO-E API-klient (XML-parsing, retry/rate-limit)
│   │   ├── zones.py             # Bidding zone -> EIC-kode mapping
│   │   ├── production_types.py  # PSR-typekode -> lesbar produksjonstype
│   │   └── interconnectors.py   # Utenlandskabel -> sonepar (+ GB EIC for North Sea Link)
│   ├── nve/
│   │   └── client.py             # NVE Magasinstatistikk API-klient (ingen nøkkel nødvendig)
│   ├── met/
│   │   ├── client.py             # MET Norway Frost API-klient (værobservasjoner)
│   │   └── stations.py           # Sone -> værstasjon-ID
│   ├── fetch_prices.py     # Henter day-ahead spotpriser og lagrer i DB + CSV
│   ├── fetch_production.py # Henter produksjon per type og lagrer i DB + CSV
│   ├── fetch_flow.py       # Henter grenseflyt på utenlandskabler og lagrer i DB + CSV
│   ├── fetch_reservoir.py  # Henter magasinfylling fra NVE og lagrer i DB + CSV
│   ├── fetch_weather.py    # Henter værobservasjoner og lagrer i DB + CSV
│   ├── plot_prices.py      # Genererer interaktiv graf over siste N dager
│   └── output/              # Genererte CSV/HTML (ikke i git)
├── db/
│   └── schema.sql      # TimescaleDB-skjema (pris, produksjon, flyt, magasin, vær, forbruk)
├── backend/            # FastAPI: REST-API for spotpris-, produksjons-, flyt-, magasin- og værdata
│   ├── app/
│   │   ├── main.py           # App-oppsett, CORS, /health
│   │   ├── config.py         # Settings (DATABASE_URL m.m.) via pydantic-settings
│   │   ├── db.py             # psycopg2 connection pool
│   │   ├── zones.py          # Sone-metadata (kode -> navn) + validate_zone()
│   │   ├── interconnectors.py # Utenlandskabel-metadata (navn -> sonepar) + validate_interconnector()
│   │   ├── stats.py          # pearson_r() — delt av /analysis-endepunktene
│   │   ├── schemas.py        # Pydantic-responsmodeller
│   │   ├── ml/
│   │   │   ├── features.py    # Bygger (sone, dag)-features fra alle 5 datakilder
│   │   │   ├── train.py       # Trener og lagrer prisprediksjonsmodellen (kjøres manuelt/periodisk)
│   │   │   └── predict.py     # Laster trent modell og predikerer neste dags pris
│   │   └── routers/
│   │       ├── prices.py      # /prices, /prices/latest, /prices/daily-average, /prices/zones
│   │       ├── production.py  # /production, /production/latest, /production/mix, /production/types
│   │       ├── flow.py        # /flow, /flow/latest, /flow/daily-average, /flow/interconnectors
│   │       ├── reservoir.py   # /reservoir, /reservoir/latest
│   │       ├── weather.py     # /weather, /weather/latest
│   │       ├── analysis.py    # /analysis/price-vs-production, /price-vs-reservoir, /price-spread-vs-flow, /price-vs-weather, /production-vs-weather
│   │       └── predict.py     # /predict/price, /predict/model-info
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/            # React + TypeScript + Vite: interaktivt dashboard
│   ├── src/
│   │   ├── api.ts            # fetch-wrapper mot backend
│   │   ├── types.ts           # TS-typer som speiler backend sine Pydantic-modeller
│   │   ├── constants.ts        # Sonefarger, sonelister, værvariabel-metadata
│   │   ├── format.ts            # Pivot/formatteringshjelpere for Recharts
│   │   ├── useApiData.ts         # Fetch-hook med loading/error-håndtering
│   │   ├── App.tsx                # Fane-navigasjon
│   │   └── components/             # PriceSection, ProductionSection, FlowSection,
│   │                                # ReservoirSection, WeatherSection, AnalysisSection,
│   │                                # PredictionSection
│   ├── package.json
│   └── Dockerfile
├── docs/               # Notater og dokumentasjon
├── docker-compose.yml  # TimescaleDB + backend + frontend lokalt
└── .env.example
```

## Oppsett

### 1. Skaff API-nøkkel for ENTSO-E

1. Registrer en gratis konto på https://transparency.entsoe.eu/
2. Gå til "My Account Settings" -> "Web API Security Token" og be om tilgang
3. Kopier nøkkelen inn i `.env` (se under)

### 2. Konfigurer miljøvariabler

```bash
cp .env.example .env
# Fyll inn ENTSOE_API_KEY i .env
```

### 3. Start databasen (valgfritt for steg 1 — CSV fungerer uten DB)

```bash
docker compose up -d
```

Dette starter PostgreSQL + TimescaleDB på port 5432 og kjører `db/schema.sql`
automatisk ved første oppstart.

### 4. Installer Python-avhengigheter

```bash
cd ingest
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 5. Hent priser

```bash
python fetch_prices.py --days 7
```

Dette henter day-ahead spotpriser for NO1-NO5, DE_LU, DK1, DK2, NL og SE3 for
de siste 7 dagene, og lagrer dem i `output/prices.csv`. Hvis `DATABASE_URL`
er satt i `.env` og databasen kjører, skrives dataene også til
`spot_price`-tabellen i TimescaleDB.

### 6. Generer graf

```bash
python plot_prices.py
```

Åpne `output/prices_chart.html` i en nettleser for å se en interaktiv
tidsserie-graf med alle sonene siste 7 dager.

### 7. Hent produksjonsmiks

```bash
python fetch_production.py --days 7
```

Dette henter faktisk produksjon per produksjonstype (ENTSO-E documentType
A75, "Actual Generation per Type") for samme sonesett, mapper ENTSO-E sine
PSR-typekoder (B01, B11, B19, ...) til lesbare typer (`hydro`,
`wind_onshore`, `solar`, ...), og lagrer i `output/production.csv` og/eller
`production_per_source`-tabellen. Forbruk/pumping i pumpekraftverk
(businessType A04) filtreres bort — dette er produksjon, ikke last.

### 8. Hent grenseflyt

```bash
python fetch_flow.py --days 7
```

Dette henter fysisk kraftflyt (ENTSO-E documentType A11) for NorNed,
NordLink, North Sea Link, Skagerrak og Kontiskan, i begge retninger per
kabel (flyt kan gå begge veier avhengig av time), og lagrer i
`output/flow.csv` og/eller `cross_border_flow`-tabellen. North Sea Link
bruker Storbritannia (GB) som eneste bruk av den sonen i ingest — GB har
ellers ingen pris-/produksjonsingest.

### 9. Hent magasinfylling

```bash
python fetch_reservoir.py --days 365
```

Dette henter ukentlig magasinfylling for NO1-NO5 og hele-landet-aggregatet
("NO") fra NVEs Magasinstatistikk-API og lagrer i `output/reservoir.csv`
og/eller `reservoir_fill`-tabellen. Krever ingen API-nøkkel.

**Merk:** denne integrasjonen er ikke verifisert mot et ekte API-svar —
utgående nettverkstilgang til nve.no var blokkert i miljøet den ble bygget
i. Feltnavnene i `nve/client.py` er basert på NVEs dokumenterte skjema,
men parsingen validerer feltene og feiler med en tydelig feilmelding
(inkl. de faktiske feltnavnene den fant) hvis skjemaet har endret seg —
kjør scriptet og se etter en eventuell feilmelding før du stoler på det i
produksjon.

### 10. Skaff API-nøkkel for MET Norway og hent værdata

1. Registrer deg gratis på https://frost.met.no/auth/requestCredentials.html
   (ingen ventetid — nøkkelen utstedes umiddelbart)
2. Kopier client-ID-en inn i `.env` som `MET_FROST_CLIENT_ID`

```bash
python fetch_weather.py --days 7
```

Dette henter timesvis temperatur, vindstyrke og nedbør fra én representativ
værstasjon per sone (Oslo, Kristiansand, Trondheim, Tromsø, Bergen — se
`met/stations.py`), og lagrer i `output/weather.csv` og/eller
`weather_observation`-tabellen. Værdata er relevant for analysen fordi
temperatur driver oppvarmingsforbruk, vindstyrke driver vindkraftproduksjon,
og nedbør driver tilsig til vannkraftmagasinene.

**Merk:** som med NVE-integrasjonen er heller ikke denne verifisert mot et
ekte API-svar — utgående nettverkstilgang til frost.met.no var blokkert i
miljøet den ble bygget i. `met/client.py` validerer responsformen og
feiler tydelig (med de faktiske nøklene den fant) hvis Frost API sitt
skjema har endret seg. Stasjons-ID-ene i `met/stations.py` bør også
dobbeltsjekkes mot https://frost.met.no/sources.html.

### 11. Start backend-API

Krever at databasen kjører (steg 3) og at den er fylt med data (steg 5, 7, 8, 9 og 10).

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API-et kjører nå på http://localhost:8000, med interaktiv dokumentasjon på
http://localhost:8000/docs. Konfigurasjon (DATABASE_URL) leses fra samme
`.env`-fil som ingest-scriptene.

Endepunkter:

| Endepunkt | Beskrivelse |
|---|---|
| `GET /health` | Liveness + DB-tilkoblingsstatus |
| `GET /prices/zones` | Liste over tilgjengelige soner (kode + navn) |
| `GET /prices?zone=NO1&start=...&end=...&limit=...` | Rå tidsserie, filtrert på sone/periode (default: siste 7 dager, maks 20 000 rader) |
| `GET /prices/latest` | Siste prispunkt per sone |
| `GET /prices/daily-average?zone=NO1&days=7` | Daglig snitt/min/maks per sone |
| `GET /production/types?zone=NO1` | Distinkte produksjonstyper i databasen |
| `GET /production?zone=NO1&production_type=hydro&start=...&end=...&limit=...` | Rå produksjonstidsserie (MW), filtrert på sone/type/periode |
| `GET /production/latest?zone=NO1` | Siste produksjonstall per sone og type |
| `GET /production/mix?zone=NO1&days=7` | Produksjonsmiks: snitt-MW og prosentandel per type, siste N dager |
| `GET /flow/interconnectors` | Liste over sporede utenlandskabler (navn + sonepar) |
| `GET /flow?from_zone=NO2&to_zone=NL&interconnector=NorNed&start=...&end=...&limit=...` | Rå flyt-tidsserie (MW), filtrert på soner/kabel/periode |
| `GET /flow/latest` | Siste flytverdi per soneparsretning |
| `GET /flow/daily-average?interconnector=NorNed&days=7` | Daglig snittflyt per soneparsretning |
| `GET /reservoir?zone=NO1&start=...&end=...&limit=...` | Ukentlig magasinfylling (%), filtrert på sone/periode (default: siste år) |
| `GET /reservoir/latest` | Siste fyllingsgrad per sone, inkl. nasjonalt aggregat ("NO") |
| `GET /weather?zone=NO1&start=...&end=...&limit=...` | Rå værobservasjoner (temperatur, vind, nedbør), filtrert på sone/periode |
| `GET /weather/latest` | Siste værobservasjon per sone |
| `GET /analysis/price-vs-production?zone=NO1&production_type=hydro&days=30` | Pris vs. produksjon av en gitt type, timesvis, med Pearson-korrelasjon |
| `GET /analysis/price-vs-reservoir?zone=NO1&weeks=52` | Ukentlig snittpris vs. magasinfylling, med Pearson-korrelasjon |
| `GET /analysis/price-spread-vs-flow?zone_a=NO2&zone_b=NL&interconnector=NorNed&days=30` | Prisdifferanse mellom to soner vs. netto kabelflyt, med Pearson-korrelasjon |
| `GET /analysis/price-vs-weather?zone=NO1&weather_variable=wind_speed_ms&days=30` | Pris vs. værvariabel (temperature_c/wind_speed_ms/precipitation_mm), med Pearson-korrelasjon |
| `GET /analysis/production-vs-weather?zone=NO1&production_type=wind_onshore&weather_variable=wind_speed_ms&days=30` | Produksjon av en gitt type vs. værvariabel, med Pearson-korrelasjon |
| `GET /predict/price?zone=NO1` | Predikert snittpris neste dag, med hvilke features som eventuelt manglet data. 503 hvis modellen ikke er trent ennå (se steg 12) |
| `GET /predict/model-info` | Metadata om trent modell: når den ble trent, holdout-metrikker (MAE/RMSE/R²), feature-viktighet |

Alle `/analysis`-endepunkter returnerer både de justerte punktparene (for
scatter-plot i frontend) og en `pearson_r`-verdi (`null` hvis færre enn 2
punkter eller ingen varians i en av seriene).

### 12. Tren prisprediksjonsmodellen (valgfritt)

Krever backend-avhengighetene (steg 11) og minst noen ukers historikk med
data fra alle fem kilder i databasen — gjerne kjør ingest-scriptene
periodisk en stund før du trener.

```bash
cd backend
python -m app.ml.train
```

Dette bygger én rad per (sone, dag) fra spotpriser, produksjonsmiks,
grenseflyt, magasinfylling og værdata, med laggede prisverdier og en
"neste dags snittpris"-target, og trener en `HistGradientBoostingRegressor`
(scikit-learn) med tidsbasert train/test-splitt (siste 20% av dagene
holdes utenfor treningen). Modellen lagres til `app/ml/model.joblib`
(ikke i git — en generert artefakt, gjenskapes ved å kjøre scriptet på
nytt). Manglende kilder for en sone (f.eks. ingen magasin-/værdata for
europeiske soner) håndteres som `NaN` av modellen, ikke som feil.

Treningsscriptet skriver ut MAE/RMSE/R² på holdout-settet og de åtte
viktigste featurene (permutation importance), slik at du kan vurdere om
modellen faktisk har lært noe fornuftig før du stoler på prediksjonene.
Kjør på nytt periodisk (f.eks. ukentlig) for å holde modellen oppdatert —
den retrenes ikke automatisk.

### 13. Start frontend-dashboardet

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Dashboardet kjører nå på http://localhost:5173. Det har seks faner —
Priser, Produksjon, Grenseflyt, Magasinfylling, Vær og Korrelasjon — som
alle henter data fra backend-API-et. Uten data i databasen vises "Ingen
data" i hver seksjon i stedet for en graf; det er ikke en feil.

Alternativt, kjør hele stacken (database + backend + frontend) med Docker:

```bash
docker compose up -d
```

Frontend blir da tilgjengelig på http://localhost:5173 (bygget statisk og
servert via nginx), backend på http://localhost:8000, begge koblet mot
`db`-tjenesten.

## Datakilder

| Kilde | Bruk | Krever nøkkel? |
|---|---|---|
| [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/) | Hovedkilde: pris, produksjon, flyt for Norge og Europa | Ja (gratis registrering) |
| [MET Norway Frost API](https://frost.met.no/) | Værobservasjoner (temperatur, vind, nedbør) per sone (brukt av `fetch_weather.py`) | Ja (gratis, umiddelbar) |
| [NVE Magasinstatistikk](https://www.nve.no/energi/analyser-og-statistikk/magasinstatistikk/) | Ukentlig magasinfylling per elspot-sone (brukt av `fetch_reservoir.py`) | Nei |
| [Statnett "Tall og data"](https://www.statnett.no/for-aktorer-i-kraftsystemet/tall-og-data-fra-kraftsystemet/) | Alternativ kilde for sanntid/historikk på flyt og fyllingsgrad | Nei |
| [Hva koster strømmen](https://www.hvakosterstrommen.no/strompriser-api) | Backup/supplement for norske spotpriser | Nei |
| [Elhub](https://elhub.no/data/) | Forbruk og produksjon i Norge (CSV/XLSX) | Nei |
| [NVE dataplattform](https://www.nve.no/energi/energisystem/kraftproduksjon/) | Nettleie/produksjonsdata | Nei (delvis) |

## Arkitektur (planlagt)

1. **Ingest-lag** (`ingest/`) — periodisk henting fra ENTSO-E og Statnett, med
   rate-limit-håndtering og retry. Kan kjøres via cron eller en scheduler
   (f.eks. `systemd timer`, GitHub Actions, eller Airflow ved behov for mer
   robusthet).
2. **Database** (`db/`) — PostgreSQL med TimescaleDB-extension. Hypertables
   for pris, produksjon per kilde, flyt mellom soner, magasinfylling, vær
   og forbruk — alle med sone + timestamp som nøkkel.
3. **Backend/API** (`backend/`) — REST- eller GraphQL-API som eksponerer
   rå og aggregerte tidsserier til frontend.
4. **Analyselag** (`backend/app/routers/analysis.py`) — Pearson-korrelasjon
   mellom pris vs. produksjonsmiks, pris vs. fyllingsgrad, prisdifferanse
   mellom soner vs. kabelflyt, og produksjon/pris vs. værvariabler.
5. **Prediksjonslag** (`backend/app/ml/`) — gradient boosting-modell
   (scikit-learn `HistGradientBoostingRegressor`) trent på laggede
   features fra alle fem kilder, predikerer neste dags snittpris per sone.
   Trenes manuelt/periodisk via `train.py`, serveres via `/predict`.
6. **Frontend/dashboard** (`frontend/`) — React + TypeScript + Vite +
   Recharts. Fane-basert: tidsserier for pris/produksjon/flyt/magasin/vær,
   spredningsdiagram med Pearson-korrelasjon, og prisprediksjon med
   modell-metrikker og feature-viktighet.

## Neste steg

- Verifisere `nve/client.py` og `met/client.py` mot ekte API-svar (se
  merknader i steg 9 og 10 over) og justere feltnavn/stasjons-ID-er ved behov
- Kjøre ingest-scriptene jevnlig (cron/scheduler) slik at dashboardet viser
  ferske data i stedet for manuelt genererte øyeblikksbilder — dette gir
  også prisprediksjonsmodellen ekte historikk å trene på
- Sette opp periodisk re-trening av prediksjonsmodellen (f.eks. ukentlig
  cron-jobb som kjører `python -m app.ml.train` etter at ingest har kjørt)
- Vurdere autentisering/rate-limiting på backend-API-et før eventuell
  offentlig eksponering
