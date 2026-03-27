"use client";

import { FormEvent, useEffect, useState } from "react";

import { getToken, getUserId } from "@/lib/auth";
import {
  type CaseLawDigestHistoryResponse,
  type CaseLawDigestResponse,
  type CaseLawSearchItem,
  type CaseLawSearchResponse,
  type CaseLawSyncStatusResponse,
  generateCaseLawDigest,
  getCaseLawDigest,
  getCaseLawDigestDetail,
  getCaseLawDigestHistory,
  getCaseLawSyncStatus,
  getCurrentSubscription,
  importCaseLaw,
  searchCaseLaw,
  syncCaseLaw,
  getUserPreferences,
  updateUserPreferences,
} from "@/lib/api";

const PROMPT_STORAGE_KEY = "legal_ai_prompt_context";
const CASE_LAW_SETTINGS_KEY = "legal_ai_case_law_settings_v1";
const CASE_LAW_SEED_KEY = "legal_ai_case_law_seed_v1";

const PLAN_RANK: Record<string, number> = {
  FREE: 0,
  START: 1,
  PRO: 2,
  PRO_PLUS: 3,
  TEAM: 4,
};

const COURT_TYPES = [
  { value: "", label: "Усі типи" },
  { value: "civil", label: "Цивільні" },
  { value: "commercial", label: "Господарські" },
  { value: "admin", label: "Адміністративні" },
  { value: "criminal", label: "Кримінальні" },
];

const HERO_CHALLENGES = [
  "Надлишок інформації: тисячі рішень, які фізично неможливо переглянути вручну.",
  "Рутинні операції: пошук, порівняння і підготовка витягів забирають години.",
  "Неочевидні патерни: важко швидко побачити релевантні аргументи зі схожих справ.",
];

const HERO_BENEFITS = [
  "Миттєві інсайти про зміну практики і ключові висновки для вашої справи.",
  "AI-дайджести, які перетворюють десятки рішень на готові prompt-фрагменти.",
  "Контекст для генерації документів без ручного копіювання витягів і цитат.",
  "PRO+ операційний контур для sync, імпорту та оновлення бази рішень.",
];

function getPlanRank(plan: string | null | undefined): number {
  return PLAN_RANK[(plan || "").toUpperCase()] ?? -1;
}

function formatPlanLabel(plan: string): string {
  if (plan === "PRO_PLUS") return "PRO+";
  return plan;
}

function formatError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function appendPromptContext(chunk: string): void {
  try {
    const previous = localStorage.getItem(PROMPT_STORAGE_KEY);
    localStorage.setItem(PROMPT_STORAGE_KEY, previous ? `${previous}\n\n${chunk}` : chunk);
  } catch {
    // no-op
  }
}

function parseImportRecords(raw: string) {
  const parsed = JSON.parse(raw) as unknown;
  if (Array.isArray(parsed)) {
    return parsed;
  }
  if (parsed && typeof parsed === "object" && Array.isArray((parsed as { records?: unknown[] }).records)) {
    return (parsed as { records: unknown[] }).records;
  }
  throw new Error("Очікується JSON-масив записів або об'єкт з полем records.");
}

