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
- [x] Ingest + backend for forbruk (ENTSO-E Actual Total Load)
- [x] Kraftbalanse (produksjon − forbruk): historisk + neste dags prediksjon for Norge og sporede europeiske soner
- [x] Scenario-fane: fremskrivning 1-5 år frem med brukerstyrte vekstrater, inkl. "med vs. uten utbygging"-sammenligning
- [x] Automatisert ingest + periodisk re-trening via cron (`ops/scheduler/`)
- [x] Kraft-i-rørledningen: vann-/vindkraftverk under bygging/med konsesjon per prisområde (NVE, uverifisert skjema)

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
│   │   ├── client.py             # NVE Magasinstatistikk + kraftverksdatabase-klienter (ingen nøkkel nødvendig)
│   │   └── zones.py              # Grov fylke -> elspot-sone-tilnærming
│   ├── met/
│   │   ├── client.py             # MET Norway Frost API-klient (værobservasjoner)
│   │   └── stations.py           # Sone -> værstasjon-ID
│   ├── fetch_prices.py     # Henter day-ahead spotpriser og lagrer i DB + CSV
│   ├── fetch_production.py # Henter produksjon per type og lagrer i DB + CSV
│   ├── fetch_consumption.py # Henter faktisk forbruk (ENTSO-E A65) og lagrer i DB + CSV
│   ├── fetch_flow.py       # Henter grenseflyt på utenlandskabler og lagrer i DB + CSV
│   ├── fetch_reservoir.py  # Henter magasinfylling fra NVE og lagrer i DB + CSV
│   ├── fetch_weather.py    # Henter værobservasjoner og lagrer i DB + CSV
│   ├── fetch_capacity_pipeline.py # Henter vann-/vindkraftverk under bygging/med konsesjon fra NVE
│   ├── plot_prices.py      # Genererer interaktiv graf over siste N dager
│   ├── run_all.py          # Kjører alle fetch_*.py-scriptene samlet (brukes av cron-jobben)
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
│   │   │   ├── features.py    # Bygger (sone, dag)-features fra alle 6 datakilder
│   │   │   ├── train.py       # Trener og lagrer begge modellene (kjøres manuelt/periodisk)
│   │   │   └── predict.py     # Laster trente modeller og predikerer neste dags pris/balanse
│   │   └── routers/
│   │       ├── prices.py      # /prices, /prices/latest, /prices/daily-average, /prices/zones
│   │       ├── production.py  # /production, /production/latest, /production/mix, /production/types
│   │       ├── consumption.py # /consumption, /consumption/latest
│   │       ├── flow.py        # /flow, /flow/latest, /flow/daily-average, /flow/interconnectors
│   │       ├── reservoir.py   # /reservoir, /reservoir/latest
│   │       ├── weather.py     # /weather, /weather/latest
│   │       ├── analysis.py    # /analysis/price-vs-production, /price-vs-reservoir, /price-spread-vs-flow, /price-vs-weather, /production-vs-weather
│   │       ├── predict.py     # /predict/price, /predict/model-info
│   │       ├── deficit.py     # /deficit, /deficit/forecast, /deficit/scenario, /deficit/model-info
│   │       └── capacity.py    # /capacity/pipeline — kraftverk under bygging/med konsesjon fra NVE, per sone
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/            # React + TypeScript + Vite: interaktivt dashboard
│   ├── src/
│   │   ├── api.ts            # fetch-wrapper mot backend
│   │   ├── types.ts           # TS-typer som speiler backend sine Pydantic-modeller
│   │   ├── constants.ts        # Sonefarger, sonelister, værvariabel-metadata
│   │   ├── format.ts            # Pivot/formatteringshjelpere for Recharts
│   │   ├── mapColors.ts          # Sone-layout + fargeskala, delt av kart-komponentene
│   │   ├── useApiData.ts         # Fetch-hook med loading/error-håndtering
│   │   ├── App.tsx                # Fane-navigasjon
│   │   └── components/             # PriceSection, ProductionSection, FlowSection,
│   │                                # ReservoirSection, WeatherSection, AnalysisSection,
│   │                                # PredictionSection, DeficitSection, ScenarioSection,
│   │                                # ZoneMap (delt skjematisk kart), BalanceMapSection
│   ├── package.json
│   └── Dockerfile
├── ops/
│   └── scheduler/       # Docker-image med cron: kjører run_all.py daglig og app.ml.train ukentlig
│       ├── Dockerfile
│       ├── crontab
│       └── entrypoint.sh
├── docs/               # Notater og dokumentasjon
├── docker-compose.yml  # TimescaleDB + backend + frontend + scheduler lokalt
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

