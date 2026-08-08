import type {
  ConsumptionPoint,
  DeficitForecast,
  DeficitSummary,
  FlowPoint,
  InterconnectorInfo,
  ModelInfo,
  PriceProductionCorrelation,
  PricePoint,
  PricePrediction,
  PriceReservoirCorrelation,
  PriceSpreadFlowCorrelation,
  PriceWeatherCorrelation,
  ProductionMixShare,
  ReservoirPoint,
  ScenarioForecast,
  WeatherPoint,
  ZoneInfo,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function get<T>(path: string, params: Record<string, string | number | undefined> = {}): Promise<T> {
  const url = new URL(path, BASE_URL);
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) url.searchParams.set(key, String(value));
  }
  const res = await fetch(url.toString());
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const message = body?.detail ?? `${res.status} ${res.statusText} for ${url}`;
    throw new ApiError(res.status, message);
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

  predictPrice: (zone: string) => get<PricePrediction>("/predict/price", { zone }),
  modelInfo: () => get<ModelInfo>("/predict/model-info"),

  consumption: (zone: string, days: number) => get<ConsumptionPoint[]>("/consumption", { zone, start: sinceDays(days) }),

  deficit: (zone: string, days: number) => get<DeficitSummary>("/deficit", { zone, start: sinceDays(days) }),
  deficitForecast: (zone: string) => get<DeficitForecast>("/deficit/forecast", { zone }),
  deficitModelInfo: () => get<ModelInfo>("/deficit/model-info"),

  deficitScenario: (zone: string, consumptionGrowthPct: number, productionGrowthPct: number, years: number) =>
    get<ScenarioForecast>("/deficit/scenario", {
      zone,
      consumption_growth_pct: consumptionGrowthPct,
      production_growth_pct: productionGrowthPct,
      years,
    }),
};

function sinceDays(days: number): string {
  const d = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
  return d.toISOString();
}
