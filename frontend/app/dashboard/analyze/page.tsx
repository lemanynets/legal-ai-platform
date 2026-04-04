"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import React, { FormEvent, Suspense, useEffect, useState } from "react";

import { getToken, getUserId } from "@/lib/auth";
import {
  analyzeIntake,
  analyzeIntakeStream,
  analyzeGdprCompliance,
  analyzePrecedentMap,
  createCase,
  createStrategyBlueprint,
  runJudgeSimulation,
  autoProcessDecisionAnalysis,
  type AnalysisComment,
  type ContractAnalysisHistoryResponse,
  type GdprComplianceResponse,
  type ContractAnalysisItem,
  type DocumentIntakeResponse,
  type StreamEvent,
  type PrecedentMapResponse,
  type StrategyBlueprintResponse,
  type JudgeSimulationResponse,
  type DecisionAnalysisResponse,
  getCase,
  getCases,
  getContractAnalysisHistory,
  getAnalysisComments,
  createAnalysisComment,
  deleteAnalysisComment,
  processContractAnalysis,
  type Case,
} from "@/lib/api";

const CASE_LAW_SEED_KEY = "legal_ai_case_law_seed_v1";

// ---------------------------------------------------------------------------
// Litigation tab — strategy pipeline (intake → precedent map → blueprint → judge)
// ---------------------------------------------------------------------------
function LitigationTab() {
  const [file, setFile] = useState<File | null>(null);
  const [decisionFile, setDecisionFile] = useState<File | null>(null);
  const [stage, setStage] = useState<"" | "intake" | "precedent" | "strategy" | "judge" | "decision">("") ;
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [intake, setIntake] = useState<DocumentIntakeResponse | null>(null);
  const [precedentMap, setPrecedentMap] = useState<PrecedentMapResponse | null>(null);
  const [strategy, setStrategy] = useState<StrategyBlueprintResponse | null>(null);
  const [judgeResult, setJudgeResult] = useState<JudgeSimulationResponse | null>(null);
  const [decisionResult, setDecisionResult] = useState<DecisionAnalysisResponse | null>(null);

  const step = !intake ? 1 : !precedentMap ? 2 : !strategy ? 3 : 4;

  async function handleIntake(e: FormEvent) {
    e.preventDefault();
    if (!file) { setError("Оберіть файл для аналізу."); return; }
    setStage("intake"); setError(""); setInfo("");
    try {
      const res = await analyzeIntake({ file }, getToken(), getUserId());
      setIntake(res);
      setPrecedentMap(null); setStrategy(null); setJudgeResult(null);
      setInfo(`Intake: ${res.classified_type} — ${res.subject_matter}`);
    } catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setStage(""); }
  }

  async function handlePrecedentMap() {
    if (!intake) return;
    setStage("precedent"); setError(""); setInfo("");
    try {
      const res = await analyzePrecedentMap(intake.id, { limit: 15 }, getToken(), getUserId());
      setPrecedentMap(res);
      setInfo(`Прецедентна карта: ${res.refs.length} рішень.`);
    } catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setStage(""); }
  }

  async function handleStrategy() {
    if (!intake) return;
    setStage("strategy"); setError(""); setInfo("");
    try {
      const res = await createStrategyBlueprint(
        { intake_id: intake.id, regenerate: true, refresh_precedent_map: false, precedent_limit: 15 },
        getToken(), getUserId()
      );
      setStrategy(res);
      setInfo("Стратегічний план готовий.");
    } catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setStage(""); }
  }

  async function handleJudge() {
    if (!strategy) return;
    setStage("judge"); setError(""); setInfo("");
    try {
      const res = await runJudgeSimulation({ strategy_id: strategy.id }, getToken());
      setJudgeResult(res);
      setInfo("Симуляцію судді завершено.");
    } catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setStage(""); }
  }

  async function handleDecisionAnalysis(e: FormEvent) {
    e.preventDefault();
    if (!decisionFile) { setError("Оберіть файл рішення суду."); return; }
    setStage("decision"); setError(""); setInfo("");
    try {
      const res = await autoProcessDecisionAnalysis({ file: decisionFile }, getToken(), getUserId());
      setDecisionResult(res);
      setInfo("Аналіз рішення завершено.");
    } catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setStage(""); }
  }

  const isLoading = Boolean(stage);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {error && (
        <div className="preflight-block">
          <span style={{ color: "var(--danger)" }}>Помилка: {error}</span>
        </div>
      )}
      {info && (
        <div className="card-elevated" style={{ padding: "12px 16px", borderLeft: "3px solid var(--success)", color: "var(--success)" }}>
          {info}
        </div>
      )}

      {/* Step indicators */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px" }}>
        {[
          { num: 1, label: "Intake аналіз", active: step === 1, done: step > 1 },
          { num: 2, label: "Прецедентна карта", active: step === 2, done: step > 2 },
          { num: 3, label: "Стратегічний план", active: step === 3, done: step > 3 },
          { num: 4, label: "Симуляція судді", active: step === 4, done: false },
        ].map(({ num, label, active, done }) => (
          <div key={num} className="card-elevated" style={{
            padding: "14px 16px",
            border: `1px solid ${done ? "rgba(16,185,129,0.3)" : active ? "rgba(212,168,67,0.3)" : "rgba(255,255,255,0.05)"}`,
            background: done ? "rgba(16,185,129,0.06)" : active ? "rgba(212,168,67,0.06)" : "rgba(255,255,255,0.02)",
          }}>
            <div style={{ fontSize: "10px", fontWeight: 800, textTransform: "uppercase", color: done ? "var(--success)" : active ? "var(--gold-400)" : "var(--text-muted)", marginBottom: "6px" }}>Крок {num}</div>
            <div style={{ fontWeight: 600, color: "#fff", fontSize: "13px" }}>{label}</div>
            <div style={{ fontSize: "11px", color: done ? "var(--success)" : active ? "var(--gold-400)" : "var(--text-muted)", marginTop: "4px" }}>
              {done ? "Готово" : active ? "Поточний" : "Очікує"}
            </div>
          </div>
        ))}
      </div>

      {/* Intake form */}
      <div className="card-elevated" style={{ padding: "24px" }}>
        <h3 style={{ marginBottom: "16px", fontSize: "16px" }}>Крок 1: Стратегічний Intake</h3>
        <form onSubmit={handleIntake} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div>
            <label className="form-label">Файл документа (PDF, DOCX, TXT)</label>
            <input type="file" className="form-input" accept=".pdf,.docx,.doc,.txt"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </div>
          <button type="submit" className="btn btn-primary" disabled={isLoading} style={{ alignSelf: "flex-start" }}>
            {stage === "intake" ? "Аналізую..." : "Запустити Intake"}
          </button>
        </form>
        {intake && (
          <div style={{ marginTop: "16px", display: "flex", flexDirection: "column", gap: "8px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "10px", marginTop: "8px" }}>
              {[
                ["Тип документа", intake.classified_type],
                ["Предмет", intake.subject_matter],
                ["Роль клієнта", intake.primary_party_role],
              ].map(([label, val]) => (
                <div key={label} style={{ background: "rgba(255,255,255,0.03)", borderRadius: "8px", padding: "10px" }}>
                  <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "4px" }}>{label}</div>
                  <div style={{ color: "#fff", fontSize: "13px", fontWeight: 600 }}>{val || "—"}</div>
                </div>
              ))}
            </div>
            <button className="btn btn-secondary" disabled={isLoading} style={{ alignSelf: "flex-start", marginTop: "8px" }}
              onClick={handlePrecedentMap}>
              {stage === "precedent" ? "Будую карту..." : "Крок 2: Побудувати прецедентну карту"}
            </button>
          </div>
        )}
      </div>

      {/* Precedent map results */}
      {precedentMap && (
        <div className="card-elevated" style={{ padding: "24px" }}>
          <h3 style={{ marginBottom: "16px", fontSize: "16px" }}>Прецедентна карта ({precedentMap.refs.length} рішень)</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "240px", overflowY: "auto" }}>
            {precedentMap.refs.slice(0, 10).map((ref, i) => (
              <div key={i} style={{ background: "rgba(255,255,255,0.03)", borderRadius: "8px", padding: "10px 12px" }}>
                <div style={{ fontWeight: 600, color: "#fff", fontSize: "13px" }}>{ref.case_number || ref.decision_id}</div>
                <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>{ref.court_name} · {ref.relevance_score != null ? `Релевантність: ${ref.relevance_score}` : ""}</div>
              </div>
            ))}
          </div>
          <button className="btn btn-secondary" disabled={isLoading} style={{ alignSelf: "flex-start", marginTop: "12px" }}
            onClick={handleStrategy}>
            {stage === "strategy" ? "Будую стратегію..." : "Крок 3: Стратегічний план"}
          </button>
        </div>
      )}

      {/* Strategy blueprint */}
      {strategy && (
        <div className="card-elevated" style={{ padding: "24px" }}>
          <h3 style={{ marginBottom: "16px", fontSize: "16px" }}>Стратегічний план</h3>
          {strategy.win_probability != null && (
            <div style={{ marginBottom: "12px", padding: "10px 14px", background: "rgba(212,168,67,0.08)", borderRadius: "8px", border: "1px solid rgba(212,168,67,0.2)" }}>
              <span style={{ color: "var(--gold-400)", fontWeight: 700 }}>Прогноз перемоги: {strategy.win_probability}%</span>
            </div>
          )}
          {strategy.swot_analysis?.strengths && strategy.swot_analysis.strengths.length > 0 && (
            <div style={{ marginBottom: "12px" }}>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "6px", textTransform: "uppercase" }}>Сильні сторони</div>
              <ul style={{ paddingLeft: "18px", display: "flex", flexDirection: "column", gap: "4px" }}>
                {strategy.swot_analysis.strengths.slice(0, 4).map((arg, i) => (
                  <li key={i} style={{ fontSize: "13px", color: "var(--text-secondary)" }}>{arg}</li>
                ))}
              </ul>
            </div>
          )}
          <button className="btn btn-secondary" disabled={isLoading} style={{ alignSelf: "flex-start" }}
            onClick={handleJudge}>
            {stage === "judge" ? "Симулюю суддю..." : "Крок 4: Симуляція судді"}
          </button>
        </div>
      )}

      {/* Judge simulation */}
      {judgeResult && (
        <div className="card-elevated" style={{ padding: "24px" }}>
          <h3 style={{ marginBottom: "16px", fontSize: "16px" }}>Симуляція судді</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={{ padding: "12px", background: "rgba(255,255,255,0.03)", borderRadius: "8px" }}>
              <div style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "4px" }}>Прогноз вердикту</div>
              <div style={{ color: "var(--gold-400)", fontWeight: 700, fontSize: "18px" }}>{judgeResult.verdict_probability}%</div>
            </div>
            <div style={{ padding: "12px", background: "rgba(255,255,255,0.03)", borderRadius: "8px" }}>
              <div style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "4px" }}>Персона судді</div>
              <div style={{ color: "#fff", fontSize: "13px" }}>{judgeResult.judge_persona}</div>
            </div>
            {judgeResult.key_vulnerabilities.length > 0 && (
              <div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "6px", textTransform: "uppercase" }}>Ключові вразливості</div>
                <ul style={{ paddingLeft: "18px", display: "flex", flexDirection: "column", gap: "4px" }}>
                  {judgeResult.key_vulnerabilities.slice(0, 4).map((c, i) => (
                    <li key={i} style={{ fontSize: "13px", color: "var(--text-secondary)" }}>{c}</li>
                  ))}
                </ul>
              </div>
            )}
            {judgeResult.suggested_corrections.length > 0 && (
              <div>
                <div style={{ fontSize: "12px", color: "var(--success)", marginBottom: "6px", textTransform: "uppercase" }}>Рекомендації щодо виправлень</div>
                <ul style={{ paddingLeft: "18px", display: "flex", flexDirection: "column", gap: "4px" }}>
                  {judgeResult.suggested_corrections.slice(0, 4).map((c, i) => (
                    <li key={i} style={{ fontSize: "13px", color: "var(--text-secondary)" }}>{c}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Decision analysis section */}
      <div className="card-elevated" style={{ padding: "24px", borderTop: "1px solid rgba(255,255,255,0.05)" }}>
        <h3 style={{ marginBottom: "8px", fontSize: "16px" }}>Аналіз судового рішення</h3>
        <p style={{ color: "var(--text-secondary)", fontSize: "13px", marginBottom: "16px" }}>
          Завантажте наявне рішення суду для детального розбору та рекомендацій.
        </p>
        <form onSubmit={handleDecisionAnalysis} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div>
            <label className="form-label">Файл рішення (PDF, DOCX, TXT)</label>
            <input type="file" className="form-input" accept=".pdf,.docx,.doc,.txt"
              onChange={(e) => setDecisionFile(e.target.files?.[0] ?? null)} />
          </div>
          <button type="submit" className="btn btn-primary" disabled={isLoading} style={{ alignSelf: "flex-start" }}>
            {stage === "decision" ? "Аналізую рішення..." : "Аналізувати рішення"}
          </button>
        </form>
        {decisionResult && (
          <div style={{ marginTop: "16px", display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={{ padding: "12px", background: "rgba(255,255,255,0.03)", borderRadius: "8px" }}>
              <div style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "4px" }}>Резюме спору</div>
              <div style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{decisionResult.dispute_summary}</div>
            </div>
            {decisionResult.final_conclusion && (
              <div style={{ padding: "12px", background: "rgba(16,185,129,0.05)", borderRadius: "8px", border: "1px solid rgba(16,185,129,0.2)" }}>
                <div style={{ fontSize: "11px", color: "var(--success)", textTransform: "uppercase", marginBottom: "4px" }}>Висновок</div>
                <div style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{decisionResult.final_conclusion}</div>
              </div>
            )}
            {decisionResult.cassation_vulnerabilities.length > 0 && (
              <div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "6px", textTransform: "uppercase" }}>Вразливості для касації</div>
                <ul style={{ paddingLeft: "18px", display: "flex", flexDirection: "column", gap: "4px" }}>
                  {decisionResult.cassation_vulnerabilities.slice(0, 5).map((r, i) => (
                    <li key={i} style={{ fontSize: "13px", color: "var(--text-secondary)" }}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function riskTone(level?: string | null) {
  const value = String(level || "").toLowerCase();
  if (value === "high") return { color: "var(--danger)", background: "rgba(239,68,68,0.12)" };
  if (value === "medium") return { color: "var(--warning)", background: "rgba(245,158,11,0.12)" };
  return { color: "var(--success)", background: "rgba(16,185,129,0.12)" };
}

function buildCaseLawSeed(result: DocumentIntakeResponse): string {
  return [result.subject_matter, result.classified_type, result.primary_party_role].filter(Boolean).join(" ").trim();
}

/**
 * Runs `fn` over all `items` with at most `limit` concurrent calls at a time.
 * Processes items in order, waits for each chunk before starting the next.
 */
async function runWithConcurrency<T>(
  items: T[],
  limit: number,
  fn: (item: T, index: number) => Promise<void>
): Promise<void> {
  for (let i = 0; i < items.length; i += limit) {
    await Promise.all(items.slice(i, i + limit).map((item, j) => fn(item, i + j)));
  }
}

function AnalyzePageInner() {
  const searchParams = useSearchParams();
  const mode = searchParams.get("mode") || "quick";

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [quickFileName, setQuickFileName] = useState("");
  const [quickText, setQuickText] = useState("");
  const [intakeResults, setIntakeResults] = useState<DocumentIntakeResponse[]>([]);
  const [activeResultIndex, setActiveResultIndex] = useState(0);
  const [quickResult, setQuickResult] = useState<ContractAnalysisItem | null>(null);
  const [history, setHistory] = useState<ContractAnalysisHistoryResponse | null>(null);
  const [loadingIntake, setLoadingIntake] = useState(false);
  const [loadingQuick, setLoadingQuick] = useState(false);
  const [error, setError] = useState("");
  const [intakeErrors, setIntakeErrors] = useState<Record<string, string>>({});
  const [activeIssueIndex, setActiveIssueIndex] = useState<number | null>(null);
  const [isEditingText, setIsEditingText] = useState(false);
  const [editedText, setEditedText] = useState("");
  const [info, setInfo] = useState("");
  const [intakeMode, setIntakeMode] = useState<"standard" | "deep">("standard");
  const [quickMode, setQuickMode] = useState<"standard" | "deep">("standard");
  const [intakeProgress, setIntakeProgress] = useState("");
  const [jurisdiction, setJurisdiction] = useState("UA");
  const [gdprResult, setGdprResult] = useState<GdprComplianceResponse | null>(null);
  const [loadingGdpr, setLoadingGdpr] = useState(false);
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>("");
  const [showCreateCaseModal, setShowCreateCaseModal] = useState(false);
  const [newCaseTitle, setNewCaseTitle] = useState("");
  const [tagFilter, setTagFilter] = useState("");

  // Collaborative comments
  const [comments, setComments] = useState<AnalysisComment[]>([]);
  const [commentsLoading, setCommentsLoading] = useState(false);
  const [commentText, setCommentText] = useState("");
  const [submittingComment, setSubmittingComment] = useState(false);
  const [deletingCommentId, setDeletingCommentId] = useState<string | null>(null);

  const intakeResult = intakeResults[activeResultIndex] ?? null;
  const currentUserId = getUserId() ?? "";

  useEffect(() => {
    void loadHistory();
    getCases(getToken(), getUserId())
      .then(setCases)
      .catch((err) => console.error("Failed to load cases:", err));
  }, []);

  // Load comments whenever the active intake result changes
  useEffect(() => {
    if (!intakeResult?.id) {
      setComments([]);
      return;
    }
    setCommentsLoading(true);
    getAnalysisComments(intakeResult.id, getToken(), getUserId())
      .then(setComments)
      .catch(() => setComments([]))
      .finally(() => setCommentsLoading(false));
  }, [intakeResult?.id]);

  function getErrorMessage(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
  }

  async function loadHistory(): Promise<void> {
    try {
      setHistory(await getContractAnalysisHistory(getToken(), getUserId()));
    } catch {
      // Ignore history fetch errors on first load to keep the page usable.
    }
  }

  async function onRunIntake(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (selectedFiles.length === 0) {
      setError("Оберіть один або декілька файлів для intake-аналізу.");
      return;
    }

    setLoadingIntake(true);
    setError("");
    setInfo("");
    setIntakeResults([]);
    setIntakeErrors({});
    setGdprResult(null);
    setActiveResultIndex(0);

    const orderedResults: (DocumentIntakeResponse | null)[] = new Array(selectedFiles.length).fill(null);
    const errors: Record<string, string> = {};
    let completedCount = 0;

    setIntakeProgress(`Аналізую 0 з ${selectedFiles.length} файлів...`);

    await runWithConcurrency(selectedFiles, 3, async (file, index) => {
      try {
        const result = await analyzeIntakeStream(
          { file, jurisdiction, case_id: selectedCaseId || undefined },
          (event: StreamEvent) => {
            if (event.message) {
              setIntakeProgress(`[${file.name}] ${event.message}`);
            }
          },
          getToken(),
          getUserId(),
          { mode: intakeMode }
        );
        orderedResults[index] = result;
      } catch (err) {
        errors[file.name] = String(err);
      } finally {
        completedCount++;
        setIntakeProgress(`Аналізую ${completedCount} з ${selectedFiles.length} файлів...`);
      }
    });

    const results = orderedResults.filter((r): r is DocumentIntakeResponse => r !== null);

    setIntakeResults(results);
    setIntakeErrors(errors);
    setIntakeProgress("");

    const successCount = results.length;
    const failureCount = Object.keys(errors).length;

    if (successCount > 0) {
      setInfo(`${intakeMode === "deep" ? "Глибокий i" : "I"}ntake-аналіз успішно завершено для ${successCount} файл(ів).`);
    }
    if (failureCount > 0) {
      setError(`Не вдалося проаналізувати ${failureCount} файл(ів).`);
    }

    setLoadingIntake(false);
  }

  async function onRunQuickAnalysis(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setLoadingQuick(true);
    setError("");
    setIntakeErrors({});
    setGdprResult(null);
    setInfo("");

    try {
      const result = await processContractAnalysis(
        {
          contract_text: quickText,
          file_name: quickFileName || undefined,
          mode: quickMode
        },
        getToken(),
        getUserId()
      );
      setQuickResult(result);
      setInfo(`${quickMode === "deep" ? "Глибокий" : "Швидкий"} контрактний аналіз завершено.`);
      await loadHistory();
    } catch (nextError) {
      setError(String(nextError));
    } finally {
      setLoadingQuick(false);
    }
  }

  function sendToCaseLaw(): void {
    if (!intakeResult) return;
    const query = buildCaseLawSeed(intakeResult);
    localStorage.setItem(CASE_LAW_SEED_KEY, JSON.stringify({ query }));
  }

  async function onRunGdprCheck() {
    if (!intakeResult?.raw_text_preview) return;
    setLoadingGdpr(true);
    setError("");
    setGdprResult(null);
    try {
      const result = await analyzeGdprCompliance({ text: intakeResult.raw_text_preview, intake_id: intakeResult.id }, getToken(), getUserId());
      setGdprResult(result);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoadingGdpr(false);
    }
  }

  async function handleCreateCase() {
    if (!newCaseTitle.trim()) return;
    setLoadingIntake(true); // reuse loading state
    setError("");
    try {
      const newCase = await createCase({ title: newCaseTitle.trim() }, getToken(), getUserId());
      const updatedCases = await getCases(getToken(), getUserId());
      setCases(updatedCases);
      setSelectedCaseId(newCase.id);
      setShowCreateCaseModal(false);
      setNewCaseTitle("");
      setInfo(`Справу "${newCase.title}" створено та обрано. Тепер можна запускати аналіз.`);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoadingIntake(false);
    }
  }

  function openCreateCaseModal() {
    setNewCaseTitle(intakeResult?.classified_type || "");
    setShowCreateCaseModal(true);
  }

  async function handleAddComment(e: React.FormEvent) {
    e.preventDefault();
    if (!intakeResult?.id || !commentText.trim()) return;
    setSubmittingComment(true);
    try {
      const newComment = await createAnalysisComment(
        intakeResult.id,
        commentText.trim(),
        getToken(),
        getUserId()
      );
      setComments((prev) => [...prev, newComment]);
      setCommentText("");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmittingComment(false);
    }
  }

  async function handleDeleteComment(commentId: string) {
    if (!intakeResult?.id) return;
    setDeletingCommentId(commentId);
    try {
      await deleteAnalysisComment(intakeResult.id, commentId, getToken(), getUserId());
      setComments((prev) => prev.filter((c) => c.id !== commentId));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setDeletingCommentId(null);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div className="section-header">
        <div>
          <h1 className="section-title">AI Аналіз</h1>
          <p className="section-subtitle">
            {mode === "litigation"
              ? "Стратегічний аналіз: intake → прецеденти → план → симуляція судді + аналіз рішень."
              : "Швидкий аналіз документів: intake, ризики договору, GDPR-відповідність."}
          </p>
        </div>
      </div>

      {/* Mode tabs */}
      <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid rgba(255,255,255,0.07)", paddingBottom: "0" }}>
        {[
          { key: "quick", label: "Швидкий аналіз" },
          { key: "litigation", label: "Судовий аналіз" },
        ].map(({ key, label }) => (
          <Link
            key={key}
            href={`/dashboard/analyze?mode=${key}`}
            style={{
              display: "inline-block",
              padding: "10px 20px",
              textDecoration: "none",
              fontSize: "14px",
              fontWeight: mode === key ? 700 : 400,
              color: mode === key ? "var(--gold-400)" : "var(--text-secondary)",
              borderBottom: mode === key ? "2px solid var(--gold-400)" : "2px solid transparent",
              marginBottom: "-1px",
              transition: "all 0.2s",
            }}
          >
            {label}
          </Link>
        ))}
      </div>

      {/* Litigation mode */}
      {mode === "litigation" && <LitigationTab />}

      {/* Quick mode — existing content below */}
      {mode !== "litigation" && error && (
        <div className="preflight-block">
          <span style={{ color: "var(--danger)", whiteSpace: "pre-wrap" }}>Помилка: {error}</span>
        </div>
      )}

      {mode !== "litigation" && info && (
        <div
          className="card-elevated"
          style={{ padding: "12px 16px", borderLeft: "3px solid var(--success)", color: "var(--success)" }}
        >
          {info}
        </div>
      )}

      {mode !== "litigation" && <>
      {Object.keys(intakeErrors).length > 0 && (
        <div className="card-elevated" style={{ padding: "16px", background: "rgba(239, 68, 68, 0.05)", border: "1px solid rgba(239, 68, 68, 0.15)" }}>
          <h4 style={{ color: "var(--danger)", marginBottom: "12px" }}>Помилки аналізу файлів</h4>
          <ul style={{ margin: 0, paddingLeft: "20px", display: "flex", flexDirection: "column", gap: "8px" }}>
            {Object.entries(intakeErrors).map(([fileName, errorMsg]) => (
              <li key={fileName} style={{ fontSize: "13px" }}>
                <strong style={{ color: "#fff" }}>{fileName}:</strong> <span style={{ color: "var(--danger)" }}>{errorMsg}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <section
        className="card-elevated"
        style={{ padding: "24px", display: "grid", gridTemplateColumns: "1.1fr 0.9fr", gap: "20px" }}
      >
        <form onSubmit={onRunIntake}>
          <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>1. Intake-аналіз документів</h2>
          <p style={{ color: "var(--text-secondary)", marginBottom: "18px" }}>
            Завантажте один або <strong style={{ color: "var(--gold-400)" }}>декілька файлів</strong> одразу для пакетного аналізу.
          </p>

          <label htmlFor="document-files" className="form-label">
            Файли документів (можна обрати декілька)
          </label>
          <input
            id="document-files"
            aria-label="Файли документів"
            type="file"
            className="form-input"
            accept=".txt,.pdf,.docx,.doc,.rtf,.md,.html,.htm"
            multiple
            onChange={(event) => setSelectedFiles(Array.from(event.target.files || []))}
          />
          {selectedFiles.length > 1 && (
            <div style={{ marginTop: "8px", fontSize: "12px", color: "var(--gold-400)", fontWeight: 700 }}>
              📎 Обрано файлів: {selectedFiles.length}
            </div>
          )}

          <div style={{ marginTop: "16px" }}>
            <label htmlFor="case-select" className="form-label">
              Прив'язати до справи (необов'язково)
            </label>
            <select
              id="case-select"
              className="form-input"
              value={selectedCaseId}
              onChange={(e) => setSelectedCaseId(e.target.value)}
            >
              <option value="">Не прив'язувати</option>
              {cases.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title} {c.case_number ? `(${c.case_number})` : ""}
                </option>
              ))}
            </select>
          </div>
          <div style={{ marginTop: "16px" }}>
            <label htmlFor="jurisdiction-select" className="form-label">
              Юрисдикція аналізу
            </label>
            <select
              id="jurisdiction-select"
              className="form-input"
              value={jurisdiction}
              onChange={(e) => setJurisdiction(e.target.value)}
            >
              <option value="UA">Україна</option>
              <option value="EU">Європейський Союз (загальне право)</option>
              <option value="PL">Польща</option>
              <option value="DE">Німеччина</option>
            </select>
          </div>

          <div style={{ marginTop: "16px" }}>
            <label className="form-label">Якість аналізу</label>
            <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
              <button
                type="button"
                className={`btn ${intakeMode === "standard" ? "btn-primary" : "btn-secondary"} btn-sm`}
                style={{ flex: 1 }}
                onClick={() => setIntakeMode("standard")}
              >
                Стандартна
              </button>
              <button
                type="button"
                className={`btn ${intakeMode === "deep" ? "btn-primary" : "btn-secondary"} btn-sm`}
                style={{ flex: 1 }}
                onClick={() => setIntakeMode("deep")}
              >
                Глибока (Deep)
              </button>
            </div>
          </div>

          {intakeProgress && (
            <div style={{ marginTop: "12px", padding: "10px 14px", background: "rgba(212,168,67,0.08)", borderRadius: "12px", fontSize: "13px", color: "var(--gold-400)", fontWeight: 600 }}>
              ⏳ {intakeProgress}
            </div>
          )}

          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "18px" }}>
            <button type="submit" className="btn btn-primary" disabled={loadingIntake}>
              {loadingIntake ? "Аналіз..." : selectedFiles.length > 1 ? `Аналізувати ${selectedFiles.length} файлів` : "Запустити intake-аналіз"}
            </button>
            <Link href="/dashboard/strategy-studio" className="btn btn-secondary">
              До Strategy Studio
            </Link>
          </div>
        </form>

        <div className="card-elevated" style={{ padding: "20px", background: "rgba(255,255,255,0.02)" }}>
          <h3 style={{ fontSize: "18px", marginBottom: "12px" }}>Що дає цей крок</h3>
          <div style={{ display: "grid", gap: "10px" }}>
            {[
              "Класифікація документа та предмета спору",
              "Первинний risk-профіль: legal / procedural / financial",
              "Виділення сторін, дедлайнів і важливих фрагментів",
              "Seed для переходу в Судову практику і далі в Strategy Studio",
            ].map((item) => (
              <div
                key={item}
                style={{
                  padding: "12px 14px",
                  borderRadius: "14px",
                  background: "rgba(255,255,255,0.03)",
                  color: "var(--text-secondary)",
                  fontSize: "14px",
                }}
              >
                {item}
              </div>
            ))}
          </div>
        </div>
      </section>

      {intakeResults.length > 0 && (
        <section className="card-elevated" style={{ padding: "24px" }}>
          {intakeResults.length > 1 && (
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "20px", padding: "12px", background: "rgba(212,168,67,0.05)", borderRadius: "16px", border: "1px solid rgba(212,168,67,0.15)" }}>
              <div style={{ width: "100%", fontSize: "11px", color: "var(--gold-400)", fontWeight: 800, textTransform: "uppercase", letterSpacing: "1px", marginBottom: "6px" }}>
                📎 Результати по файлах ({intakeResults.length})
              </div>
              {intakeResults.map((r, idx) => (
                <button
                  key={idx}
                  className={`btn ${activeResultIndex === idx ? "btn-primary" : "btn-secondary"} btn-sm`}
                  style={{ fontSize: "12px" }}
                  onClick={() => setActiveResultIndex(idx)}
                >
                  {idx + 1}. {r.classified_type || `Файл ${idx + 1}`}
                </button>
              ))}
            </div>
          )}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: "16px",
              alignItems: "center",
              flexWrap: "wrap",
              marginBottom: "18px",
            }}
          >
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
                <h2 style={{ fontSize: "22px", margin: 0 }}>Результат intake-аналізу</h2>
                {intakeResult.cache_hit && (
                  <span style={{
                    fontSize: "10px",
                    fontWeight: 800,
                    padding: "3px 10px",
                    borderRadius: "999px",
                    background: "rgba(16,185,129,0.12)",
                    color: "var(--success)",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}>
                    cached
                  </span>
                )}
              </div>
              <p style={{ color: "var(--text-secondary)" }}>
                Це ядро для наступних етапів: судова практика {"->"} стратегія {"->"} генерація.
              </p>
            </div>
            <Link href="/dashboard/case-law" className="btn btn-primary" onClick={sendToCaseLaw}>
              Передати в судову практику
            </Link>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
              gap: "12px",
              marginBottom: "18px",
            }}
          >
            {[
              { label: "Тип документа", value: intakeResult.classified_type },
              { label: "Предмет", value: intakeResult.subject_matter || "—" },
              { label: "Роль сторони", value: intakeResult.primary_party_role || "—" },
              { label: "Юрисдикція", value: intakeResult.jurisdiction || "—" },
              { label: "Терміновість", value: intakeResult.urgency_level || "—" },
              { label: "Дедлайн", value: intakeResult.deadline_from_document || "—" },
            ].map((item) => (
              <div
                key={item.label}
                style={{ padding: "14px", borderRadius: "16px", background: "rgba(255,255,255,0.03)" }}
              >
                <div
                  style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "6px" }}
                >
                  {item.label}
                </div>
                <div style={{ color: "#fff", fontWeight: 700 }}>{item.value}</div>
              </div>
            ))}
          </div>

          {!!intakeResult.tags?.length && (
            <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "18px" }}>
              {intakeResult.tags.map((tag) => (
                <span
                  key={tag}
                  style={{
                    padding: "4px 12px",
                    borderRadius: "999px",
                    fontSize: "11px",
                    fontWeight: 700,
                    background: "rgba(212,168,67,0.1)",
                    color: "var(--gold-400)",
                    border: "1px solid rgba(212,168,67,0.2)",
                  }}
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
              gap: "12px",
              marginBottom: "18px",
            }}
          >
            {[
              { label: "Legal risk", value: intakeResult.risk_level_legal },
              { label: "Procedural risk", value: intakeResult.risk_level_procedural },
              { label: "Financial risk", value: intakeResult.risk_level_financial },
            ].map((item) => {
              const tone = riskTone(item.value);
              return (
                <div key={item.label} style={{ padding: "14px", borderRadius: "16px", background: tone.background, color: tone.color }}>
                  <div style={{ fontSize: "11px", textTransform: "uppercase", marginBottom: "6px" }}>{item.label}</div>
                  <div style={{ fontWeight: 700 }}>{item.value || "unknown"}</div>
                </div>
              );
            })}
          </div>

          <div className="card-elevated" style={{ padding: "16px", marginBottom: "18px", border: "1px solid var(--accent)", background: "rgba(59, 130, 246, 0.05)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", justifyContent: "space-between" }}>
              <div style={{ fontSize: "14px", fontWeight: 600 }}>Швидкі дії:</div>
              <div style={{ display: "flex", gap: "10px" }}>
                <button
                  className="btn-light"
                  style={{ fontSize: "12px", padding: "8px 14px" }}
                  onClick={() => alert(`Створення дедлайну для: ${intakeResult.deadline_from_document || 'цього документа'}`)}
                >
                  Створити дедлайн
                </button>
                <button
                  className="btn-primary"
                  style={{ fontSize: "12px", padding: "8px 14px" }}
                  onClick={openCreateCaseModal}
                  disabled={!intakeResult}
                >
                  Створити справу
                </button>
                <button
                  className="btn-light"
                  style={{ fontSize: "12px", padding: "8px 14px" }}
                  onClick={() => void onRunGdprCheck()}
                  disabled={loadingGdpr}
                >
                  {loadingGdpr ? "Перевірка..." : "🇪🇺 Перевірити на GDPR"}
                </button>
              </div>
            </div>
          </div>

          {!!intakeResult.detected_issues?.length && (
            <div style={{ marginBottom: "18px" }}>
              <h3 style={{ fontSize: "16px", marginBottom: "10px" }}>Виявлені проблеми</h3>
              <div style={{ display: "grid", gap: "10px" }}>
                {intakeResult.detected_issues.map((item, index) => {
                  const tone = riskTone(item.severity);
                  return (
                    <div
                      key={`${item.issue_type}-${index}`}
                      className={`card-elevated ${activeIssueIndex === index ? 'active-issue' : ''}`}
                      style={{
                        padding: "14px",
                        cursor: "pointer",
                        borderLeft: activeIssueIndex === index ? "4px solid var(--accent)" : "4px solid transparent",
                        transition: "all 0.2s"
                      }}
                      onClick={() => setActiveIssueIndex(index === activeIssueIndex ? null : index)}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", marginBottom: "6px" }}>
                        <strong>{item.issue_type}</strong>
                        <span
                          style={{
                            padding: "3px 10px",
                            borderRadius: "999px",
                            fontSize: "12px",
                            fontWeight: 700,
                            color: tone.color,
                            background: tone.background,
                          }}
                        >
                          {item.severity}
                        </span>
                      </div>
                      <p style={{ color: "var(--text-secondary)", fontSize: "14px", marginBottom: "6px" }}>{item.description}</p>
                      <p style={{ color: "var(--text-muted)", fontSize: "12px" }}>{item.impact}</p>
                      {activeIssueIndex === index && (
                        <div style={{ marginTop: "10px", fontSize: "11px", color: "var(--accent)", fontWeight: 600 }}>
                          ↑ Текст підсвічено в Raw Preview
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {gdprResult && (
            <div className="card-elevated" style={{ padding: "20px", marginTop: "18px", background: gdprResult.compliant ? "rgba(16, 185, 129, 0.05)" : "rgba(239, 68, 68, 0.05)", border: `1px solid ${gdprResult.compliant ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)"}` }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <h3 style={{ fontSize: "16px", color: gdprResult.compliant ? "var(--success)" : "var(--danger)", margin: 0 }}>
                  {gdprResult.compliant ? "✅" : "⚠️"} Звіт по GDPR
                </h3>
                <span style={{
                  padding: "4px 12px",
                  borderRadius: "999px",
                  fontSize: "12px",
                  fontWeight: 700,
                  color: gdprResult.compliant ? "var(--success)" : "var(--danger)",
                  background: gdprResult.compliant ? "rgba(16,185,129,0.12)" : "rgba(239,68,68,0.12)",
                }}>
                  {gdprResult.compliant ? "Compliant" : `${gdprResult.issues.length} issues`}
                </span>
              </div>

              {!!gdprResult.personal_data_found?.length && (
                <div style={{ marginBottom: "14px" }}>
                  <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "8px" }}>
                    Знайдені персональні дані
                  </div>
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    {gdprResult.personal_data_found.map((item) => (
                      <div key={item.type} style={{ padding: "8px 12px", borderRadius: "12px", background: "rgba(239,68,68,0.08)", fontSize: "13px" }}>
                        <strong style={{ color: "var(--danger)" }}>{item.type}</strong>
                        <span style={{ color: "var(--text-secondary)", marginLeft: "6px" }}>{item.count}x</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {!!gdprResult.recommendations?.length && (
                <div style={{ marginBottom: "14px" }}>
                  <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "8px" }}>
                    Рекомендації
                  </div>
                  <ul style={{ margin: 0, paddingLeft: "18px", display: "flex", flexDirection: "column", gap: "4px" }}>
                    {gdprResult.recommendations.map((rec, i) => (
                      <li key={i} style={{ fontSize: "13px", color: "var(--text-secondary)" }}>{rec}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div style={{ whiteSpace: "pre-wrap", fontSize: "13px", color: "var(--text-secondary)", maxHeight: "300px", overflowY: "auto", padding: "12px", background: "rgba(255,255,255,0.02)", borderRadius: "10px" }}>
                {gdprResult.report}
              </div>
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "0.9fr 1.1fr", gap: "16px" }}>
            <div className="card-elevated" style={{ padding: "16px" }}>
              <h3 style={{ fontSize: "16px", marginBottom: "10px" }}>Ідентифіковані сторони</h3>
              {intakeResult.identified_parties?.length ? (
                intakeResult.identified_parties.map((party, index) => (
                  <div
                    key={index}
                    style={{
                      padding: "10px 0",
                      borderBottom: index === intakeResult.identified_parties.length - 1 ? "none" : "1px solid var(--border)",
                      color: "var(--text-secondary)",
                      fontSize: "14px",
                    }}
                  >
                    {Object.entries(party).map(([key, value]) => (
                      <div key={key}>
                        <strong style={{ color: "#fff" }}>{key}:</strong> {String(value)}
                      </div>
                    ))}
                  </div>
                ))
              ) : (
                <p style={{ color: "var(--text-muted)" }}>Сторони не визначені.</p>
              )}
            </div>

            <div className="card-elevated" style={{ padding: "16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                <h3 style={{ fontSize: "16px", margin: 0 }}>Raw preview</h3>
                {intakeResult?.raw_text_preview && !isEditingText && (
                  <button className="btn btn-secondary btn-sm" onClick={() => {
                    setEditedText(intakeResult.raw_text_preview || "");
                    setIsEditingText(true);
                  }}>
                    Редагувати
                  </button>
                )}
              </div>
              {isEditingText ? (
                <div>
                  <textarea
                    className="form-input"
                    rows={10}
                    value={editedText}
                    onChange={(e) => setEditedText(e.target.value)}
                    style={{ width: '100%', marginBottom: '10px', fontSize: '13px', lineHeight: 1.55 }}
                  />
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button className="btn btn-primary btn-sm" onClick={() => {
                      if (intakeResult) {
                        const newResults = [...intakeResults];
                        newResults[activeResultIndex] = { ...intakeResult, raw_text_preview: editedText };
                        setIntakeResults(newResults);
                      }
                      setIsEditingText(false);
                    }}>
                      Зберегти зміни
                    </button>
                    <button className="btn btn-secondary btn-sm" onClick={() => setIsEditingText(false)}>
                      Скасувати
                    </button>
                  </div>
                </div>
              ) : (
                <div
                  style={{
                    maxHeight: "220px",
                    overflowY: "auto",
                    color: "var(--text-secondary)",
                    whiteSpace: "pre-wrap",
                    fontSize: "13px",
                    lineHeight: 1.55,
                  }}
                >
                  {(function () {
                    const text = intakeResult.raw_text_preview || "";
                    if (activeIssueIndex !== null && intakeResult.detected_issues[activeIssueIndex]) {
                      const issue = intakeResult.detected_issues[activeIssueIndex];
                      if (issue.start_index !== undefined && issue.end_index !== undefined && issue.start_index >= 0 && issue.end_index > issue.start_index) {
                        const before = text.slice(0, issue.start_index);
                        const match = text.slice(issue.start_index, issue.end_index);
                        const after = text.slice(issue.end_index);
                        return (
                          <>
                            {before}<span style={{ background: "rgba(239, 68, 68, 0.3)", color: "#fff", padding: "1px 2px", borderRadius: "2px", fontWeight: "bold" }}>{match}</span>{after}
                          </>
                        );
                      }
                    }
                    return text || "Попередній витяг не повернувся.";
                  })()}
                </div>
              )}
            </div>
          </div>

          {/* ── Collaborative comments ── */}
          <div style={{ marginTop: "28px", borderTop: "1px solid rgba(255,255,255,0.07)", paddingTop: "24px" }}>
            <h3 style={{ fontSize: "15px", fontWeight: 700, color: "#fff", marginBottom: "14px" }}>
              Коментарі до аналізу
              {commentsLoading && <span className="spinner" style={{ width: 12, height: 12, marginLeft: 8 }} />}
              {!commentsLoading && (
                <span style={{ fontSize: "12px", fontWeight: 400, color: "var(--text-muted)", marginLeft: "8px" }}>
                  {comments.length}
                </span>
              )}
            </h3>

            <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginBottom: "16px" }}>
              {comments.length === 0 && !commentsLoading && (
                <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                  Коментарів поки немає. Будьте першим.
                </p>
              )}
              {comments.map((c) => (
                <div
                  key={c.id}
                  style={{
                    padding: "12px 14px",
                    borderRadius: "12px",
                    background: c.user_id === currentUserId
                      ? "rgba(212,168,67,0.06)"
                      : "rgba(255,255,255,0.03)",
                    border: `1px solid ${c.user_id === currentUserId ? "rgba(212,168,67,0.15)" : "rgba(255,255,255,0.06)"}`,
                    display: "flex",
                    gap: "10px",
                    alignItems: "flex-start",
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "5px" }}>
                      <span style={{ fontSize: "12px", fontWeight: 700, color: c.user_id === currentUserId ? "var(--gold-400)" : "var(--text-secondary)" }}>
                        {c.user_id === currentUserId ? "Ви" : (c.user_name || "Колега")}
                      </span>
                      <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                        {new Date(c.created_at).toLocaleString("uk-UA", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                    <p style={{ fontSize: "13px", color: "var(--text-secondary)", margin: 0, lineHeight: 1.55, whiteSpace: "pre-wrap" }}>
                      {c.content}
                    </p>
                  </div>
                  {c.user_id === currentUserId && (
                    <button
                      type="button"
                      onClick={() => void handleDeleteComment(c.id)}
                      disabled={deletingCommentId === c.id}
                      style={{
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        color: "var(--text-muted)",
                        fontSize: "16px",
                        padding: "2px 4px",
                        lineHeight: 1,
                        flexShrink: 0,
                      }}
                      title="Видалити коментар"
                    >
                      {deletingCommentId === c.id ? <span className="spinner" style={{ width: 12, height: 12 }} /> : "×"}
                    </button>
                  )}
                </div>
              ))}
            </div>

            <form onSubmit={(e) => void handleAddComment(e)} style={{ display: "flex", gap: "8px", alignItems: "flex-end" }}>
              <textarea
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                placeholder="Напишіть коментар до аналізу..."
                rows={2}
                maxLength={4000}
                style={{
                  flex: 1,
                  resize: "vertical",
                  minHeight: "60px",
                  padding: "10px 14px",
                  borderRadius: "12px",
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  color: "#fff",
                  fontSize: "13px",
                  lineHeight: 1.5,
                  fontFamily: "inherit",
                }}
              />
              <button
                type="submit"
                className="btn btn-primary btn-sm"
                disabled={submittingComment || !commentText.trim()}
                style={{ padding: "10px 18px", alignSelf: "flex-end", whiteSpace: "nowrap" }}
              >
                {submittingComment ? <span className="spinner" style={{ width: 12, height: 12 }} /> : "Надіслати"}
              </button>
            </form>
          </div>
          {/* ── /Collaborative comments ── */}
        </section>
      )}

      <section style={{ display: "grid", gridTemplateColumns: "1fr 0.9fr", gap: "20px" }}>
        <form className="card-elevated" style={{ padding: "24px" }} onSubmit={onRunQuickAnalysis}>
          <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>2. Швидкий контрактний аналіз</h2>
          <p style={{ color: "var(--text-secondary)", marginBottom: "18px" }}>
            Допоміжний режим для швидкого огляду тексту договору без повного intake-пайплайну.
          </p>

          <div style={{ marginBottom: "14px" }}>
            <label htmlFor="quick-file-name" className="form-label">
              Назва файлу
            </label>
            <input
              id="quick-file-name"
              className="form-input"
              value={quickFileName}
              onChange={(event) => setQuickFileName(event.target.value)}
              placeholder="dogovir_orendy_2026.pdf"
            />
          </div>

          <div style={{ marginBottom: "18px" }}>
            <label className="form-label">Якість аналізу</label>
            <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
              <button
                type="button"
                className={`btn ${quickMode === "standard" ? "btn-primary" : "btn-secondary"}`}
                style={{ flex: 1, padding: "8px" }}
                onClick={() => setQuickMode("standard")}
              >
                Стандартна (Швидко)
              </button>
              <button
                type="button"
                className={`btn ${quickMode === "deep" ? "btn-primary" : "btn-secondary"}`}
                style={{ flex: 1, padding: "8px" }}
                onClick={() => setQuickMode("deep")}
              >
                Глибока (Deep Audit)
              </button>
            </div>
            <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "6px" }}>
              {quickMode === "deep"
                ? "Використовує найпотужніші моделі для пошуку прихованих ризиків. Довше очікування."
                : "Збалансований режим для швидкої перевірки основних пунктів."}
            </p>
          </div>

          <div style={{ marginBottom: "14px" }}>
            <label htmlFor="quick-contract-text" className="form-label">
              Текст договору
            </label>
            <textarea
              id="quick-contract-text"
              className="form-input"
              rows={10}
              value={quickText}
              onChange={(event) => setQuickText(event.target.value)}
              placeholder="Вставте текст договору..."
              required
              minLength={20}
            />
          </div>

          <button type="submit" className="btn btn-secondary" disabled={loadingQuick}>
            {loadingQuick ? "Аналіз..." : "Швидкий аналіз"}
          </button>
        </form>

        <div className="card-elevated" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>Історія швидких аналізів</h2>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "18px" }}>
            <p style={{ color: "var(--text-secondary)", margin: 0 }}>{history?.total || 0} записів</p>
            {(() => {
              const allTags = Array.from(new Set((history?.items || []).flatMap((i) => i.tags || [])));
              if (allTags.length === 0) return null;
              return (
                <select
                  value={tagFilter}
                  onChange={(e) => setTagFilter(e.target.value)}
                  style={{ fontSize: "12px", padding: "4px 10px", borderRadius: "8px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", color: "#fff" }}
                >
                  <option value="">Всі теги</option>
                  {allTags.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              );
            })()}
          </div>

          {quickResult && (
            <div className="card-elevated" style={{ padding: "14px", marginBottom: "14px", borderLeft: "3px solid var(--gold-500)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", marginBottom: "8px" }}>
                <strong>Останній quick-аналіз</strong>
                <span
                  style={{
                    padding: "3px 10px",
                    borderRadius: "999px",
                    fontSize: "12px",
                    fontWeight: 700,
                    ...riskTone(quickResult.risk_level),
                  }}
                >
                  {quickResult.risk_level || "unknown"}
                </span>
              </div>
              <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
                {quickResult.summary || "Підсумок не повернувся."}
              </p>
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {history?.items?.length ? (
              history.items
                .filter((item) => !tagFilter || (item.tags || []).includes(tagFilter))
                .map((item) => (
                <div key={item.id} className="card-elevated" style={{ padding: "12px 14px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
                    <div>
                      <div style={{ fontWeight: 700, color: "#fff" }}>{item.file_name || "Контракт без назви"}</div>
                      <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>{item.created_at}</div>
                    </div>
                    <span
                      style={{
                        padding: "3px 10px",
                        borderRadius: "999px",
                        fontSize: "12px",
                        fontWeight: 700,
                        ...riskTone(item.risk_level),
                      }}
                    >
                      {item.risk_level || "—"}
                    </span>
                  </div>
                  {!!item.tags?.length && (
                    <div style={{ display: "flex", gap: "4px", flexWrap: "wrap", marginTop: "8px" }}>
                      {item.tags.map((tag) => (
                        <span key={tag} style={{
                          padding: "2px 8px",
                          borderRadius: "999px",
                          fontSize: "10px",
                          fontWeight: 700,
                          background: "rgba(212,168,67,0.1)",
                          color: "var(--gold-400)",
                          border: "1px solid rgba(212,168,67,0.15)",
                        }}>{tag}</span>
                      ))}
                    </div>
                  )}
                  {item.summary && <p style={{ marginTop: "8px", color: "var(--text-secondary)", fontSize: "13px" }}>{item.summary}</p>}
                </div>
              ))
            ) : (
              <p style={{ color: "var(--text-muted)" }}>Історія ще порожня.</p>
            )}
          </div>
        </div>
      </section>

      {showCreateCaseModal && (
        <div className="modal-overlay">
          <div className="modal-content card-elevated" style={{ maxWidth: "500px", width: "90%" }}>
            <h2 style={{ marginBottom: "16px" }}>Створити нову справу</h2>
            <p style={{ color: "var(--text-secondary)", fontSize: "14px", marginBottom: "16px" }}>
              Створіть нову справу на основі результатів аналізу.
            </p>
            <div className="form-group">
              <label className="form-label">Назва справи</label>
              <input
                className="form-input"
                value={newCaseTitle}
                onChange={(e) => setNewCaseTitle(e.target.value)}
                placeholder="Наприклад, Позов про стягнення боргу"
              />
            </div>
            <div className="modal-actions" style={{ marginTop: "24px" }}>
              <button className="btn btn-secondary" onClick={() => setShowCreateCaseModal(false)}>
                Скасувати
              </button>
              <button className="btn btn-primary" onClick={() => void handleCreateCase()} disabled={loadingIntake}>
                {loadingIntake ? "Створення..." : "Створити"}
              </button>
            </div>
          </div>
        </div>
      )}
      </>}
    </div>
  );
}

export default function AnalyzePage() {
  return (
    <Suspense fallback={<div style={{ padding: "24px", color: "var(--text-secondary)" }}>Завантаження...</div>}>
      <AnalyzePageInner />
    </Suspense>
  );
}