### 8. Hent forbruk

```bash
python fetch_consumption.py --days 7
```

Dette henter faktisk forbruk (ENTSO-E documentType A65, "Actual Total
Load") for samme sonesett, og lagrer i `output/consumption.csv` og/eller
`consumption`-tabellen. Sammen med produksjonsdataene fra forrige steg gir
dette grunnlaget for `/deficit`-endepunktene i backend: produksjon minus
forbruk = kraftbalanse, og negativ balanse = underskudd.

### 9. Hent grenseflyt

```bash
python fetch_flow.py --days 7
```

Dette henter fysisk kraftflyt (ENTSO-E documentType A11) for NorNed,
NordLink, North Sea Link, Skagerrak og Kontiskan, i begge retninger per
kabel (flyt kan gå begge veier avhengig av time), og lagrer i
`output/flow.csv` og/eller `cross_border_flow`-tabellen. North Sea Link
bruker Storbritannia (GB) som eneste bruk av den sonen i ingest — GB har
ellers ingen pris-/produksjonsingest.

### 10. Hent magasinfylling

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

### 11. Skaff API-nøkkel for MET Norway og hent værdata

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

### 12. Start backend-API

Krever at databasen kjører (steg 3) og at den er fylt med data (steg 5, 7, 8, 9, 10 og 11).

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
| `GET /consumption?zone=NO1&start=...&end=...&limit=...` | Rå forbrukstidsserie (MW), filtrert på sone/periode |
| `GET /consumption/latest` | Siste forbrukstall per sone |
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
| `GET /predict/price?zone=NO1` | Predikert snittpris neste dag, med hvilke features som eventuelt manglet data. 503 hvis modellen ikke er trent ennå (se steg 13) |
| `GET /predict/model-info` | Metadata om prismodellen: når den ble trent, holdout-metrikker (MAE/RMSE/R²), feature-viktighet |
| `GET /deficit?zone=NO1&start=...&end=...&limit=...` | Faktisk historisk kraftbalanse (produksjon − forbruk, MW), timesvis. `zone` kan være en enkeltsone eller aggregatene `NO` (NO1-NO5 samlet) / `EU` (sporede europeiske soner samlet) |
| `GET /deficit/forecast?zone=NO1` | Predikert kraftbalanse neste dag. For `NO`/`EU` summeres individuelle soneprediksjon, vist i `zone_breakdown` |
| `GET /deficit/model-info` | Metadata om balansemodellen: metrikker (MAE/RMSE i MW), feature-viktighet |
| `GET /deficit/scenario?zone=NO1&consumption_growth_pct=2&production_growth_pct=0&years=5&baseline_days=30` | Deterministisk hva-hvis-fremskrivning 1-5 år frem — **ikke** en trent prediksjon. Snittproduksjon/-forbruk siste `baseline_days` dager vokser med de valgte årlige ratene |

Alle `/analysis`-endepunkter returnerer både de justerte punktparene (for
scatter-plot i frontend) og en `pearson_r`-verdi (`null` hvis færre enn 2
punkter eller ingen varians i en av seriene).

### 13. Tren modellene (valgfritt)

Krever backend-avhengighetene (steg 12) og minst noen ukers historikk med
data fra alle seks kildene i databasen — gjerne kjør ingest-scriptene
periodisk en stund før du trener.

```bash
cd backend
python -m app.ml.train
```

Dette trener to modeller i samme kjøring: prismodellen (`model.joblib`)
og balansemodellen (`deficit_model.joblib`, produksjon minus forbruk neste
dag — negativ betyr predikert underskudd). Hvis det ikke finnes nok
forbruksdata ennå (steg 8), hopper scriptet over balansemodellen med en
tydelig advarsel og trener prismodellen som normalt — det ene datagapet
stopper ikke det andre.

Begge modellene bygger på samme features: én rad per (sone, dag) fra
spotpriser, produksjonsmiks, forbruk, grenseflyt, magasinfylling og
værdata, med laggede prisverdier, dagens kraftbalanse (produksjon minus
forbruk) og sesongvariabler. Trent med `HistGradientBoostingRegressor`
(scikit-learn) og tidsbasert train/test-splitt (siste 20% av dagene
holdes utenfor treningen). Modellene lagres til `app/ml/model.joblib` og
`app/ml/deficit_model.joblib` (ingen av delene i git — genererte
artefakter, gjenskapes ved å kjøre scriptet på nytt). Manglende kilder for
en sone (f.eks. ingen magasin-/værdata for europeiske soner) håndteres
som `NaN`, ikke som feil.

Treningsscriptet skriver ut MAE/RMSE/R² på holdout-settet og de åtte
viktigste featurene (permutation importance) for hver modell, slik at du
kan vurdere om modellene faktisk har lært noe fornuftig før du stoler på
prediksjonene. Kjør på nytt periodisk (f.eks. ukentlig) for å holde
modellene oppdatert — de retrenes ikke automatisk.

### 14. Start frontend-dashboardet

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Dashboardet kjører nå på http://localhost:5173. Det har ni faner —
Priser, Produksjon, Grenseflyt, Magasinfylling, Vær, Korrelasjon,
Prediksjon, Kraftbalanse og Scenario 1-5 år — som alle henter data fra
backend-API-et.

Kraftbalanse-fanen viser et **skjematisk kart** over alle ti
prisområdene (NO1-NO5 + DE_LU, DK1, DK2, NL, SE3) farget etter predikert
kraftbalanse neste dag (rødt = underskudd, grønt = overskudd — se
`BalanceMapSection.tsx`), samt historisk produksjon-vs-forbruk og en
detaljert neste-dags-prediksjon for Norge samlet, europeiske soner
samlet, eller enkeltsoner. Kartet er en forenklet skjematisk fremstilling
med relative posisjoner (ikke ekte geografiske grenser) — presis
kartografi for prisområdene var ikke tilgjengelig i miljøet dette ble
bygget i.

Scenario-fanen (`ScenarioSection.tsx`) svarer på "hva om forbruket vokser
X% i året" 1-5 år frem — **ikke** en ML-prediksjon (dagligmodellen har
ingen mening så langt frem), men en transparent fremskrivning av dagens
snittproduksjon/-forbruk med brukerstyrte vekstrater (glidebrytere for
forbruksvekst og produksjonsvekst), med samme skjematiske kart (nå med en
årsvelger) og en linjegraf over balanseutviklingen. Gjenbruker
`ZoneMap.tsx` og `mapColors.ts` fra Kraftbalanse-fanen.

