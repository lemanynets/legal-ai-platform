"use client";

import { useEffect, useMemo, useState } from "react";

import { getToken, getUserId } from "@/lib/auth";
import {
  getDocumentsHistory,
  getECourtCourts,
  getECourtHearings,
  getECourtHistory,
  searchPublicCourtCase,
  submitToECourt,
  syncECourtStatus,
  type ECourtHearingItem,
  type ECourtHistoryResponse,
  type ECourtSubmissionItem,
} from "@/lib/api";

type ReadyDocument = {
  id: string;
  document_type: string;
  e_court_ready: boolean;
  filing_blockers: string[];
};

type CaseRow = {
  id: string;
  case_number: string;
  court_name: string;
  next_hearing: string | null;
  judge: string | null;
  status: string | null;
  source: string;
};

const SIGNER_METHODS = [
  { value: "diia_sign", label: "Дія.Підпис" },
  { value: "mobile_id", label: "Mobile ID" },
  { value: "file_key", label: "Файловий КЕП" },
  { value: "hardware_key", label: "Апаратний КЕП" },
];

const STATUS_META: Record<string, { label: string; color: string; background: string }> = {
  submitted: { label: "Подано", color: "#d4a843", background: "rgba(212,168,67,0.12)" },
  pending: { label: "В черзі", color: "#f59e0b", background: "rgba(245,158,11,0.12)" },
  processing: { label: "Обробляється", color: "#3b82f6", background: "rgba(59,130,246,0.12)" },
  accepted: { label: "Прийнято", color: "#10b981", background: "rgba(16,185,129,0.12)" },
  delivered: { label: "Доставлено", color: "#10b981", background: "rgba(16,185,129,0.12)" },
  rejected: { label: "Відхилено", color: "#ef4444", background: "rgba(239,68,68,0.12)" },
  scheduled: { label: "Заплановано", color: "#3b82f6", background: "rgba(59,130,246,0.12)" },
};

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("uk-UA", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return value;
  }
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleDateString("uk-UA");
  } catch {
    return value;
  }
}

function badgeForStatus(status: string | null | undefined) {
  const meta = STATUS_META[(status || "").toLowerCase()] ?? {
    label: status || "Невідомо",
    color: "#94a3b8",
    background: "rgba(148,163,184,0.12)",
  };

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "4px 10px",
        borderRadius: "999px",
        fontSize: "12px",
        fontWeight: 700,
        color: meta.color,
        background: meta.background,
      }}
    >
      {meta.label}
    </span>
  );
}

function toPublicCaseRows(caseNumber: string, assignments: unknown[]): CaseRow[] {
  return assignments.map((item, index) => {
    const row = item as Record<string, unknown>;
    return {
      id: `public-${caseNumber}-${index}`,
      case_number: caseNumber,
      court_name: String(row.court_name || "Суд не вказано"),
      next_hearing: typeof row.date === "string" ? row.date : null,
      judge: typeof row.judge === "string" ? row.judge : null,
      status: typeof row.status === "string" ? row.status : "scheduled",
      source: "court.gov.ua/fair",
    };
  });
}

function groupHearingsToCases(items: ECourtHearingItem[]): CaseRow[] {
  const grouped = new Map<string, CaseRow>();

  items.forEach((item) => {
    const key = item.case_number || item.id;
    const nextHearing = item.time ? `${item.date}T${item.time}` : item.date;
    const existing = grouped.get(key);
    if (!existing) {
      grouped.set(key, {
        id: key,
        case_number: item.case_number,
        court_name: item.court_name,
        next_hearing: nextHearing,
        judge: item.judge || null,
        status: item.status || "scheduled",
        source: "cabinet.court.gov.ua",
      });
      return;
    }

    if (nextHearing && (!existing.next_hearing || nextHearing > existing.next_hearing)) {
      existing.next_hearing = nextHearing;
    }
    if (!existing.judge && item.judge) {
      existing.judge = item.judge;
    }
    if (!existing.status && item.status) {
      existing.status = item.status;
    }
  });

  return Array.from(grouped.values()).sort((a, b) => (b.next_hearing || "").localeCompare(a.next_hearing || ""));
}

