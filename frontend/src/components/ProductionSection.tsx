import { useState } from "react";
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { PieLabelRenderProps } from "recharts";
import { api } from "../api";
import { NORWEGIAN_ZONES } from "../constants";
import { formatNumber } from "../format";
import type { ProductionMixShare } from "../types";
import { useApiData } from "../useApiData";
import { Card } from "./Card";
import { StatusBox } from "./StatusBox";

const DAY_OPTIONS = [7, 14, 30];

const PRODUCTION_TYPE_COLORS: Record<string, string> = {
  hydro: "#2563eb",
  hydro_pumped_storage: "#60a5fa",
  wind_onshore: "#059669",
  wind_offshore: "#10b981",
  solar: "#f59e0b",
  thermal_gas: "#dc2626",
  thermal_coal: "#7f1d1d",
  thermal_oil: "#b45309",
  thermal_other: "#92400e",
  nuclear: "#7c3aed",
  biomass: "#65a30d",
  waste: "#78716c",
  other_renewable: "#0891b2",
  other: "#94a3b8",
};

function colorForType(type: string): string {
  return PRODUCTION_TYPE_COLORS[type] ?? "#94a3b8";
}

const RADIAN = Math.PI / 180;

function renderPieLabel(props: PieLabelRenderProps) {
  const cx = Number(props.cx);
  const cy = Number(props.cy);
  const midAngle = Number(props.midAngle);
  const innerRadius = Number(props.innerRadius);
  const outerRadius = Number(props.outerRadius);
  const entry = props as unknown as ProductionMixShare;

  const radius = innerRadius + (outerRadius - innerRadius) * 1.25;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  return (
    <text x={x} y={y} textAnchor={x > cx ? "start" : "end"} dominantBaseline="central" fill="var(--text)" fontSize={13}>
      {entry.production_type} {formatNumber(entry.share_percent, 0)}%
    </text>
  );
}

export function ProductionSection() {
  const [zone, setZone] = useState("NO1");
  const [days, setDays] = useState(7);

  const { data, loading, error } = useApiData(() => api.productionMix(zone, days), [zone, days]);

  return (
    <Card
      title="Produksjonsmiks"
      controls={
        <div className="controls-row">
          <select value={zone} onChange={(e) => setZone(e.target.value)}>
            {NORWEGIAN_ZONES.map((z) => (
              <option key={z} value={z}>
                {z}
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
      <StatusBox loading={loading} error={error} empty={!loading && (data?.length ?? 0) === 0} />
      {data && data.length > 0 && (
        <ResponsiveContainer width="100%" height={340}>
          <PieChart>
            <Pie
              data={data}
              dataKey="share_percent"
              nameKey="production_type"
              cx="50%"
              cy="50%"
              outerRadius={110}
              isAnimationActive={false}
              labelLine
              label={renderPieLabel}
            >
              {data.map((entry) => (
                <Cell key={entry.production_type} fill={colorForType(entry.production_type)} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value, _name, item) => {
                const payload = item.payload as ProductionMixShare;
                return [`${formatNumber(value, 1)}% (${formatNumber(payload.avg_quantity_mw, 0)} MW snitt)`, payload.production_type];
              }}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
