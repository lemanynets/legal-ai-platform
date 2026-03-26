"use client";

import { useEffect, useMemo, useState } from "react";

import { getToken, getUserId } from "@/lib/auth";
import {
  createCase,
  createDeadline,
  getCases,
  getCourtCase,
  getDeadlines,
  getOpendatabotUsage,
  importCaseLaw,
  type CourtCase,
  type CourtCaseDecision,
  type CourtCaseSide,
  type OpendatabotUsage,
} from "@/lib/api";

type StageDetails = {
  court_code?: number;
  court_name?: string;
  judge?: string;
  consideration?: string;
  description?: string;
  decisions?: CourtCaseDecision[];
};

const ROLE_LABELS: Record<string, string> = {
  plaintiff: "Позивач",
  defendant: "Відповідач",
  third_party: "Третя особа",
  appeal_party: "Скаржник",
  cassation_party: "Касатор",
  "позивач": "Позивач",
  "відповідач": "Відповідач",
  "третя особа": "Третя особа",
};

const ROLE_COLORS: Record<string, string> = {
  plaintiff: "#4ade80",
  defendant: "#f87171",
  third_party: "#facc15",
  appeal_party: "#60a5fa",
  cassation_party: "#c084fc",
  "позивач": "#4ade80",
  "відповідач": "#f87171",
  "третя особа": "#facc15",
};

const STAGE_META: Array<{ key: string; title: string; tone: string }> = [
  { key: "first", title: "Перша інстанція", tone: "#4ade80" },
  { key: "appeal", title: "Апеляція", tone: "#60a5fa" },
  { key: "cassation", title: "Касація", tone: "#c084fc" },
];

function getRoleLabel(role: string): string {
  return ROLE_LABELS[role.toLowerCase()] || role;
}

function getRoleColor(role: string): string {
  return ROLE_COLORS[role.toLowerCase()] || "#94a3b8";
}

function isIsoDate(value: string | null | undefined): value is string {
  return Boolean(value && /^\d{4}-\d{2}-\d{2}$/.test(value));
}

function normalizeDecisionDate(value: string | null | undefined): string | undefined {
  if (!value) return undefined;
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  const match = trimmed.match(/\d{4}-\d{2}-\d{2}/);
  return match?.[0] || undefined;
}

function buildCaseTitle(caseData: CourtCase): string {
  const suffix = caseData.subject || caseData.court || "Судова справа";
  return `Справа №${caseData.number} · ${suffix}`.slice(0, 255);
}

function buildCaseDescription(caseData: CourtCase): string {
  return [
    caseData.court ? `Суд: ${caseData.court}` : "",
    caseData.subject ? `Предмет: ${caseData.subject}` : "",
    caseData.last_status ? `Статус: ${caseData.last_status}` : "",
    caseData.next_hearing_date ? `Наступне засідання: ${caseData.next_hearing_date}` : "",
  ]
    .filter(Boolean)
    .join("\n");
}

function buildDecisionId(
  current: CourtCase,
  decision: CourtCaseDecision,
  index: number,
  stageKey?: string,
): string {
  const explicit = decision.id?.trim();
  if (explicit) return explicit;

  const url = decision.url?.trim();
  if (url) {
    const tail = url.split("/").filter(Boolean).pop();
    if (tail) return `odb-${tail}`;
  }

  const datePart = normalizeDecisionDate(decision.date) || "undated";
  const typePart = (decision.type || "decision").trim().toLowerCase().replace(/\s+/g, "-");
  return `odb-${current.number}-${stageKey || "general"}-${datePart}-${typePart}-${index + 1}`;
}