export default function ECourtPage() {
  const [courts, setCourts] = useState<string[]>([]);
  const [courtsSource, setCourtsSource] = useState("fallback");
  const [history, setHistory] = useState<ECourtHistoryResponse | null>(null);
  const [hearings, setHearings] = useState<ECourtHearingItem[]>([]);
  const [documents, setDocuments] = useState<ReadyDocument[]>([]);
  const [searchCases, setSearchCases] = useState<CaseRow[]>([]);

  const [historyLoading, setHistoryLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);
  const [searchLoading, setSearchLoading] = useState(false);
  const [submitLoading, setSubmitLoading] = useState(false);
  const [syncingId, setSyncingId] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState("");
  const [caseSearchInput, setCaseSearchInput] = useState("");
  const [courtSearch, setCourtSearch] = useState("");
  const [docId, setDocId] = useState("");
  const [courtName, setCourtName] = useState("");
  const [signerMethod, setSignerMethod] = useState("diia_sign");
  const [note, setNote] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const readyDocuments = documents.filter((item) => item.e_court_ready);
  const cabinetCases = useMemo(() => groupHearingsToCases(hearings), [hearings]);
  const mergedCases = useMemo(() => {
    const byId = new Map<string, CaseRow>();
    [...searchCases, ...cabinetCases].forEach((item) => byId.set(`${item.source}-${item.case_number}-${item.court_name}`, item));
    return Array.from(byId.values());
  }, [cabinetCases, searchCases]);

  const filteredCourts = useMemo(
    () => courts.filter((item) => item.toLowerCase().includes(courtSearch.toLowerCase())).slice(0, 8),
    [courts, courtSearch]
  );

  const stats = {
    myCases: mergedCases.length,
    hearings: hearings.length,
    submissions: history?.total ?? 0,
    readyDocs: readyDocuments.length,
  };

  async function loadHistory(): Promise<void> {
    setHistoryLoading(true);
    try {
      const result = await getECourtHistory(
        { page: 1, page_size: 10, status: statusFilter || undefined },
        getToken(),
        getUserId()
      );
      setHistory(result);
    } catch (nextError) {
      setError(String(nextError));
    } finally {
      setHistoryLoading(false);
    }
  }

  useEffect(() => {
    let isMounted = true;

    async function bootstrap(): Promise<void> {
      setPageLoading(true);
      setError("");

      const [courtsResult, historyResult, hearingsResult, documentsResult] = await Promise.allSettled([
        getECourtCourts(getToken(), getUserId()),
        getECourtHistory({ page: 1, page_size: 10 }, getToken(), getUserId()),
        getECourtHearings(getToken(), getUserId()),
        getDocumentsHistory({ page: 1, page_size: 100 }, getToken(), getUserId()),
      ]);

      if (!isMounted) return;

      if (courtsResult.status === "fulfilled") {
        setCourts(courtsResult.value.courts);
        setCourtsSource(courtsResult.value.source);
      }
      if (historyResult.status === "fulfilled") {
        setHistory(historyResult.value);
      }
      if (hearingsResult.status === "fulfilled") {
        setHearings(hearingsResult.value.items);
      }
      if (documentsResult.status === "fulfilled") {
        setDocuments(
          documentsResult.value.items.map((item) => ({
            id: item.id,
            document_type: item.document_type,
            e_court_ready: item.e_court_ready,
            filing_blockers: item.filing_blockers,
          }))
        );
      }

      const rejected = [courtsResult, historyResult, hearingsResult, documentsResult].find((item) => item.status === "rejected");
      if (rejected && rejected.status === "rejected") {
        setError(String(rejected.reason));
      }

      setPageLoading(false);
    }

    void bootstrap();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (pageLoading) return;
    void loadHistory();
  }, [statusFilter]);

  async function handlePublicSearch(): Promise<void> {
    if (!caseSearchInput.trim()) return;

    setSearchLoading(true);
    setError("");
    setSuccess("");
    try {
      const result = await searchPublicCourtCase(caseSearchInput.trim(), getToken(), getUserId());
      const rows = toPublicCaseRows(result.case_number, result.assignments || []);
      setSearchCases(rows);
      setSuccess(rows.length ? `Знайдено ${rows.length} публічних записів для справи ${result.case_number}.` : `Для справи ${result.case_number} активних записів не знайдено.`);
    } catch (nextError) {
      setError(String(nextError));
    } finally {
      setSearchLoading(false);
    }
  }

  async function handleSubmit(): Promise<void> {
    setError("");
    setSuccess("");

    if (!docId.trim()) {
      setError("Оберіть документ для подачі.");
      return;
    }
    if (!courtName.trim()) {
      setError("Вкажіть назву суду.");
      return;
    }

    const selected = documents.find((item) => item.id === docId);
    if (selected && !selected.e_court_ready) {
      setError(`Документ не готовий до подачі. Блокери: ${selected.filing_blockers.join(", ")}`);
      return;
    }

    setSubmitLoading(true);
    try {
      const result = await submitToECourt(
        {
          document_id: docId,
          court_name: courtName,
          signer_method: signerMethod,
          note: note.trim() || undefined,
        },
        getToken(),
        getUserId()
      );
      setSuccess(`Подачу прийнято. Зовнішній ID: ${result.submission.external_submission_id}`);
      setDocId("");
      setNote("");
      await loadHistory();
    } catch (nextError) {
      setError(String(nextError));
    } finally {
      setSubmitLoading(false);
    }
  }

  async function handleSync(submissionId: string): Promise<void> {
    setSyncingId(submissionId);
    setError("");
    setSuccess("");
    try {
      const result = await syncECourtStatus(submissionId, getToken(), getUserId());
      setSuccess(result.synced_live ? "Статус оновлено з court.gov.ua." : "Статус перевірено у stub-режимі.");
      await loadHistory();
    } catch (nextError) {
      setError(String(nextError));
    } finally {
      setSyncingId(null);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div className="section-header">
        <div>
          <h1 className="section-title">Е-суд та мої справи</h1>
          <p className="section-subtitle">
            Робочий екран у стилі `cabinet.court.gov.ua/cases`: ваші справи, публічний пошук, подача документів і контроль статусів.
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <a href="https://cabinet.court.gov.ua/cases" target="_blank" rel="noreferrer" className="btn btn-primary">
            Відкрити кабінет
          </a>
          <a href="https://court.gov.ua/fair/" target="_blank" rel="noreferrer" className="btn btn-secondary">
            court.gov.ua/fair
          </a>
        </div>
      </div>

      {error && <div className="preflight-block"><span style={{ color: "var(--danger)" }}>⚠ {error}</span></div>}
      {success && <div className="card-elevated" style={{ padding: "12px 16px", borderLeft: "3px solid var(--success)", color: "var(--success)" }}>{success}</div>}

      <section className="card-elevated" style={{ padding: "24px", background: "linear-gradient(180deg, rgba(16,89,168,0.9), rgba(8,61,123,0.9))" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: "18px", alignItems: "flex-start", flexWrap: "wrap" }}>
          <div>
            <div style={{ fontSize: "13px", opacity: 0.8, marginBottom: "6px" }}>Мої справи</div>
            <h2 style={{ fontSize: "30px", margin: 0, color: "#fff" }}>Список судових справ та подач</h2>
            <p style={{ color: "rgba(255,255,255,0.82)", marginTop: "10px", maxWidth: "760px" }}>
              Повна двостороння синхронізація з авторизованим кабінетом `cabinet.court.gov.ua/cases` потребує окремої інтеграції. Зараз цей екран чесно поєднує доступні дані з `hearings`, публічного `fair`-пошуку та історії подач.
            </p>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(120px, 1fr))", gap: "10px" }}>
            {[
              { label: "Мої справи", value: stats.myCases },
              { label: "Засідання", value: stats.hearings },
              { label: "Подачі", value: stats.submissions },
              { label: "Готові документи", value: stats.readyDocs },
            ].map((item) => (
              <div key={item.label} style={{ padding: "14px", borderRadius: "14px", background: "rgba(255,255,255,0.12)" }}>
                <strong style={{ display: "block", color: "#fff", fontSize: "24px" }}>{item.value}</strong>
                <span style={{ color: "rgba(255,255,255,0.75)", fontSize: "12px" }}>{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="card-elevated" style={{ padding: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: "16px", alignItems: "flex-end", flexWrap: "wrap", marginBottom: "18px" }}>
          <div>
            <h2 style={{ fontSize: "22px", marginBottom: "6px" }}>Пошук справи за номером</h2>
            <p style={{ color: "var(--text-secondary)" }}>Підтягує публічні записи з `court.gov.ua/fair` і додає їх у список справ на цьому екрані.</p>
          </div>
          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            <input className="form-input" style={{ minWidth: "280px" }} placeholder="Наприклад: 756/20811/25" value={caseSearchInput} onChange={(event) => setCaseSearchInput(event.target.value)} />
            <button type="button" className="btn btn-secondary" onClick={() => void handlePublicSearch()} disabled={searchLoading || !caseSearchInput.trim()}>
              {searchLoading ? "Пошук..." : "Знайти"}
            </button>
          </div>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["Номер справи", "Суд", "Найближча подія", "Суддя", "Статус", "Джерело"].map((label) => (
                  <th key={label} style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid var(--border)", color: "var(--text-muted)", fontSize: "11px", textTransform: "uppercase" }}>
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pageLoading ? (
                <tr>
                  <td colSpan={6} style={{ padding: "28px 12px", color: "var(--text-muted)", textAlign: "center" }}>Завантаження справ...</td>
                </tr>
              ) : mergedCases.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ padding: "28px 12px", color: "var(--text-muted)", textAlign: "center" }}>Справи поки не знайдено. Використайте пошук або синхронізацію засідань.</td>
                </tr>
              ) : (
                mergedCases.map((item) => (
                  <tr key={item.id}>
                    <td style={{ padding: "14px 12px", borderBottom: "1px solid var(--border)" }}>{item.case_number}</td>
                    <td style={{ padding: "14px 12px", borderBottom: "1px solid var(--border)", color: "var(--text-secondary)" }}>{item.court_name}</td>
                    <td style={{ padding: "14px 12px", borderBottom: "1px solid var(--border)", color: "var(--text-secondary)" }}>{formatDateTime(item.next_hearing)}</td>
                    <td style={{ padding: "14px 12px", borderBottom: "1px solid var(--border)", color: "var(--text-secondary)" }}>{item.judge || "—"}</td>
                    <td style={{ padding: "14px 12px", borderBottom: "1px solid var(--border)" }}>{badgeForStatus(item.status)}</td>
                    <td style={{ padding: "14px 12px", borderBottom: "1px solid var(--border)", color: "var(--text-muted)", fontSize: "12px" }}>{item.source}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "1.1fr 0.9fr", gap: "20px" }}>
        <div className="card-elevated" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>Подача документів до суду</h2>
          <p style={{ color: "var(--text-secondary)", marginBottom: "18px" }}>Подача працює через наявний бекендовий модуль `E-суд`; тут залишився реальний робочий сценарій відправки й sync-статусів.</p>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "14px" }}>
            <div>
              <label htmlFor="e-court-doc-select" className="form-label">Документ</label>
              <select id="e-court-doc-select" className="form-input" value={docId} onChange={(event) => setDocId(event.target.value)}>
                <option value="">Оберіть документ</option>
                {documents.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.document_type} · {item.e_court_ready ? "готовий" : "є блокери"}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="e-court-signer-method" className="form-label">Метод підпису</label>
              <select id="e-court-signer-method" className="form-input" value={signerMethod} onChange={(event) => setSignerMethod(event.target.value)}>
                {SIGNER_METHODS.map((item) => (
                  <option key={item.value} value={item.value}>{item.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="e-court-court-name" className="form-label">Суд</label>
              <input id="e-court-court-name" className="form-input" value={courtName} onChange={(event) => { setCourtName(event.target.value); setCourtSearch(event.target.value); }} placeholder="Почніть вводити назву суду" />
              {courtSearch.trim() && filteredCourts.length > 0 && (
                <div className="card-elevated" style={{ marginTop: "8px", padding: "8px" }}>
                  {filteredCourts.map((item) => (
                    <button
                      key={item}
                      type="button"
                      onClick={() => { setCourtName(item); setCourtSearch(item); }}
                      style={{ display: "block", width: "100%", textAlign: "left", padding: "8px 10px", border: "none", background: "transparent", color: "var(--text-secondary)", cursor: "pointer" }}
                    >
                      {item}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div>
              <label htmlFor="e-court-note" className="form-label">Примітка</label>
              <textarea id="e-court-note" className="form-input" rows={3} value={note} onChange={(event) => setNote(event.target.value)} placeholder="Наприклад: термінова подача або технічна примітка" />
            </div>
          </div>

          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "18px" }}>
            <button type="button" className="btn btn-primary" onClick={() => void handleSubmit()} disabled={submitLoading || !docId || !courtName}>
              {submitLoading ? "Подача..." : "Подати до суду"}
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => void loadHistory()} disabled={historyLoading}>
              {historyLoading ? "Оновлення..." : "Оновити історію"}
            </button>
          </div>
        </div>

        <div className="card-elevated" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>Що реально підключено</h2>
          <div style={{ display: "grid", gap: "12px" }}>
            <div style={{ padding: "14px", borderRadius: "14px", background: "rgba(255,255,255,0.03)" }}>
              <strong style={{ display: "block", marginBottom: "6px" }}>cabinet.court.gov.ua/cases</strong>
              <span style={{ color: "var(--text-secondary)", fontSize: "14px" }}>Використано як UX-референс для секції `Мої справи`. Повної авторизованої інтеграції кабінету в бекенді ще немає.</span>
            </div>
            <div style={{ padding: "14px", borderRadius: "14px", background: "rgba(255,255,255,0.03)" }}>
              <strong style={{ display: "block", marginBottom: "6px" }}>court.gov.ua/fair</strong>
              <span style={{ color: "var(--text-secondary)", fontSize: "14px" }}>Є реальний публічний пошук за номером справи через `/api/e-court/public-search`.</span>
            </div>
            <div style={{ padding: "14px", borderRadius: "14px", background: "rgba(255,255,255,0.03)" }}>
              <strong style={{ display: "block", marginBottom: "6px" }}>Подача та sync статусу</strong>
              <span style={{ color: "var(--text-secondary)", fontSize: "14px" }}>Залишено поточний маршрут подачі, історію та poll статуса із бекенду `E-суд`.</span>
            </div>
            <div style={{ padding: "14px", borderRadius: "14px", background: "rgba(255,255,255,0.03)" }}>
              <strong style={{ display: "block", marginBottom: "6px" }}>Джерело довідника судів</strong>
              <span style={{ color: "var(--text-secondary)", fontSize: "14px" }}>{courtsSource === "court_gov_ua" ? "Live court.gov.ua API" : "Fallback-довідник судів у локальному режимі"}.</span>
            </div>
          </div>
        </div>
      </section>

      <section className="card-elevated" style={{ padding: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: "16px", alignItems: "center", flexWrap: "wrap", marginBottom: "18px" }}>
          <div>
            <h2 style={{ fontSize: "22px", marginBottom: "6px" }}>Історія подач</h2>
            <p style={{ color: "var(--text-secondary)" }}>Жива таблиця відправлених документів з можливістю повторного sync статусу.</p>
          </div>
          <select className="form-input" style={{ width: "auto", minWidth: "180px" }} value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="">Усі статуси</option>
            {Object.entries(STATUS_META).map(([key, value]) => (
              <option key={key} value={key}>{value.label}</option>
            ))}
          </select>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["Зовнішній ID", "Суд", "Документ", "Статус", "Дата подачі", "Дія"].map((label) => (
                  <th key={label} style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid var(--border)", color: "var(--text-muted)", fontSize: "11px", textTransform: "uppercase" }}>
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {historyLoading ? (
                <tr>
                  <td colSpan={6} style={{ padding: "28px 12px", textAlign: "center", color: "var(--text-muted)" }}>Завантаження історії...</td>
                </tr>
              ) : !history?.items?.length ? (
                <tr>
                  <td colSpan={6} style={{ padding: "28px 12px", textAlign: "center", color: "var(--text-muted)" }}>Історія подач поки порожня.</td>
                </tr>
              ) : (
                history.items.map((row: ECourtSubmissionItem) => (
                  <tr key={row.id}>
                    <td style={{ padding: "14px 12px", borderBottom: "1px solid var(--border)" }}>
                      <code style={{ color: "var(--gold-400)", fontSize: "12px" }}>{row.external_submission_id}</code>
                    </td>
                    <td style={{ padding: "14px 12px", borderBottom: "1px solid var(--border)", color: "var(--text-secondary)" }}>{row.court_name}</td>
                    <td style={{ padding: "14px 12px", borderBottom: "1px solid var(--border)", color: "var(--text-secondary)" }}>{row.document_id ? row.document_id.slice(0, 12) + "…" : "—"}</td>
                    <td style={{ padding: "14px 12px", borderBottom: "1px solid var(--border)" }}>{badgeForStatus(row.status)}</td>
                    <td style={{ padding: "14px 12px", borderBottom: "1px solid var(--border)", color: "var(--text-secondary)" }}>{formatDate(row.submitted_at)}</td>
                    <td style={{ padding: "14px 12px", borderBottom: "1px solid var(--border)" }}>
                      <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                        {row.tracking_url && <a href={row.tracking_url} target="_blank" rel="noreferrer" style={{ color: "var(--accent)", textDecoration: "none", fontSize: "13px" }}>Відстежити</a>}
                        <button type="button" className="btn btn-secondary" style={{ padding: "8px 12px", fontSize: "12px" }} onClick={() => void handleSync(row.id)} disabled={syncingId === row.id}>
                          {syncingId === row.id ? "Sync..." : "Оновити статус"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
