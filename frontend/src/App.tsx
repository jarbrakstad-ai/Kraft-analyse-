import { useState } from "react";
import { api } from "./api";
import { useApiData } from "./useApiData";
import { PriceSection } from "./components/PriceSection";
import { ProductionSection } from "./components/ProductionSection";
import { FlowSection } from "./components/FlowSection";
import { ReservoirSection } from "./components/ReservoirSection";
import { WeatherSection } from "./components/WeatherSection";
import { AnalysisSection } from "./components/AnalysisSection";

type Tab = "priser" | "produksjon" | "flyt" | "magasin" | "vaer" | "analyse";

const TABS: { value: Tab; label: string }[] = [
  { value: "priser", label: "Priser" },
  { value: "produksjon", label: "Produksjon" },
  { value: "flyt", label: "Grenseflyt" },
  { value: "magasin", label: "Magasinfylling" },
  { value: "vaer", label: "Vær" },
  { value: "analyse", label: "Korrelasjon" },
];

function HealthBadge() {
  const { data, loading } = useApiData(() => api.health(), []);
  if (loading) return <span className="badge badge-loading">API: sjekker...</span>;
  if (!data || data.status !== "ok") return <span className="badge badge-down">API: nede</span>;
  return <span className="badge badge-ok">API: OK</span>;
}

function App() {
  const [tab, setTab] = useState<Tab>("priser");

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Kraft-analyse</h1>
          <p className="subtitle">Pris, produksjon, flyt, magasinfylling og vær i det norske kraftsystemet</p>
        </div>
        <HealthBadge />
      </header>

      <nav className="tabs">
        {TABS.map((t) => (
          <button key={t.value} className={`tab ${tab === t.value ? "active" : ""}`} onClick={() => setTab(t.value)}>
            {t.label}
          </button>
        ))}
      </nav>

      <main className="app-main">
        {tab === "priser" && <PriceSection />}
        {tab === "produksjon" && <ProductionSection />}
        {tab === "flyt" && <FlowSection />}
        {tab === "magasin" && <ReservoirSection />}
        {tab === "vaer" && <WeatherSection />}
        {tab === "analyse" && <AnalysisSection />}
      </main>
    </div>
  );
}

export default App;