Scenario-fanen har også en sammenligningsseksjon, "Konsekvens av å ikke
bygge ut i tide", ment som et konkret faktagrunnlag for
utbyggingsdiskusjoner: to `/deficit/scenario`-kall med samme forbruksvekst
men ulik produksjonsvekst (brukerstyrt "med utbygging"-rate vs. fast 0 %
"uten utbygging") plottes sammen i én graf, med en utregnet "underskudd fra
år X"-callout per scenario (første år balansen blir negativ, eller "ingen
underskudd innen 5 år"). Ingen nye backend-endepunkter — `/deficit/scenario`
tok allerede vekstrater som parametre.

Uten data i databasen vises "Ingen data" i hver seksjon i stedet for en
graf; det er ikke en feil.

Alternativt, kjør hele stacken (database + backend + frontend) med Docker:

```bash
docker compose up -d
```

Frontend blir da tilgjengelig på http://localhost:5173 (bygget statisk og
servert via nginx), backend på http://localhost:8000, begge koblet mot
`db`-tjenesten.

### 15. Automatisk ingest + re-trening (cron)

`docker compose up -d` starter også en `scheduler`-tjeneste
(`ops/scheduler/`) — et lite Docker-image med `cron` som kjører uten at
noen trenger å logge inn og kjøre scriptene manuelt:

- **Daglig kl. 03:00 UTC**: `ingest/run_all.py --days 2` — kjører alle
  `fetch_*.py`-scriptene på rad (pris, produksjon, flyt, forbruk, vær,
  magasin, og utbyggingspipeline, se steg 16). `--days 2` overlapper forrige
  kjøring med vilje (alle databaseskriv er upserts på
  `(zone, timestamp, source)` eller tilsvarende, så det er trygt å hente
  samme periode to ganger — en forsinket/glemt time reparerer seg selv
  neste natt).
