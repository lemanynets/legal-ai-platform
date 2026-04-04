"use client";

import { useEffect } from "react";

export default function DashboardError({
  error,
  reset
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="page-content">
      <div className="card-elevated" style={{ padding: "24px" }}>
        <h2 className="section-title" style={{ fontSize: "24px" }}>Помилка дашборду</h2>
        <p className="section-subtitle" style={{ marginTop: "8px", marginBottom: "16px" }}>
          Не вдалося завантажити дані розділу.
        </p>
        <button type="button" className="btn btn-primary" onClick={reset}>
          Спробувати знову
        </button>
      </div>
    </div>
  );
}