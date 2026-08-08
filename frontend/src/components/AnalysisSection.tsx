import { useEffect, useState } from "react";
import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { NORWEGIAN_ZONES, WEATHER_VARIABLES } from "../constants";
import { useApiData } from "../useApiData";
import { formatNumber, formatR } from "../format";
import { Card } from "./Card";
import { StatusBox } from "./StatusBox";

type Mode = "price-vs-production" | "price-vs-reservoir" | "price-spread-vs-flow" | "price-vs-weather";

const MODES: { value: Mode; label: string }[] = [
  { value: "price-vs-production", label: "Pris vs. produksjon" },
  { value: "price-vs-reservoir", label: "Pris vs. magasinfylling" },
  { value: "price-spread-vs-flow", label: "Prisdifferanse vs. kabelflyt" },
  { value: "price-vs-weather", label: "Pris vs. vær" },
];

function RCallout({ r, n }: { r: number | null; n: number }) {
  const strength = r === null ? "" : Math.abs(r) > 0.7 ? "sterk" : Math.abs(r) > 0.3 ? "moderat" : "svak";
  return (
    <div className="r-callout">
      <span className="r-value">r = {formatR(r)}</span>
      {r !== null && <span className="r-strength">({strength} {r > 0 ? "positiv" : "negativ"} sammenheng)</span>}
      <span className="r-n">n = {n}</span>
    </div>
  );
}

