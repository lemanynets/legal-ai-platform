"use client";

import { useEffect } from "react";

export default function GlobalError({
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
    <html lang="uk">
      <body className="inter-font">
        <div className="page-content">
          <div className="card-elevated" style={{ padding: "24px" }}>
            <h2 className="section-title" style={{ fontSize: "24px" }}>Сталася помилка</h2>
            <p className="section-subtitle" style={{ marginTop: "8px", marginBottom: "16px" }}>
              Не вдалося завантажити сторінку. Спробуй ще раз.
            </p>
            <button type="button" className="btn btn-primary" onClick={reset}>
              Повторити
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}