- **Ukentlig, søndag kl. 04:00 UTC**: `python -m app.ml.train` — trener
  begge modellene på nytt på den ferskeste dataen. Modellfilene
  (`backend/app/ml/*.joblib`) deles mellom `scheduler`- og
  `backend`-containeren via en bind mount, så `backend` plukker opp den nye
  modellen automatisk (den sjekker filens endringstidspunkt ved hver
  prediksjon) — ingen restart nødvendig.

`scheduler` trenger de samme miljøvariablene som ingest-scriptene
(`ENTSOE_API_KEY`, `MET_FROST_CLIENT_ID`) — sett dem i en `.env`-fil i
repo-roten (samme som `.env.example`), så plukker `docker compose` dem opp
automatisk. NVE-henting (`fetch_reservoir.py`) trenger ingen nøkkel og
kjører uansett.

For å kjøre en jobb manuelt (f.eks. for å teste, eller bootstrappe historikk
før første cron-kjøring):

```bash
docker compose exec scheduler python3 /app/ingest/run_all.py --days 30
docker compose exec scheduler sh -c "cd /app/backend && python3 -m app.ml.train"
```

Logger fra begge jobbene havner i `/var/log/cron.log` inni containeren og
strømmes til `docker compose logs -f scheduler`. Tidspunktene er satt i
`ops/scheduler/crontab` — juster der og bygg containeren på nytt
(`docker compose build scheduler`) om du vil ha en annen frekvens.

Under utvikling av denne funksjonen ble en reell bug i tidligere
`train.py` funnet og fikset: en feature som er 100 % NaN i hele
treningssettet (f.eks. `fill_percent`/`temp_avg` for soner uten
magasin-/værdata ennå) fikk `HistGradientBoostingRegressor` til å krasje i
nyere scikit-learn-versjoner. `train_one()` dropper nå slike helt-tomme
features før trening (og lagrer den faktiske feature-listen i
`model.joblib`, som `predict.py` nå leser derfra i stedet for en fast
konstant) — viktig for at en automatisk, ubevoktet ukentlig re-trening
faktisk er pålitelig fra dag én, før alle datakilder har rukket å fylles
opp for alle soner.

### 16. Kraft i rørledningen — utbyggingspipeline fra NVE

Scenario-fanen viser nå også "Kraft i rørledningen (NVE)": vann- og
vindkraftverk som er **under bygging** eller har **fått konsesjon** (ikke i
drift ennå), summert per prisområde. Dette er et faktafeed for
kraftutbyggingsdiskusjonen — hva er faktisk vedtatt/i gang, ikke et
behovs- eller prognosetall som scenario-verktøyet.

Hentes av `fetch_capacity_pipeline.py` fra to NVE-endepunkter
(`ingest/nve/client.py`):

- `GetHydroPowerPlants` — bekreftet (via NVEs eget eksempelscript på
  GitHub) å inkludere anlegg under bygging, ikke bare de som er i drift.
- `GetWindPowerPlantsInOperation` — det eneste vindkraft-endepunktet som
  ble bekreftet herfra; navnet antyder at det **kun** dekker anlegg
  allerede i drift, så vinddelen av pipelinen kan være ufullstendig inntil
  et bredere endepunkt er bekreftet med reell nettverkstilgang.

Sone settes med en grov fylke->sone-tilnærming
(`ingest/nve/zones.py`, `FYLKE_TO_ZONE`) — bidding zones følger ikke
fylkesgrenser nøyaktig (Innlandet er det største kjente tilfellet), så
`zone` kan være feil for anlegg nær en sonegrense. Anlegg med ukjent/
ukartlagt fylke beholdes med `zone = NULL` og telles i
`unmapped_effect_mw` i stedet for å forsvinne stille.

**Viktig**: feltnavnene i NVEs JSON-respons (status, effekt, fylke, osv.)
er **ikke verifisert mot en reell kjøring** — api.nve.no var blokkert av
nettverksproxyen i miljøet dette ble bygget i. `_parse_plant_rows` i
`nve/client.py` feiler høylytt med en liste over faktiske nøkler i
responsen hvis ingen av kandidatnavnene treffer, i stedet for å stille
mappe feil data — samme mønster som `fetch_reservoir.py` allerede brukte.
Kjør `python fetch_capacity_pipeline.py --no-db` med ekte nettverkstilgang
og sjekk output/eventuell feilmelding før dette brukes til noe viktig.

