import { useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { EUROPEAN_ZONES, NORWEGIAN_ZONES, colorForZone } from "../constants";
import { useApiData } from "../useApiData";
import { Card } from "./Card";
import { StatusBox } from "./StatusBox";
import { formatDateTimeLabel, formatNumber, formatTimeAxis, pivotByTimestamp } from "../format";

const ALL_ZONES = [...NORWEGIAN_ZONES, ...EUROPEAN_ZONES];
const DAY_OPTIONS = [3, 7, 14, 30];

export function PriceSection() {
  const [selectedZones, setSelectedZones] = useState<string[]>(NORWEGIAN_ZONES);
  const [days, setDays] = useState(7);

  const { data, loading, error } = useApiData(() => api.prices(undefined, days), [days]);

  const chartData = useMemo(() => {
    if (!data) return [];
    const filtered = data.filter((p) => selectedZones.includes(p.zone));
    return pivotByTimestamp(filtered, "zone", "price_eur_mwh");
  }, [data, selectedZones]);

  function toggleZone(zone: string) {
    setSelectedZones((zs) => (zs.includes(zone) ? zs.filter((z) => z !== zone) : [...zs, zone]));
  }

  return (
    <Card
      title="Spotpriser"
      controls={
        <div className="controls-row">
          <div className="zone-toggles">
            {ALL_ZONES.map((zone) => (
              <button
                key={zone}
                className={`zone-toggle ${selectedZones.includes(zone) ? "active" : ""}`}
                style={selectedZones.includes(zone) ? { borderColor: colorForZone(zone), color: colorForZone(zone) } : undefined}
                onClick={() => toggleZone(zone)}
              >
                {zone}
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
      <StatusBox loading={loading} error={error} empty={!loading && chartData.length === 0} />
      {chartData.length > 0 && (
        <ResponsiveContainer width="100%" height={360}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="timestamp_utc" tickFormatter={formatTimeAxis} minTickGap={40} stroke="var(--text-muted)" />
            <YAxis unit=" €/MWh" width={90} stroke="var(--text-muted)" />
            <Tooltip labelFormatter={formatDateTimeLabel} formatter={(v) => formatNumber(v, 2)} />
            <Legend />
            {selectedZones.map((zone) => (
              <Line key={zone} type="monotone" dataKey={zone} stroke={colorForZone(zone)} dot={false} strokeWidth={2} connectNulls />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
