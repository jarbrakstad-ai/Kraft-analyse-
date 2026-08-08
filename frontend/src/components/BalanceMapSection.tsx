import { useMemo } from "react";
import { api } from "../api";
import { formatNumber } from "../format";
import type { DeficitForecastZone } from "../types";
import { useApiData } from "../useApiData";
import { Card } from "./Card";
import { StatusBox } from "./StatusBox";

// Schematic (not geographically accurate) relative positions of each zone,
// loosely matching real layout: NO4 north, NO3 mid-Norway, NO1/NO5/NO2
// south, SE3 to the east, DK/DE/NL further south. Good enough to read at a
// glance which region is which — this is not a GIS map.
const ZONE_LAYOUT: Record<string, { x: number; y: number; w: number; h: number }> = {
  NO4: { x: 120, y: 16, w: 130, h: 70 },
  NO3: { x: 100, y: 100, w: 130, h: 70 },
  SE3: { x: 260, y: 130, w: 120, h: 90 },
  NO5: { x: 40, y: 190, w: 100, h: 80 },
  NO1: { x: 150, y: 190, w: 100, h: 80 },
  NO2: { x: 95, y: 285, w: 130, h: 65 },
  DK1: { x: 90, y: 375, w: 100, h: 60 },
  DK2: { x: 200, y: 375, w: 100, h: 60 },
  NL: { x: 20, y: 450, w: 110, h: 60 },
  DE_LU: { x: 145, y: 450, w: 150, h: 60 },
};

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function hexToRgb(hex: string): [number, number, number] {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

const DEFICIT_RGB = hexToRgb("#dc2626");
const NEUTRAL_RGB = hexToRgb("#e5e7eb");
const SURPLUS_RGB = hexToRgb("#16a34a");

function balanceColor(mw: number, maxAbs: number): string {
  const t = maxAbs > 0 ? Math.max(-1, Math.min(1, mw / maxAbs)) : 0;
  const from = t < 0 ? DEFICIT_RGB : NEUTRAL_RGB;
  const to = t < 0 ? NEUTRAL_RGB : SURPLUS_RGB;
  const localT = t < 0 ? t + 1 : t;
  const [r, g, b] = [lerp(from[0], to[0], localT), lerp(from[1], to[1], localT), lerp(from[2], to[2], localT)];
  return `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`;
}

function textColorFor(mw: number, maxAbs: number): string {
  const t = maxAbs > 0 ? Math.abs(mw) / maxAbs : 0;
  return t > 0.35 ? "#ffffff" : "#111827";
}

export function BalanceMapSection() {
  const no = useApiData(() => api.deficitForecast("NO"), []);
  const eu = useApiData(() => api.deficitForecast("EU"), []);

  const loading = no.loading || eu.loading;
  const error = no.error ?? eu.error;
  const errorStatus = no.errorStatus ?? eu.errorStatus;

  const zones: DeficitForecastZone[] = useMemo(() => {
    return [...(no.data?.zone_breakdown ?? []), ...(eu.data?.zone_breakdown ?? [])];
  }, [no.data, eu.data]);

  const maxAbs = useMemo(() => Math.max(1, ...zones.map((z) => Math.abs(z.predicted_balance_mw))), [zones]);
  const predictedDate = no.data?.predicted_date ?? eu.data?.predicted_date;

  return (
    <Card title="Kart: forventet under-/overskudd neste dag">
      {errorStatus === 503 && (
        <div className="status">
          Underskuddsmodellen er ikke trent ennå. Kjør <code>python -m app.ml.train</code> i <code>backend/</code>{" "}
          når det finnes forbruksdata og noen ukers historikk.
        </div>
      )}
      {errorStatus !== 503 && <StatusBox loading={loading} error={error} empty={!loading && zones.length === 0} />}

      {zones.length > 0 && (
        <>
          {predictedDate && <p className="hint">Prisområder farget etter predikert kraftbalanse for {new Date(predictedDate).toLocaleDateString("no-NO")}. Skjematisk kart — ikke geografisk nøyaktig.</p>}

          <div className="map-wrap">
            <svg viewBox="0 0 440 520" className="balance-map" role="img" aria-label="Kart over prisområder farget etter forventet kraftbalanse">
              {Object.entries(ZONE_LAYOUT).map(([zone, layout]) => {
                const zb = zones.find((z) => z.zone === zone);
                const fill = zb ? balanceColor(zb.predicted_balance_mw, maxAbs) : "var(--border)";
                const textColor = zb ? textColorFor(zb.predicted_balance_mw, maxAbs) : "var(--text-muted)";
                return (
                  <g key={zone}>
                    <rect x={layout.x} y={layout.y} width={layout.w} height={layout.h} rx={12} fill={fill} stroke="var(--card-bg)" strokeWidth={2}>
                      <title>
                        {zone}: {zb ? `${zb.predicted_balance_mw >= 0 ? "+" : ""}${formatNumber(zb.predicted_balance_mw, 0)} MW` : "ingen data"}
                      </title>
                    </rect>
                    <text x={layout.x + layout.w / 2} y={layout.y + layout.h / 2 - 6} textAnchor="middle" fontSize={15} fontWeight={700} fill={textColor}>
                      {zone}
                    </text>
                    <text x={layout.x + layout.w / 2} y={layout.y + layout.h / 2 + 14} textAnchor="middle" fontSize={12} fill={textColor}>
                      {zb ? `${zb.predicted_balance_mw >= 0 ? "+" : ""}${formatNumber(zb.predicted_balance_mw, 0)} MW` : "—"}
                    </text>
                  </g>
                );
              })}
            </svg>

            <div className="map-legend">
              <div className="map-legend-bar" />
              <div className="map-legend-labels">
                <span>Underskudd</span>
                <span>0</span>
                <span>Overskudd</span>
              </div>
            </div>
          </div>
        </>
      )}
    </Card>
  );
}
