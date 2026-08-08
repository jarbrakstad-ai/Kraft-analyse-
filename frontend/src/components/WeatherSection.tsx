import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { NORWEGIAN_ZONES, WEATHER_VARIABLES } from "../constants";
import { useApiData } from "../useApiData";
import { Card } from "./Card";
import { StatusBox } from "./StatusBox";
import { formatDateTimeLabel, formatNumber, formatTimeAxis } from "../format";

const DAY_OPTIONS = [3, 7, 14, 30];

export function WeatherSection() {
  const [zone, setZone] = useState("NO1");
  const [variable, setVariable] = useState("temperature_c");
  const [days, setDays] = useState(7);

  const { data, loading, error } = useApiData(() => api.weather(zone, days), [zone, days]);
  const meta = WEATHER_VARIABLES.find((v) => v.value === variable)!;

  return (
    <Card
      title="Værdata"
      controls={
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
            {DAY_OPTIONS.map((d) => (
              <option key={d} value={d}>
                Siste {d} dager
              </option>
            ))}
          </select>
        </div>
      }
    >
      <StatusBox loading={loading} error={error} empty={!loading && (data?.length ?? 0) === 0} />
      {data && data.length > 0 && (
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="timestamp_utc" tickFormatter={formatTimeAxis} minTickGap={40} stroke="var(--text-muted)" />
            <YAxis unit={` ${meta.unit}`} width={80} stroke="var(--text-muted)" />
            <Tooltip labelFormatter={formatDateTimeLabel} formatter={(v) => `${formatNumber(v)} ${meta.unit}`} />
            <Line type="monotone" dataKey={variable} stroke="#0891b2" dot={false} strokeWidth={2} name={meta.label} connectNulls />
          </LineChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
