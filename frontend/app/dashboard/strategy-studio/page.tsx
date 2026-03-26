"use client";

import React, { FormEvent, useEffect, useState } from "react";

import { getToken, getUserId } from "@/lib/auth";
import {
  analyzeIntake,
  analyzePrecedentMap,
  createStrategyBlueprint,
  generateWithStrategy,
  getStrategyAudit,
  runJudgeSimulation,
  getExportDocxUrl,
  type DocumentIntakeResponse,
  type GenerateWithStrategyResponse,
  type JudgeSimulationResponse,
  type PrecedentMapResponse,
  type StrategyAuditResponse,
  type StrategyBlueprintResponse,
  getCases,
  type Case,
} from "@/lib/api";

const DOC_TYPES = [
  { value: "appeal_complaint", label: "Апеляційна скарга" },
  { value: "motion_appeal_deadline_renewal", label: "Клопотання про поновлення строку" },
  { value: "cassation_complaint", label: "Касаційна скарга" },
  { value: "objection_response", label: "Відзив / заперечення" },
  { value: "lawsuit_debt_loan", label: "Позов про стягнення боргу за позикою" },
  { value: "lawsuit_debt_sale", label: "Позов про стягнення за договором купівлі-продажу" },
  { value: "motion_claim_security", label: "Заява про забезпечення позову" },
  { value: "civil_claim", label: "Цивільний позов (універсальний)" },
  { value: "divorce_claim", label: "Позов про розірвання шлюбу" },
  { value: "motion_injunction", label: "Заява про забезп. (терміново)" },
  { value: "evidence_request", label: "Клопотання про витребування доказів" },
];

function StepBadge({
  index,
  title,
  active,
  done,
}: {
  index: number;
  title: string;
  active: boolean;
  done: boolean;
}) {
  return (
    <div
      className="card-elevated"
      style={{
        padding: "16px",
        border: active ? "1px solid var(--gold-400)" : "1px solid rgba(255,255,255,0.05)",
        background: done
          ? "linear-gradient(145deg, rgba(16, 185, 129, 0.1), rgba(16, 185, 129, 0.02))"
          : active
            ? "linear-gradient(145deg, rgba(212, 168, 67, 0.1), rgba(212, 168, 67, 0.02))"
            : "rgba(255,255,255,0.02)",
        position: "relative",
        transition: "all 0.3s ease",
        transform: active ? "translateY(-2px)" : "none",
        boxShadow: active ? "0 8px 25px -5px rgba(212, 168, 67, 0.2)" : "none"
      }}
    >
      <div
        style={{
          fontSize: "10px",
          fontWeight: 800,
          textTransform: "uppercase",
          color: active ? "var(--gold-400)" : "var(--text-muted)",
          marginBottom: "8px",
          letterSpacing: "0.1em"
        }}
      >
        Крок {index}
      </div>
      <div style={{ fontWeight: 700, color: "#fff", marginBottom: "8px", fontSize: "14px" }}>{title}</div>
      <div style={{
        fontSize: "12px",
        color: done ? "var(--success)" : active ? "var(--gold-400)" : "var(--text-muted)",
        display: "flex",
        alignItems: "center",
        gap: "6px"
      }}>
        <div style={{
          width: "6px",
          height: "6px",
          borderRadius: "50%",
          background: done ? "var(--success)" : active ? "var(--gold-400)" : "rgba(255,255,255,0.1)",
          boxShadow: active ? `0 0 10px ${done ? 'var(--success)' : 'var(--gold-400)'}` : "none"
        }} />
        {done ? "Готово" : active ? "Аналіз..." : "Очікує"}
      </div>
    </div>
  );
}

function SummaryStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card-elevated" style={{
      padding: "16px",
      background: "rgba(255,255,255,0.03)",
      border: "1px solid rgba(255,255,255,0.05)",
      borderRadius: "16px"
    }}>
      <div style={{
        fontSize: "10px",
        textTransform: "uppercase",
        color: "var(--text-muted)",
        marginBottom: "8px",
        fontWeight: 700,
        letterSpacing: "0.05em"
      }}>{label}</div>
      <div style={{ color: "#fff", fontWeight: 800, fontSize: "18px" }}>{value}</div>
    </div>
  );
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export default function StrategyStudioPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [docType, setDocType] = useState("appeal_complaint");
  const [loadingStage, setLoadingStage] = useState("");
  const [error, setError] = useState("");
  const [autopilot, setAutopilot] = useState(false);
  const [info, setInfo] = useState("");

  const [intake, setIntake] = useState<DocumentIntakeResponse | null>(null);
  const [precedentMap, setPrecedentMap] = useState<PrecedentMapResponse | null>(null);
  const [strategy, setStrategy] = useState<StrategyBlueprintResponse | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [judgeSimulation, setJudgeSimulation] = useState<JudgeSimulationResponse | null>(null);

  const onRunJudgeSimulation = async () => {
    if (!strategy) return;
    setIsSimulating(true);
    try {
      const res = await runJudgeSimulation({ strategy_id: strategy.id }, getToken());
      setJudgeSimulation(res);
    } catch (e) {
      setError("Помилка симуляції: " + (e as Error).message);
    } finally {
      setIsSimulating(false);
    }
  };

  useEffect(() => {
    getCases(getToken(), getUserId())
      .then(setCases)
      .catch((err) => console.error("Failed to load cases:", err));
  }, []);
  const [generated, setGenerated] = useState<GenerateWithStrategyResponse | null>(null);
  const [audit, setAudit] = useState<StrategyAuditResponse | null>(null);

  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>("");

  const isLoading = Boolean(loadingStage);
  const currentStep = !intake ? 1 : !precedentMap ? 2 : !strategy ? 3 : !generated ? 4 : !audit ? 5 : 5;

  async function onRunIntake(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!selectedFile) {
      setError("Оберіть файл для strategy intake.");
      return;
    }

    setLoadingStage("intake");
    setError("");
    setInfo("");

    try {
      const payload = await analyzeIntake({ file: selectedFile }, getToken(), getUserId());
      setIntake(payload);
      setPrecedentMap(null);
      setStrategy(null);
      setGenerated(null);
      setAudit(null);
      setInfo(`Intake завершено: ${payload.classified_type}.`);

      if (autopilot) {
        setInfo("Автопілот: Наступний крок - Precedent map...");
        const pMap = await analyzePrecedentMap(payload.id, { limit: 15 }, getToken(), getUserId());
        setPrecedentMap(pMap);
        setInfo("Автопілот: Наступний крок - Strategy blueprint...");
        const strat = await createStrategyBlueprint(
          { intake_id: payload.id, regenerate: true, refresh_precedent_map: true, precedent_limit: 15 },
          getToken(),
          getUserId()
        );
        setStrategy(strat);
        setInfo("Автопілот завершено. Стратегія готова до генерації.");
      }
    } catch (nextError) {
      setError(getErrorMessage(nextError));
    } finally {
      setLoadingStage("");
    }
  }

  async function onBuildPrecedentMap(): Promise<void> {
    if (!intake) return;
    setLoadingStage("precedent-map");
    setError("");
    setInfo("");
    try {
      const payload = await analyzePrecedentMap(intake.id, { limit: 15 }, getToken(), getUserId());
      setPrecedentMap(payload);
      setStrategy(null);
      setGenerated(null);
      setAudit(null);
      setInfo(`Precedent map побудовано: ${payload.refs.length} рішень.`);
    } catch (nextError) {
      setError(getErrorMessage(nextError));
    } finally {
      setLoadingStage("");
    }
  }

  async function onBuildStrategy(): Promise<void> {
    if (!intake) return;
    setLoadingStage("strategy");
    setError("");
    setInfo("");
    try {
      const payload = await createStrategyBlueprint(
        { intake_id: intake.id, regenerate: true, refresh_precedent_map: true, precedent_limit: 15 },
        getToken(),
        getUserId()
      );
      setStrategy(payload);
      setGenerated(null);
      setAudit(null);
      setInfo("Strategy blueprint готовий.");
    } catch (nextError) {
      setError(getErrorMessage(nextError));
    } finally {
      setLoadingStage("");
    }
  }

  async function onGenerateDocument(): Promise<void> {
    if (!strategy) return;
    setLoadingStage("generation");
    setError("");
    setInfo("");
    try {
      const payload = await generateWithStrategy(
        {
          strategy_blueprint_id: strategy.id,
          doc_type: docType,
          form_data: {},
          extra_prompt_context: "Генерація через Strategy Studio UI.",
          case_id: selectedCaseId || undefined,
        },
        getToken(),
        getUserId()
      );
      setGenerated(payload);
      setAudit(null);
      setInfo(`Документ згенеровано: ${payload.document_id}.`);
    } catch (nextError) {
      setError(getErrorMessage(nextError));
    } finally {
      setLoadingStage("");
    }
  }

  async function onLoadAudit(): Promise<void> {
    if (!generated) return;
    setLoadingStage("audit");
    setError("");
    setInfo("");
    try {
      const payload = await getStrategyAudit(generated.document_id, getToken(), getUserId());
      setAudit(payload);
      setInfo("Strategy audit завантажено.");
    } catch (nextError) {
      setError(getErrorMessage(nextError));
    } finally {
      setLoadingStage("");
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div className="section-header">
        <div>
          <h1 className="section-title">Strategy Studio</h1>
          <p className="section-subtitle">
            Крок 3 ядра продукту: після аналізу документа і пошуку практики тут збирається стратегія, а потім запускається генерація.
          </p>
        </div>
      </div>

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

      <section style={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", gap: "12px" }}>
        <StepBadge index={1} title="Intake" active={currentStep === 1} done={!!intake} />
        <StepBadge index={2} title="Precedent map" active={currentStep === 2} done={!!precedentMap} />
        <StepBadge index={3} title="Blueprint" active={currentStep === 3} done={!!strategy} />
        <StepBadge index={4} title="Generation" active={currentStep === 4} done={!!generated} />
        <StepBadge index={5} title="Audit" active={currentStep === 5} done={!!audit} />
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <form className="card-elevated" style={{ padding: "24px" }} onSubmit={onRunIntake}>
            <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>1. Strategy intake</h2>
            <p style={{ color: "var(--text-secondary)", marginBottom: "18px" }}>
              Завантажте матеріал справи. На цьому етапі запускається intake-класифікація для побудови стратегії.
            </p>

            <label htmlFor="strategy-file" className="form-label">
              Файл для strategy intake
            </label>
            <input
              id="strategy-file"
              aria-label="Файл для strategy intake"
              type="file"
              className="form-input"
              accept=".txt,.pdf,.docx,.doc,.rtf,.md,.html,.htm"
              onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
            />

            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginTop: "14px", marginBottom: "14px" }}>
              <input
                id="autopilot-check"
                type="checkbox"
                checked={autopilot}
                onChange={(e) => setAutopilot(e.target.checked)}
                style={{ cursor: "pointer", width: "16px", height: "16px" }}
              />
              <label htmlFor="autopilot-check" style={{ fontSize: "14px", fontWeight: 600, cursor: "pointer", color: "var(--gold-400)" }}>
                Continuous Workflow (Автопілот: Крок 1 → Крок 3)
              </label>
            </div>

            <button type="submit" className="btn btn-primary" disabled={isLoading} style={{ width: "100%" }}>
              {loadingStage === "intake" ? "Обробка всього пайплайну..." : autopilot ? "Запустити повний цикл (AI Steer)" : "Запустити strategy intake"}
            </button>
          </form>

          <div className="card-elevated" style={{ padding: "24px" }}>
            <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>2. Практика і стратегія</h2>
            <p style={{ color: "var(--text-secondary)", marginBottom: "18px" }}>
              Після intake формується precedent map, а потім strategy blueprint. Кроки йдуть послідовно.
            </p>

            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
              <button type="button" className="btn btn-secondary" onClick={() => void onBuildPrecedentMap()} disabled={isLoading || !intake}>
                {loadingStage === "precedent-map" ? "Побудова..." : "Побудувати precedent map"}
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => void onBuildStrategy()} disabled={isLoading || !intake}>
                {loadingStage === "strategy" ? "Побудова..." : "Створити strategy blueprint"}
              </button>
            </div>
          </div>

          <div className="card-elevated" style={{ padding: "24px" }}>
            <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>3. Генерація і audit</h2>
            <p style={{ color: "var(--text-secondary)", marginBottom: "18px" }}>
              Генерація стартує тільки після створення strategy blueprint. Після цього можна завантажити strategy audit.
            </p>

            <label htmlFor="strategy-doc-type" className="form-label">
              Тип документа для генерації
            </label>
            <select id="strategy-doc-type" className="form-input" value={docType} onChange={(event) => setDocType(event.target.value)}>
              {DOC_TYPES.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>

            <div style={{ marginTop: "18px" }}>
              <label htmlFor="case-select-strategy" className="form-label">
                Прив'язати до справи (необов'язково)
              </label>
              <select
                id="case-select-strategy"
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

            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "18px" }}>
              <button type="button" className="btn btn-primary" onClick={() => void onGenerateDocument()} disabled={isLoading || !strategy}>
                {loadingStage === "generation" ? "Генерація..." : "Згенерувати документ"}
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => void onLoadAudit()} disabled={isLoading || !generated}>
                {loadingStage === "audit" ? "Завантаження..." : "Завантажити strategy audit"}
              </button>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {intake ? (
            <div className="card-elevated" style={{ padding: "24px" }}>
              <h2 style={{ fontSize: "22px", marginBottom: "12px" }}>Результат intake</h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "12px", marginBottom: "16px" }}>
                <SummaryStat label="Тип документа" value={intake.classified_type} />
                <SummaryStat label="Предмет" value={intake.subject_matter || "—"} />
                <SummaryStat label="Роль сторони" value={intake.primary_party_role || "—"} />
                <SummaryStat label="Юрисдикція" value={intake.jurisdiction || "—"} />
              </div>
              <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
                Ризики: legal {intake.risk_level_legal || "unknown"}, procedural {intake.risk_level_procedural || "unknown"}, financial{" "}
                {intake.risk_level_financial || "unknown"}.
              </p>
              {intake.raw_text_preview && (
                <div style={{ marginTop: "16px" }}>
                  <div style={{ fontSize: "12px", textTransform: "uppercase", color: "var(--text-muted)", marginBottom: "8px" }}>
                    Ключові значення
                  </div>
                  <pre
                    className="card-elevated"
                    style={{
                      padding: "14px",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      fontSize: "13px",
                      lineHeight: 1.5,
                      color: "var(--text-secondary)",
                      margin: 0,
                    }}
                  >
                    {intake.raw_text_preview}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div className="card-elevated" style={{ padding: "24px", color: "var(--text-muted)" }}>
              Після успішного intake тут з’явиться стисла картка справи.
            </div>
          )}

          {precedentMap && (
            <div className="card-elevated" style={{ padding: "24px" }}>
              <h2 style={{ fontSize: "22px", marginBottom: "12px" }}>Precedent map</h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "12px", marginBottom: "16px" }}>
                <SummaryStat label="Запит" value={precedentMap.query_used} />
                <SummaryStat label="Груп" value={precedentMap.groups.length} />
                <SummaryStat label="Рішень" value={precedentMap.refs.length} />
              </div>
              <div style={{ display: "grid", gap: "10px" }}>
                {precedentMap.groups.slice(0, 3).map((group) => (
                  <div key={group.id} className="card-elevated" style={{ padding: "12px 14px" }}>
                    <div style={{ fontWeight: 700, color: "#fff", marginBottom: "4px" }}>{group.pattern_type}</div>
                    <div style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                      Прецедентів: {group.precedent_count}. Сила патерну: {group.pattern_strength ?? 0}.
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {strategy && (
            <div className="card-elevated" style={{ padding: "24px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <h2 style={{ fontSize: "22px", margin: 0 }}>Strategy blueprint</h2>
                <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>ID: {strategy.id}</div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "12px", marginBottom: "24px" }}>
                <SummaryStat
                  label="Шанс виграшу"
                  value={strategy.win_probability ? `${Math.round(strategy.win_probability * 100)}%` : `${Math.round((strategy.confidence_score || 0) * 100)}%`}
                />
                <SummaryStat label="Immediate actions" value={strategy.immediate_actions.length} />
                <SummaryStat label="Critical deadlines" value={strategy.critical_deadlines.length} />
              </div>

              {/* SWOT & Probabilities */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "32px" }}>
                <div className="card-elevated" style={{ padding: "20px", background: "rgba(255,255,255,0.01)" }}>
                  <h3 style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-muted)", marginBottom: "16px", textTransform: 'uppercase' }}>SWOT Аналіз</h3>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                    <div style={{ padding: "10px", background: "rgba(16, 185, 129, 0.05)", borderRadius: "8px", borderLeft: "2px solid var(--success)" }}>
                      <div style={{ fontSize: "10px", fontWeight: 800, color: "var(--success)", marginBottom: "4px" }}>STRENGTHS</div>
                      <ul style={{ fontSize: "11px", color: "var(--text-secondary)", paddingLeft: "14px", margin: 0 }}>
                        {strategy.swot_analysis?.strengths.map((s: string, i: number) => <li key={i}>{s}</li>)}
                      </ul>
                    </div>
                    <div style={{ padding: "10px", background: "rgba(239, 68, 68, 0.05)", borderRadius: "8px", borderLeft: "2px solid var(--error)" }}>
                      <div style={{ fontSize: "10px", fontWeight: 800, color: "var(--error)", marginBottom: "4px" }}>WEAKNESSES</div>
                      <ul style={{ fontSize: "11px", color: "var(--text-secondary)", paddingLeft: "14px", margin: 0 }}>
                        {strategy.swot_analysis?.weaknesses.map((w: string, i: number) => <li key={i}>{w}</li>)}
                      </ul>
                    </div>
                  </div>
                </div>

                <div className="card-elevated" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "16px", background: "rgba(212, 168, 67, 0.02)", border: "1px solid rgba(212, 168, 67, 0.1)" }}>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "4px" }}>Ймовірність успіху (AI)</div>
                    <div style={{ fontSize: "32px", fontWeight: 900, color: "var(--gold-400)" }}>
                      {Math.round((strategy.win_probability || strategy.confidence_score || 0) * 100)}%
                    </div>
                  </div>

                  <button
                    className="btn btn-primary"
                    onClick={() => void onRunJudgeSimulation()}
                    disabled={isSimulating}
                    style={{ width: "100%", marginTop: "auto" }}
                  >
                    {isSimulating ? "Симуляція..." : "⚖️ Сформувати вердикт судді"}
                  </button>
                </div>
              </div>

              {/* Judge Simulation Result */}
              {judgeSimulation && (
                <div className="card-elevated animate-fade-in" style={{
                  padding: "24px",
                  marginBottom: "32px",
                  border: "1px solid var(--gold-400)",
                  background: "rgba(212, 168, 67, 0.03)"
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "20px" }}>
                    <div>
                      <h2 style={{ fontSize: "20px", fontWeight: 800, color: "var(--gold-400)", marginBottom: "4px" }}>
                        Симуляція рішення суду
                      </h2>
                      <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                        Персона судді: <span style={{ color: "#fff", fontWeight: 600 }}>{judgeSimulation.judge_persona}</span>
                      </div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "4px" }}>Оцінка судді</div>
                      <div style={{ fontSize: "24px", fontWeight: 900, color: judgeSimulation.verdict_probability > 0.6 ? "var(--success)" : "var(--error)" }}>
                        {Math.round(judgeSimulation.verdict_probability * 100)}%
                      </div>
                    </div>
                  </div>

                  <div style={{ fontStyle: "italic", color: "var(--text-secondary)", borderLeft: "4px solid var(--gold-400)", paddingLeft: "16px", marginBottom: "24px", fontSize: "15px", lineHeight: 1.6 }}>
                    "{judgeSimulation.judge_commentary}"
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
                    <div>
                      <h4 style={{ fontSize: "13px", fontWeight: 700, color: "var(--error)", marginBottom: "12px" }}>Слабкі місця</h4>
                      <ul style={{ fontSize: "12px", color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: "8px", paddingLeft: "16px" }}>
                        {judgeSimulation.key_vulnerabilities.map((v: string, i: number) => <li key={i}>{v}</li>)}
                      </ul>
                    </div>
                    <div>
                      <h4 style={{ fontSize: "13px", fontWeight: 700, color: "var(--success)", marginBottom: "12px" }}>Сильні сторони</h4>
                      <ul style={{ fontSize: "12px", color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: "8px", paddingLeft: "16px" }}>
                        {judgeSimulation.strong_points.map((v: string, i: number) => <li key={i}>{v}</li>)}
                      </ul>
                    </div>
                  </div>

                  <div style={{ marginTop: "24px", padding: "16px", background: "rgba(255,255,255,0.02)", borderRadius: "12px" }}>
                    <h4 style={{ fontSize: "13px", fontWeight: 700, color: "#fff", marginBottom: "8px" }}>Рекомендації щодо виправлення</h4>
                    <p style={{ fontSize: "13px", color: "var(--text-muted)", margin: 0 }}>
                      {judgeSimulation.suggested_corrections.join(". ")}
                    </p>
                  </div>
                </div>
              )}

              {strategy.financial_strategy && (
                <div style={{ marginBottom: "24px" }}>
                  <div style={{ fontSize: "12px", textTransform: "uppercase", color: "var(--text-muted)", marginBottom: "12px", fontWeight: 700, letterSpacing: '1px' }}>
                    Economic Outlook & ROI
                  </div>
                  <div className="card-elevated" style={{ padding: "20px", background: 'linear-gradient(145deg, rgba(255,255,255,0.02), transparent)' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                      <div>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>EXPECTED RECOVERY</div>
                        <div style={{ fontSize: '20px', fontWeight: 900, color: 'var(--success)' }}>
                          {strategy.financial_strategy.expected_recovery_min?.toLocaleString()} - {strategy.financial_strategy.expected_recovery_max?.toLocaleString()} ₴
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>ESTIMATED COSTS</div>
                        <div style={{ fontSize: '20px', fontWeight: 900, color: 'var(--danger)' }}>
                          {(strategy.financial_strategy.estimated_court_fees + strategy.financial_strategy.estimated_attorney_costs)?.toLocaleString()} ₴
                        </div>
                      </div>
                    </div>
                    <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Economic Viability Score</span>
                        <span style={{ fontSize: '13px', fontWeight: 800, color: strategy.financial_strategy.economic_viability_score > 0.7 ? 'var(--success)' : 'var(--gold-400)' }}>
                          {Math.round(strategy.financial_strategy.economic_viability_score * 100)}%
                        </span>
                      </div>
                      <div style={{ height: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px' }}>
                        <div style={{ height: '100%', background: 'var(--gold-500)', width: `${strategy.financial_strategy.economic_viability_score * 100}%`, borderRadius: '2px' }}></div>
                      </div>
                      <p style={{ fontSize: '12px', fontStyle: 'italic', color: 'var(--text-muted)', marginTop: '12px' }}>
                        Rationale: {strategy.financial_strategy.roi_rationale}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {strategy.timeline_projection && strategy.timeline_projection.length > 0 && (
                <div style={{ marginBottom: "24px" }}>
                  <div style={{ fontSize: "12px", textTransform: "uppercase", color: "var(--text-muted)", marginBottom: "12px", fontWeight: 700, letterSpacing: '1px' }}>
                    Procedural Timeline Roadmap
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {strategy.timeline_projection.map((step: any, idx: number) => (
                      <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                          <div style={{
                            width: '24px', height: '24px', borderRadius: '50%',
                            background: step.status === 'current' ? 'var(--gold-500)' : 'rgba(255,255,255,0.1)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: 900,
                            color: step.status === 'current' ? '#000' : '#fff'
                          }}>
                            {idx + 1}
                          </div>
                          {idx < (strategy.timeline_projection?.length || 0) - 1 && (
                            <div style={{ width: '1px', height: '20px', background: 'rgba(255,255,255,0.1)' }}></div>
                          )}
                        </div>
                        <div className="card-elevated" style={{ flexGrow: 1, padding: '12px', fontSize: '13px', display: 'flex', justifyContent: 'space-between' }}>
                          <span style={{ fontWeight: 600 }}>{step.stage}</span>
                          <span style={{ color: 'var(--text-muted)' }}>~{step.duration_days} днів</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {strategy.penalty_forecast && strategy.penalty_forecast.total_extra > 0 && (
                <div style={{ marginBottom: "24px" }}>
                  <div style={{ fontSize: "12px", textTransform: "uppercase", color: "var(--text-muted)", marginBottom: "12px", fontWeight: 700, letterSpacing: '1px' }}>
                    Damage Recovery Forecaster: 3% & Inflation
                  </div>
                  <div className="card-elevated" style={{ padding: "20px", borderLeft: "3px solid var(--purple-400)" }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '15px' }}>
                      <div style={{ textAlign: "center" }}>
                        <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '5px' }}>3% ANNUAL</div>
                        <div style={{ fontSize: '16px', fontWeight: 800 }}>{strategy.penalty_forecast.three_percent_annual?.toLocaleString()} ₴</div>
                      </div>
                      <div style={{ textAlign: "center" }}>
                        <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '5px' }}>INFLATION</div>
                        <div style={{ fontSize: '16px', fontWeight: 800 }}>{strategy.penalty_forecast.inflation_losses?.toLocaleString()} ₴</div>
                      </div>
                      <div style={{ textAlign: "center" }}>
                        <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '5px' }}>PENALTIES</div>
                        <div style={{ fontSize: '16px', fontWeight: 800 }}>{strategy.penalty_forecast.penalties_contractual?.toLocaleString()} ₴</div>
                      </div>
                    </div>
                    <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Calculation basis: </span>
                        <span style={{ fontSize: '12px', fontWeight: 700 }}>{strategy.penalty_forecast.basis_days} days</span>
                      </div>
                      <div>
                        <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginRight: '10px' }}>TOTAL EXTRA:</span>
                        <span style={{ fontSize: '18px', fontWeight: 900, color: 'var(--purple-400)' }}>+ {strategy.penalty_forecast.total_extra?.toLocaleString()} ₴</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <p style={{ color: "var(--text-secondary)", fontSize: "14px", borderTop: "1px solid rgba(255,255,255,0.05)", paddingTop: "12px" }}>
                {strategy.recommended_next_steps || "Рекомендації ще не побудовані."}
              </p>
            </div>
          )}

          {generated && (
            <div className="card-elevated" style={{ padding: "24px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <h2 style={{ fontSize: "22px", margin: 0 }}>Згенерований документ</h2>
                <a
                  href={getExportDocxUrl(generated.document_id, getToken(), getUserId())}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-secondary"
                  style={{ fontSize: "12px", padding: "6px 12px" }}
                >
                  📥 Скачати .docx
                </a>
              </div>
              <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "10px" }}>
                ID документа: <strong style={{ color: "#fff" }}>{generated.document_id}</strong>
              </div>
              <div
                className="card-elevated"
                style={{
                  padding: "14px",
                  maxHeight: "260px",
                  overflowY: "auto",
                  whiteSpace: "pre-wrap",
                  fontSize: "13px",
                  color: "var(--text-secondary)",
                }}
              >
                {generated.generated_text}
              </div>
            </div>
          )}

          {audit && (
            <div className="card-elevated" style={{ padding: "24px" }}>
              <h2 style={{ fontSize: "22px", marginBottom: "12px" }}>Strategy audit</h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "12px", marginBottom: "16px" }}>
                <SummaryStat label="Цитат практики" value={audit.precedent_citations.length} />
                <SummaryStat label="Контраргументів" value={audit.counter_argument_addresses.length} />
              </div>
              <div style={{ display: "grid", gap: "10px", fontSize: "14px", color: "var(--text-secondary)" }}>
                <div>{audit.evidence_positioning_notes || "Немає evidence notes."}</div>
                <div>{audit.procedure_optimization_notes || "Немає procedure notes."}</div>
                <div>{audit.appeal_proofing_notes || "Немає appeal-proofing notes."}</div>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
