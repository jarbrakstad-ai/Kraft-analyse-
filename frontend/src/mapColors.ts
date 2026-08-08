// Schematic (not geographically accurate) relative positions of each zone,
// loosely matching real layout: NO4 north, NO3 mid-Norway, NO1/NO5/NO2
// south, SE3 to the east, DK/DE/NL further south. Good enough to read at a
// glance which region is which — this is not a GIS map.
export const ZONE_LAYOUT: Record<string, { x: number; y: number; w: number; h: number }> = {
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

export function balanceColor(mw: number, maxAbs: number): string {
  const t = maxAbs > 0 ? Math.max(-1, Math.min(1, mw / maxAbs)) : 0;
  const from = t < 0 ? DEFICIT_RGB : NEUTRAL_RGB;
  const to = t < 0 ? NEUTRAL_RGB : SURPLUS_RGB;
  const localT = t < 0 ? t + 1 : t;
  const [r, g, b] = [lerp(from[0], to[0], localT), lerp(from[1], to[1], localT), lerp(from[2], to[2], localT)];
  return `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`;
}

export function textColorFor(mw: number, maxAbs: number): string {
  const t = maxAbs > 0 ? Math.abs(mw) / maxAbs : 0;
  return t > 0.35 ? "#ffffff" : "#111827";
}
