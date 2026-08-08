import type { ReactNode } from "react";

export function Card({ title, controls, children }: { title: string; controls?: ReactNode; children: ReactNode }) {
  return (
    <section className="card">
      <div className="card-header">
        <h2>{title}</h2>
        {controls && <div className="card-controls">{controls}</div>}
      </div>
      <div className="card-body">{children}</div>
    </section>
  );
}
