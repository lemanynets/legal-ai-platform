"use client";

import { useEffect, useState } from "react";
import { getToken, getUserId } from "@/lib/auth";
import {
  exportFullLawyerPreflightHistoryReport,
  getFullLawyerPreflightHistory,
  type FullLawyerPreflightHistoryResponse,
} from "@/lib/api";

const EVENT_OPTIONS: Array<{ value: "all" | "upload" | "export"; label: string }> = [
  { value: "all", label: "Всі події" },
  { value: "upload", label: "Завантаження" },
  { value: "export", label: "Експорт" },
];

const STATUS_BADGE: Record<string, string> = {
  pass: "badge-success",
  fail: "badge-danger",
  needs_clarification: "badge-warning",
};

export default function ReportsPage() {
  const [event, setEvent] = useState<"all" | "upload" | "export">("all");
  const [pageSize, setPageSize] = useState(20);
  const [history, setHistory] = useState<FullLawyerPreflightHistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloadingKey, setDownloadingKey] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  useEffect(() => { void load(1); }, []);

  async function load(page: number = history?.page ?? 1): Promise<void> {
    setLoading(true); setError(""); setInfo("");
    try {
      const result = await getFullLawyerPreflightHistory({ page, page_size: pageSize, event }, getToken(), getUserId());
      setHistory(result);
    } catch (err) { setError(String(err)); }
    finally { setLoading(false); }
  }

  async function downloadSnapshot(auditId: string, format: "pdf" | "docx"): Promise<void> {
    const key = `${auditId}:${format}`;
    setDownloadingKey(key); setError(""); setInfo("");
    try {
      const blob = await exportFullLawyerPreflightHistoryReport(auditId, format, getToken(), getUserId());
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `preflight-history-${auditId}.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setInfo(`Завантажено preflight-history-${auditId}.${format}`);
    } catch (err) { setError(String(err)); }
    finally { setDownloadingKey(null); }
  }

  return (
    <div>
      <div className="section-header">
        <div>
          <h1 className="section-title">Звіти</h1>
          <p className="section-subtitle">Історія префлайт-перевірок та аудит подань до суду</p>
        </div>
      </div>

      {error && <div className="preflight-block" style={{ marginBottom: 16 }}><span style={{ color: "var(--danger)" }}>⚠ {error}</span></div>}
      {info && <div className="card-elevated" style={{ padding: "12px 16px", marginBottom: 16, borderLeft: "3px solid var(--success)", color: "var(--success)" }}>✓ {info}</div>}

      {/* Filters */}
      <div className="card-elevated" style={{ padding: 20, marginBottom: 20 }}>
        <div style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
          <div>
            <label className="form-label">Тип події</label>
            <div style={{ display: "flex", gap: 6 }}>
              {EVENT_OPTIONS.map((opt) => (
                <button key={opt.value} type="button"
                  className={`btn btn-sm ${event === opt.value ? "btn-primary" : "btn-ghost"}`}
                  onClick={() => setEvent(opt.value)}>
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="form-label">Записів / сторінка</label>
            <select className="form-input" style={{ width: "auto" }} value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))}>
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </div>
          <button type="button" className="btn btn-primary btn-sm" onClick={() => load(1)} disabled={loading}>
            {loading ? "Завантаження..." : "Показати звіти"}
          </button>
        </div>
      </div>

      {/* Table */}
      {history && (
        <div className="card-elevated" style={{ padding: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
              Всього <strong style={{ color: "var(--text-primary)" }}>{history.total}</strong> записів
            </span>
            <div style={{ display: "flex", gap: 8 }}>
              <button type="button" className="btn btn-ghost btn-sm" disabled={loading || history.page <= 1} onClick={() => load(history.page - 1)}>
                ← Попередня
              </button>
              <span style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: "30px" }}>
                {history.page} / {history.pages}
              </span>
              <button type="button" className="btn btn-ghost btn-sm" disabled={loading || history.page >= history.pages} onClick={() => load(history.page + 1)}>
                Наступна →
              </button>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {history.items.map((item) => (
              <div key={item.id} className="card-elevated" style={{ padding: "14px 16px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                      {item.source_file_name || "Файл без назви"}
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
                      {item.created_at} · {item.event_type}
                      {item.format ? ` · ${item.format.toUpperCase()}` : ""}
                      {item.extracted_chars ? ` · ${item.extracted_chars} симв.` : ""}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    {item.final_submission_gate_status && (
                      <span className={`badge ${STATUS_BADGE[item.final_submission_gate_status] || "badge-muted"}`}>
                        {item.final_submission_gate_status}
                      </span>
                    )}
                    {item.has_report_snapshot && (
                      <div style={{ display: "flex", gap: 6 }}>
                        <button type="button" className="btn btn-sm btn-ghost"
                          disabled={downloadingKey === `${item.id}:pdf`}
                          onClick={() => downloadSnapshot(item.id, "pdf")}>
                          {downloadingKey === `${item.id}:pdf` ? "..." : "PDF"}
                        </button>
                        <button type="button" className="btn btn-sm btn-ghost"
                          disabled={downloadingKey === `${item.id}:docx`}
                          onClick={() => downloadSnapshot(item.id, "docx")}>
                          {downloadingKey === `${item.id}:docx` ? "..." : "DOCX"}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {history && history.total === 0 && (
        <div className="card-elevated" style={{ padding: 40, textAlign: "center" }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>📊</div>
          <p style={{ color: "var(--text-muted)", fontSize: 14 }}>Звітів не знайдено. Запустіть "Повний юрист" для створення звітів.</p>
        </div>
      )}
    </div>
  );
}