function buildCaseLawImportRecords(current: CourtCase) {
  const records: Array<{
    source?: string;
    decision_id: string;
    court_name?: string;
    court_type?: string;
    decision_date?: string;
    case_number?: string;
    subject_categories?: string[];
    legal_positions?: Record<string, unknown>;
    summary?: string;
  }> = [];
  const seen = new Set<string>();

  const pushRecord = (
    decision: CourtCaseDecision,
    index: number,
    options?: { stageKey?: string; courtName?: string; courtType?: string },
  ) => {
    const decisionId = buildDecisionId(current, decision, index, options?.stageKey);
    if (seen.has(decisionId)) return;
    seen.add(decisionId);

    records.push({
      source: "opendatabot",
      decision_id: decisionId,
      court_name: options?.courtName || current.court || undefined,
      court_type: options?.courtType || undefined,
      decision_date: normalizeDecisionDate(decision.date),
      case_number: current.number,
      subject_categories: [current.proceeding_type, current.subject].filter(Boolean),
      legal_positions: {
        opendatabot_url: decision.url || null,
        document_type: decision.type || null,
        stage: options?.stageKey || null,
      },
      summary: decision.summary || undefined,
    });
  };

  current.decisions?.forEach((decision, index) => pushRecord(decision, index));

  if (current.stages && typeof current.stages === "object") {
    Object.entries(current.stages).forEach(([stageKey, stageValue]) => {
      if (!stageValue || typeof stageValue !== "object") return;
      const stage = stageValue as StageDetails;
      const courtType =
        stageKey === "first" ? "first" : stageKey === "appeal" ? "appeal" : stageKey === "cassation" ? "cassation" : undefined;
      stage.decisions?.forEach((decision, index) =>
        pushRecord(decision, index, {
          stageKey,
          courtName: stage.court_name || current.court || undefined,
          courtType,
        }),
      );
    });
  }

  return records;
}

function InfoRow({ label, value }: { label: string; value?: string | number | null }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "180px 1fr",
        gap: "12px",
        padding: "10px 0",
        borderBottom: "1px solid rgba(255,255,255,0.05)",
      }}
    >
      <span
        style={{
          fontSize: "12px",
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
        }}
      >
        {label}
      </span>
      <span style={{ color: "var(--text-primary)", fontSize: "14px" }}>
        {typeof value === "number" ? value.toLocaleString("uk-UA") : value}
      </span>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const lower = status.toLowerCase();
  let color = "#94a3b8";
  let background = "rgba(148,163,184,0.12)";

  if (lower.includes("признач") || lower.includes("розгляд") || lower.includes("слух")) {
    color = "#4ade80";
    background = "rgba(74,222,128,0.12)";
  } else if (lower.includes("закрит") || lower.includes("скас") || lower.includes("заверш")) {
    color = "#f87171";
    background = "rgba(248,113,113,0.12)";
  } else if (lower.includes("зупин") || lower.includes("відклад")) {
    color = "#facc15";
    background = "rgba(250,204,21,0.12)";
  }

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "8px",
        padding: "6px 12px",
        borderRadius: "999px",
        background,
        color,
        fontSize: "13px",
        fontWeight: 700,
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: color, display: "inline-block" }} />
      {status}
    </span>
  );
}

function DecisionCard({ decision, index }: { decision: CourtCaseDecision; index: number }) {
  return (
    <div
      style={{
        padding: "16px",
        background: "rgba(255,255,255,0.03)",
        borderRadius: "14px",
        border: "1px solid rgba(255,255,255,0.07)",
        display: "flex",
        gap: "16px",
        alignItems: "flex-start",
      }}
    >
      <div
        style={{
          width: "32px",
          height: "32px",
          borderRadius: "50%",
          background: "rgba(212,168,67,0.15)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
          fontSize: "14px",
          fontWeight: 700,
          color: "var(--gold-400)",
        }}
      >
        {index + 1}
      </div>

      <div style={{ flex: 1 }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", alignItems: "center", marginBottom: "8px" }}>
          {decision.type ? (
            <span
              style={{
                fontSize: "11px",
                padding: "2px 8px",
                background: "rgba(212,168,67,0.1)",
                color: "var(--gold-400)",
                borderRadius: "6px",
              }}
            >
              {decision.type}
            </span>
          ) : null}
          {decision.date ? <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Дата: {decision.date}</span> : null}
          {decision.id ? <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>ID: {decision.id}</span> : null}
        </div>

        {decision.summary ? (
          <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: decision.url ? "10px" : 0 }}>
            {decision.summary}
          </p>
        ) : null}

        {decision.url ? (
          <a
            href={decision.url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary btn-sm"
            style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "12px" }}
          >
            Відкрити рішення
          </a>
        ) : null}
      </div>
    </div>
  );
}

