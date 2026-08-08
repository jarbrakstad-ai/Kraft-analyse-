# Kraft-analyse frontend

React + TypeScript + Vite dashboard for spotpriser, produksjonsmiks,
grenseflyt, magasinfylling, værdata og korrelasjonsanalyse. Konsumerer
`backend`-API-et (se `../backend/README.md`, eller repo-roten for
helhetlig oppsett).

## Oppsett

```bash
npm install
cp .env.example .env.local
# juster VITE_API_BASE_URL i .env.local om backend ikke kjører på localhost:8000
npm run dev
```

Åpner på http://localhost:5173. Krever at backend-API-et kjører (se
`../backend/README.md`) og har data — uten data vises "Ingen data" i hver
seksjon i stedet for en graf.

## Struktur

```
src/
├── api.ts              # fetch-wrapper mot backend, ett kall per endepunkt
├── types.ts             # TS-typer som speiler backend sine Pydantic-modeller
├── constants.ts          # Sonefarger, sonelister, værvariabel-metadata
├── format.ts              # Pivot/formatteringshjelpere for Recharts
├── useApiData.ts           # Hook: henter data på deps-endring, håndterer loading/error
├── App.tsx                  # Fane-navigasjon mellom seksjonene
└── components/
    ├── PriceSection.tsx      # Spotpriser, multi-sone linjediagram
    ├── ProductionSection.tsx  # Produksjonsmiks, kakediagram
    ├── FlowSection.tsx         # Grenseflyt per kabel, linjediagram
    ├── ReservoirSection.tsx     # Magasinfylling, linjediagram
    ├── WeatherSection.tsx        # Værdata, linjediagram
    └── AnalysisSection.tsx        # Korrelasjon, spredningsdiagram + Pearson r
```

## Bygg for produksjon

```bash
npm run build
```

Statiske filer havner i `dist/`. Sett `VITE_API_BASE_URL` til backend-API-ets
faktiske URL før bygg (miljøvariabelen bakes inn i bygget, ikke lest ved
kjøretid).
