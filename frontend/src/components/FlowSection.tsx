import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { useApiData } from "../useApiData";
import { Card } from "./Card";
import { StatusBox } from "./StatusBox";
import { formatDateTimeLabel, formatNumber, formatTimeAxis, pivotByTimestamp } from "../format";

const DAY_OPTIONS = [3, 7, 14, 30];
const DIRECTION_COLORS = ["#2563eb", "#dc2626"];

export function FlowSection() {
  const [interconnector, setInterconnector] = useState<string | null>(null);
  const [days, setDays] = useState(7);

  const { data: interconnectors } = useApiData(() => api.interconnectors(), []);

  useEffect(() => {
    if (!interconnector && interconnectors && interconnectors.length > 0) {
      setInterconnector(interconnectors[0].name);
    }
  }, [interconnectors, interconnector]);

  const { data, loading, error } = useApiData(
    () => (interconnector ? api.flow(interconnector, days) : Promise.resolve([])),
    [interconnector, days],
  );

  const directions = useMemo(() => {
    if (!data) return [];
    const seen = new Map<string, string>();
    for (const p of data) seen.set(`${p.from_zone}->${p.to_zone}`, `${p.from_zone} → ${p.to_zone}`);
    return Array.from(seen.entries());
  }, [data]);

  const chartData = useMemo(() => {
    if (!data) return [];
    const withDirection = data.map((p) => ({ ...p, direction: `${p.from_zone} → ${p.to_zone}` }));
    return pivotByTimestamp(withDirection, "direction", "flow_mw");
  }, [data]);

  return (
    <Card
      title="Grenseflyt (import/eksport)"
      controls={
        <div className="controls-row">
          <select value={interconnector ?? ""} onChange={(e) => setInterconnector(e.target.value)}>
            {interconnectors?.map((ic) => (
              <option key={ic.name} value={ic.name}>
                {ic.name} ({ic.from_zone} ↔ {ic.to_zone})
              </option>
            ))}
          </select>
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
      <StatusBox loading={loading} error={error} empty={!loading && chartData.length === 0} />
      {chartData.length > 0 && (
        <ResponsiveContainer width="100%" height={340}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="timestamp_utc" tickFormatter={formatTimeAxis} minTickGap={40} stroke="var(--text-muted)" />
            <YAxis unit=" MW" width={80} stroke="var(--text-muted)" />
            <Tooltip labelFormatter={formatDateTimeLabel} formatter={(v) => formatNumber(v, 0)} />
            <Legend />
            {directions.map(([key, label], i) => (
              <Line key={key} type="monotone" dataKey={label} stroke={DIRECTION_COLORS[i % 2]} dot={false} strokeWidth={2} connectNulls />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