function StageCard({
  title,
  tone,
  stage,
}: {
  title: string;
  tone: string;
  stage: StageDetails;
}) {
  return (
    <div
      className="card-elevated"
      style={{
        padding: "22px",
        border: `1px solid ${tone}33`,
        background: `linear-gradient(180deg, ${tone}12 0%, rgba(255,255,255,0.02) 100%)`,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap", marginBottom: "14px" }}>
        <div>
          <div style={{ fontSize: "12px", color: tone, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "4px" }}>
            Stage
          </div>
          <h3 style={{ fontSize: "18px", fontWeight: 800, color: "#fff" }}>{title}</h3>
        </div>
        {stage.consideration ? (
          <span
            style={{
              padding: "6px 10px",
              borderRadius: "999px",
              background: `${tone}22`,
              color: tone,
              fontSize: "12px",
              fontWeight: 700,
              alignSelf: "flex-start",
            }}
          >
            {stage.consideration}
          </span>
        ) : null}
      </div>

      <InfoRow label="Суд" value={stage.court_name || null} />
      <InfoRow label="Суддя" value={stage.judge || null} />
      <InfoRow label="Опис" value={stage.description || null} />

      {stage.decisions?.length ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "16px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Рішення інстанції
          </div>
          {stage.decisions.map((decision, index) => (
            <DecisionCard key={`${title}-${decision.id || decision.url || index}`} decision={decision} index={index} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function UsageCard({ usage }: { usage: OpendatabotUsage | null }) {
  if (!usage) return null;
  const ratio = usage.limit > 0 ? Math.min(usage.used / usage.limit, 1) : 0;

  return (
    <div className="card-elevated" style={{ padding: "20px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: "16px", flexWrap: "wrap", alignItems: "center" }}>
        <div>
          <div style={{ fontSize: "12px", color: "var(--gold-400)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            OpenDataBot Usage
          </div>
          <div style={{ fontSize: "20px", fontWeight: 800, color: "#fff", marginTop: "4px" }}>
            {usage.used} / {usage.limit}
          </div>
          <div style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "6px" }}>
            Залишилось: {usage.remaining}
            {usage.expires_at ? ` • діє до ${usage.expires_at}` : ""}
          </div>
        </div>
        <div style={{ minWidth: "220px", flex: 1 }}>
          <div style={{ height: "10px", borderRadius: "999px", background: "rgba(255,255,255,0.08)", overflow: "hidden" }}>
            <div
              style={{
                width: `${ratio * 100}%`,
                height: "100%",
                background: "linear-gradient(90deg, var(--gold-500), var(--gold-300))",
              }}
            />
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "8px" }}>{usage.api_url}</div>
        </div>
      </div>
    </div>
  );
}

export default function CourtCasesPage() {
  const [caseNumber, setCaseNumber] = useState("");
  const [judgmentCode, setJudgmentCode] = useState("");
  const [requestConfirmed, setRequestConfirmed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [usageLoading, setUsageLoading] = useState(true);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [caseData, setCaseData] = useState<CourtCase | null>(null);
  const [usage, setUsage] = useState<OpendatabotUsage | null>(null);

  async function refreshUsage() {
    setUsageLoading(true);
    try {
      const payload = await getOpendatabotUsage(getToken(), getUserId());
      setUsage(payload);
    } catch {
      // Keep the page usable even if usage tracking is unavailable.
    } finally {
      setUsageLoading(false);
    }
  }

  useEffect(() => {
    void refreshUsage();
  }, []);

  async function ensureCaseSaved(current: CourtCase) {
    const token = getToken();
    const userId = getUserId();
    const existingCases = await getCases(token, userId);
    const match = existingCases.find((item) => item.case_number?.trim() === current.number.trim());
    if (match) return match;

    return createCase(
      {
        title: buildCaseTitle(current),
        description: buildCaseDescription(current),
        case_number: current.number,
      },
      token,
      userId,
    );
  }

  async function handleSaveCase() {
    if (!caseData) return;
    setActionLoading(true);
    setError("");
    setInfo("");

    try {
      const saved = await ensureCaseSaved(caseData);
      const records = buildCaseLawImportRecords(caseData);
      let importedTotal = 0;
      let importWarning = "";

      if (records.length > 0) {
        try {
          const imported = await importCaseLaw(records, getToken(), getUserId());
          importedTotal = imported.total;
        } catch (importErr: unknown) {
          const importMessage = importErr instanceof Error ? importErr.message : String(importErr);
          importWarning = importMessage || "Не вдалося імпортувати рішення.";
        }
      }

      setInfo(
        importedTotal > 0
          ? `Справу №${saved.case_number || caseData.number} збережено в "Мої справи". Імпортовано рішень у базу: ${importedTotal}.`
          : importWarning
            ? `Справу №${saved.case_number || caseData.number} збережено в "Мої справи", але імпорт рішень не завершився: ${importWarning}`
            : `Справу №${saved.case_number || caseData.number} збережено в "Мої справи". Але рішень для імпорту не знайдено.`,
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg || "Не вдалося зберегти справу та імпортувати рішення.");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleAddToCalendar() {
    if (!caseData) return;

    const suggestedDate = isIsoDate(caseData.next_hearing_date) ? caseData.next_hearing_date : "";
    const manualDate = !suggestedDate
      ? window.prompt("OpenDataBot не повернув дату засідання. Вкажи дату у форматі YYYY-MM-DD.", "")
      : suggestedDate;

    const targetDate = typeof manualDate === "string" ? manualDate.trim() : "";
    if (!isIsoDate(targetDate)) {
      setError("Щоб додати подію в календар, потрібна дата у форматі YYYY-MM-DD.");
      return;
    }

    setActionLoading(true);
    setError("");
    setInfo("");

    try {
      const savedCase = await ensureCaseSaved(caseData);
      const token = getToken();
      const userId = getUserId();
      const title = isIsoDate(caseData.next_hearing_date)
        ? `Засідання у справі №${caseData.number}`
        : `Контроль справи №${caseData.number}`;

      const existing = await getDeadlines(token, userId);
      const duplicate = existing.items.find((item) => item.title === title && item.end_date === targetDate);

      if (!duplicate) {
        await createDeadline(
          {
            title,
            deadline_type: isIsoDate(caseData.next_hearing_date) ? "hearing" : "other",
            start_date: targetDate,
            end_date: targetDate,
            notes: [savedCase.title, caseData.court, caseData.subject].filter(Boolean).join(" | "),
          },
          token,
          userId,
        );
      }

      setInfo(
        duplicate
          ? `Подія для справи №${caseData.number} вже є в календарі на ${targetDate}.`
          : `Подію для справи №${caseData.number} додано в календар на ${targetDate}.`,
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg || "Не вдалося додати подію в календар.");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleSearch(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = caseNumber.trim();
    if (!trimmed) {
      setError("Введи номер справи.");
      return;
    }
    if (!requestConfirmed) {
      setError("Підтвердь разовий запит до OpenDataBot перед пошуком.");
      return;
    }

    setLoading(true);
    setError("");
    setInfo("");
    setCaseData(null);

    try {
      const data = await getCourtCase(
        {
          number: trimmed,
          judgmentCode: judgmentCode ? Number(judgmentCode) : null,
        },
        getToken(),
        getUserId(),
      );
      setCaseData(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg || "Не вдалося отримати дані про справу.");
    } finally {
      setLoading(false);
      setRequestConfirmed(false);
      void refreshUsage();
    }
  }

  const stages = useMemo(() => {
    if (!caseData?.stages || typeof caseData.stages !== "object") return [];
    return STAGE_META.map((meta) => {
      const stage = (caseData.stages?.[meta.key] as StageDetails | undefined) || null;
      return stage ? { ...meta, stage } : null;
    }).filter(Boolean) as Array<{ key: string; title: string; tone: string; stage: StageDetails }>;
  }, [caseData]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div className="section-header">
        <div>
          <h1 className="section-title">Реєстр судових справ</h1>
          <p className="section-subtitle">
            Пошук справ через OpenDataBot з окремими блоками по інстанціях, рішеннях і поточному статусу.
          </p>
        </div>
        <span
          style={{
            fontSize: "11px",
            color: "var(--text-muted)",
            padding: "4px 10px",
            background: "rgba(255,255,255,0.05)",
            borderRadius: "8px",
          }}
        >
          OpenDataBot v2
        </span>
      </div>

      {usageLoading ? (
        <div className="card-elevated" style={{ padding: "20px", color: "var(--text-muted)" }}>
          Оновлюю usage OpenDataBot...
        </div>
      ) : (
        <UsageCard usage={usage} />
      )}

      <div className="card-elevated" style={{ padding: "28px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "18px", color: "var(--text-primary)" }}>
          Пошук справи за номером
        </h2>

        <form onSubmit={handleSearch} style={{ display: "flex", gap: "12px", alignItems: "flex-end", flexWrap: "wrap" }}>
          <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
            <label className="form-label" htmlFor="caseNumber">
              Номер справи
            </label>
            <input
              id="caseNumber"
              className="form-input"
              type="text"
              value={caseNumber}
              onChange={(e) => setCaseNumber(e.target.value)}
              placeholder="Наприклад: 904/6017/17"
              disabled={loading}
              style={{ fontSize: "15px" }}
            />
            <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "6px" }}>
              Якщо справа неунікальна, вкажи вид судочинства в полі праворуч.
            </p>
          </div>

          <div className="form-group" style={{ minWidth: "220px", marginBottom: 0 }}>
            <label className="form-label" htmlFor="judgmentCode">
              Вид судочинства
            </label>
            <select
              id="judgmentCode"
              className="form-input"
              value={judgmentCode}
              onChange={(e) => setJudgmentCode(e.target.value)}
              disabled={loading}
            >
              <option value="">Автовизначення</option>
              <option value="1">1. Цивільне</option>
              <option value="2">2. Кримінальне</option>
              <option value="3">3. Господарське</option>
              <option value="4">4. Адміністративне</option>
              <option value="5">5. Адмінправопорушення</option>
            </select>
          </div>

          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              minHeight: "44px",
              padding: "0 12px",
              borderRadius: "12px",
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.08)",
              color: "var(--text-secondary)",
              fontSize: "13px",
            }}
          >
            <input
              type="checkbox"
              checked={requestConfirmed}
              onChange={(e) => setRequestConfirmed(e.target.checked)}
              disabled={loading}
            />
            Погоджую разовий запит до OpenDataBot для цієї справи
          </label>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading || !requestConfirmed}
            style={{ whiteSpace: "nowrap", minWidth: "150px", height: "44px" }}
          >
            {loading ? "Пошук..." : "Знайти справу"}
          </button>
        </form>

        <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "14px" }}>
          Зовнішній запит до OpenDataBot виконується лише після твого підтвердження. При збереженні справи рішення теж імпортуються
          в локальну базу практики, щоб їх можна було використовувати в аналізі та генерації.
        </p>
      </div>

      {error ? (
        <div className="alert alert-error">
          <strong>Помилка:</strong> {error}
        </div>
      ) : null}

      {info ? (
        <div
          className="card-elevated"
          style={{
            padding: "14px 18px",
            border: "1px solid rgba(74,222,128,0.2)",
            background: "rgba(74,222,128,0.08)",
            color: "#bbf7d0",
          }}
        >
          {info}
        </div>
      ) : null}

      {caseData ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div
            className="card-elevated"
            style={{
              padding: "24px",
              border: "1px solid rgba(212,168,67,0.2)",
              background: "linear-gradient(135deg, rgba(212,168,67,0.05) 0%, rgba(0,0,0,0) 100%)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "16px", flexWrap: "wrap" }}>
              <div>
                <div style={{ fontSize: "12px", color: "var(--gold-400)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "6px" }}>
                  Судова справа
                </div>
                <h2 style={{ fontSize: "22px", fontWeight: 800, color: "#fff", marginBottom: "8px" }}>№ {caseData.number}</h2>
                {caseData.last_status ? <StatusBadge status={caseData.last_status} /> : null}
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "6px", textAlign: "right" }}>
                {caseData.start_date ? (
                  <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                    Початок: <strong style={{ color: "var(--text-secondary)" }}>{caseData.start_date}</strong>
                  </div>
                ) : null}
                {caseData.next_hearing_date ? (
                  <div style={{ fontSize: "12px", color: "#4ade80" }}>
                    Наступне засідання: <strong>{caseData.next_hearing_date}</strong>
                  </div>
                ) : null}

                <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", flexWrap: "wrap", marginTop: "8px" }}>
                  <button type="button" className="btn btn-secondary btn-sm" onClick={handleSaveCase} disabled={actionLoading}>
                    {actionLoading ? "Збереження..." : "Зберегти в мої справи"}
                  </button>
                  <button type="button" className="btn btn-primary btn-sm" onClick={handleAddToCalendar} disabled={actionLoading}>
                    {actionLoading ? "Обробка..." : "Додати в календар"}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
            <div className="card-elevated" style={{ padding: "24px" }}>
              <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--gold-400)", marginBottom: "16px" }}>Загальна інформація</h3>
              <InfoRow label="Суд" value={caseData.court} />
              <InfoRow label="Суддя" value={caseData.judge} />
              <InfoRow label="Тип" value={caseData.proceeding_type} />
              <InfoRow label="Предмет спору" value={caseData.subject} />
              <InfoRow label="Дата справи" value={caseData.date} />
              <InfoRow label="Кількість засідань" value={caseData.schedule_count ?? null} />
              <InfoRow label="Останній документ" value={caseData.last_document_date} />
              {caseData.claim_price != null ? (
                <InfoRow
                  label="Ціна позову"
                  value={typeof caseData.claim_price === "number" ? `${caseData.claim_price.toLocaleString("uk-UA")} грн` : String(caseData.claim_price)}
                />
              ) : null}
            </div>

            <div className="card-elevated" style={{ padding: "24px" }}>
              <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--gold-400)", marginBottom: "16px" }}>Статус і технічні поля</h3>
              <InfoRow label="Judgment code" value={caseData.judgment_code ?? null} />
              <InfoRow label="Live" value={caseData.live ?? null} />
              <InfoRow label="Результат інстанції" value={caseData.instance_result} />
              {Object.keys(caseData.instance_info || {}).length ? (
                Object.entries(caseData.instance_info).map(([key, value]) =>
                  typeof value === "string" || typeof value === "number" ? <InfoRow key={key} label={key} value={String(value)} /> : null,
                )
              ) : (
                <p style={{ color: "var(--text-muted)", fontSize: "13px" }}>Окремих даних про instance_info немає.</p>
              )}
            </div>
          </div>

          {stages.length ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ fontSize: "15px", fontWeight: 800, color: "#fff" }}>Інстанції</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
                {stages.map((item) => (
                  <StageCard key={item.key} title={item.title} tone={item.tone} stage={item.stage} />
                ))}
              </div>
            </div>
          ) : null}

          {caseData.sides?.length ? (
            <div className="card-elevated" style={{ padding: "24px" }}>
              <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--gold-400)", marginBottom: "18px" }}>Сторони справи</h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "14px" }}>
                {caseData.sides.map((side: CourtCaseSide, idx: number) => {
                  const roleColor = getRoleColor(side.role);
                  return (
                    <div
                      key={`${side.role}-${side.name}-${idx}`}
                      style={{
                        padding: "16px",
                        background: "rgba(255,255,255,0.03)",
                        borderRadius: "12px",
                        border: `1px solid ${roleColor}30`,
                      }}
                    >
                      <div style={{ fontSize: "11px", color: roleColor, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "8px", fontWeight: 700 }}>
                        {getRoleLabel(side.role)}
                      </div>
                      <div style={{ fontSize: "14px", color: "#fff", fontWeight: 600, marginBottom: side.code ? "4px" : 0 }}>
                        {side.name || "—"}
                      </div>
                      {side.code ? <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>ЄДРПОУ: {side.code}</div> : null}
                    </div>
                  );
                })}
              </div>
            </div>
          ) : null}

          {caseData.decisions?.length ? (
            <div className="card-elevated" style={{ padding: "24px" }}>
              <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--gold-400)", marginBottom: "18px" }}>
                Судові рішення ({caseData.decisions.length})
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {caseData.decisions.map((decision, index) => (
                  <DecisionCard key={`${decision.id || decision.url || index}`} decision={decision} index={index} />
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ) : !loading && !error ? (
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
          <div style={{ fontSize: "48px", marginBottom: "16px" }}>⚖</div>
          <div style={{ fontSize: "16px", fontWeight: 600, marginBottom: "8px", color: "var(--text-secondary)" }}>
            Введи номер справи для пошуку
          </div>
          <div style={{ fontSize: "13px" }}>
            Платформа покаже сторони, інстанції, рішення, статуси й найближчі засідання.
          </div>
        </div>
      ) : null}
    </div>
  );
}
