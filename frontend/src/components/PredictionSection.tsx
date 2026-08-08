import { useState } from "react";
import { api } from "../api";
import { NORWEGIAN_ZONES, EUROPEAN_ZONES } from "../constants";
import { formatNumber } from "../format";
import { useApiData } from "../useApiData";
import { Card } from "./Card";
import { StatusBox } from "./StatusBox";

const ALL_ZONES = [...NORWEGIAN_ZONES, ...EUROPEAN_ZONES];

function ModelUntrainedNotice() {
  return (
    <div className="status">
      Modellen er ikke trent ennå. Kjør{" "}
      <code>python -m app.ml.train</code> i <code>backend/</code> når det finnes noen ukers historikk i databasen.
    </div>
  );
}

function PredictionCard() {
  const [zone, setZone] = useState("NO1");
  const { data, loading, error, errorStatus } = useApiData(() => api.predictPrice(zone), [zone]);

  return (
    <div>
      <div className="controls-row" style={{ marginBottom: 16 }}>
        <select value={zone} onChange={(e) => setZone(e.target.value)}>
          {ALL_ZONES.map((z) => (
            <option key={z} value={z}>
              {z}
            </option>
          ))}
        </select>
      </div>

      {errorStatus === 503 && <ModelUntrainedNotice />}
      {errorStatus !== 503 && <StatusBox loading={loading} error={error} />}

      {data && (
        <div className="prediction-result">
          <div className="prediction-value">{formatNumber(data.predicted_avg_price_eur_mwh, 1)} €/MWh</div>
          <div className="prediction-meta">
            Predikert snittpris for {data.zone} {new Date(data.predicted_date).toLocaleDateString("no-NO")}, basert
            på data fra {new Date(data.based_on_day).toLocaleDateString("no-NO")}.
          </div>
          {data.missing_features.length > 0 && (
            <div className="prediction-warning">
              Manglet data for: {data.missing_features.join(", ")} — modellen håndterer dette, men prediksjonen kan
              være mindre presis enn normalt for denne sonen.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ModelInfoCard() {
  const { data, loading, error, errorStatus } = useApiData(() => api.modelInfo(), []);

  if (errorStatus === 503) return <ModelUntrainedNotice />;
  if (loading || error || !data) return <StatusBox loading={loading} error={error} />;

  const { metrics } = data;

  return (
    <div>
      <div className="model-stats">
        <div>
          <div className="model-stat-value">{metrics.mae_eur_mwh !== null ? formatNumber(metrics.mae_eur_mwh, 2) : "—"}</div>
          <div className="model-stat-label">MAE (€/MWh)</div>
        </div>
        <div>
          <div className="model-stat-value">{metrics.r2 !== null ? formatNumber(metrics.r2, 3) : "—"}</div>
          <div className="model-stat-label">R²</div>
        </div>
        <div>
          <div className="model-stat-value">{data.n_training_rows}</div>
          <div className="model-stat-label">Treningsrader</div>
        </div>
        <div>
          <div className="model-stat-value">{new Date(data.trained_at).toLocaleDateString("no-NO")}</div>
          <div className="model-stat-label">Sist trent</div>
        </div>
      </div>

      <h3 className="feature-importance-title">Viktigste features</h3>
      <div className="feature-bars">
        {data.feature_importances.slice(0, 8).map((fi) => {
          const max = data.feature_importances[0]?.importance || 1;
          const pct = max > 0 ? (fi.importance / max) * 100 : 0;
          return (
            <div key={fi.feature} className="feature-bar-row">
              <span className="feature-bar-label">{fi.feature}</span>
              <div className="feature-bar-track">
                <div className="feature-bar-fill" style={{ width: `${pct}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function PredictionSection() {
  return (
    <>
      <Card title="Prisprediksjon (neste dag)">
        <PredictionCard />
      </Card>
      <Card title="Om modellen">
        <ModelInfoCard />
      </Card>
    </>
  );
}
