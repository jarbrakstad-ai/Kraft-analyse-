import { useMemo } from "react";
import { api } from "../api";
import { useApiData } from "../useApiData";
import { Card } from "./Card";
import { StatusBox } from "./StatusBox";
import { ZoneMap } from "./ZoneMap";

export function BalanceMapSection() {
  const no = useApiData(() => api.deficitForecast("NO"), []);
  const eu = useApiData(() => api.deficitForecast("EU"), []);

  const loading = no.loading || eu.loading;
  const error = no.error ?? eu.error;
  const errorStatus = no.errorStatus ?? eu.errorStatus;

  const values = useMemo(() => {
    const breakdown = [...(no.data?.zone_breakdown ?? []), ...(eu.data?.zone_breakdown ?? [])];
    return breakdown.map((zb) => ({ zone: zb.zone, balance_mw: zb.predicted_balance_mw }));
  }, [no.data, eu.data]);

  const predictedDate = no.data?.predicted_date ?? eu.data?.predicted_date;

  return (
    <Card title="Kart: forventet under-/overskudd neste dag">
      {errorStatus === 503 && (
        <div className="status">
          Underskuddsmodellen er ikke trent ennå. Kjør <code>python -m app.ml.train</code> i <code>backend/</code>{" "}
          når det finnes forbruksdata og noen ukers historikk.
        </div>
      )}
      {errorStatus !== 503 && <StatusBox loading={loading} error={error} empty={!loading && values.length === 0} />}

      {values.length > 0 && (
        <>
          {predictedDate && (
            <p className="hint">
              Prisområder farget etter predikert kraftbalanse for {new Date(predictedDate).toLocaleDateString("no-NO")}. Skjematisk
              kart — ikke geografisk nøyaktig.
            </p>
          )}
          <ZoneMap values={values} label="Kart over prisområder farget etter forventet kraftbalanse neste dag" />
        </>
      )}
    </Card>
  );
}
