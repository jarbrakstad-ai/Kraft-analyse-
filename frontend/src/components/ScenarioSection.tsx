import { useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { ALL_TRACKED_ZONES, DEFICIT_ZONE_OPTIONS } from "../constants";
import { formatNumber } from "../format";
import { useApiData } from "../useApiData";
import { Card } from "./Card";
import { StatusBox } from "./StatusBox";
import { ZoneMap } from "./ZoneMap";

const YEARS = 5;
const GROWTH_MIN = -5;
const GROWTH_MAX = 10;
const GROWTH_STEP = 0.5;

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

  return (
    <>
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
    </>
  );
}
