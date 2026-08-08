export interface ZoneInfo {
  code: string;
  name: string;
}

export interface PricePoint {
  zone: string;
  timestamp_utc: string;
  price_eur_mwh: number;
  resolution_min: number;
}

export interface ProductionMixShare {
  zone: string;
  production_type: string;
  avg_quantity_mw: number;
  share_percent: number;
}

export interface InterconnectorInfo {
  name: string;
  from_zone: string;
  to_zone: string;
}

export interface FlowPoint {
  from_zone: string;
  to_zone: string;
  interconnector: string | null;
  timestamp_utc: string;
  flow_mw: number;
}

export interface ReservoirPoint {
  zone: string;
  week_start_utc: string;
  fill_percent: number;
  capacity_gwh: number | null;
}

export interface WeatherPoint {
  zone: string;
  station_id: string;
  timestamp_utc: string;
  temperature_c: number | null;
  wind_speed_ms: number | null;
  precipitation_mm: number | null;
}

export interface PriceProductionPoint {
  timestamp_utc: string;
  price_eur_mwh: number;
  quantity_mw: number;
}

export interface PriceProductionCorrelation {
  zone: string;
  production_type: string;
  n: number;
  pearson_r: number | null;
  points: PriceProductionPoint[];
}

export interface PriceReservoirPoint {
  week_start_utc: string;
  avg_price_eur_mwh: number;
  fill_percent: number;
}

export interface PriceReservoirCorrelation {
  zone: string;
  n: number;
  pearson_r: number | null;
  points: PriceReservoirPoint[];
}

export interface PriceSpreadFlowPoint {
  timestamp_utc: string;
  price_spread_eur_mwh: number;
  net_flow_mw: number;
}

export interface PriceSpreadFlowCorrelation {
  zone_a: string;
  zone_b: string;
  n: number;
  pearson_r: number | null;
  points: PriceSpreadFlowPoint[];
}

export interface PriceWeatherPoint {
  timestamp_utc: string;
  price_eur_mwh: number;
  weather_value: number;
}

export interface PriceWeatherCorrelation {
  zone: string;
  weather_variable: string;
  n: number;
  pearson_r: number | null;
  points: PriceWeatherPoint[];
}

export type WeatherVariable = "temperature_c" | "wind_speed_ms" | "precipitation_mm";

export interface PricePrediction {
  zone: string;
  based_on_day: string;
  predicted_date: string;
  predicted_avg_price_eur_mwh: number;
  missing_features: string[];
  model_trained_at: string;
}

export interface ModelMetrics {
  mae_eur_mwh: number | null;
  rmse_eur_mwh: number | null;
  r2: number | null;
  n_test: number | null;
}

export interface FeatureImportance {
  feature: string;
  importance: number;
}

export interface ModelInfo {
  trained_at: string;
  n_training_rows: number;
  metrics: ModelMetrics;
  feature_importances: FeatureImportance[];
  zone_categories: string[];
}
