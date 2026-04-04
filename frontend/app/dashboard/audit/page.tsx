"use client";

import { useEffect, useState } from "react";
import { getToken, getUserId } from "@/lib/auth";
import {
  getAuditHistory,
  getAuditIntegrity,
  type AuditHistoryResponse,
  type AuditIntegrityResponse
} from "@/lib/api";

export default function AuditPage() {
  const [action, setAction] = useState("");
  const [entityType, setEntityType] = useState("");
  const [query, setQuery] = useState("");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [pageSize, setPageSize] = useState(20);
  const [history, setHistory] = useState<AuditHistoryResponse | null>(null);
  const [integrity, setIntegrity] = useState<AuditIntegrityResponse | null>(null);
  const [integrityMaxRows, setIntegrityMaxRows] = useState(2000);
  const [loading, setLoading] = useState(false);
  const [checkingIntegrity, setCheckingIntegrity] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  useEffect(() => { void load(1); }, []);

  async function load(page: number = history?.page ?? 1): Promise<void> {
    setError(""); setInfo(""); setLoading(true);
    try {
      const result = await getAuditHistory(
        {
          page, page_size: pageSize,
          action: action.trim() || undefined,
          entity_type: entityType.trim() || undefined,
          query: query.trim() || undefined,
          sort_dir: sortDir
        },
        getToken(), getUserId()
      );
      setHistory(result);
    } catch (err) { setError(String(err)); }
    finally { setLoading(false); }
  }

  async function verifyIntegrity(): Promise<void> {
    setError(""); setInfo(""); setCheckingIntegrity(true);
    try {
      const result = await getAuditIntegrity({ max_rows: integrityMaxRows }, getToken(), getUserId());
      setIntegrity(result);
      if (result.status === "pass") setInfo(`Цілісність підтверджена. Перевірено ${result.rows_checked} записів.`);
      else setInfo(`Виявлено проблеми цілісності: ${result.issues.length}.`);
    } catch (err) { setError(String(err)); }
    finally { setCheckingIntegrity(false); }
  }

  return (
    <div className="animate-fade-in">
      <div className="section-header">
        <div>
          <h1 className="section-title">Журнал аудиту</h1>
          <p className="section-subtitle">Система контролю цілісності даних на основі криптографічних гешів</p>
        </div>
        <div style={{ display: "flex", gap: "12px" }}>
          <button className="btn btn-secondary btn-sm" onClick={verifyIntegrity} disabled={checkingIntegrity}>
            {checkingIntegrity ? "Перевірка..." : "🔐 Перевірити цілісність"}
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => load()} disabled={loading}>
            {loading ? "..." : "↻ Оновити"}
          </button>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "32px" }}>
        
        {/* Integrity Result */}
        {integrity && (
          <div className="card-elevated" style={{ 
            padding: "32px", 
            border: `1px solid ${integrity.status === "pass" ? "rgba(34, 197, 94, 0.2)" : "rgba(239, 68, 68, 0.2)"}`,
            background: integrity.status === "pass" ? "rgba(34, 197, 94, 0.02)" : "rgba(239, 68, 68, 0.02)"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
               <div>
                 <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
                    <span style={{ fontSize: "24px" }}>{integrity.status === 'pass' ? '🛡️' : '⚠️'}</span>
                    <h2 style={{ fontSize: "20px", fontWeight: 800 }}>Звіт про цілісність</h2>
                 </div>
                 <p style={{ fontSize: "14px", color: "var(--text-secondary)" }}>
                   Статус: <strong style={{ color: integrity.status === 'pass' ? "var(--success)" : "var(--danger)" }}>{integrity.status.toUpperCase()}</strong> | 
                   Перевірено: <strong>{integrity.rows_checked}</strong> / {integrity.rows_total} записів
                 </p>
               </div>
               <div style={{ textAlign: "right", fontSize: "12px", color: "var(--text-muted)" }}>
                 Остання перевірка: {integrity.verified_at}<br/>
                 Tail Hash: <code style={{ color: "var(--gold-400)" }}>{integrity.tail_hash?.slice(0, 16)}...</code>
               </div>
            </div>
          </div>
        )}

        {/* Filters & Table */}
        <div className="card-elevated" style={{ padding: "32px" }}>
          
          <div style={{ display: "flex", gap: "20px", marginBottom: "32px", alignItems: "flex-end" }}>
            <div style={{ flex: 1 }}>
              <label className="form-label">Пошук</label>
              <input className="form-input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Пошук за метаданими..." />
            </div>
            <div style={{ width: "200px" }}>
              <label className="form-label">Дія</label>
              <select className="form-select" value={action} onChange={(e) => setAction(e.target.value)}>
                <option value="">Усі дії</option>
                <option value="login">Вхід</option>
                <option value="create">Створення</option>
                <option value="update">Оновлення</option>
                <option value="delete">Видалення</option>
              </select>
            </div>
            <button className="btn btn-primary" onClick={() => load(1)}>Знайти</button>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: "0 8px" }}>
              <thead>
                <tr style={{ color: "var(--text-muted)", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  <th style={{ textAlign: "left", padding: "0 12px" }}>Дата та час</th>
                  <th style={{ textAlign: "left", padding: "0 12px" }}>Дія</th>
                  <th style={{ textAlign: "left", padding: "0 12px" }}>Об'єкт</th>
                  <th style={{ textAlign: "center", padding: "0 12px" }}>Геш</th>
                  <th style={{ textAlign: "left", padding: "0 12px" }}>Опис</th>
                </tr>
              </thead>
              <tbody>
                {(history?.items || []).map((item) => (
                  <tr key={item.id} className="card-hover" style={{ background: "rgba(255,255,255,0.02)" }}>
                    <td style={{ padding: "16px 12px", borderTopLeftRadius: "12px", borderBottomLeftRadius: "12px", fontSize: "13px", color: "rgba(255,255,255,0.6)" }}>
                      {item.created_at}
                    </td>
                    <td style={{ padding: "16px 12px" }}>
                      <span className="badge badge-muted" style={{ fontWeight: 800 }}>{item.action}</span>
                    </td>
                    <td style={{ padding: "16px 12px", fontSize: "14px", fontWeight: 600 }}>
                      {item.entity_type || "SYSTEM"}
                    </td>
                    <td style={{ padding: "16px 12px", textAlign: "center" }}>
                       <span title="Криптографічно захищено" style={{ cursor: "help", fontSize: "16px" }}>
                         {item.integrity_hash ? "🔐" : "🔓"}
                       </span>
                    </td>
                    <td style={{ padding: "16px 12px", borderTopRightRadius: "12px", borderBottomRightRadius: "12px", fontSize: "12px", color: "var(--text-muted)" }}>
                      <div style={{ maxWidth: "400px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {JSON.stringify(item.metadata)}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {history && history.pages > 1 && (
            <div style={{ display: "flex", justifyContent: "center", gap: "12px", marginTop: "32px" }}>
              <button className="btn btn-secondary btn-sm" disabled={history.page <= 1} onClick={() => load(history.page - 1)}>Назад</button>
              <div style={{ display: "flex", alignItems: "center", padding: "0 16px", fontSize: "14px", fontWeight: 700 }}>
                {history.page} / {history.pages}
              </div>
              <button className="btn btn-secondary btn-sm" disabled={history.page >= history.pages} onClick={() => load(history.page + 1)}>Далі</button>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
