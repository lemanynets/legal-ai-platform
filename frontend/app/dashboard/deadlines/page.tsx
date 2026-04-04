"use client";

import { FormEvent, useEffect, useState } from "react";
import { getToken, getUserId } from "@/lib/auth";
import { createDeadline, getDeadlines, type DeadlineListResponse } from "@/lib/api";

const DEADLINE_TYPES = [
  { value: "appeal", label: "Апеляція" },
  { value: "cassation", label: "Касація" },
  { value: "response", label: "Відповідь" },
  { value: "payment", label: "Сплата мита" },
  { value: "submission", label: "Подання документів" },
  { value: "other", label: "Інше" },
];

export default function DeadlinesPage() {
  const [title, setTitle] = useState("");
  const [deadlineType, setDeadlineType] = useState("appeal");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [notes, setNotes] = useState("");
  const [data, setData] = useState<DeadlineListResponse | null>(null);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => { void refresh(); }, []);

  async function refresh(): Promise<void> {
    setLoading(true); setError("");
    try {
      const response = await getDeadlines(getToken(), getUserId());
      setData(response);
    } catch (err) { setError(String(err)); }
    finally { setLoading(false); }
  }

  async function onCreate(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setLoading(true); setError(""); setInfo("");
    try {
      await createDeadline(
        { title, deadline_type: deadlineType, start_date: startDate || undefined, end_date: endDate || undefined, notes: notes || undefined },
        getToken(), getUserId()
      );
      setTitle(""); setNotes(""); setStartDate(""); setEndDate("");
      setInfo("Строк успішно додано!");
      await refresh();
    } catch (err) { setError(String(err)); }
    finally { setLoading(false); }
  }

  const isOverdue = (endDate: string | null) => {
    if (!endDate) return false;
    return new Date(endDate) < new Date();
  };

  const daysLeft = (endDate: string | null) => {
    if (!endDate) return null;
    const diff = Math.ceil((new Date(endDate).getTime() - Date.now()) / 86400000);
    return diff;
  };

  return (
    <div>
      <div className="section-header">
        <div>
          <h1 className="section-title">Строки</h1>
          <p className="section-subtitle">Відстеження процесуальних строків та дедлайнів</p>
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={refresh} disabled={loading}>
          {loading ? "Оновлення..." : "↻ Оновити"}
        </button>
      </div>

      {error && <div className="preflight-block" style={{ marginBottom: 16 }}><span style={{ color: "var(--danger)" }}>⚠ {error}</span></div>}
      {info && <div className="card-elevated" style={{ padding: "12px 16px", marginBottom: 16, borderLeft: "3px solid var(--success)", color: "var(--success)" }}>✓ {info}</div>}

      <div className="grid-2" style={{ gap: 20, marginBottom: 20 }}>
        {/* Add new deadline */}
        <div className="card-elevated" style={{ padding: 24 }}>
          <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 20, color: "var(--text-primary)" }}>➕ Новий строк</h2>
          <form onSubmit={onCreate}>
            <div style={{ marginBottom: 14 }}>
              <label className="form-label">Назва <span style={{ color: "var(--danger)" }}>*</span></label>
              <input className="form-input" value={title} onChange={(e) => setTitle(e.target.value)} required placeholder="Подання апеляційної скарги" />
            </div>
            <div style={{ marginBottom: 14 }}>
              <label className="form-label">Тип строку</label>
              <select className="form-input" value={deadlineType} onChange={(e) => setDeadlineType(e.target.value)}>
                {DEADLINE_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div className="grid-2" style={{ marginBottom: 14 }}>
              <div>
                <label className="form-label">Дата початку</label>
                <input className="form-input" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
              </div>
              <div>
                <label className="form-label">Дата закінчення</label>
                <input className="form-input" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
              </div>
            </div>
            <div style={{ marginBottom: 14 }}>
              <label className="form-label">Нотатки</label>
              <input className="form-input" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Додаткова інформація..." />
            </div>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? "Збереження..." : "Зберегти строк"}
            </button>
          </form>
        </div>

        {/* Stats */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {data && ([
            { label: "Всього строків", value: data.total, icon: "📋" },
            { label: "Прострочені", value: data.items?.filter((i) => isOverdue(i.end_date)).length ?? 0, icon: "🔴" },
            { label: "Активні", value: data.items?.filter((i) => !isOverdue(i.end_date) && i.end_date).length ?? 0, icon: "🟢" },
          ].map(({ label, value, icon }) => (
            <div key={label} className="stat-card">
              <div className="stat-label">{icon} {label}</div>
              <div className="stat-value">{value}</div>
            </div>
          )))}
        </div>
      </div>

      {/* Deadlines list */}
      {data && data.items && data.items.length > 0 && (
        <div className="card-elevated" style={{ padding: 24 }}>
          <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, color: "var(--text-primary)" }}>📅 Список строків</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {data.items.map((item) => {
              const overdue = isOverdue(item.end_date);
              const days = daysLeft(item.end_date);
              const urgent = days !== null && days >= 0 && days <= 3;
              return (
                <div key={item.id} className="card-elevated" style={{
                  padding: "14px 16px",
                  borderLeft: `3px solid ${overdue ? "var(--danger)" : urgent ? "var(--warning, #f59e0b)" : "var(--success)"}`,
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>{item.title}</div>
                      <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
                        {DEADLINE_TYPES.find((t) => t.value === item.deadline_type)?.label || item.deadline_type}
                        {item.start_date && ` · з ${item.start_date}`}
                      </div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      {item.end_date && (
                        <span className={`badge ${overdue ? "badge-danger" : urgent ? "badge-warning" : "badge-success"}`}>
                          {overdue ? "Прострочено" : days === 0 ? "Сьогодні!" : `${days} дн.`}
                        </span>
                      )}
                      <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>{item.end_date || "—"}</div>
                    </div>
                  </div>
                  {item.notes && <p style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 8 }}>{item.notes}</p>}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {data && data.total === 0 && (
        <div className="card-elevated" style={{ padding: 40, textAlign: "center" }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>📅</div>
          <p style={{ color: "var(--text-muted)", fontSize: 14 }}>Строків не знайдено. Додайте перший строк.</p>
        </div>
      )}
    </div>
  );
}
