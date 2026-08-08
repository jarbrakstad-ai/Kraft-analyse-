import { useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { DEFICIT_ZONE_OPTIONS } from "../constants";
import { formatDateTimeLabel, formatNumber, formatTimeAxis } from "../format";
import { useApiData } from "../useApiData";
import { Card } from "./Card";
import { StatusBox } from "./StatusBox";
import { BalanceMapSection } from "./BalanceMapSection";

const ZONE_OPTIONS = DEFICIT_ZONE_OPTIONS;
const DAY_OPTIONS = [3, 7, 14, 30];

function HistorySection() {
  const [zone, setZone] = useState("NO");
  const [days, setDays] = useState(7);
  const { data, loading, error } = useApiData(() => api.deficit(zone, days), [zone, days]);

  return (
    <Card
      title="Kraftbalanse (historisk)"
      controls={
        <div className="controls-row">
          <select value={zone} onChange={(e) => setZone(e.target.value)}>
            {ZONE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
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
      <StatusBox loading={loading} error={error} empty={!loading && (data?.points.length ?? 0) === 0} />
      {data && data.points.length > 0 && (
        <>
          <div className="model-stats" style={{ marginBottom: 20 }}>
            <div>
              <div className="model-stat-value">{formatNumber(data.avg_balance_mw, 0)} MW</div>
              <div className="model-stat-label">Snittbalanse</div>
            </div>
            <div>
              <div className="model-stat-value">{data.hours_in_deficit}</div>
              <div className="model-stat-label">Timer med underskudd</div>
            </div>
            <div>
              <div className="model-stat-value">
                {data.n > 0 ? formatNumber((data.hours_in_deficit / data.n) * 100, 0) : 0}%
              </div>
              <div className="model-stat-label">Andel av perioden</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={data.points}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="timestamp_utc" tickFormatter={formatTimeAxis} minTickGap={40} stroke="var(--text-muted)" />
              <YAxis unit=" MW" width={90} stroke="var(--text-muted)" />
              <Tooltip labelFormatter={formatDateTimeLabel} formatter={(v) => `${formatNumber(v, 0)} MW`} />
              <ReferenceLine y={0} stroke="var(--text-muted)" strokeDasharray="4 4" />
              <Line type="monotone" dataKey="balance_mw" stroke="#2563eb" dot={false} strokeWidth={2} name="Balanse (produksjon − forbruk)" />
            </LineChart>
          </ResponsiveContainer>
          <p className="hint">Negativ balanse (under den stiplede linjen) betyr underskudd — sonen forbrukte mer enn den produserte den timen.</p>
        </>
      )}
    </Card>
  );
}

function ForecastSection() {
  const [zone, setZone] = useState("NO");
  const { data, loading, error, errorStatus } = useApiData(() => api.deficitForecast(zone), [zone]);

  return (
    <Card
      title="Forventet balanse (neste dag)"
      controls={
        <div className="controls-row">
          <select value={zone} onChange={(e) => setZone(e.target.value)}>
            {ZONE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      }
    >
      {errorStatus === 503 && (
        <div className="status">
          Underskuddsmodellen er ikke trent ennå. Kjør <code>python -m app.ml.train</code> i <code>backend/</code>{" "}
          når det finnes forbruksdata (<code>fetch_consumption.py</code>) og noen ukers historikk.
        </div>
      )}
      {errorStatus !== 503 && <StatusBox loading={loading} error={error} />}

      {data && (
        <div>
          <div className={`prediction-value ${data.predicted_balance_mw < 0 ? "prediction-deficit" : "prediction-surplus"}`}>
            {data.predicted_balance_mw >= 0 ? "+" : ""}
            {formatNumber(data.predicted_balance_mw, 0)} MW
          </div>
          <div className="prediction-meta">
            {data.predicted_balance_mw < 0 ? "Forventet underskudd" : "Forventet overskudd"} for {data.zone}{" "}
            {new Date(data.predicted_date).toLocaleDateString("no-NO")}, basert på data fra{" "}
            {new Date(data.based_on_day).toLocaleDateString("no-NO")}.
          </div>

          {data.is_aggregate && (
            <div className="feature-bars" style={{ marginTop: 20 }}>
              {data.zone_breakdown.map((zb) => (
                <div key={zb.zone} className="feature-bar-row">
                  <span className="feature-bar-label">{zb.zone}</span>
                  <span style={{ color: zb.predicted_balance_mw < 0 ? "#dc2626" : "#16a34a", fontVariantNumeric: "tabular-nums" }}>
                    {zb.predicted_balance_mw >= 0 ? "+" : ""}
                    {formatNumber(zb.predicted_balance_mw, 0)} MW
                  </span>
                </div>
              ))}
            </div>
          )}

          {data.zone_breakdown.some((zb) => zb.missing_features.length > 0) && (
            <div className="prediction-warning" style={{ marginTop: 16 }}>
              Enkelte soner manglet data for noen features (magasin/vær/flyt finnes ikke for alle soner) — modellen
              håndterer dette, men prediksjonen kan være mindre presis der.
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

export function DeficitSection() {
  return (
    <>
      <BalanceMapSection />
      <ForecastSection />
      <HistorySection />
    </>
  );
}
