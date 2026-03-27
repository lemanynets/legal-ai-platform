"use client";

import Link from "next/link";
import React, { FormEvent, useEffect, useState } from "react";

import { getToken, getUserId } from "@/lib/auth";
import {
  analyzeIntake,
  createCase,
  type ContractAnalysisHistoryResponse,
  type GdprComplianceResponse,
  type ContractAnalysisItem,
  type DocumentIntakeResponse,
  getCase,
  getCases,
  getContractAnalysisHistory,
  processContractAnalysis,
  type Case,
} from "@/lib/api";

const CASE_LAW_SEED_KEY = "legal_ai_case_law_seed_v1";
import { analyzeGdprCompliance } from "@/lib/api";

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

export default function AnalyzePage() {
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
  const [gdprResult, setGdprResult] = useState<string | null>(null);
  const [loadingGdpr, setLoadingGdpr] = useState(false);
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>("");
  const [showCreateCaseModal, setShowCreateCaseModal] = useState(false);
  const [newCaseTitle, setNewCaseTitle] = useState("");

  const intakeResult = intakeResults[activeResultIndex] ?? null;

  useEffect(() => {
    void loadHistory();
    getCases(getToken(), getUserId())
      .then(setCases)
      .catch((err) => console.error("Failed to load cases:", err));
  }, []);

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
        const result = await analyzeIntake(
          { file, jurisdiction, case_id: selectedCaseId || undefined },
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
      const result = await analyzeGdprCompliance({ text: intakeResult.raw_text_preview }, getToken(), getUserId());
      setGdprResult(result.report);
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
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div className="section-header">
        <div>
          <h1 className="section-title">AI Аналізатор (Усі види)</h1>
          <p className="section-subtitle">
            Завантажуйте один або декілька документів для intake-аналізу та швидкого огляду договорів.
          </p>
        </div>
      </div>

      {error && (
        <div className="preflight-block">
          <span style={{ color: "var(--danger)", whiteSpace: "pre-wrap" }}>Помилка: {error}</span>
        </div>
      )}

      {info && (
        <div
          className="card-elevated"
          style={{ padding: "12px 16px", borderLeft: "3px solid var(--success)", color: "var(--success)" }}
        >
          {info}
        </div>
      )}

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
              <h2 style={{ fontSize: "22px", marginBottom: "6px" }}>Результат intake-аналізу</h2>
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
            <div className="card-elevated" style={{ padding: "20px", marginTop: "18px", background: "rgba(16, 185, 129, 0.05)", border: "1px solid rgba(16, 185, 129, 0.15)" }}>
              <h3 style={{ fontSize: "16px", color: "var(--success)", marginBottom: "10px" }}>🇪🇺 Звіт по GDPR</h3>
              <div style={{ whiteSpace: "pre-wrap", fontSize: "13px", color: "var(--text-secondary)", maxHeight: "300px", overflowY: "auto" }}>
                {gdprResult}
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
          <p style={{ color: "var(--text-secondary)", marginBottom: "18px" }}>{history?.total || 0} записів</p>

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
              history.items.map((item) => (
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
    </div>
  );
}