export default function CaseLawPage() {
  const [query, setQuery] = useState("");
  const [courtType, setCourtType] = useState("");
  const [onlySupreme, setOnlySupreme] = useState(true);
  const [source, setSource] = useState("");
  const [tags, setTags] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [freshDays, setFreshDays] = useState("");
  const [sortBy, setSortBy] = useState<keyof CaseLawSearchItem>("decision_date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});

  const [digestDays, setDigestDays] = useState("7");
  const [digestLimit, setDigestLimit] = useState("10");
  const [digestOnlySupreme, setDigestOnlySupreme] = useState(true);
  const [digestTitle, setDigestTitle] = useState("");

  const [syncQuery, setSyncQuery] = useState("");
  const [syncLimit, setSyncLimit] = useState("50");
  const [syncSources, setSyncSources] = useState("opendatabot,json_feed");
  const [syncAllowSeedFallback, setSyncAllowSeedFallback] = useState(true);
  const [importPayload, setImportPayload] = useState(`[
  {
    "source": "manual",
    "decision_id": "demo-001",
    "court_name": "Верховний Суд",
    "court_type": "civil",
    "decision_date": "2026-03-01",
    "case_number": "910/100/26",
    "subject_categories": ["договір", "стягнення"],
    "summary": "Демонстраційний запис для швидкого імпорту."
  }
]`);

  const [searchResult, setSearchResult] = useState<CaseLawSearchResponse | null>(null);
  const [digestResult, setDigestResult] = useState<CaseLawDigestResponse | null>(null);
  const [digestHistory, setDigestHistory] = useState<CaseLawDigestHistoryResponse | null>(null);
  const [syncStatus, setSyncStatus] = useState<CaseLawSyncStatusResponse | null>(null);

  const [loadingSearch, setLoadingSearch] = useState(false);
  const [loadingDigest, setLoadingDigest] = useState(false);
  const [loadingDigestHistory, setLoadingDigestHistory] = useState(false);
  const [loadingSync, setLoadingSync] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [loadingImport, setLoadingImport] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [currentPlan, setCurrentPlan] = useState<string | null>(null);
  const [currentStatus, setCurrentStatus] = useState<string | null>(null);
  const [entitlementsLoaded, setEntitlementsLoaded] = useState(false);

  const rows = searchResult?.items ?? [];
  const activeSubscription = (currentStatus || "").toLowerCase() === "active";
  const canUseSavedDigests = activeSubscription && getPlanRank(currentPlan) >= getPlanRank("PRO");
  const canUseProPlusFeatures = activeSubscription && getPlanRank(currentPlan) >= getPlanRank("PRO_PLUS");

  useEffect(() => {
    try {
      const raw = localStorage.getItem(CASE_LAW_SETTINGS_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Record<string, unknown>;
        if (typeof parsed.query === "string") setQuery(parsed.query);
        if (typeof parsed.courtType === "string") setCourtType(parsed.courtType);
        if (typeof parsed.onlySupreme === "boolean") setOnlySupreme(parsed.onlySupreme);
        if (typeof parsed.source === "string") setSource(parsed.source);
        if (typeof parsed.tags === "string") setTags(parsed.tags);
        if (typeof parsed.dateFrom === "string") setDateFrom(parsed.dateFrom);
        if (typeof parsed.dateTo === "string") setDateTo(parsed.dateTo);
        if (typeof parsed.freshDays === "string") setFreshDays(parsed.freshDays);
        if (typeof parsed.digestDays === "string") setDigestDays(parsed.digestDays);
        if (typeof parsed.digestLimit === "string") setDigestLimit(parsed.digestLimit);
        if (typeof parsed.digestOnlySupreme === "boolean") setDigestOnlySupreme(parsed.digestOnlySupreme);
      }
      const seedRaw = localStorage.getItem(CASE_LAW_SEED_KEY);
      if (seedRaw) {
        const seed = JSON.parse(seedRaw) as { query?: string };
        if (typeof seed.query === "string" && seed.query.trim()) {
          setQuery(seed.query.trim());
          localStorage.removeItem(CASE_LAW_SEED_KEY);
        }
      }
    } catch {
      // no-op
    }
    // Overlay server-backed preferences (non-blocking)
    getUserPreferences(getToken(), getUserId()).then((prefs) => {
      if (prefs.case_law_only_supreme !== undefined) setOnlySupreme(prefs.case_law_only_supreme);
      if (prefs.case_law_court_type) setCourtType(prefs.case_law_court_type);
      if (prefs.case_law_source) setSource(prefs.case_law_source);
    });
    void refreshEntitlements();
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(
        CASE_LAW_SETTINGS_KEY,
        JSON.stringify({
          query,
          courtType,
          onlySupreme,
          source,
          tags,
          dateFrom,
          dateTo,
          freshDays,
          digestDays,
          digestLimit,
          digestOnlySupreme,
        })
      );
    } catch {
      // no-op
    }
  }, [query, courtType, onlySupreme, source, tags, dateFrom, dateTo, freshDays, digestDays, digestLimit, digestOnlySupreme]);

  useEffect(() => {
    if (!entitlementsLoaded) return;
    if (canUseSavedDigests) {
      void refreshDigestHistory();
    } else {
      setDigestHistory(null);
    }
    if (canUseProPlusFeatures) {
      void refreshSyncStatus();
    } else {
      setSyncStatus(null);
    }
  }, [entitlementsLoaded, canUseSavedDigests, canUseProPlusFeatures]);

  async function refreshEntitlements(): Promise<void> {
    try {
      const result = await getCurrentSubscription(getToken(), getUserId());
      setCurrentPlan(result.plan);
      setCurrentStatus(result.status);
    } catch {
      setCurrentPlan(null);
      setCurrentStatus(null);
    } finally {
      setEntitlementsLoaded(true);
    }
  }

  async function refreshDigestHistory(): Promise<void> {
    if (!canUseSavedDigests) return;
    setLoadingDigestHistory(true);
    try {
      setDigestHistory(await getCaseLawDigestHistory({ page: 1, page_size: 20 }, getToken(), getUserId()));
    } catch (nextError) {
      setError(formatError(nextError));
    } finally {
      setLoadingDigestHistory(false);
    }
  }

  async function refreshSyncStatus(): Promise<void> {
    if (!canUseProPlusFeatures) return;
    setLoadingStatus(true);
    try {
      setSyncStatus(await getCaseLawSyncStatus(getToken(), getUserId()));
    } catch (nextError) {
      setError(formatError(nextError));
    } finally {
      setLoadingStatus(false);
    }
  }

  async function runSearch(
    overrides?: { page?: number; page_size?: number; sort_by?: keyof CaseLawSearchItem; sort_dir?: "asc" | "desc" }
  ): Promise<void> {
    setError("");
    setInfo("");
    setLoadingSearch(true);
    const nextPage = overrides?.page ?? page;
    const nextPageSize = overrides?.page_size ?? pageSize;
    const nextSortBy = overrides?.sort_by ?? sortBy;
    const nextSortDir = overrides?.sort_dir ?? sortDir;
    const parsedFreshDays = Number(freshDays);

    try {
      const result = await searchCaseLaw(
        {
          query: query || undefined,
          court_type: courtType || undefined,
          only_supreme: onlySupreme,
          source: source || undefined,
          tags: tags || undefined,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
          fresh_days: Number.isFinite(parsedFreshDays) && parsedFreshDays > 0 ? parsedFreshDays : undefined,
          page: nextPage,
          page_size: nextPageSize,
          sort_by: String(nextSortBy),
          sort_dir: nextSortDir,
        },
        getToken(),
        getUserId()
      );
      setSearchResult(result);
      setPage(result.page);
      setPageSize(result.page_size);
      setSortBy(result.sort_by as keyof CaseLawSearchItem);
      setSortDir(result.sort_dir);
      setInfo(`Знайдено ${result.total} рішень. Сторінка ${result.page}/${result.pages}.`);
      // Persist case-law preferences server-side (fire-and-forget)
      updateUserPreferences(
        {
          case_law_only_supreme: onlySupreme,
          case_law_court_type: courtType || undefined,
          case_law_source: source || undefined,
        },
        getToken(),
        getUserId()
      );
    } catch (nextError) {
      setError(formatError(nextError));
    } finally {
      setLoadingSearch(false);
    }
  }

  async function onDigest(): Promise<void> {
    setError("");
    setInfo("");
    setLoadingDigest(true);
    try {
      const result = await getCaseLawDigest(
        {
          days: Number(digestDays) || 7,
          limit: Number(digestLimit) || 10,
          court_type: courtType || undefined,
          source: source || undefined,
          only_supreme: digestOnlySupreme,
        },
        getToken(),
        getUserId()
      );
      setDigestResult(result);
      setInfo(`Дайджест підготовлено: ${result.items.length} із ${result.total} рішень.`);
    } catch (nextError) {
      setError(formatError(nextError));
    } finally {
      setLoadingDigest(false);
    }
  }

  async function onSaveDigest(): Promise<void> {
    if (!canUseSavedDigests) {
      setError("Збереження дайджестів доступне з плану PRO.");
      return;
    }
    setError("");
    setInfo("");
    setLoadingDigest(true);
    try {
      const result = await generateCaseLawDigest(
        {
          days: Number(digestDays) || 7,
          limit: Number(digestLimit) || 10,
          court_type: courtType || undefined,
          source: source.split(",").map((item) => item.trim()).filter(Boolean),
          only_supreme: digestOnlySupreme,
          save: true,
          title: digestTitle.trim() || undefined,
        },
        getToken(),
        getUserId()
      );
      setDigestResult(result);
      await refreshDigestHistory();
      setInfo("Дайджест збережено.");
    } catch (nextError) {
      setError(formatError(nextError));
    } finally {
      setLoadingDigest(false);
    }
  }

  async function onOpenSavedDigest(digestId: string): Promise<void> {
    if (!canUseSavedDigests) return;
    setLoadingDigestHistory(true);
    try {
      setDigestResult(await getCaseLawDigestDetail(digestId, getToken(), getUserId()));
    } catch (nextError) {
      setError(formatError(nextError));
    } finally {
      setLoadingDigestHistory(false);
    }
  }

  async function onSync(): Promise<void> {
    if (!canUseProPlusFeatures) {
      setError("Requires PRO_PLUS plan and active subscription");
      return;
    }
    setError("");
    setInfo("");
    setLoadingSync(true);
    try {
      const result = await syncCaseLaw(
        {
          query: syncQuery.trim() || undefined,
          limit: Number(syncLimit) || 50,
          sources: syncSources.split(",").map((item) => item.trim()).filter(Boolean),
          allow_seed_fallback: syncAllowSeedFallback,
        },
        getToken(),
        getUserId()
      );
      setInfo(`Синхронізацію завершено: ${result.total} записів, створено ${result.created}, оновлено ${result.updated}.`);
      await refreshSyncStatus();
    } catch (nextError) {
      setError(formatError(nextError));
    } finally {
      setLoadingSync(false);
    }
  }

  async function onImportRecords(): Promise<void> {
    if (!canUseProPlusFeatures) {
      setError("Requires PRO_PLUS plan and active subscription");
      return;
    }
    setError("");
    setInfo("");
    setLoadingImport(true);
    try {
      const records = parseImportRecords(importPayload) as Array<{
        source?: string;
        decision_id: string;
        court_name?: string;
        court_type?: string;
        decision_date?: string;
        case_number?: string;
        subject_categories?: string[];
        legal_positions?: Record<string, unknown>;
        full_text?: string;
        summary?: string;
      }>;
      const result = await importCaseLaw(records, getToken(), getUserId());
      setInfo(`Імпорт завершено: ${result.total} записів, створено ${result.created}, оновлено ${result.updated}.`);
      await refreshSyncStatus();
    } catch (nextError) {
      setError(formatError(nextError));
    } finally {
      setLoadingImport(false);
    }
  }

  async function onUseDecisionInPrompt(row: CaseLawSearchItem): Promise<void> {
    const positions = Object.entries(row.legal_positions || {})
      .map(([key, value]) => `${key}: ${String(value)}`)
      .join("; ");
    const snippet = [
      `Source: ${row.source}`,
      `Case: ${row.case_number || row.decision_id}`,
      `Date: ${row.decision_date || "-"}`,
      `Court: ${row.court_name || row.court_type || "-"}`,
      row.summary ? `Summary: ${row.summary}` : "",
      positions ? `Legal positions: ${positions}` : "",
    ]
      .filter(Boolean)
      .join("\n");

    appendPromptContext(snippet);
    try {
      if (navigator?.clipboard?.writeText) await navigator.clipboard.writeText(snippet);
    } catch {
      // no-op
    }
    setInfo("Рішення додано до prompt-контексту.");
  }

  function onUseDigestInPrompt(): void {
    if (!digestResult) return;
    appendPromptContext([digestResult.title || "Weekly case-law digest", ...digestResult.items.map((item) => item.prompt_snippet)].join("\n"));
    setInfo("Дайджест додано до prompt-контексту.");
  }

  function toggleRow(rowId: string): void {
    setExpandedRows((previous) => ({ ...previous, [rowId]: !previous[rowId] }));
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div className="section-header">
        <div>
          <h1 className="section-title">Судова практика</h1>
          <p className="section-subtitle">AI-робоче місце для пошуку, дайджестів, імпорту та PRO+ синхронізації практики.</p>
        </div>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {currentPlan && <span className="badge badge-gold">{formatPlanLabel(currentPlan)}</span>}
          {currentStatus && (
            <span className={`badge ${activeSubscription ? "badge-success" : "badge-gold"}`}>
              {activeSubscription ? "Активна підписка" : currentStatus}
            </span>
          )}
        </div>
      </div>

      {error && <div className="preflight-block"><span style={{ color: "var(--danger)" }}>⚠ {error}</span></div>}
      {info && <div className="card-elevated" style={{ padding: "12px 16px", borderLeft: "3px solid var(--success)", color: "var(--success)" }}>{info}</div>}

      <section
        className="card-elevated"
        style={{
          padding: "28px",
          display: "grid",
          gridTemplateColumns: "minmax(0,1.5fr) minmax(240px,0.9fr)",
          gap: "20px",
          background: "radial-gradient(circle at top right, rgba(212,168,67,0.2), transparent 30%), rgba(255,255,255,0.03)",
        }}
      >
        <div>
          <div style={{ display: "inline-flex", padding: "6px 12px", borderRadius: "999px", background: "rgba(212,168,67,0.12)", border: "1px solid rgba(212,168,67,0.25)", color: "var(--gold-300)", fontSize: "11px", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>
            AI можливості LIGA360
          </div>
          <h2 style={{ fontSize: "40px", lineHeight: 1.05, letterSpacing: "-0.03em", margin: "12px 0" }}>Ваш віртуальний експерт для судової практики</h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "15px", maxWidth: "760px" }}>
            Комплекс інтелектуальних функцій для юристів, які хочуть швидше знаходити рішення, бачити релевантні патерни та використовувати практику в документах без ручного копіювання.
          </p>
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginTop: "20px" }}>
            <a href="#workspace" className="btn btn-primary">Спробувати зараз</a>
            <a href="#sources" className="btn btn-secondary">Офіційні джерела</a>
          </div>
        </div>
        <div style={{ display: "grid", gap: "12px" }}>
          {[
            { label: "У фокусі", value: searchResult?.total ?? syncStatus?.total_records ?? 0 },
            { label: "Збережені дайджести", value: digestHistory?.total ?? 0 },
            { label: "Останній sync", value: syncStatus?.last_sync_total ?? 0 },
          ].map((item) => (
            <div key={item.label} style={{ padding: "18px", borderRadius: "18px", background: "rgba(6,13,26,0.45)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <strong style={{ display: "block", fontSize: "28px", color: "#fff" }}>{item.value}</strong>
              <span style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{item.label}</span>
            </div>
          ))}
        </div>
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "16px" }}>
        {HERO_CHALLENGES.map((item) => (
          <div key={item} className="card-elevated" style={{ padding: "20px" }}>
            <div style={{ width: "36px", height: "36px", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: "14px", background: "rgba(212,168,67,0.15)", color: "var(--gold-300)" }}>✦</div>
            <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>{item}</p>
          </div>
        ))}
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "16px" }}>
        {HERO_BENEFITS.map((item) => (
          <div key={item} className="card-elevated" style={{ padding: "20px", display: "flex", gap: "14px", alignItems: "flex-start" }}>
            <div style={{ width: "38px", height: "38px", borderRadius: "50%", background: "rgba(76,81,191,0.18)", color: "#c5bfff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700 }}>✓</div>
            <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>{item}</p>
          </div>
        ))}
      </section>

      <section id="sources" className="card-elevated" style={{ padding: "24px" }}>
        <h2 style={{ fontSize: "24px", marginBottom: "8px" }}>Офіційні та зовнішні джерела</h2>
        <p style={{ color: "var(--text-secondary)", marginBottom: "18px" }}>
          `court.gov.ua/fair` уже підтримується в проєкті через публічний пошук `E-суд`. `zakononline.ua` поки не інтегрований в API як source-код, тому тут його показую як зовнішній правовий референс, а не як фальшивий sync-канал.
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "16px" }}>
          <a href="https://court.gov.ua/fair/" target="_blank" rel="noreferrer" className="card-elevated" style={{ padding: "18px", textDecoration: "none", color: "inherit" }}>
            <strong style={{ display: "block", marginBottom: "6px", fontSize: "18px" }}>court.gov.ua/fair</strong>
            <span style={{ color: "var(--text-secondary)", fontSize: "14px" }}>Офіційний публічний канал для історії руху справ. У коді вже пов'язаний з модулем `E-суд`.</span>
          </a>
          <a href="https://zakononline.ua" target="_blank" rel="noreferrer" className="card-elevated" style={{ padding: "18px", textDecoration: "none", color: "inherit" }}>
            <strong style={{ display: "block", marginBottom: "6px", fontSize: "18px" }}>zakononline.ua</strong>
            <span style={{ color: "var(--text-secondary)", fontSize: "14px" }}>Зовнішній нормативний довідник. Поки що доступний як reference-link, без бекендового ingestion або sync.</span>
          </a>
        </div>
      </section>

      <section id="workspace" className="card-elevated" style={{ padding: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "16px", marginBottom: "20px" }}>
          <div>
            <h2 style={{ fontSize: "24px", marginBottom: "8px" }}>Інтелектуальний пошук рішень</h2>
            <p style={{ color: "var(--text-secondary)" }}>Пошук, фільтри та швидка передача релевантних рішень у prompt-контекст.</p>
          </div>
          <div style={{ minWidth: "100px", padding: "14px 16px", borderRadius: "18px", background: "rgba(255,255,255,0.04)", textAlign: "right" }}>
            <span style={{ display: "block", fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Пошук</span>
            <strong style={{ fontSize: "28px", color: "#fff" }}>{searchResult?.total ?? 0}</strong>
          </div>
        </div>
        <form
          onSubmit={async (event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            await runSearch({ page: 1 });
          }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: "14px" }}>
            <div>
              <label htmlFor="case-law-query" className="form-label">Запит</label>
              <input id="case-law-query" className="form-input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Наприклад: стягнення боргу, стаття 625 ЦК" />
            </div>
            <div>
              <label htmlFor="case-law-court-type" className="form-label">Тип суду</label>
              <select id="case-law-court-type" className="form-input" value={courtType} onChange={(event) => setCourtType(event.target.value)}>
                {COURT_TYPES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="case-law-source" className="form-label">Джерело</label>
              <input id="case-law-source" aria-label="Source (comma separated)" className="form-input" value={source} onChange={(event) => setSource(event.target.value)} placeholder="opendatabot, manual" />
            </div>
            <div>
              <label htmlFor="case-law-tags" className="form-label">Теги</label>
              <input id="case-law-tags" className="form-input" value={tags} onChange={(event) => setTags(event.target.value)} placeholder="борг, оренда, постачання" />
            </div>
            <div>
              <label htmlFor="case-law-date-from" className="form-label">Дата від</label>
              <input id="case-law-date-from" aria-label="Decision date from" className="form-input" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
            </div>
            <div>
              <label htmlFor="case-law-date-to" className="form-label">Дата до</label>
              <input id="case-law-date-to" aria-label="Decision date to" className="form-input" type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
            </div>
            <div>
              <label htmlFor="case-law-fresh-days" className="form-label">Свіжість, днів</label>
              <input id="case-law-fresh-days" aria-label="Fresh days (optional)" className="form-input" type="number" min={1} value={freshDays} onChange={(event) => setFreshDays(event.target.value)} placeholder="365" />
            </div>
            <div>
              <label htmlFor="case-law-only-supreme" className="form-label">Рівень практики</label>
              <select id="case-law-only-supreme" className="form-input" value={String(onlySupreme)} onChange={(event) => setOnlySupreme(event.target.value === "true")}>
                <option value="true">Лише Верховний Суд</option>
                <option value="false">Усі доступні суди</option>
              </select>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap", marginTop: "18px" }}>
            <button type="submit" className="btn btn-primary" aria-label="Search cache" disabled={loadingSearch}>{loadingSearch ? "Пошук..." : "Знайти рішення"}</button>
            <select
              className="form-input"
              style={{ width: "auto", minWidth: "148px" }}
              value={String(pageSize)}
              onChange={async (event) => {
                const nextValue = Number(event.target.value) || 20;
                setPageSize(nextValue);
                if (searchResult) await runSearch({ page: 1, page_size: nextValue });
              }}
            >
              <option value="10">10 на сторінку</option>
              <option value="20">20 на сторінку</option>
              <option value="50">50 на сторінку</option>
            </select>
            <button type="button" className="btn btn-secondary" style={{ padding: "10px 14px", fontSize: "13px" }} onClick={() => void runSearch({ page: 1, sort_by: "decision_date", sort_dir: sortBy === "decision_date" && sortDir === "asc" ? "desc" : "asc" })}>Дата</button>
            <button type="button" className="btn btn-secondary" style={{ padding: "10px 14px", fontSize: "13px" }} onClick={() => void runSearch({ page: 1, sort_by: "court_type", sort_dir: sortBy === "court_type" && sortDir === "asc" ? "desc" : "asc" })}>Суд</button>
            <button type="button" className="btn btn-secondary" style={{ padding: "10px 14px", fontSize: "13px" }} onClick={() => void runSearch({ page: 1, sort_by: "reference_count", sort_dir: sortBy === "reference_count" && sortDir === "asc" ? "desc" : "asc" })}>Посилання</button>
          </div>
        </form>

        {searchResult && (
          <div style={{ display: "flex", flexDirection: "column", gap: "14px", marginTop: "22px" }}>
            <div>
              <strong style={{ display: "block", color: "#fff", fontSize: "18px", marginBottom: "2px" }}>Знайдено {searchResult.total} рішень</strong>
              <span style={{ position: "absolute", width: 1, height: 1, padding: 0, margin: -1, overflow: "hidden", clip: "rect(0,0,0,0)", whiteSpace: "nowrap", border: 0 }}>{`Found ${searchResult.total} records`}</span>
              <p style={{ color: "var(--text-secondary)" }}>Сторінка {searchResult.page} з {searchResult.pages}</p>
            </div>
            {rows.map((row) => (
              <div key={row.id} className="card-elevated" style={{ padding: "18px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", marginBottom: "10px" }}>
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    <span className="badge badge-gold">{row.court_type || "court"}</span>
                    <span className="badge badge-success">{row.source}</span>
                    {row.reference_count > 0 && <span className="badge badge-gold">{row.reference_count} посилань</span>}
                  </div>
                  <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>{row.decision_date || "-"}</span>
                </div>
                <h4 style={{ fontSize: "18px", marginBottom: "4px" }}>{row.case_number || row.decision_id}</h4>
                <p style={{ color: "var(--text-muted)", fontSize: "12px" }}>{row.court_name || "Суд не вказано"}</p>
                {row.summary && <p style={{ marginTop: "10px", color: "var(--text-secondary)" }}>{row.summary}</p>}
                {row.subject_categories.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginTop: "14px" }}>
                    {row.subject_categories.map((tag) => <span key={tag} style={{ padding: "5px 10px", borderRadius: "999px", background: "rgba(212,168,67,0.1)", border: "1px solid rgba(212,168,67,0.24)", color: "var(--gold-300)", fontSize: "12px" }}>{tag}</span>)}
                  </div>
                )}
                <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap", marginTop: "16px" }}>
                  <button type="button" className="btn btn-secondary" style={{ padding: "10px 14px", fontSize: "13px" }} onClick={() => toggleRow(row.id)}>{expandedRows[row.id] ? "Сховати деталі" : "Показати деталі"}</button>
                  <button type="button" className="btn btn-primary" style={{ padding: "10px 14px", fontSize: "13px" }} aria-label="Use in prompt" onClick={() => void onUseDecisionInPrompt(row)}>Додати до prompt</button>
                </div>
                {expandedRows[row.id] && (
                  <div style={{ marginTop: "14px", padding: "14px", borderRadius: "14px", background: "rgba(255,255,255,0.03)" }}>
                    <strong style={{ display: "block", marginBottom: "8px" }}>Правові позиції</strong>
                    <pre style={{ whiteSpace: "pre-wrap", fontFamily: "inherit", fontSize: "12px", color: "var(--text-secondary)" }}>{JSON.stringify(row.legal_positions || {}, null, 2)}</pre>
                  </div>
                )}
              </div>
            ))}
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "12px", color: "var(--text-secondary)" }}>
              <button type="button" className="btn btn-secondary" style={{ padding: "10px 14px", fontSize: "13px" }} aria-label="Previous" disabled={loadingSearch || searchResult.page <= 1} onClick={() => void runSearch({ page: searchResult.page - 1 })}>Попередня</button>
              <span>Сторінка {searchResult.page} із {searchResult.pages}</span>
              <button type="button" className="btn btn-secondary" style={{ padding: "10px 14px", fontSize: "13px" }} aria-label="Next" disabled={loadingSearch || searchResult.page >= searchResult.pages} onClick={() => void runSearch({ page: searchResult.page + 1 })}>Наступна</button>
            </div>
          </div>
        )}
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "20px" }}>
        <div className="card-elevated" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>AI-дайджест практики</h2>
          <p style={{ color: "var(--text-secondary)", marginBottom: "18px" }}>Стискає релевантні рішення в готові fragment-и для prompt-контексту.</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "14px" }}>
            <div>
              <label htmlFor="digest-days" className="form-label">Днів назад</label>
              <input id="digest-days" className="form-input" type="number" min={1} max={3650} value={digestDays} onChange={(event) => setDigestDays(event.target.value)} />
            </div>
            <div>
              <label htmlFor="digest-limit" className="form-label">Максимум рішень</label>
              <input id="digest-limit" className="form-input" type="number" min={1} max={100} value={digestLimit} onChange={(event) => setDigestLimit(event.target.value)} />
            </div>
            <div>
              <label htmlFor="digest-only-supreme" className="form-label">Обсяг практики</label>
              <select id="digest-only-supreme" className="form-input" value={String(digestOnlySupreme)} onChange={(event) => setDigestOnlySupreme(event.target.value === "true")}>
                <option value="true">Лише Верховний Суд</option>
                <option value="false">Усі суди</option>
              </select>
            </div>
            <div>
              <label htmlFor="digest-title" className="form-label">Назва добірки</label>
              <input id="digest-title" aria-label="Digest title (optional)" className="form-input" value={digestTitle} onChange={(event) => setDigestTitle(event.target.value)} placeholder="Наприклад: Березневий дайджест ВС" />
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap", marginTop: "18px" }}>
            <button type="button" className="btn btn-primary" aria-label="Load digest" disabled={loadingDigest} onClick={() => void onDigest()}>{loadingDigest ? "Підготовка..." : "Оновити дайджест"}</button>
            <button type="button" className="btn btn-secondary" aria-label="Save digest" disabled={loadingDigest || !canUseSavedDigests} onClick={() => void onSaveDigest()}>Зберегти дайджест</button>
            <button type="button" className="btn btn-secondary" aria-label="Use digest in prompt" disabled={!digestResult} onClick={onUseDigestInPrompt}>Передати в prompt</button>
            {!canUseSavedDigests && <span style={{ color: "var(--text-muted)", fontSize: "13px" }}>Збереження доступне з плану PRO.</span>}
          </div>
          {digestResult && (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "18px" }}>
              {digestResult.items.map((item, index) => (
                <div key={`${item.id}-${index}`} style={{ padding: "12px 14px", borderRadius: "14px", background: "rgba(255,255,255,0.03)", color: "var(--text-secondary)", fontSize: "13px", lineHeight: 1.55 }}>
                  <strong>{index + 1}.</strong> {item.prompt_snippet}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card-elevated" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>Збережені дайджести</h2>
          <p style={{ color: "var(--text-secondary)", marginBottom: "18px" }}>Готові тематичні добірки для повторного використання в роботі.</p>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
            <button type="button" className="btn btn-secondary" aria-label="Refresh saved digests" disabled={loadingDigestHistory || !canUseSavedDigests} onClick={() => void refreshDigestHistory()}>{loadingDigestHistory ? "Оновлення..." : "Оновити список"}</button>
            {!canUseSavedDigests && <span style={{ color: "var(--text-muted)", fontSize: "13px" }}>Історія доступна з плану PRO.</span>}
          </div>
          {canUseSavedDigests && digestHistory?.items?.length ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "18px" }}>
              {digestHistory.items.map((item) => (
                <button key={item.id} type="button" style={{ textAlign: "left", padding: "14px", borderRadius: "14px", border: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.02)", color: "var(--text-primary)", cursor: "pointer" }} onClick={() => void onOpenSavedDigest(item.id)}>
                  <strong style={{ display: "block", marginBottom: "4px" }}>{item.title || `Дайджест від ${item.created_at}`}</strong>
                  <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>{item.item_count} рішень</span>
                </button>
              ))}
            </div>
          ) : (
            <p style={{ color: "var(--text-muted)", fontSize: "13px", marginTop: "18px" }}>{canUseSavedDigests ? "Поки немає збережених дайджестів." : "Підвищте план для історії збережених добірок."}</p>
          )}
        </div>
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "20px" }}>
        <div className="card-elevated" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>PRO+ синхронізація бази</h2>
          <p style={{ color: "var(--text-secondary)", marginBottom: "18px" }}>Оновлює кеш практики із підтримуваних джерел і показує фактичний стан останнього sync.</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "14px" }}>
            <div>
              <label htmlFor="sync-query" className="form-label">Запит для sync</label>
              <input id="sync-query" className="form-input" value={syncQuery} onChange={(event) => setSyncQuery(event.target.value)} placeholder="Наприклад: debt, lease, tax" />
            </div>
            <div>
              <label htmlFor="sync-limit" className="form-label">Ліміт записів</label>
              <input id="sync-limit" className="form-input" type="number" min={1} value={syncLimit} onChange={(event) => setSyncLimit(event.target.value)} />
            </div>
            <div>
              <label htmlFor="sync-sources" className="form-label">Джерела sync</label>
              <input id="sync-sources" className="form-input" value={syncSources} onChange={(event) => setSyncSources(event.target.value)} placeholder="opendatabot,json_feed" />
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", paddingTop: "34px", color: "var(--text-secondary)" }}>
              <input id="sync-seed-fallback" type="checkbox" checked={syncAllowSeedFallback} onChange={(event) => setSyncAllowSeedFallback(event.target.checked)} />
              <label htmlFor="sync-seed-fallback">Дозволити seed fallback</label>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap", marginTop: "18px" }}>
            <button type="button" className="btn btn-primary" aria-label="Run sync" disabled={loadingSync || !canUseProPlusFeatures} onClick={() => void onSync()}>{loadingSync ? "Синхронізація..." : "Запустити sync"}</button>
            <button type="button" className="btn btn-secondary" disabled={loadingStatus || !canUseProPlusFeatures} onClick={() => void refreshSyncStatus()}>{loadingStatus ? "Оновлення..." : "Оновити статус"}</button>
          </div>
          {!canUseProPlusFeatures && <p style={{ color: "var(--text-muted)", fontSize: "13px", marginTop: "12px" }}>Requires PRO_PLUS plan and active subscription</p>}
          {syncStatus && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "12px", marginTop: "18px" }}>
              {[
                { label: "Усього записів", value: syncStatus.total_records },
                { label: "Останній sync", value: syncStatus.last_sync_at || "-" },
                { label: "Останній обсяг", value: syncStatus.last_sync_total ?? 0 },
                { label: "Остання дата рішення", value: syncStatus.latest_decision_date || "-" },
              ].map((item) => (
                <div key={item.label} style={{ padding: "14px", borderRadius: "16px", background: "rgba(255,255,255,0.03)", display: "flex", flexDirection: "column", gap: "6px" }}>
                  <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>{item.label}</span>
                  <strong style={{ color: "#fff", fontSize: "16px" }}>{item.value}</strong>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card-elevated" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>Імпорт власних записів</h2>
          <p style={{ color: "var(--text-secondary)", marginBottom: "18px" }}>Вставте JSON-масив або об'єкт з полем <code>records</code>, щоб швидко додати свою добірку практики.</p>
          <label htmlFor="import-payload" className="form-label">JSON payload</label>
          <textarea
            id="import-payload"
            value={importPayload}
            onChange={(event) => setImportPayload(event.target.value)}
            spellCheck={false}
            style={{ width: "100%", minHeight: "260px", marginTop: "8px", padding: "14px", borderRadius: "16px", border: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.03)", color: "var(--text-primary)", fontSize: "13px", lineHeight: 1.5, resize: "vertical", outline: "none" }}
          />
          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap", marginTop: "18px" }}>
            <button type="button" className="btn btn-primary" aria-label="Import records" disabled={loadingImport || !canUseProPlusFeatures || !importPayload.trim()} onClick={() => void onImportRecords()}>{loadingImport ? "Імпорт..." : "Імпортувати записи"}</button>
          </div>
          {!canUseProPlusFeatures && <p style={{ color: "var(--text-muted)", fontSize: "13px", marginTop: "12px" }}>Requires PRO_PLUS plan and active subscription</p>}
        </div>
      </section>
    </div>
  );
}
