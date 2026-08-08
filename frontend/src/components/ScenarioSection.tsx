import { useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { ALL_TRACKED_ZONES, DEFICIT_ZONE_OPTIONS } from "../constants";
import { formatNumber } from "../format";
import { useApiData } from "../useApiData";
import type { ScenarioForecast } from "../types";
import { Card } from "./Card";
import { StatusBox } from "./StatusBox";
import { ZoneMap } from "./ZoneMap";

const YEARS = 5;
const GROWTH_MIN = -5;
const GROWTH_MAX = 10;
const GROWTH_STEP = 0.5;

/** First year (1..YEARS) where the scenario tips into deficit, or null if it never does within the window. */
function crossoverYear(forecast: ScenarioForecast | null | undefined): number | null {
  if (!forecast) return null;
  const hit = forecast.years.find((y) => y.year > 0 && y.balance_mw < 0);
  return hit ? hit.year : null;
}

function GrowthSlider({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <label className="growth-slider">
      <span className="growth-slider-label">
        {label}: <strong>{value >= 0 ? "+" : ""}{formatNumber(value, 1)}% / år</strong>
      </span>
      <input
        type="range"
        min={GROWTH_MIN}
        max={GROWTH_MAX}
        step={GROWTH_STEP}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </label>
  );
}

export function ScenarioSection() {
  const [consumptionGrowth, setConsumptionGrowth] = useState(2);
  const [productionGrowth, setProductionGrowth] = useState(0);
  const [year, setYear] = useState(YEARS);
  const [chartZone, setChartZone] = useState("NO");

  // One scenario per real zone, fetched once per growth-rate change; the
  // year slider then just picks an index client-side — no refetch needed.
  // allSettled (not all) so one zone lacking data (e.g. no consumption
  // ingest yet) doesn't blank out the whole map for every other zone.
  const allZones = useApiData(
    async () => {
      const results = await Promise.allSettled(
        ALL_TRACKED_ZONES.map((z) => api.deficitScenario(z, consumptionGrowth, productionGrowth, YEARS)),
      );
      return results.filter((r) => r.status === "fulfilled").map((r) => r.value);
    },
    [consumptionGrowth, productionGrowth],
  );

  const chart = useApiData(
    () => api.deficitScenario(chartZone, consumptionGrowth, productionGrowth, YEARS),
    [chartZone, consumptionGrowth, productionGrowth],
  );

  const mapValues = useMemo(() => {
    if (!allZones.data) return [];
    return allZones.data.map((forecast) => ({
      zone: forecast.zone,
      balance_mw: forecast.years[year]?.balance_mw ?? forecast.years[forecast.years.length - 1].balance_mw,
    }));
  }, [allZones.data, year]);

  // "Med vs. uten utbygging": samme forbruksvekst, men produksjonen enten fortsetter å vokse
  // eller flater helt ut (0 %) — status quo, altså ingen ny kraftproduksjon bygges.
  const [compareZone, setCompareZone] = useState("NO");
  const [compareConsumptionGrowth, setCompareConsumptionGrowth] = useState(2);
  const [expansionGrowth, setExpansionGrowth] = useState(3);

  const withExpansion = useApiData(
    () => api.deficitScenario(compareZone, compareConsumptionGrowth, expansionGrowth, YEARS),
    [compareZone, compareConsumptionGrowth, expansionGrowth],
  );
  const withoutExpansion = useApiData(
    () => api.deficitScenario(compareZone, compareConsumptionGrowth, 0, YEARS),
    [compareZone, compareConsumptionGrowth],
  );

  const compareChartData = useMemo(() => {
    if (!withExpansion.data || !withoutExpansion.data) return [];
    return withExpansion.data.years.map((y, i) => ({
      year: y.year,
      med_utbygging: y.balance_mw,
      uten_utbygging: withoutExpansion.data!.years[i]?.balance_mw ?? null,
    }));
  }, [withExpansion.data, withoutExpansion.data]);

  const withExpansionCrossover = crossoverYear(withExpansion.data);
  const withoutExpansionCrossover = crossoverYear(withoutExpansion.data);

  const pipeline = useApiData(() => api.capacityPipeline(), []);
  const maxZoneEffect = useMemo(
    () => Math.max(1, ...(pipeline.data?.zones.map((z) => z.total_effect_mw) ?? [0])),
    [pipeline.data],
  );

  return (
    <>
      <Card title="Kraft i rørledningen (NVE)">
        <p className="hint">
          Vann- og vindkraftverk som er <strong>under bygging</strong> eller har{" "}
          <strong>fått konsesjon</strong> (ikke satt i drift ennå), hentet fra NVEs kraftverksdatabaser. Dette er en
          faktasjekk på hva som faktisk er i gang — ikke et behov- eller prognosetall.
        </p>

        <StatusBox loading={pipeline.loading} error={pipeline.error} empty={!pipeline.loading && (pipeline.data?.plants.length ?? 0) === 0} />

        {pipeline.data && pipeline.data.plants.length > 0 && (
          <>
            <div className="feature-bars" style={{ marginBottom: 20 }}>
              {pipeline.data.zones.map((z) => (
                <div key={z.zone} className="feature-bar-row pipeline-bar-row">
                  <span className="feature-bar-label">
                    {z.zone} ({z.n_plants})
                  </span>
                  <div className="feature-bar-track">
                    <div
                      className="feature-bar-fill"
                      style={{ width: `${(z.total_effect_mw / maxZoneEffect) * 100}%` }}
                    />
                  </div>
                  <span style={{ fontVariantNumeric: "tabular-nums", fontSize: 13, color: "var(--text-muted)" }}>
                    {formatNumber(z.total_effect_mw, 0)} MW
                  </span>
                </div>
              ))}
            </div>

            <table className="pipeline-table">
              <thead>
                <tr>
                  <th>Anlegg</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Sone</th>
                  <th>Effekt (MW)</th>
                  <th>Forventet idriftsettelse</th>
                </tr>
              </thead>
              <tbody>
                {pipeline.data.plants.map((p) => (
                  <tr key={`${p.source_type}-${p.plant_id}`}>
                    <td>{p.name}</td>
                    <td>{p.source_type === "hydro" ? "Vann" : "Vind"}</td>
                    <td>{p.status}</td>
                    <td>{p.zone ?? p.county ?? "Ukjent"}</td>
                    <td style={{ textAlign: "right" }}>{p.installed_effect_mw != null ? formatNumber(p.installed_effect_mw, 1) : "—"}</td>
                    <td>{p.expected_commissioning ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {pipeline.data.unmapped_effect_mw > 0 && (
              <p className="hint" style={{ marginTop: 12 }}>
                {formatNumber(pipeline.data.unmapped_effect_mw, 0)} MW kunne ikke knyttes til et prisområde (ukjent
                eller ukartlagt fylke) og mangler i søylene over.
              </p>
            )}

            <div className="prediction-warning" style={{ marginTop: 16 }}>
              NVE-integrasjonen er bygget defensivt, men feltnavnene i API-responsen er ikke verifisert mot en reell
              kjøring i dette miljøet (nettverkstilgang til nve.no var blokkert under utvikling) — se
              ingest/nve/client.py. Vinddekningen kan også være ufullstendig: kun ett bekreftet API-endepunkt for
              vindkraft ble funnet, og det dekker mulig bare kraftverk allerede i drift.
            </div>
          </>
        )}
      </Card>

      <Card title="Scenario: kraftbalanse 1-5 år frem">
        <p className="hint">
          Dette er <strong>ikke</strong> en trent prediksjon — den daglige ML-modellen har ingen mening så langt frem.
          Dette er en enkel fremskrivning: dagens snittproduksjon og -forbruk (siste 30 dager) vokser med de valgte
          årlige ratene du setter under. Juster og se hva som skjer.
        </p>

        <div className="growth-sliders">
          <GrowthSlider label="Forbruksvekst" value={consumptionGrowth} onChange={setConsumptionGrowth} />
          <GrowthSlider label="Produksjonsvekst" value={productionGrowth} onChange={setProductionGrowth} />
        </div>

        <label className="growth-slider" style={{ marginTop: 8 }}>
          <span className="growth-slider-label">
            Viser kartet for år: <strong>{year === 0 ? "i dag" : `+${year}`}</strong>
          </span>
          <input type="range" min={0} max={YEARS} step={1} value={year} onChange={(e) => setYear(Number(e.target.value))} />
        </label>

        <StatusBox loading={allZones.loading} error={allZones.error} empty={!allZones.loading && mapValues.length === 0} />
        {mapValues.length > 0 && (
          <ZoneMap values={mapValues} label={`Kart over prisområder, scenario for år ${year}`} />
        )}
      </Card>

      <Card
        title="Balanseutvikling over tid"
        controls={
          <select value={chartZone} onChange={(e) => setChartZone(e.target.value)}>
            {DEFICIT_ZONE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        }
      >
        <StatusBox loading={chart.loading} error={chart.error} empty={!chart.loading && (chart.data?.years.length ?? 0) === 0} />
        {chart.data && (
          <>
            <p className="hint">
              Utgangspunkt: {formatNumber(chart.data.baseline_production_mw, 0)} MW produksjon,{" "}
              {formatNumber(chart.data.baseline_load_mw, 0)} MW forbruk (snitt siste {chart.data.baseline_days} dager).
            </p>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chart.data.years}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="year" tickFormatter={(y) => (y === 0 ? "I dag" : `+${y} år`)} stroke="var(--text-muted)" />
                <YAxis unit=" MW" width={90} stroke="var(--text-muted)" />
                <Tooltip labelFormatter={(y) => (y === 0 ? "I dag" : `Om ${y} år`)} formatter={(v) => `${formatNumber(v, 0)} MW`} />
                <ReferenceLine y={0} stroke="var(--text-muted)" strokeDasharray="4 4" />
                <Line type="monotone" dataKey="balance_mw" stroke="#2563eb" strokeWidth={2} name="Balanse" dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </>
        )}
      </Card>

      <Card
        title="Konsekvens av å ikke bygge ut i tide"
        controls={
          <select value={compareZone} onChange={(e) => setCompareZone(e.target.value)}>
            {DEFICIT_ZONE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        }
      >
        <p className="hint">
          Samme forbruksvekst i begge scenarioer. "Med utbygging" lar produksjonen vokse med raten under. "Uten
          utbygging" holder produksjonen flat på dagens nivå — status quo, ingen ny kraft bygges ut.
        </p>

        <div className="growth-sliders">
          <GrowthSlider label="Forbruksvekst" value={compareConsumptionGrowth} onChange={setCompareConsumptionGrowth} />
          <GrowthSlider label="Produksjonsvekst med utbygging" value={expansionGrowth} onChange={setExpansionGrowth} />
        </div>

        <StatusBox
          loading={withExpansion.loading || withoutExpansion.loading}
          error={withExpansion.error || withoutExpansion.error}
          empty={!withExpansion.loading && compareChartData.length === 0}
        />

        {compareChartData.length > 0 && (
          <>
            <div className="crossover-callouts">
              <div className="crossover-callout crossover-good">
                <div className="crossover-callout-label">Med utbygging</div>
                <div className="crossover-callout-value">
                  {withExpansionCrossover ? `Underskudd fra år +${withExpansionCrossover}` : `Ingen underskudd innen ${YEARS} år`}
                </div>
              </div>
              <div className="crossover-callout crossover-bad">
                <div className="crossover-callout-label">Uten utbygging</div>
                <div className="crossover-callout-value">
                  {withoutExpansionCrossover
                    ? `Underskudd fra år +${withoutExpansionCrossover}`
                    : `Ingen underskudd innen ${YEARS} år`}
                </div>
              </div>
            </div>

            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={compareChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="year" tickFormatter={(y) => (y === 0 ? "I dag" : `+${y} år`)} stroke="var(--text-muted)" />
                <YAxis unit=" MW" width={90} stroke="var(--text-muted)" />
                <Tooltip labelFormatter={(y) => (y === 0 ? "I dag" : `Om ${y} år`)} formatter={(v) => `${formatNumber(v as number, 0)} MW`} />
                <Legend />
                <ReferenceLine y={0} stroke="var(--text-muted)" strokeDasharray="4 4" />
                <Line type="monotone" dataKey="med_utbygging" stroke="#16a34a" strokeWidth={2} name="Med utbygging" dot={{ r: 4 }} />
                <Line type="monotone" dataKey="uten_utbygging" stroke="#dc2626" strokeWidth={2} name="Uten utbygging" dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </>
        )}
      </Card>
    </>
  );
}
