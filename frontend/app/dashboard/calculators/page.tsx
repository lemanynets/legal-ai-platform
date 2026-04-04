"use client";

import { FormEvent, useState, useCallback } from "react";
import { getToken, getUserId } from "@/lib/auth";
import {
  calculateFullClaim,
  getCalculationHistory,
  getCalculationDetail,
  type FullCalculationResponse,
  type CalculationHistoryResponse,
  type CalculationDetailResponse,
} from "@/lib/api";

function formatUAH(value: number | null | undefined): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("uk-UA", { style: "currency", currency: "UAH", maximumFractionDigits: 2 }).format(value);
}

export default function CalculatorsPage() {
  const [claimAmount, setClaimAmount] = useState("100000");
  const [principalAmount, setPrincipalAmount] = useState("100000");
  const [debtStartDate, setDebtStartDate] = useState("2025-01-01");
  const [debtEndDate, setDebtEndDate] = useState("2025-12-31");
  const [processStartDate, setProcessStartDate] = useState("2026-02-22");
  const [processDays, setProcessDays] = useState("30");
  const [violationDate, setViolationDate] = useState("2025-01-01");
  const [limitationYears, setLimitationYears] = useState("3");
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [save, setSave] = useState(true);

  const [result, setResult] = useState<FullCalculationResponse | null>(null);
  const [history, setHistory] = useState<CalculationHistoryResponse | null>(null);
  const [detail, setDetail] = useState<CalculationDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [detailLoadingId, setDetailLoadingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    setError("");
    try {
      const res = await getCalculationHistory({ page: 1, page_size: 20, calculation_type: "full_claim" }, getToken(), getUserId());
      setHistory(res);
    } catch (err) {
      setError(String(err));
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  async function loadDetail(id: string) {
    setDetailLoadingId(id);
    setError("");
    try {
      const res = await getCalculationDetail(id, getToken(), getUserId());
      setDetail(res);
    } catch (err) {
      setError(String(err));
    } finally {
      setDetailLoadingId(null);
    }
  }

  async function onCalculate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setInfo("");
    try {
      const res = await calculateFullClaim(
        {
          claim_amount_uah: Number(claimAmount),
          principal_uah: Number(principalAmount),
          debt_start_date: debtStartDate,
          debt_end_date: debtEndDate,
          process_start_date: processStartDate,
          process_days: Number(processDays),
          violation_date: violationDate,
          limitation_years: Number(limitationYears),
          save,
          title: title.trim() || undefined,
          notes: notes.trim() || undefined,
        },
        getToken(),
        getUserId()
      );
      setResult(res);
      setInfo(res.saved ? `Збережено як ${res.calculation_id}.` : "Розраховано без збереження.");
      if (res.saved) await loadHistory();
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="section-header">
        <div>
          <h1 className="section-title">Юридичні калькулятори</h1>
          <p className="section-subtitle">Розрахунок судового збору, пені, строків позовної давності</p>
        </div>
        <button type="button" className="btn btn-secondary btn-sm" onClick={loadHistory} disabled={historyLoading}>
          {historyLoading ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Завантаження...</> : "📋 Історія розрахунків"}
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: result ? "1fr 1fr" : "1fr", gap: "24px" }}>
        {/* Form */}
        <form onSubmit={onCalculate} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>

          <div className="card-elevated" style={{ padding: "20px" }}>
            <h2 style={{ fontSize: "15px", fontWeight: 700, marginBottom: "16px", color: "var(--text-primary)" }}>
              🧮 Повний розрахунок вимоги
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
              {[
                { label: "Сума позову (грн)", value: claimAmount, set: setClaimAmount, type: "number", min: "1" },
                { label: "Основний борг (грн)", value: principalAmount, set: setPrincipalAmount, type: "number", min: "1" },
                { label: "Початок боргу", value: debtStartDate, set: setDebtStartDate, type: "date" },
                { label: "Кінець боргу", value: debtEndDate, set: setDebtEndDate, type: "date" },
                { label: "Початок провадження", value: processStartDate, set: setProcessStartDate, type: "date" },
                { label: "Тривалість (днів)", value: processDays, set: setProcessDays, type: "number", min: "1", max: "3650" },
                { label: "Дата порушення", value: violationDate, set: setViolationDate, type: "date" },
                { label: "Позовна давність (роки)", value: limitationYears, set: setLimitationYears, type: "number", min: "1", max: "20" },
              ].map(({ label, value, set, type, min, max }) => (
                <div key={label} className="form-group">
                  <label className="form-label">{label}</label>
                  <input
                    className="form-input"
                    type={type}
                    value={value}
                    min={min}
                    max={max}
                    onChange={(e) => set(e.target.value)}
                  />
                </div>
              ))}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px", marginTop: "14px" }}>
              <div className="form-group">
                <label className="form-label">Назва (необов'язково)</label>
                <input className="form-input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Справа №..." />
              </div>
              <div className="form-group">
                <label className="form-label">Нотатки (необов'язково)</label>
                <input className="form-input" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Додаткові примітки" />
              </div>
            </div>

            <div className="flex items-center gap-2" style={{ marginTop: "14px" }}>
              <input
                type="checkbox"
                id="saveCalc"
                checked={save}
                onChange={(e) => setSave(e.target.checked)}
                style={{ accentColor: "var(--gold-500)", width: "16px", height: "16px" }}
              />
              <label htmlFor="saveCalc" className="text-sm text-secondary">Зберегти в історію</label>
            </div>
          </div>

          {error && <div className="alert alert-error">⚠ {error}</div>}
          {info && <div className="alert alert-success">✓ {info}</div>}

          <button type="submit" className="btn btn-primary btn-lg" disabled={loading}>
            {loading ? <><span className="spinner" style={{ width: 16, height: 16 }} /> Розрахунок...</> : "🧮 Розрахувати"}
          </button>
        </form>

        {/* Result */}
        {result && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div className="card-elevated" style={{ padding: "20px" }}>
              <h2 style={{ fontSize: "15px", fontWeight: 700, marginBottom: "16px", color: "var(--text-primary)" }}>
                Результат розрахунку
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {[
                  ["Судовий збір", formatUAH(result.result.court_fee_uah)],
                  ["Пеня", formatUAH(result.result.penalty_uah)],
                  ["Загальна сума позову", formatUAH(result.result.total_claim_uah)],
                  ["Загальна сума зі збором", formatUAH(result.result.total_with_fee_uah)],
                  ["Дедлайн провадження", result.result.process_deadline ?? "—"],
                  ["Позовна давність до", result.result.limitation_deadline ?? "—"],
                ].map(([label, value]) => (
                  <div key={label} style={{
                    display: "flex", justifyContent: "space-between", padding: "8px 12px",
                    background: "rgba(0,0,0,0.15)", borderRadius: "6px",
                  }}>
                    <span className="text-sm text-muted">{label}</span>
                    <span style={{
                      fontSize: "13px", fontWeight: 700,
                      color: String(value).includes("⚠") ? "var(--warning)" : "var(--gold-400)",
                    }}>{value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* History */}
      {history && history.items.length > 0 && (
        <div className="card-elevated" style={{ padding: "20px", marginTop: "24px" }}>
          <h2 style={{ fontSize: "15px", fontWeight: 700, marginBottom: "14px", color: "var(--text-primary)" }}>
            Історія розрахунків ({history.total})
          </h2>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Назва</th>
                  <th>Тип</th>
                  <th>Дата</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {history.items.map((item) => (
                  <tr key={item.id}>
                    <td className="text-primary font-semibold">{item.title || item.id}</td>
                    <td><span className="badge badge-blue">{item.calculation_type}</span></td>
                    <td className="text-muted text-sm">{new Date(item.created_at).toLocaleDateString("uk-UA")}</td>
                    <td>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => void loadDetail(item.id)}
                        disabled={detailLoadingId === item.id}
                      >
                        {detailLoadingId === item.id ? "..." : "Відкрити"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {detail && (
        <div className="card-elevated" style={{ padding: "20px", marginTop: "16px" }}>
          <h2 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "12px" }}>Деталі розрахунку</h2>
          <pre style={{ fontSize: "12px", color: "var(--text-muted)", overflow: "auto" }}>
            {JSON.stringify(detail.item, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
