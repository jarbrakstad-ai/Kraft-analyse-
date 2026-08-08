import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { NORWEGIAN_ZONES, colorForZone } from "../constants";
import { useApiData } from "../useApiData";
import { Card } from "./Card";
import { StatusBox } from "./StatusBox";
import { formatDateAxis, formatDateLabel, formatNumber } from "../format";

const ZONE_OPTIONS = [...NORWEGIAN_ZONES, "NO"];
const DAY_OPTIONS = [
  { label: "Siste 26 uker", days: 182 },
  { label: "Siste år", days: 365 },
  { label: "Siste 2 år", days: 730 },
];

export function ReservoirSection() {
  const [zone, setZone] = useState("NO");
  const [days, setDays] = useState(365);

  const { data, loading, error } = useApiData(() => api.reservoir(zone, days), [zone, days]);

  const chartData = data?.map((p) => ({ ...p, timestamp_utc: p.week_start_utc })) ?? [];

  return (
    <Card
      title="Magasinfylling"
      controls={
        <div className="controls-row">
          <select value={zone} onChange={(e) => setZone(e.target.value)}>
            {ZONE_OPTIONS.map((z) => (
              <option key={z} value={z}>
                {z === "NO" ? "Hele Norge" : z}
              </option>
            ))}
          </select>
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
            {DAY_OPTIONS.map((o) => (
              <option key={o.days} value={o.days}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      }
    >
      <StatusBox loading={loading} error={error} empty={!loading && chartData.length === 0} />
      {chartData.length > 0 && (
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="timestamp_utc" tickFormatter={formatDateAxis} minTickGap={40} stroke="var(--text-muted)" />
            <YAxis unit="%" domain={[0, 100]} width={60} stroke="var(--text-muted)" />
            <Tooltip labelFormatter={formatDateLabel} formatter={(v) => `${formatNumber(v)}%`} />
            <Line type="monotone" dataKey="fill_percent" stroke={colorForZone(zone)} dot={false} strokeWidth={2} name="Fyllingsgrad" />
          </LineChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
