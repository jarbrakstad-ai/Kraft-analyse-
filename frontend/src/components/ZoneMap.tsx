import { formatNumber } from "../format";
import { ZONE_LAYOUT, balanceColor, textColorFor } from "../mapColors";

export interface ZoneMapValue {
  zone: string;
  balance_mw: number;
}

/** Schematic map of the ten tracked price zones, colored by an arbitrary MW balance value per zone. */
export function ZoneMap({ values, label }: { values: ZoneMapValue[]; label: string }) {
  const maxAbs = Math.max(1, ...values.map((z) => Math.abs(z.balance_mw)));

  return (
    <div className="map-wrap">
      <svg viewBox="0 0 440 520" className="balance-map" role="img" aria-label={label}>
        {Object.entries(ZONE_LAYOUT).map(([zone, layout]) => {
          const zb = values.find((z) => z.zone === zone);
          const fill = zb ? balanceColor(zb.balance_mw, maxAbs) : "var(--border)";
          const textColor = zb ? textColorFor(zb.balance_mw, maxAbs) : "var(--text-muted)";
          return (
            <g key={zone}>
              <rect x={layout.x} y={layout.y} width={layout.w} height={layout.h} rx={12} fill={fill} stroke="var(--card-bg)" strokeWidth={2}>
                <title>
                  {zone}: {zb ? `${zb.balance_mw >= 0 ? "+" : ""}${formatNumber(zb.balance_mw, 0)} MW` : "ingen data"}
                </title>
              </rect>
              <text x={layout.x + layout.w / 2} y={layout.y + layout.h / 2 - 6} textAnchor="middle" fontSize={15} fontWeight={700} fill={textColor}>
                {zone}
              </text>
              <text x={layout.x + layout.w / 2} y={layout.y + layout.h / 2 + 14} textAnchor="middle" fontSize={12} fill={textColor}>
                {zb ? `${zb.balance_mw >= 0 ? "+" : ""}${formatNumber(zb.balance_mw, 0)} MW` : "—"}
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
  );
}
