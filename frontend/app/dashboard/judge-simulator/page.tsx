"use client";

import { FormEvent, Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { getToken, getUserId } from "@/lib/auth";
import {
  runJudgeSimulation,
  getDocumentsHistory,
  type JudgeSimulationResponse,
  type DocumentHistoryItem,
} from "@/lib/api";

function JudgeSimulatorContent() {
  const searchParams = useSearchParams();

  const [strategyId, setStrategyId] = useState(searchParams.get("strategy_id") || "");
  const [documentId, setDocumentId] = useState(searchParams.get("document_id") || "");
  const [documents, setDocuments] = useState<DocumentHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [result, setResult] = useState<JudgeSimulationResponse | null>(null);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<JudgeSimulationResponse[]>([]);

  useEffect(() => {
    setLoadingDocs(true);
    getDocumentsHistory({ page: 1, page_size: 30 }, getToken(), getUserId())
      .then((res) => setDocuments(res.items || []))
      .catch((err) => console.error("Failed to load documents:", err))
      .finally(() => setLoadingDocs(false));
  }, []);

  async function onSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!strategyId.trim()) {
      setError("Введіть Strategy ID для симуляції.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await runJudgeSimulation(
        { strategy_id: strategyId.trim(), document_id: documentId.trim() || undefined },
        getToken(),
        getUserId()
      );
      setResult(res);
      setHistory((prev) => [res, ...prev].slice(0, 5));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  const verdictColor = (prob: number) =>
    prob >= 0.7 ? "var(--success)" : prob >= 0.45 ? "var(--warning)" : "var(--danger)";

  const verdictLabel = (prob: number) =>
    prob >= 0.7 ? "Висока" : prob >= 0.45 ? "Середня" : "Низька";

  return (
    <div>
      <div className="section-header">
        <div>
          <h1 className="section-title">Симулятор судді</h1>
          <p className="section-subtitle">
            Аналіз перспектив справи з позиції судді — виявлення вразливостей та сильних сторін
          </p>
        </div>
        <Link href="/dashboard/strategy-studio" className="btn btn-ghost" style={{ fontSize: 13 }}>
          ← Strategy Studio
        </Link>
      </div>

      {error && (
        <div className="preflight-block" style={{ marginBottom: 16 }}>
          <span style={{ color: "var(--danger)" }}>⚠ {error}</span>
        </div>
      )}

      <div className="grid-2" style={{ gap: 20, marginBottom: 20 }}>
        {/* Form */}
        <div className="card-elevated" style={{ padding: 24 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16, color: "var(--text-primary)" }}>
            ⚖️ Параметри симуляції
          </h2>
          <form onSubmit={onSubmit}>
            <div style={{ marginBottom: 16 }}>
              <label className="form-label">Strategy ID *</label>
              <input
                className="form-input"
                placeholder="Вставте ID стратегії зі Strategy Studio"
                value={strategyId}
                onChange={(e) => setStrategyId(e.target.value)}
              />
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                Отримайте ID після проходження стратегії в{" "}
                <Link href="/dashboard/strategy-studio" style={{ color: "var(--gold-400)" }}>
                  Strategy Studio
                </Link>
              </div>
            </div>

            <div style={{ marginBottom: 20 }}>
              <label className="form-label">Документ для аналізу (необов&apos;язково)</label>
              {loadingDocs ? (
                <div style={{ fontSize: 13, color: "var(--text-muted)", padding: "8px 0" }}>Завантаження документів...</div>
              ) : (
                <select
                  className="form-input"
                  value={documentId}
                  onChange={(e) => setDocumentId(e.target.value)}
                >
                  <option value="">Без документа (аналіз на основі стратегії)</option>
                  {documents.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.title || doc.document_type} — {new Date(doc.created_at || "").toLocaleDateString("uk-UA")}
                    </option>
                  ))}
                </select>
              )}
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                Якщо обрано документ — суддя аналізує його текст, інакше — процесуальну карту стратегії
              </div>
            </div>

            <div
              className="card-elevated"
              style={{
                padding: 14,
                marginBottom: 20,
                background: "rgba(212,168,67,0.06)",
                border: "1px solid rgba(212,168,67,0.15)",
                borderRadius: 8,
              }}
            >
              <div style={{ fontSize: 12, color: "var(--gold-400)", fontWeight: 700, marginBottom: 6 }}>
                Що робить симулятор?
              </div>
              <ul style={{ fontSize: 12, color: "var(--text-muted)", paddingLeft: 16, margin: 0 }}>
                <li style={{ marginBottom: 4 }}>Оцінює вірогідність позитивного судового рішення</li>
                <li style={{ marginBottom: 4 }}>Виявляє процесуальні ризики та вразливості</li>
                <li style={{ marginBottom: 4 }}>Виділяє сильні сторони позиції</li>
                <li style={{ marginBottom: 4 }}>Пропонує конкретні корекції для посилення документів</li>
              </ul>
            </div>

            <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: "100%" }}>
              {loading ? "Симуляція..." : "🧑‍⚖️ Запустити симуляцію судді"}
            </button>
          </form>
        </div>

        {/* Result or placeholder */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {result ? (
            <div
              className="card-elevated"
              style={{ padding: 24, border: "1px solid var(--gold-500)", flex: 1 }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
                <div>
                  <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 4 }}>Персона судді</div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: "#fff" }}>{result.judge_persona}</div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>Вірогідність перемоги</div>
                  <div
                    style={{
                      fontSize: 32,
                      fontWeight: 900,
                      color: verdictColor(result.verdict_probability),
                      lineHeight: 1,
                    }}
                  >
                    {Math.round(result.verdict_probability * 100)}%
                  </div>
                  <div style={{ fontSize: 11, color: verdictColor(result.verdict_probability), marginTop: 2 }}>
                    {verdictLabel(result.verdict_probability)}
                  </div>
                </div>
              </div>

              <div
                style={{
                  padding: "12px 16px",
                  background: "rgba(255,255,255,0.03)",
                  borderRadius: 8,
                  borderLeft: "3px solid var(--gold-500)",
                  marginBottom: 16,
                  fontSize: 13,
                  color: "var(--text-secondary)",
                  fontStyle: "italic",
                  lineHeight: 1.6,
                }}
              >
                &ldquo;{result.judge_commentary}&rdquo;
              </div>

              <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>Обґрунтування рішення:</div>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: 0 }}>
                {result.decision_rationale}
              </p>
            </div>
          ) : (
            <div
              className="card-elevated"
              style={{
                padding: 40,
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: 12,
                border: "1px dashed rgba(255,255,255,0.1)",
              }}
            >
              <div style={{ fontSize: 48 }}>🧑‍⚖️</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", textAlign: "center" }}>
                Суддя очікує на матеріали справи
              </div>
              <div style={{ fontSize: 12, color: "var(--text-muted)", textAlign: "center", maxWidth: 280 }}>
                Введіть Strategy ID та натисніть кнопку для запуску симуляції судового рішення
              </div>
            </div>
          )}

          {/* History */}
          {history.length > 0 && (
            <div className="card-elevated" style={{ padding: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, color: "var(--text-primary)" }}>
                Остання симуляція
              </div>
              {history.map((h, i) => (
                <div
                  key={i}
                  onClick={() => setResult(h)}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "8px 10px",
                    borderRadius: 6,
                    cursor: "pointer",
                    background: result?.id === h.id ? "rgba(212,168,67,0.08)" : "transparent",
                    marginBottom: 4,
                  }}
                >
                  <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                    {h.judge_persona}
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: verdictColor(h.verdict_probability) }}>
                    {Math.round(h.verdict_probability * 100)}%
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Detailed result */}
      {result && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="grid-2" style={{ gap: 16 }}>
            {/* Vulnerabilities */}
            {result.key_vulnerabilities?.length > 0 && (
              <div className="card-elevated" style={{ padding: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: "var(--danger)" }}>
                  ⚠ Ключові вразливості
                </h3>
                <ul style={{ paddingLeft: 16, margin: 0 }}>
                  {result.key_vulnerabilities.map((v, i) => (
                    <li key={i} style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 8, lineHeight: 1.5 }}>
                      {v}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Strong points */}
            {result.strong_points?.length > 0 && (
              <div className="card-elevated" style={{ padding: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: "var(--success)" }}>
                  ✓ Сильні сторони
                </h3>
                <ul style={{ paddingLeft: 16, margin: 0 }}>
                  {result.strong_points.map((v, i) => (
                    <li key={i} style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 8, lineHeight: 1.5 }}>
                      {v}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="grid-2" style={{ gap: 16 }}>
            {/* Procedural risks */}
            {result.procedural_risks?.length > 0 && (
              <div className="card-elevated" style={{ padding: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: "var(--warning)" }}>
                  📋 Процесуальні ризики
                </h3>
                <ul style={{ paddingLeft: 16, margin: 0 }}>
                  {result.procedural_risks.map((v, i) => (
                    <li key={i} style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 8, lineHeight: 1.5 }}>
                      {v}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Suggested corrections */}
            {result.suggested_corrections?.length > 0 && (
              <div className="card-elevated" style={{ padding: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: "var(--gold-400)" }}>
                  💡 Рекомендовані корекції
                </h3>
                <ul style={{ paddingLeft: 16, margin: 0 }}>
                  {result.suggested_corrections.map((v, i) => (
                    <li key={i} style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 8, lineHeight: 1.5 }}>
                      {v}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="card-elevated" style={{ padding: 20, display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
            <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
              Strategy ID: <code style={{ color: "var(--gold-400)", fontSize: 12 }}>{result.strategy_blueprint_id}</code>
            </div>
            <Link
              href={`/dashboard/strategy-studio`}
              className="btn btn-ghost"
              style={{ fontSize: 12 }}
            >
              Повернутись до Strategy Studio →
            </Link>
            <button
              onClick={() => setResult(null)}
              className="btn btn-ghost"
              style={{ fontSize: 12 }}
            >
              Нова симуляція
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function JudgeSimulatorPage() {
  return (
    <Suspense fallback={<div className="card-elevated" style={{ padding: 24 }}>Завантаження...</div>}>
      <JudgeSimulatorContent />
    </Suspense>
  );
}
