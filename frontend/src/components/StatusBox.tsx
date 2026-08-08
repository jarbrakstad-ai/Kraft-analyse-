export function StatusBox({ loading, error, empty }: { loading: boolean; error: string | null; empty?: boolean }) {
  if (loading) return <div className="status status-loading">Laster...</div>;
  if (error) return <div className="status status-error">Feil: {error}</div>;
  if (empty) return <div className="status status-empty">Ingen data for valgt periode/filter.</div>;
  return null;
}