function PriceVsProduction() {
  const [zone, setZone] = useState("NO1");
  const [productionType, setProductionType] = useState("hydro");
  const [days, setDays] = useState(30);

  const { data: types } = useApiData(() => api.productionTypes(zone), [zone]);
  useEffect(() => {
    if (types && types.length > 0 && !types.includes(productionType)) setProductionType(types[0]);
  }, [types, productionType]);

  const { data, loading, error } = useApiData(() => api.priceVsProduction(zone, productionType, days), [zone, productionType, days]);

  return (
    <>
      <div className="controls-row">
        <select value={zone} onChange={(e) => setZone(e.target.value)}>
          {NORWEGIAN_ZONES.map((z) => (
            <option key={z} value={z}>
              {z}
            </option>
          ))}
        </select>
        <select value={productionType} onChange={(e) => setProductionType(e.target.value)}>
          {(types ?? [productionType]).map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
          {[7, 30, 90].map((d) => (
            <option key={d} value={d}>
              Siste {d} dager
            </option>
          ))}
        </select>
      </div>
      <StatusBox loading={loading} error={error} empty={!loading && (data?.points.length ?? 0) === 0} />
      {data && data.points.length > 0 && (
        <>
          <RCallout r={data.pearson_r} n={data.n} />
          <ResponsiveContainer width="100%" height={340}>
            <ScatterChart margin={{ left: 10, right: 20, top: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis type="number" dataKey="quantity_mw" name="Produksjon" unit=" MW" domain={["auto", "auto"]} stroke="var(--text-muted)" />
              <YAxis type="number" dataKey="price_eur_mwh" name="Pris" unit=" €/MWh" domain={["auto", "auto"]} stroke="var(--text-muted)" />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(v) => formatNumber(v, 1)} />
              <Scatter data={data.points} fill="#2563eb" fillOpacity={0.6} />
            </ScatterChart>
          </ResponsiveContainer>
        </>
      )}
    </>
  );
}

function PriceVsReservoir() {
  const [zone, setZone] = useState("NO1");
  const [weeks, setWeeks] = useState(52);

  const { data, loading, error } = useApiData(() => api.priceVsReservoir(zone, weeks), [zone, weeks]);

  return (
    <>
      <div className="controls-row">
        <select value={zone} onChange={(e) => setZone(e.target.value)}>
          {[...NORWEGIAN_ZONES, "NO"].map((z) => (
            <option key={z} value={z}>
              {z === "NO" ? "Hele Norge" : z}
            </option>
          ))}
        </select>
        <select value={weeks} onChange={(e) => setWeeks(Number(e.target.value))}>
          {[26, 52, 104].map((w) => (
            <option key={w} value={w}>
              Siste {w} uker
            </option>
          ))}
        </select>
      </div>
      <StatusBox loading={loading} error={error} empty={!loading && (data?.points.length ?? 0) === 0} />
      {data && data.points.length > 0 && (
        <>
          <RCallout r={data.pearson_r} n={data.n} />
          <ResponsiveContainer width="100%" height={340}>
            <ScatterChart margin={{ left: 10, right: 20, top: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis type="number" dataKey="fill_percent" name="Fyllingsgrad" unit="%" domain={["auto", "auto"]} stroke="var(--text-muted)" />
              <YAxis type="number" dataKey="avg_price_eur_mwh" name="Ukesnittpris" unit=" €/MWh" domain={["auto", "auto"]} stroke="var(--text-muted)" />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(v) => formatNumber(v, 1)} />
              <Scatter data={data.points} fill="#059669" fillOpacity={0.6} />
            </ScatterChart>
          </ResponsiveContainer>
        </>
      )}
    </>
  );
}

function PriceSpreadVsFlow() {
  const [zoneA, setZoneA] = useState("NO2");
  const [zoneB, setZoneB] = useState("NL");
  const [days, setDays] = useState(30);

  const { data, loading, error } = useApiData(() => api.priceSpreadVsFlow(zoneA, zoneB, days), [zoneA, zoneB, days]);

  return (
    <>
      <div className="controls-row">
        <label>
          Sone A: <input value={zoneA} onChange={(e) => setZoneA(e.target.value.toUpperCase())} className="zone-input" />
        </label>
        <label>
          Sone B: <input value={zoneB} onChange={(e) => setZoneB(e.target.value.toUpperCase())} className="zone-input" />
        </label>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
          {[7, 30, 90].map((d) => (
            <option key={d} value={d}>
              Siste {d} dager
            </option>
          ))}
        </select>
      </div>
      <StatusBox loading={loading} error={error} empty={!loading && (data?.points.length ?? 0) === 0} />
      {data && data.points.length > 0 && (
        <>
          <RCallout r={data.pearson_r} n={data.n} />
          <p className="hint">
            Positiv prisdifferanse = {zoneA} dyrere enn {zoneB}. Positiv netto flyt = strøm fra {zoneA} til {zoneB}.
          </p>
          <ResponsiveContainer width="100%" height={340}>
            <ScatterChart margin={{ left: 10, right: 20, top: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis type="number" dataKey="net_flow_mw" name="Netto flyt" unit=" MW" domain={["auto", "auto"]} stroke="var(--text-muted)" />
              <YAxis type="number" dataKey="price_spread_eur_mwh" name="Prisdifferanse" unit=" €/MWh" domain={["auto", "auto"]} stroke="var(--text-muted)" />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(v) => formatNumber(v, 1)} />
              <Scatter data={data.points} fill="#dc2626" fillOpacity={0.6} />
            </ScatterChart>
          </ResponsiveContainer>
        </>
      )}
    </>
  );
}

function PriceVsWeather() {
  const [zone, setZone] = useState("NO1");
  const [variable, setVariable] = useState("wind_speed_ms");
  const [days, setDays] = useState(30);
  const meta = WEATHER_VARIABLES.find((v) => v.value === variable)!;

  const { data, loading, error } = useApiData(() => api.priceVsWeather(zone, variable, days), [zone, variable, days]);

  return (
    <>
      <div className="controls-row">
        <select value={zone} onChange={(e) => setZone(e.target.value)}>
          {NORWEGIAN_ZONES.map((z) => (
            <option key={z} value={z}>
              {z}
            </option>
          ))}
        </select>
        <div className="segmented">
          {WEATHER_VARIABLES.map((v) => (
            <button key={v.value} className={variable === v.value ? "active" : ""} onClick={() => setVariable(v.value)}>
              {v.label}
            </button>
          ))}
        </div>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
          {[7, 30, 90].map((d) => (
            <option key={d} value={d}>
              Siste {d} dager
            </option>
          ))}
        </select>
      </div>
      <StatusBox loading={loading} error={error} empty={!loading && (data?.points.length ?? 0) === 0} />
      {data && data.points.length > 0 && (
        <>
          <RCallout r={data.pearson_r} n={data.n} />
          <ResponsiveContainer width="100%" height={340}>
            <ScatterChart margin={{ left: 10, right: 20, top: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis type="number" dataKey="weather_value" name={meta.label} unit={` ${meta.unit}`} domain={["auto", "auto"]} stroke="var(--text-muted)" />
              <YAxis type="number" dataKey="price_eur_mwh" name="Pris" unit=" €/MWh" domain={["auto", "auto"]} stroke="var(--text-muted)" />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(v) => formatNumber(v, 1)} />
              <Scatter data={data.points} fill="#0891b2" fillOpacity={0.6} />
            </ScatterChart>
          </ResponsiveContainer>
        </>
      )}
    </>
  );
}

export function AnalysisSection() {
  const [mode, setMode] = useState<Mode>("price-vs-production");

  return (
    <Card
      title="Korrelasjonsanalyse"
      controls={
        <div className="segmented">
          {MODES.map((m) => (
            <button key={m.value} className={mode === m.value ? "active" : ""} onClick={() => setMode(m.value)}>
              {m.label}
            </button>
          ))}
        </div>
      }
    >
      {mode === "price-vs-production" && <PriceVsProduction />}
      {mode === "price-vs-reservoir" && <PriceVsReservoir />}
      {mode === "price-spread-vs-flow" && <PriceSpreadVsFlow />}
      {mode === "price-vs-weather" && <PriceVsWeather />}
    </Card>
  );
}
