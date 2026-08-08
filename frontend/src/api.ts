import type {
  FlowPoint,
  InterconnectorInfo,
  PriceProductionCorrelation,
  PricePoint,
  PriceReservoirCorrelation,
  PriceSpreadFlowCorrelation,
  PriceWeatherCorrelation,
  ProductionMixShare,
  ReservoirPoint,
  WeatherPoint,
  ZoneInfo,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function get<T>(path: string, params: Record<string, string | number | undefined> = {}): Promise<T> {
  const url = new URL(path, BASE_URL);
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) url.searchParams.set(key, String(value));
  }
  const res = await fetch(url.toString());
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText} for ${url}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => get<{ status: string; database: boolean }>("/health"),

  zones: () => get<ZoneInfo[]>("/prices/zones"),

  prices: (zone: string | undefined, days: number) => get<PricePoint[]>("/prices", { zone, start: sinceDays(days) }),

  productionTypes: (zone: string) => get<string[]>("/production/types", { zone }),
  productionMix: (zone: string, days: number) => get<ProductionMixShare[]>("/production/mix", { zone, days }),

  interconnectors: () => get<InterconnectorInfo[]>("/flow/interconnectors"),
  flow: (interconnector: string, days: number) => get<FlowPoint[]>("/flow", { interconnector, start: sinceDays(days) }),

  reservoir: (zone: string, days: number) => get<ReservoirPoint[]>("/reservoir", { zone, start: sinceDays(days) }),

  weather: (zone: string, days: number) => get<WeatherPoint[]>("/weather", { zone, start: sinceDays(days) }),

  priceVsProduction: (zone: string, productionType: string, days: number) =>
    get<PriceProductionCorrelation>("/analysis/price-vs-production", { zone, production_type: productionType, days }),

  priceVsReservoir: (zone: string, weeks: number) => get<PriceReservoirCorrelation>("/analysis/price-vs-reservoir", { zone, weeks }),

  priceSpreadVsFlow: (zoneA: string, zoneB: string, days: number, interconnector?: string) =>
    get<PriceSpreadFlowCorrelation>("/analysis/price-spread-vs-flow", { zone_a: zoneA, zone_b: zoneB, days, interconnector }),

  priceVsWeather: (zone: string, weatherVariable: string, days: number) =>
    get<PriceWeatherCorrelation>("/analysis/price-vs-weather", { zone, weather_variable: weatherVariable, days }),
};

function sinceDays(days: number): string {
  const d = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
  return d.toISOString();
}
