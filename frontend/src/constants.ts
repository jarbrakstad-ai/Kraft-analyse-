export const ZONE_COLORS: Record<string, string> = {
  NO1: "#2563eb",
  NO2: "#7c3aed",
  NO3: "#059669",
  NO4: "#d97706",
  NO5: "#dc2626",
  DE_LU: "#6b7280",
  DK1: "#0891b2",
  DK2: "#0e7490",
  NL: "#ea580c",
  SE3: "#16a34a",
  GB: "#334155",
  NO: "#111827",
};

export const NORWEGIAN_ZONES = ["NO1", "NO2", "NO3", "NO4", "NO5"];
export const EUROPEAN_ZONES = ["DE_LU", "DK1", "DK2", "NL", "SE3"];
export const ALL_TRACKED_ZONES = [...NORWEGIAN_ZONES, ...EUROPEAN_ZONES];

/** Zone selector options: real zones plus the "NO"/"EU" aggregates the /deficit endpoints accept. */
export const DEFICIT_ZONE_OPTIONS = [
  { value: "NO", label: "Norge (NO1-NO5 samlet)" },
  ...NORWEGIAN_ZONES.map((z) => ({ value: z, label: z })),
  { value: "EU", label: "Europa (sporede soner samlet)" },
  ...EUROPEAN_ZONES.map((z) => ({ value: z, label: z })),
];

export const WEATHER_VARIABLES: { value: string; label: string; unit: string }[] = [
  { value: "temperature_c", label: "Temperatur", unit: "°C" },
  { value: "wind_speed_ms", label: "Vindstyrke", unit: "m/s" },
  { value: "precipitation_mm", label: "Nedbør", unit: "mm" },
];

export function colorForZone(zone: string): string {
  return ZONE_COLORS[zone] ?? "#94a3b8";
}
