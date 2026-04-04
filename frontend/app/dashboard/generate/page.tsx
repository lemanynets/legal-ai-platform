"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { getSession, getToken, getUserId } from "@/lib/auth";
import {
  type CaseLawDigestHistoryItem,
  type CaseLawSearchItem,
  type CaseDetail,
  type DocumentType,
  type FormField,
  type GenerateResponse,
  type GenerateBundleResponse,
  type TargetLanguage,
  type StreamEvent,
  generateDocument,
  generateDocumentStream,
  getCase,
  getCaseLawDigest,
  getCaseLawDigestDetail,
  getCaseLawDigestHistory,
  getDocumentFormSchema,
  getDocumentTypes,
  getCases,
  type Case,
  getKnowledgeEntries,
  type KnowledgeEntry,
  searchCaseLaw,
  createKnowledgeEntry,
  getUserPreferences,
  updateUserPreferences,
  type UserPreferences,
} from "@/lib/api";
import { type BlockerItem } from "@/lib/error-codes";

type RawFormData = Record<string, string>;

const PROMPT_STORAGE_KEY = "legal_ai_prompt_context";

function convertValue(field: FormField, value: string): unknown {
  if (field.type === "number") {
    if (!value.trim()) return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  if (field.type === "array") {
    return value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  return value;
}

function appendContextBlock(previous: string, block: string): string {
  const base = previous.trim();
  return base ? `${base}\n\n${block}` : block;
}

function prettifyFieldLabel(key: string): string {
  const normalized = key.replace(/_/g, " ").trim();
  return normalized ? normalized.charAt(0).toUpperCase() + normalized.slice(1) : key;
}

function findMissingRequiredFields(schema: FormField[], formData: RawFormData): string[] {
  return schema
    .filter((field) => field.required)
    .filter((field) => !(formData[field.key] || "").trim())
    .map((field) => field.key);
}

function SummaryStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card-elevated" style={{ padding: "14px" }}>
      <div style={{ fontSize: "11px", textTransform: "uppercase", color: "var(--text-muted)", marginBottom: "6px" }}>{label}</div>
      <div style={{ color: "#fff", fontWeight: 700 }}>{value}</div>
    </div>
  );
}