## Datakilder

| Kilde | Bruk | Krever nøkkel? |
|---|---|---|
| [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/) | Hovedkilde: pris, produksjon, flyt for Norge og Europa | Ja (gratis registrering) |
| [MET Norway Frost API](https://frost.met.no/) | Værobservasjoner (temperatur, vind, nedbør) per sone (brukt av `fetch_weather.py`) | Ja (gratis, umiddelbar) |
| [NVE Magasinstatistikk](https://www.nve.no/energi/analyser-og-statistikk/magasinstatistikk/) | Ukentlig magasinfylling per elspot-sone (brukt av `fetch_reservoir.py`) | Nei |
| [NVE Vannkraftdatabase](https://api.nve.no/doc/vannkraftdatabase/) (`GetHydroPowerPlants`) | Vannkraftverk under bygging/med konsesjon — kraft-i-rørledningen (brukt av `fetch_capacity_pipeline.py`) | Nei |
| [NVE Vindkraftdatabase](https://api.nve.no/doc/vindkraftdatabase/) (`GetWindPowerPlantsInOperation`) | Samme for vindkraft — **kun bekreftet for anlegg i drift**, se advarsel i steg 16 | Nei |
| [Statnett "Tall og data"](https://www.statnett.no/for-aktorer-i-kraftsystemet/tall-og-data-fra-kraftsystemet/) | Alternativ kilde for sanntid/historikk på flyt og fyllingsgrad | Nei |
| [Statnett tilknytningsdatabase](https://www.statnett.no/for-aktorer-i-kraftbransjen/nettkapasitet-til-produksjon-og-forbruk/foresporsler-og-reservasjon-i-nettet/) | Nettilknytningskø — hvem har reservert kapasitet, hvor mye, hvor. Ikke integrert ennå (ikke et rent API, kun Excel-eksport fra nettsiden) | Nei |
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
5. **Prediksjonslag** (`backend/app/ml/`) — to gradient boosting-modeller
   (scikit-learn `HistGradientBoostingRegressor`) trent på laggede
   features fra alle seks kilder: én predikerer neste dags snittpris per
   sone, én predikerer neste dags kraftbalanse (produksjon minus forbruk)
   — negativ balanse er et predikert underskudd. Trenes sammen via
   `train.py`, serveres via `/predict` og `/deficit/forecast`.
6. **Scenariolag** (`/deficit/scenario`) — en enkel deterministisk
   fremskrivning, bevisst atskilt fra prediksjonslaget: dagens
   snittproduksjon/-forbruk vokser med brukerstyrte årlige rater, 1-5 år
   frem. Ingen trent modell involvert — dette er for langt frem til at
   den daglige ML-modellen kan si noe meningsfullt.
7. **Frontend/dashboard** (`frontend/`) — React + TypeScript + Vite +
   Recharts. Fane-basert: tidsserier for pris/produksjon/flyt/magasin/vær,
   spredningsdiagram med Pearson-korrelasjon, prisprediksjon, kraftbalanse
   (historisk + prediksjon, pluss et skjematisk fargekodet kart over alle
   ti sonene) og et scenario-verktøy med glidebrytere for vekstrater, hver
   med modell-metrikker/feature-viktighet der det er relevant.

## Neste steg

- Verifisere `nve/client.py` og `met/client.py` mot ekte API-svar (se
  merknader i steg 10 og 11 over) og justere feltnavn/stasjons-ID-er ved behov
- Sette API-nøkler i `.env` og starte `scheduler`-tjenesten i produksjon
  (se steg 15) slik at dashboardet viser ferske data i stedet for manuelt
  genererte øyeblikksbilder — dette gir også prediksjonsmodellene ekte
  historikk å trene på
- Utvide "EU"-aggregatet i `/deficit` utover de fem sporede sonene
  (DE_LU, DK1, DK2, NL, SE3) hvis bredere europeisk dekning blir viktig —
  krever ingest for flere soner, ikke bare en kodeendring
- Vurdere autentisering/rate-limiting på backend-API-et før eventuell
  offentlig eksponering