function GeneratePageInner() {
  const searchParams = useSearchParams();
  const [docTypes, setDocTypes] = useState<DocumentType[]>([]);
  const [selectedDocType, setSelectedDocType] = useState("");
  const [schema, setSchema] = useState<FormField[]>([]);
  const [formData, setFormData] = useState<RawFormData>({});
  const [extraContext, setExtraContext] = useState("");
  const [includeDigest, setIncludeDigest] = useState(true);
  const [savedDigests, setSavedDigests] = useState<CaseLawDigestHistoryItem[]>([]);
  const [selectedSavedDigestId, setSelectedSavedDigestId] = useState("");
  const [useSelectedSavedDigest, setUseSelectedSavedDigest] = useState(false);
  const [loading, setLoading] = useState(false);
  const [schemaLoading, setSchemaLoading] = useState(false);
  const [savedDigestLoading, setSavedDigestLoading] = useState(false);
  const [error, setError] = useState("");
  const [blockers, setBlockers] = useState<BlockerItem[]>([]);
  const [missingFields, setMissingFields] = useState<string[]>([]);
  const [info, setInfo] = useState("");
  const [result, setResult] = useState<GenerateResponse | GenerateBundleResponse | null>(null);
  const [genMode, setGenMode] = useState<"standard" | "deep">("standard");
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [selectedCaseDetail, setSelectedCaseDetail] = useState<CaseDetail | null>(null);
  const [caseDecisions, setCaseDecisions] = useState<CaseLawSearchItem[]>([]);
  
  // New State for Style and Precedents
  const [genStyle, setGenStyle] = useState<"persuasive" | "aggressive" | "conciliatory" | "analytical">("persuasive");
  const [targetLanguage, setTargetLanguage] = useState<TargetLanguage>("uk");
  const [knowledgeBase, setKnowledgeBase] = useState<KnowledgeEntry[]>([]);
  const [selectedPrecedentIds, setSelectedPrecedentIds] = useState<string[]>([]);
  const [kbLoading, setKbLoading] = useState(false);
  const [savingToKb, setSavingToKb] = useState(false);
  const [isSavedToKb, setIsSavedToKb] = useState(false);
  const [genProgress, setGenProgress] = useState("");
  const prefsApplied = useRef(false);

  // Bundle states
  const [isBundleMode, setIsBundleMode] = useState(false);
  const [selectedBundle, setSelectedBundle] = useState<"civil_set" | "divorce_set" | "any">("civil_set");
  const bundleDocMapping: Record<string, string[]> = {
    civil_set: ["civil_claim", "motion_injunction", "evidence_request"],
    divorce_set: ["divorce_claim", "property_division_claim"]
  };

  const session = getSession();
  const tariff = session?.plan ?? "FREE";

  const handleSaveToKB = async () => {
    if (!displayResult || !displayResult.generated_text) return;
    setSavingToKb(true);
    try {
      await createKnowledgeEntry(
        {
          title: displayResult.title || `Згенерований: ${selectedDocType}`,
          content: displayResult.generated_text,
          category: "Прецедент",
          tags: ["generated", selectedDocType],
        },
        getToken(),
        getUserId()
      );
      setIsSavedToKb(true);
      setInfo("Успішно збережено до бази знань.");
      
      // Refresh Knowledge Base
      const kb = await getKnowledgeEntries({}, getToken());
      setKnowledgeBase(kb);
    } catch (err) {
      setError("Не вдалося зберегти до бази знань: " + String(err));
    } finally {
      setSavingToKb(false);
    }
  };

  const [isResearching, setIsResearching] = useState(false);

  const handleSmartResearch = async () => {
    setLoading(true);
    setIsResearching(true);
    setError("");
    setInfo("AI аналізує ваші факти для пошуку релевантної практики...");
    
    try {
      // 1. Estimate query from form data
      const queryParts = [selectedDocType];
      if (formData.factual_points) queryParts.push(formData.factual_points);
      const query = queryParts.join(" ").substring(0, 300);

      // 2. Perform search
      const searchResponse = await searchCaseLaw({ 
        query, 
        only_supreme: true, 
        page_size: 5 
      }, getToken(), getUserId());

      if (searchResponse.items.length > 0) {
        // 3. Format context
        let newContext = "\n--- AUTO-RESEARCHED CASE LAW ---\n";
        searchResponse.items.forEach((item, idx) => {
          newContext += `[${idx+1}] Справа №${item.case_number || 'н/д'}. Позиція: ${item.summary || 'див. повний текст'}\n`;
        });
        
        setExtraContext(prev => appendContextBlock(prev, newContext));
        setInfo(`Знайдено ${searchResponse.items.length} релевантних рішень ВСУ та додано в контекст.`);
      } else {
        setInfo("Релевантної практики за цими фактами не знайдено, але ви можете додати її вручну.");
      }
    } catch (err) {
      setError("Помилка при пошуку практики: " + String(err));
    } finally {
      setLoading(false);
      setIsResearching(false);
    }
  };

  const selectedDocMeta = useMemo(
    () => docTypes.find((item) => item.doc_type === selectedDocType) ?? null,
    [docTypes, selectedDocType]
  );

  const requiredTotal = useMemo(() => schema.filter((field) => field.required).length, [schema]);
  const requiredFilled = useMemo(
    () => schema.filter((field) => field.required && (formData[field.key] || "").trim()).length,
    [schema, formData]
  );

  useEffect(() => {
    getDocumentTypes()
      .then((items) => {
        setDocTypes(items);
        if (items.length > 0) {
          setSelectedDocType(items[0].doc_type);
        }
      })
      .catch((nextError) => setError(String(nextError)));

    setSavedDigestLoading(true);
    getCaseLawDigestHistory({ page: 1, page_size: 20 }, getToken(), getUserId())
      .then((response) => setSavedDigests(response.items))
      .catch(() => setSavedDigests([]))
      .finally(() => setSavedDigestLoading(false));

    getCases(getToken(), getUserId())
      .then((items) => {
        setCases(items);
        const requestedCaseId = searchParams.get("case_id") || "";
        if (requestedCaseId && items.some((item) => item.id === requestedCaseId)) {
          setSelectedCaseId(requestedCaseId);
        }
      })
      .catch((err) => console.error("Failed to load cases", err));

    setKbLoading(true);
    getKnowledgeEntries({}, getToken())
      .then(setKnowledgeBase)
      .catch(() => setKnowledgeBase([]))
      .finally(() => setKbLoading(false));

    // Load server-backed preferences (non-blocking)
    getUserPreferences(getToken(), getUserId()).then((prefs) => {
      if (prefsApplied.current) return;
      prefsApplied.current = true;
      if (prefs.gen_mode) setGenMode(prefs.gen_mode);
      if (prefs.gen_style) setGenStyle(prefs.gen_style);
      if (prefs.target_language) setTargetLanguage(prefs.target_language);
      if (typeof prefs.include_digest === "boolean") setIncludeDigest(prefs.include_digest);
      if (prefs.default_doc_type) setSelectedDocType(prefs.default_doc_type);
    });
  }, [searchParams]);

  useEffect(() => {
    if (!selectedCaseId) {
      setSelectedCaseDetail(null);
      setCaseDecisions([]);
      return;
    }

    getCase(selectedCaseId, getToken(), getUserId())
      .then(async (caseDetail) => {
        setSelectedCaseDetail(caseDetail);
        const caseNumber = caseDetail.case_number?.trim();
        if (!caseNumber) {
          setCaseDecisions([]);
          return;
        }
        const response = await searchCaseLaw(
          { query: caseNumber, page_size: 5, sort_by: "decision_date", sort_dir: "desc" },
          getToken(),
          getUserId()
        );
        setCaseDecisions(response.items);
      })
      .catch((err) => {
        console.error("Failed to load case-bound decisions", err);
        setSelectedCaseDetail(null);
        setCaseDecisions([]);
      });
  }, [selectedCaseId]);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(PROMPT_STORAGE_KEY);
      if (stored) {
        setExtraContext(stored);
        setInfo("Контекст із Судової практики підхоплено в генерацію.");
      }
    } catch {
      // Ignore local storage access errors.
    }
  }, []);

  useEffect(() => {
    try {
      if (extraContext.trim()) {
        localStorage.setItem(PROMPT_STORAGE_KEY, extraContext);
      } else {
        localStorage.removeItem(PROMPT_STORAGE_KEY);
      }
    } catch {
      // Ignore local storage access errors.
    }
  }, [extraContext]);

  useEffect(() => {
    if (!selectedDocType) return;

    setSchemaLoading(true);
    setError("");

    getDocumentFormSchema(selectedDocType)
      .then((fields) => {
        setSchema(fields);
        const initial: RawFormData = {};
        fields.forEach((field) => {
          initial[field.key] = "";
        });
        setFormData(initial);
      })
      .catch((nextError) => setError(String(nextError)))
      .finally(() => setSchemaLoading(false));
  }, [selectedDocType]);

  async function loadDigest(): Promise<void> {
    setError("");
    try {
      const response = await getCaseLawDigest(
        { days: 365, limit: 5, only_supreme: true },
        getToken(),
        getUserId()
      );
      const block = [
        `Case-law digest (${response.generated_at}):`,
        ...response.items.map((item, index) => `${index + 1}. ${item.prompt_snippet}`),
      ].join("\n");
      setExtraContext((previous) => appendContextBlock(previous, block));
      setInfo("Свіжий digest додано в контекст генерації.");
    } catch (nextError) {
      setError(String(nextError));
    }
  }

  async function loadSelectedSavedDigest(): Promise<void> {
    if (!selectedSavedDigestId) return;

    setError("");
    try {
      const response = await getCaseLawDigestDetail(selectedSavedDigestId, getToken(), getUserId());
      const title = response.title?.trim() || "Saved digest";
      const block = [
        `Saved case-law digest: ${title}`,
        ...response.items.map((item, index) => `${index + 1}. ${item.prompt_snippet}`),
      ].join("\n");
      setExtraContext((previous) => appendContextBlock(previous, block));
      setInfo(`Збережений digest "${title}" додано в контекст.`);
    } catch (nextError) {
      setError(String(nextError));
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();

    if (!isBundleMode && !selectedDocType) {
      setError("Оберіть тип документа.");
      return;
    }

    const missingRequired = findMissingRequiredFields(schema, formData);
    if (missingRequired.length > 0) {
      setError(`Заповніть обов'язкові поля: ${missingRequired.join(", ")}`);
      return;
    }

    const payload: Record<string, unknown> = {};
    schema.forEach((field) => {
      const raw = formData[field.key] ?? "";
      if (!raw.trim() && !field.required) return;
      payload[field.key] = convertValue(field, raw);
    });

    const caseContextBlock = selectedCaseDetail
      ? [
          "CASE CONTEXT FROM SAVED CASE",
          `Назва: ${selectedCaseDetail.title}`,
          selectedCaseDetail.case_number ? `Номер: ${selectedCaseDetail.case_number}` : "",
          selectedCaseDetail.description ? `Опис: ${selectedCaseDetail.description}` : "",
          caseDecisions.length
            ? "Рішення з локальної бази:\n" +
              caseDecisions
                .map((item, index) => `${index + 1}. ${item.court_name || "Суд"} | ${item.case_number || item.decision_id} | ${item.decision_date || "без дати"}\n${item.summary || ""}`)
                .join("\n")
            : "",
        ]
          .filter(Boolean)
          .join("\n\n")
      : "";

    const options: Parameters<typeof generateDocument>[5] = {
      extra_prompt_context: [caseContextBlock, extraContext.trim()].filter(Boolean).join("\n\n") || undefined,
      include_digest: includeDigest,
      digest_days: 365,
      digest_limit: 5,
      digest_only_supreme: true,
      saved_digest_id: useSelectedSavedDigest && selectedSavedDigestId ? selectedSavedDigestId : undefined,
      mode: genMode,
      style: genStyle,
      precedent_ids: selectedPrecedentIds.length > 0 ? selectedPrecedentIds : undefined,
      case_id: selectedCaseId || undefined,
      bundle_doc_types: isBundleMode ? bundleDocMapping[selectedBundle] : undefined,
      target_language: targetLanguage !== "uk" ? targetLanguage : undefined,
    };

    setLoading(true);
    setResult(null);
    setIsSavedToKb(false);
    setError("");
    setBlockers([]);
    setMissingFields([]);
    setInfo("");
    setGenProgress("");

    const targetType = isBundleMode ? "bundle" : selectedDocType;

    generateDocumentStream(
      targetType, payload, tariff,
      (event: StreamEvent) => {
        if (event.message) setGenProgress(event.message);
      },
      getToken(), getUserId(), options
    )
      .then((data) => {
        setResult(data);
        setGenProgress("");
        if ("bundle_id" in data) {
          setInfo(`Пакет документів згенеровано (ID: ${data.bundle_id}).`);
        } else {
          setInfo(`Документ згенеровано: ${data.title}.`);
        }
        // Persist current settings as user preferences (fire-and-forget)
        updateUserPreferences(
          {
            gen_mode: genMode,
            gen_style: genStyle,
            target_language: targetLanguage,
            include_digest: includeDigest,
            default_doc_type: selectedDocType,
          },
          getToken(),
          getUserId()
        );
      })
      .catch((nextError: unknown) => {
        // Extract structured blocker/missing-fields data from 422 responses
        if (
          nextError &&
          typeof nextError === "object" &&
          "code" in nextError
        ) {
          const apiErr = nextError as {
            code?: string;
            blockers?: BlockerItem[];
            missingFields?: string[];
            message?: string;
          };
          if (apiErr.blockers?.length) setBlockers(apiErr.blockers);
          if (apiErr.missingFields?.length) setMissingFields(apiErr.missingFields);
        }
        setError(nextError instanceof Error ? nextError.message : String(nextError));
      })
      .finally(() => setLoading(false));
  }

  const [activeBundleItemIndex, setActiveBundleItemIndex] = useState(0);

  const displayResult = useMemo<GenerateResponse | null>(() => {
    if (!result) return null;
    if ("bundle_id" in result) {
      return (result as GenerateBundleResponse).items[activeBundleItemIndex];
    }
    return result as GenerateResponse;
  }, [result, activeBundleItemIndex]);

  // Sync URL mode param with bundle state
  const urlMode = searchParams.get("mode") || "single";
  const isPackageMode = urlMode === "package" || isBundleMode;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div className="section-header">
        <div>
          <h1 className="section-title">Генерація документів</h1>
          <p className="section-subtitle">
            {isPackageMode
              ? "Пакетна генерація: набори документів для типових правових ситуацій."
              : "Генерація окремого документа: форма, стиль, прецеденти, AI-контекст."}
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          {result && (
            <Link href="/dashboard/documents" className="btn btn-secondary btn-sm">
              Відкрити мої документи
            </Link>
          )}
        </div>
      </div>

      {/* Mode tabs */}
      <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
        {[
          { key: "single", label: "Документ" },
          { key: "package", label: "Пакет" },
        ].map(({ key, label }) => (
          <Link
            key={key}
            href={`/dashboard/generate?mode=${key}`}
            onClick={() => setIsBundleMode(key === "package")}
            style={{
              display: "inline-block",
              padding: "10px 20px",
              textDecoration: "none",
              fontSize: "14px",
              fontWeight: isPackageMode === (key === "package") ? 700 : 400,
              color: isPackageMode === (key === "package") ? "var(--gold-400)" : "var(--text-secondary)",
              borderBottom: isPackageMode === (key === "package") ? "2px solid var(--gold-400)" : "2px solid transparent",
              marginBottom: "-1px",
              transition: "all 0.2s",
            }}
          >
            {label}
          </Link>
        ))}
      </div>

      {info && (
        <div className="card-elevated" style={{ padding: "12px 16px", borderLeft: "3px solid var(--success)", color: "var(--success)" }}>
          {info}
        </div>
      )}

      {error && <div className="alert alert-error">Помилка: {error}</div>}

      {/* Structured missing-fields block (INPUT_MISSING_REQUIRED_FIELDS) */}
      {missingFields.length > 0 && (
        <div className="card-elevated" style={{ padding: "14px 18px", borderLeft: "3px solid var(--danger)", background: "rgba(239,68,68,0.06)" }}>
          <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--danger)", marginBottom: "8px" }}>
            Обов'язкові поля не заповнені
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
            {missingFields.map((f) => (
              <span key={f} style={{ padding: "3px 10px", borderRadius: "999px", fontSize: "12px", fontWeight: 600, background: "rgba(239,68,68,0.12)", color: "var(--danger)" }}>
                {f}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Structured processual blockers block (PROC_BLOCKER) — split by severity */}
      {blockers.length > 0 && (() => {
        const criticals = blockers.filter(b => !b.severity || b.severity === "critical");
        const warnings  = blockers.filter(b => b.severity === "warning");
        const infos     = blockers.filter(b => b.severity === "info");
        return (
          <>
            {criticals.length > 0 && (
              <div className="card-elevated" style={{ padding: "14px 18px", borderLeft: "3px solid var(--danger)", background: "rgba(239,68,68,0.06)" }}>
                <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--danger)", marginBottom: "8px" }}>
                  Процесуальні блокери — генерація заблокована
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  {criticals.map((b, i) => (
                    <div key={i} style={{ display: "flex", gap: "8px", alignItems: "flex-start", fontSize: "13px" }}>
                      <span style={{ padding: "2px 8px", borderRadius: "6px", fontSize: "11px", fontWeight: 700, background: "rgba(239,68,68,0.18)", color: "var(--danger)", flexShrink: 0 }}>
                        {b.code}
                      </span>
                      <span style={{ color: "var(--text-secondary)" }}>{b.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {warnings.length > 0 && (
              <div className="card-elevated" style={{ padding: "14px 18px", borderLeft: "3px solid var(--warning)", background: "rgba(245,158,11,0.06)" }}>
                <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--warning)", marginBottom: "8px" }}>
                  Попередження — генерацію дозволено, але є зауваження
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  {warnings.map((b, i) => (
                    <div key={i} style={{ display: "flex", gap: "8px", alignItems: "flex-start", fontSize: "13px" }}>
                      <span style={{ padding: "2px 8px", borderRadius: "6px", fontSize: "11px", fontWeight: 700, background: "rgba(245,158,11,0.18)", color: "var(--warning)", flexShrink: 0 }}>
                        {b.code}
                      </span>
                      <span style={{ color: "var(--text-secondary)" }}>{b.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {infos.length > 0 && (
              <div className="card-elevated" style={{ padding: "14px 18px", borderLeft: "3px solid #60a5fa", background: "rgba(96,165,250,0.06)" }}>
                <div style={{ fontSize: "13px", fontWeight: 600, color: "#60a5fa", marginBottom: "8px" }}>
                  Рекомендації
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  {infos.map((b, i) => (
                    <div key={i} style={{ display: "flex", gap: "8px", alignItems: "flex-start", fontSize: "13px" }}>
                      <span style={{ padding: "2px 8px", borderRadius: "6px", fontSize: "11px", fontWeight: 600, background: "rgba(96,165,250,0.12)", color: "#60a5fa", flexShrink: 0 }}>
                        {b.code}
                      </span>
                      <span style={{ color: "var(--text-secondary)" }}>{b.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        );
      })()}

      {selectedCaseDetail && (
        <div className="card-elevated" style={{ padding: "16px 18px", border: "1px solid rgba(96,165,250,0.18)", background: "rgba(96,165,250,0.06)" }}>
          <div style={{ fontSize: "12px", color: "#93c5fd", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "6px" }}>Контекст справи</div>
          <div style={{ fontSize: "15px", fontWeight: 700, color: "#fff" }}>{selectedCaseDetail.title}</div>
          <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "6px" }}>
            {selectedCaseDetail.case_number ? `Номер: ${selectedCaseDetail.case_number}` : "Номер справи не заповнений"}
            {caseDecisions.length ? ` • Рішень з бази: ${caseDecisions.length}` : " • Рішень з локальної бази поки не знайдено"}
          </div>
        </div>
      )}

      <section style={{ display: "grid", gridTemplateColumns: result ? "1.05fr 0.95fr" : "1fr", gap: "24px" }}>
        <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div className="card-elevated" style={{ padding: "24px" }}>
            <h3 style={{ fontSize: "16px", marginBottom: "14px", color: "#fff" }}>Якість генерації (Deep Mode)</h3>
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                type="button"
                className={`btn ${genMode === "standard" ? "btn-primary" : "btn-secondary"}`}
                style={{ flex: 1 }}
                onClick={() => setGenMode("standard")}
              >
                Standard
              </button>
              <button
                type="button"
                className={`btn ${genMode === "deep" ? "btn-primary" : "btn-secondary"}`}
                style={{ flex: 1 }}
                onClick={() => setGenMode("deep")}
              >
                Deep Mode
              </button>
            </div>
            <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "6px", marginBottom: "20px" }}>
              {genMode === "deep" 
                ? "Використовує GPT-4o / Claude 3.5 Sonnet з розширеними юридичними інструкціями."
                : "Стандартна генерація. Підходить для простих документів."}
            </p>

            <h3 style={{ fontSize: "16px", marginBottom: "14px", color: "#fff" }}>Стиль аргументації (Tone Selection)</h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
              {[
                { id: "persuasive", label: "Переконливий", icon: "🤝" },
                { id: "aggressive", label: "Агресивний", icon: "⚔️" },
                { id: "conciliatory", label: "Мирний", icon: "🕊️" },
                { id: "analytical", label: "Аналітичний", icon: "🧠" },
              ].map((style) => (
                <button
                  key={style.id}
                  type="button"
                  className={`btn ${genStyle === style.id ? "btn-primary" : "btn-secondary"}`}
                  style={{ fontSize: "12px", padding: "10px" }}
                  onClick={() => setGenStyle(style.id as any)}
                >
                  <span style={{ marginRight: "6px" }}>{style.icon}</span>
                  {style.label}
                </button>
              ))}
            </div>

            <h3 style={{ fontSize: "16px", marginTop: "20px", marginBottom: "14px", color: "#fff" }}>Мова документа</h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
              {([
                { id: "uk", label: "Українська", flag: "🇺🇦" },
                { id: "en", label: "English", flag: "🇬🇧" },
                { id: "pl", label: "Polski", flag: "🇵🇱" },
                { id: "de", label: "Deutsch", flag: "🇩🇪" },
              ] as const).map((lang) => (
                <button
                  key={lang.id}
                  type="button"
                  className={`btn ${targetLanguage === lang.id ? "btn-primary" : "btn-secondary"}`}
                  style={{ fontSize: "12px", padding: "10px" }}
                  onClick={() => setTargetLanguage(lang.id)}
                >
                  <span style={{ marginRight: "6px" }}>{lang.flag}</span>
                  {lang.label}
                </button>
              ))}
            </div>
          </div>
          
          <div className="card-elevated" style={{ padding: "20px" }}>
            <h2 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "14px", color: "var(--text-primary)" }}>0. Судова справа</h2>
            <div className="form-group">
              <label className="form-label" htmlFor="caseSelect">
                Пов'язати з існуючою справою
              </label>
              <select
                id="caseSelect"
                className="form-select"
                value={selectedCaseId}
                onChange={(event) => setSelectedCaseId(event.target.value)}
              >
                <option value="">Без прив'язки до справи (персональний документ)</option>
                {cases.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title} {c.case_number ? `(${c.case_number})` : ""}
                  </option>
                ))}
              </select>
            </div>
            <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "6px" }}>
              Це дозволить автоматично групувати документ у розділі "Кейси".
            </p>
          </div>

          <div className="card-elevated" style={{ padding: "24px", border: "1px solid var(--gold-400)", backgroundColor: "rgba(212, 168, 67, 0.05)" }}>
            <h3 style={{ fontSize: "16px", marginBottom: "14px", color: "var(--gold-400)" }}>🎁 Режим генерації</h3>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
              <button
                type="button"
                className={`btn ${!isBundleMode ? "btn-primary" : "btn-secondary"}`}
                style={{ flex: "1 1 auto" }}
                onClick={() => setIsBundleMode(false)}
              >
                Окремий документ
              </button>
              <button
                type="button"
                className={`btn ${isBundleMode ? "btn-primary" : "btn-secondary"}`}
                style={{ flex: "1 1 auto" }}
                onClick={() => setIsBundleMode(true)}
              >
                Пакет документів
              </button>
            </div>
          </div>

          <div className="card-elevated" style={{ padding: "20px" }}>
            <h2 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "14px", color: "var(--text-primary)" }}>1. Тип документа / Пакета</h2>
            {!isBundleMode ? (
              <div className="form-group">
                <label className="form-label" htmlFor="documentType">
                  Тип документа
                </label>
                <select
                  id="documentType"
                  className="form-select"
                  value={selectedDocType}
                  onChange={(event) => setSelectedDocType(event.target.value)}
                >
                  {docTypes.map((item) => (
                    <option key={item.doc_type} value={item.doc_type}>
                      {item.title}
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <div className="form-group">
                <label className="form-label">Оберіть пакет документів</label>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {[
                    { id: "civil_set", title: "Цивільний позов (Повний пакет)", desc: "Позов + Забезпечення + Докази" },
                    { id: "divorce_set", title: "Розлучення та майно", desc: "Два взаємопов'язані позови" }
                  ].map(bundle => (
                    <label key={bundle.id} style={{ display: "flex", alignItems: "center", gap: "10px", padding: "12px", background: "rgba(255,255,255,0.05)", borderRadius: "12px", cursor: "pointer", border: selectedBundle === bundle.id ? "1px solid var(--gold-500)" : "1px solid transparent" }}>
                      <input type="radio" name="bundle" checked={selectedBundle === bundle.id} onChange={() => setSelectedBundle(bundle.id as any)} />
                      <div>
                        <div style={{ fontWeight: 600, color: "#fff" }}>{bundle.title}</div>
                        <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>{bundle.desc}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {selectedDocMeta && (
              <div
                className="card-elevated"
                style={{ marginTop: "14px", padding: "14px", background: "rgba(255,255,255,0.02)" }}
              >
                <div style={{ fontWeight: 700, color: "#fff", marginBottom: "6px" }}>{selectedDocMeta.title}</div>
                <div style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                  Категорія: {selectedDocMeta.category}. Процедура: {selectedDocMeta.procedure}.
                </div>
              </div>
            )}
          </div>

          <div className="card-elevated" style={{ padding: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "center", marginBottom: "14px" }}>
              <h2 style={{ fontSize: "18px", fontWeight: 700, color: "var(--text-primary)" }}>2. Поля документа</h2>
              <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                Обов'язкових: {requiredFilled}/{requiredTotal}
              </span>
            </div>

            {schemaLoading ? (
              <div style={{ textAlign: "center", padding: "20px" }}>
                <span className="spinner" />
              </div>
            ) : schema.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                {schema.map((field) => (
                  <div key={field.key} className="form-group">
                    <label className="form-label" htmlFor={field.key}>
                      {prettifyFieldLabel(field.key)}
                      {field.required && <span style={{ color: "var(--danger)", marginLeft: "4px" }}>*</span>}
                    </label>
                    {field.type === "select" ? (
                      <select
                        id={field.key}
                        aria-label={field.key}
                        className="form-select"
                        value={formData[field.key] ?? ""}
                        onChange={(event) => setFormData((previous) => ({ ...previous, [field.key]: event.target.value }))}
                      >
                        <option value="">Оберіть значення</option>
                        {(field.options ?? []).map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        id={field.key}
                        aria-label={field.key}
                        className="form-input"
                        type={field.type === "number" ? "number" : field.type === "date" ? "date" : "text"}
                        value={formData[field.key] ?? ""}
                        onChange={(event) => setFormData((previous) => ({ ...previous, [field.key]: event.target.value }))}
                        placeholder={field.type === "array" ? "значення 1, значення 2" : prettifyFieldLabel(field.key)}
                      />
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: "var(--text-muted)" }}>Схема документа ще не завантажилась.</div>
            )}
          </div>

          <div className="card-elevated" style={{ padding: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", marginBottom: "14px" }}>
              <h2 style={{ fontSize: "18px", fontWeight: 700, color: "var(--text-primary)" }}>3. Юридичний контекст</h2>
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => void loadDigest()}>
                  Завантажити свіжий digest
                </button>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setExtraContext("")}>
                  Очистити контекст
                </button>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "12px", marginBottom: "16px" }}>
              <SummaryStat label="Saved digests" value={savedDigests.length} />
              <SummaryStat label="Прецеденти" value={selectedPrecedentIds.length} />
              <SummaryStat label="Fresh digest" value={includeDigest ? "on" : "off"} />
            </div>

            {/* Knowledge Base Integration */}
            <div className="form-group" style={{ marginBottom: "20px" }}>
              <label className="form-label" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                Бібліотека прецедентів (Knowledge Base)
                {kbLoading && <span className="spinner" style={{ width: 12, height: 12 }} />}
              </label>
              <div style={{ 
                display: "flex", 
                flexDirection: "column", 
                gap: "8px", 
                maxHeight: "160px", 
                overflowY: "auto", 
                padding: "12px", 
                background: "rgba(255,255,255,0.03)", 
                borderRadius: "12px",
                border: "1px solid rgba(255,255,255,0.05)"
              }}>
                {knowledgeBase.length === 0 && !kbLoading && (
                  <div style={{ fontSize: "12px", color: "var(--text-muted)", textAlign: "center", padding: "10px" }}>
                    У базі знань поки порожньо. <Link href="/dashboard/knowledge-base" style={{ color: "var(--gold-500)" }}>Додати прецедент</Link>
                  </div>
                )}
                {knowledgeBase.map((entry) => (
                  <label key={entry.id} style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px", cursor: "pointer", padding: "4px 0" }}>
                    <input
                      type="checkbox"
                      checked={selectedPrecedentIds.includes(entry.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedPrecedentIds([...selectedPrecedentIds, entry.id]);
                        } else {
                          setSelectedPrecedentIds(selectedPrecedentIds.filter(id => id !== entry.id));
                        }
                      }}
                      style={{ accentColor: "var(--gold-500)", width: "16px", height: "16px" }}
                    />
                    <span style={{ color: selectedPrecedentIds.includes(entry.id) ? "var(--gold-500)" : "var(--text-secondary)" }}>
                      {entry.title} <span style={{ opacity: 0.5, fontSize: "11px" }}>· {entry.category}</span>
                    </span>
                  </label>
                ))}
              </div>
              <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "8px" }}>
                Обрані прецеденти будуть використані як <strong>Gold Standard</strong> для стилю та структури.
              </p>
            </div>

            <div className="card-elevated" style={{ padding: "16px", marginBottom: "20px", border: "1px solid rgba(212,168,67,0.15)", background: "rgba(212,168,67,0.03)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <h4 style={{ fontSize: "14px", fontWeight: 800, color: "var(--gold-400)", marginBottom: "4px" }}>💎 AI Smart Research</h4>
                  <p style={{ fontSize: "11px", color: "var(--text-muted)", margin: 0 }}>
                    Автоматичний пошук практики Верховного Суду під ваші факти.
                  </p>
                </div>
                <button
                  type="button"
                  className="btn btn-gold btn-sm"
                  style={{ whiteSpace: "nowrap" }}
                  disabled={isResearching || loading}
                  onClick={handleSmartResearch}
                >
                  {isResearching ? (
                    <>
                      <span className="spinner" style={{ width: 12, height: 12 }} /> Пошук...
                    </>
                  ) : (
                    "Знайти практику"
                  )}
                </button>
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: "14px" }}>
              <label className="form-label" htmlFor="savedDigest">
                Saved digest (Case Law)
              </label>
              <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                <select
                  id="savedDigest"
                  aria-label="Saved digest"
                  className="form-select"
                  value={selectedSavedDigestId}
                  onChange={(event) => {
                    setSelectedSavedDigestId(event.target.value);
                    if (!event.target.value) {
                      setUseSelectedSavedDigest(false);
                    }
                  }}
                  disabled={savedDigestLoading}
                >
                  <option value="">Оберіть збережений digest</option>
                  {savedDigests.map((item) => (
                    <option key={item.id} value={item.id}>
                      {(item.title?.trim() || `Digest ${item.created_at}`)} ({item.item_count})
                    </option>
                  ))}
                </select>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => void loadSelectedSavedDigest()} disabled={!selectedSavedDigestId}>
                  Додати
                </button>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="extraContext">
                Додаткові інструкції / Довільний контекст
              </label>
              <textarea
                id="extraContext"
                aria-label="Additional legal context"
                className="form-textarea"
                value={extraContext}
                onChange={(event) => setExtraContext(event.target.value)}
                placeholder="Наприклад: 'Зроби акцент на порушенні термінів поставки'..."
                style={{ minHeight: "100px" }}
              />
            </div>

            <div className="flex items-center gap-2 mt-2">
              <input
                id="includeDigest"
                type="checkbox"
                checked={includeDigest}
                onChange={(event) => setIncludeDigest(event.target.checked)}
                style={{ accentColor: "var(--gold-500)", width: "16px", height: "16px" }}
              />
              <label htmlFor="includeDigest" className="text-sm text-secondary">
                Автоматично додати свіжий digest у запит.
              </label>
            </div>
          </div>

          <button type="submit" className="btn btn-primary btn-lg" disabled={loading}>
            {loading ? (
              <>
                <span className="spinner" style={{ width: 16, height: 16 }} /> Генерація...
              </>
            ) : (
              "Згенерувати"
            )}
          </button>
          {loading && genProgress && (
            <div style={{ marginTop: "10px", padding: "10px 14px", background: "rgba(212,168,67,0.08)", borderRadius: "12px", fontSize: "13px", color: "var(--gold-400)", fontWeight: 600 }}>
              {genProgress}
            </div>
          )}
        </form>

        {result && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {"bundle_id" in result && (
              <div className="card-elevated" style={{ padding: "16px", border: "1px solid var(--gold-400)" }}>
                <h3 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "12px", color: "var(--gold-400)" }}>📦 Весь пакет ({result.total_count})</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  {result.items.map((item: GenerateResponse, idx: number) => (
                    <button
                      key={item.document_id}
                      className={`btn ${activeBundleItemIndex === idx ? "btn-primary" : "btn-secondary"} btn-sm`}
                      style={{ justifyContent: "flex-start", textAlign: "left" }}
                      onClick={() => setActiveBundleItemIndex(idx)}
                    >
                      {idx + 1}. {item.title}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="card-elevated" style={{ padding: "20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px", gap: "10px" }}>
                <h2 style={{ fontSize: "18px", fontWeight: 700, color: "var(--text-primary)" }}>
                  {displayResult?.title || "Результат"}
                </h2>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  <span className="badge badge-success">Ready</span>
                  {displayResult?.used_ai && <span className="badge badge-blue">AI {displayResult.ai_model ?? ""}</span>}
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "12px", marginBottom: "16px" }}>
                <SummaryStat label="Document ID" value={displayResult?.document_id || "-"} />
                <SummaryStat label="Створено" value={displayResult?.created_at || "-"} />
                <SummaryStat label="Case-law refs" value={displayResult?.case_law_refs?.length ?? 0} />
                <SummaryStat label="Validation checks" value={displayResult?.processual_validation_checks?.length ?? 0} />
              </div>

              <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "16px" }}>
                Quality guard: <strong style={{ color: "#fff" }}>{displayResult?.quality_guard_applied ? "Applied" : "Skipped"}</strong>
              </div>

              <Link href="/dashboard/documents" className="btn btn-primary btn-sm">
                Відкрити всі документи
              </Link>
            </div>

            {displayResult?.case_law_refs && displayResult.case_law_refs.length > 0 && (
              <div className="card-elevated" style={{ padding: "20px" }}>
                <h3 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "12px", color: "var(--text-primary)" }}>
                  Практика, яку підключено
                </h3>
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {displayResult.case_law_refs.map((item: any) => (
                    <div key={item.id} className="card-elevated" style={{ padding: "12px 14px" }}>
                      <div style={{ fontWeight: 700, color: "#fff", marginBottom: "4px" }}>
                        {item.case_number || item.decision_id}
                      </div>
                      <div style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                        {item.court_name || item.source} · relevance {item.relevance_score}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {displayResult?.pre_generation_gate_checks && displayResult.pre_generation_gate_checks.length > 0 && (
              <div className="card-elevated" style={{ padding: "20px" }}>
                <h3 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "12px", color: "var(--text-primary)" }}>
                  Pre-generation checks
                </h3>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  {displayResult.pre_generation_gate_checks.map((item: any) => (
                    <div key={item.code} style={{ display: "flex", gap: "8px", alignItems: "flex-start", fontSize: "13px" }}>
                      <span
                        className={`badge ${
                          item.status === "pass" ? "badge-success" : item.status === "warn" ? "badge-warning" : "badge-danger"
                        } badge`}
                        style={{ minWidth: "52px", justifyContent: "center" }}
                      >
                        {item.status}
                      </span>
                      <span className="text-secondary">{item.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {displayResult?.processual_validation_checks && displayResult.processual_validation_checks.length > 0 && (() => {
              const checks = displayResult.processual_validation_checks;
              const criticalFails = checks.filter(c => c.status !== "pass" && (!c.severity || c.severity === "critical"));
              const warningFails  = checks.filter(c => c.status !== "pass" && c.severity === "warning");
              const passes        = checks.filter(c => c.status === "pass");
              const borderColor = criticalFails.length > 0 ? "var(--danger)" : warningFails.length > 0 ? "var(--warning)" : "var(--success)";
              return (
                <div className="card-elevated" style={{ padding: "20px", borderLeft: `3px solid ${borderColor}` }}>
                  <h3 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "12px", color: "var(--text-primary)" }}>
                    Процесуальна валідація
                    {criticalFails.length > 0 && (
                      <span style={{ marginLeft: "8px", fontSize: "12px", fontWeight: 700, color: "var(--danger)" }}>
                        {criticalFails.length} критичних
                      </span>
                    )}
                    {warningFails.length > 0 && (
                      <span style={{ marginLeft: "8px", fontSize: "12px", fontWeight: 600, color: "var(--warning)" }}>
                        {warningFails.length} попереджень
                      </span>
                    )}
                  </h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    {checks.map((item, idx) => {
                      const isFailing = item.status !== "pass";
                      const sev = item.severity ?? (isFailing ? "critical" : undefined);
                      const statusClass = item.status === "pass"
                        ? "badge-success"
                        : sev === "critical" ? "badge-danger"
                        : sev === "warning" ? "badge-warning"
                        : "badge-secondary";
                      return (
                        <div key={`${item.code}-${idx}`} style={{ display: "flex", gap: "8px", alignItems: "flex-start", fontSize: "13px" }}>
                          <span className={`badge ${statusClass}`} style={{ minWidth: "52px", justifyContent: "center" }}>
                            {item.status}
                          </span>
                          {isFailing && sev && (
                            <span style={{
                              padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: 700, flexShrink: 0,
                              background: sev === "critical" ? "rgba(239,68,68,0.18)" : sev === "warning" ? "rgba(245,158,11,0.18)" : "rgba(96,165,250,0.12)",
                              color: sev === "critical" ? "var(--danger)" : sev === "warning" ? "var(--warning)" : "#60a5fa",
                              textTransform: "uppercase",
                            }}>
                              {sev}
                            </span>
                          )}
                          <span className="text-secondary">{item.message}</span>
                        </div>
                      );
                    })}
                  </div>
                  {passes.length > 0 && criticalFails.length + warningFails.length > 0 && (
                    <div style={{ marginTop: "8px", fontSize: "12px", color: "var(--text-muted)" }}>
                      {passes.length} перевірок пройдено успішно
                    </div>
                  )}
                </div>
              );
            })()}

            {displayResult?.generated_text && (
              <div className="card-elevated" style={{ padding: "20px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <h3 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
                    Згенерований текст
                  </h3>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => {
                        void navigator.clipboard.writeText(displayResult.generated_text);
                        setInfo("Текст скопійовано в буфер обміну.");
                      }}
                    >
                      Копіювати
                    </button>
                    <button
                      type="button"
                      className={`btn ${isSavedToKb ? "btn-secondary" : "btn-gold"} btn-sm`}
                      disabled={savingToKb || isSavedToKb}
                      onClick={handleSaveToKB}
                    >
                      {savingToKb ? (
                        <>
                          <span className="spinner" style={{ width: 12, height: 12 }} /> Збереження...
                        </>
                      ) : isSavedToKb ? (
                        "Збережено в базу"
                      ) : (
                        "Зберегти як прецедент"
                      )}
                    </button>
                  </div>
                </div>
                <div
                  style={{
                    maxHeight: "400px",
                    overflow: "auto",
                    fontSize: "13px",
                    lineHeight: 1.7,
                    color: "var(--text-secondary)",
                    whiteSpace: "pre-wrap",
                    background: "rgba(0,0,0,0.2)",
                    padding: "16px",
                    borderRadius: "8px",
                  }}
                >
                  {displayResult.generated_text}
                </div>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

export default function GeneratePage() {
  return (
    <Suspense fallback={null}>
      <GeneratePageInner />
    </Suspense>
  );
}
