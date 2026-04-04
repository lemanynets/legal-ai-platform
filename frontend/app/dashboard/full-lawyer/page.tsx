"use client";

import { FormEvent, ReactNode, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { getToken, getUserId } from "@/lib/auth";
import {
  autoProcessFullLawyer,
  autoProcessFullLawyerPreflight,
  exportDocument,
  exportFullLawyerPreflightReport,
  getCase,
  getCases,
  searchCaseLaw,
  type FullLawyerPreflightResponse,
  type FullLawyerResponse,
  type Case,
  type CaseDetail,
  type CaseLawSearchItem,
} from "@/lib/api";

type SectionPair = [string, keyof FullLawyerResponse];

const SECTION_PAIRS: SectionPair[] = [
  ["Workflow stages", "workflow_stages"],
  ["Procedural timeline", "procedural_timeline"],
  ["Evidence matrix", "evidence_matrix"],
  ["Fact chronology matrix", "fact_chronology_matrix"],
  ["Burden of proof map", "burden_of_proof_map"],
  ["Drafting instructions", "drafting_instructions"],
  ["Opponent weakness map", "opponent_weakness_map"],
  ["Evidence collection plan", "evidence_collection_plan"],
  ["Factual circumstances blocks", "factual_circumstances_blocks"],
  ["Legal qualification blocks", "legal_qualification_blocks"],
  ["Prayer part variants", "prayer_part_variants"],
  ["Counterargument response matrix", "counterargument_response_matrix"],
  ["Document narrative completeness", "document_narrative_completeness"],
  ["Case law application matrix", "case_law_application_matrix"],
  ["Procedural violation hypotheses", "procedural_violation_hypotheses"],
  ["Document fact enrichment plan", "document_fact_enrichment_plan"],
  ["Hearing positioning notes", "hearing_positioning_notes"],
  ["Process stage action map", "process_stage_action_map"],
  ["Readiness breakdown", "readiness_breakdown"],
  ["Party profile", "party_profile"],
  ["Jurisdiction recommendation", "jurisdiction_recommendation"],
  ["E-court submission preview", "e_court_submission_preview"],
  ["Consistency report", "consistency_report"],
  ["Remedy coverage", "remedy_coverage"],
  ["Citation pack", "citation_pack"],
  ["Fee scenarios", "fee_scenarios"],
  ["Filing risk simulation", "filing_risk_simulation"],
  ["Procedural defect scan", "procedural_defect_scan"],
  ["Evidence admissibility map", "evidence_admissibility_map"],
  ["Motion recommendations", "motion_recommendations"],
  ["Hearing preparation plan", "hearing_preparation_plan"],
  ["Package completeness", "package_completeness"],
  ["Opponent objections", "opponent_objections"],
  ["Settlement strategy", "settlement_strategy"],
  ["Enforcement plan", "enforcement_plan"],
  ["CPC compliance check", "cpc_compliance_check"],
  ["Procedural document blueprint", "procedural_document_blueprint"],
  ["Deadline control", "deadline_control"],
  ["Court fee breakdown", "court_fee_breakdown"],
  ["Filing attachments register", "filing_attachments_register"],
  ["CPC 175 requisites map", "cpc_175_requisites_map"],
  ["CPC 177 attachments map", "cpc_177_attachments_map"],
  ["Prayer part audit", "prayer_part_audit"],
  ["Fact-norm-evidence chain", "fact_norm_evidence_chain"],
  ["Pre-filing red flags", "pre_filing_red_flags"],
  ["Text section audit", "text_section_audit"],
  ["Service plan", "service_plan"],
  ["Prayer rewrite suggestions", "prayer_rewrite_suggestions"],
  ["Contradiction hotspots", "contradiction_hotspots"],
  ["Judge questions simulation", "judge_questions_simulation"],
  ["Citation quality gate", "citation_quality_gate"],
  ["Filing decision card", "filing_decision_card"],
  ["Processual language audit", "processual_language_audit"],
  ["Evidence gap actions", "evidence_gap_actions"],
  ["Deadline alert board", "deadline_alert_board"],
  ["Filing packet order", "filing_packet_order"],
  ["Opponent response playbook", "opponent_response_playbook"],
  ["Limitation period card", "limitation_period_card"],
  ["Jurisdiction challenge guard", "jurisdiction_challenge_guard"],
  ["Claim formula card", "claim_formula_card"],
  ["Filing cover letter", "filing_cover_letter"],
  ["Execution step tracker", "execution_step_tracker"],
  ["Version control card", "version_control_card"],
  ["E-court packet readiness", "e_court_packet_readiness"],
  ["Hearing script pack", "hearing_script_pack"],
  ["Settlement offer card", "settlement_offer_card"],
  ["Appeal reserve card", "appeal_reserve_card"],
  ["Procedural costs allocator card", "procedural_costs_allocator_card"],
  ["Document export readiness", "document_export_readiness"],
  ["Filing submission checklist card", "filing_submission_checklist_card"],
  ["Post-filing monitoring board", "post_filing_monitoring_board"],
  ["Legal research backlog", "legal_research_backlog"],
  ["Procedural consistency scorecard", "procedural_consistency_scorecard"],
  ["Hearing evidence order card", "hearing_evidence_order_card"],
  ["Digital signature readiness", "digital_signature_readiness"],
  ["Case law update watchlist", "case_law_update_watchlist"],
  ["Court behavior forecast card", "court_behavior_forecast_card"],
  ["Evidence pack compression plan", "evidence_pack_compression_plan"],
  ["Filing channel strategy card", "filing_channel_strategy_card"],
  ["Legal budget timeline card", "legal_budget_timeline_card"],
  ["Counterparty pressure map", "counterparty_pressure_map"],
  ["Courtroom timeline scenarios", "courtroom_timeline_scenarios"],
  ["Evidence authenticity checklist", "evidence_authenticity_checklist"],
  ["Remedy priority matrix", "remedy_priority_matrix"],
  ["Judge question drill card", "judge_question_drill_card"],
  ["Client instruction packet", "client_instruction_packet"],
  ["Procedural risk heatmap", "procedural_risk_heatmap"],
  ["Evidence disclosure plan", "evidence_disclosure_plan"],
  ["Settlement negotiation script", "settlement_negotiation_script"],
  ["Hearing readiness scorecard", "hearing_readiness_scorecard"],
  ["Advocate signoff packet", "advocate_signoff_packet"],
];

function hasContent(value: unknown): boolean {
  if (value == null) return false;
  if (typeof value === "string") return value.trim().length > 0;
  if (typeof value === "number" || typeof value === "boolean") return true;
  if (Array.isArray(value)) return value.some(hasContent);
  if (typeof value === "object") return Object.values(value as Record<string, unknown>).some(hasContent);
  return false;
}

function labelFor(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatScalar(value: string | number | boolean): string {
  return typeof value === "boolean" ? (value ? "Так" : "Ні") : String(value);
}

function normalizeTextValue(path: string, value: string): string {
  if (path.endsWith("-check") && value === "Final submission gate") return "Фінальний шлюз подання";
  return value;
}

function badge(status: string): ReactNode {
  const s = status.toLowerCase();
  const cls = ["ok", "pass", "ready", "conditional_pass", "conditional_go"].includes(s)
    ? "badge-success"
    : ["warn", "warning", "partial", "conditional"].includes(s)
      ? "badge-warning"
      : ["fail", "blocked", "error", "not_ready", "review_needed"].includes(s)
        ? "badge-danger"
        : "badge-muted";
  return <span className={`badge ${cls}`}>{status}</span>;
}

function renderData(value: unknown, path: string): ReactNode {
  if (!hasContent(value)) return <span style={{ color: "var(--text-muted)" }}>—</span>;
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    const output = typeof value === "string" ? normalizeTextValue(path, value) : formatScalar(value);
    return <span style={{ color: "var(--text-secondary)", whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{output}</span>;
  }
  if (Array.isArray(value)) {
    return (
      <div style={{ display: "grid", gap: "10px" }}>
        {value.map((item, index) => (
          <div key={`${path}-${index}`} style={{ padding: "12px 14px", borderRadius: "12px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
            {renderData(item, `${path}-${index}`)}
          </div>
        ))}
      </div>
    );
  }
  return (
    <div style={{ display: "grid", gap: "10px" }}>
      {Object.entries(value as Record<string, unknown>)
        .filter(([key, item]) => key !== "note" && hasContent(item))
        .map(([key, item]) => (
          <div key={`${path}-${key}`} style={{ padding: "12px 14px", borderRadius: "12px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <div style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase", color: "var(--text-muted)", marginBottom: "6px" }}>{labelFor(key)}</div>
            {renderData(item, `${path}-${key}`)}
          </div>
        ))}
    </div>
  );
}

function Section({ title, value }: { title: string; value: unknown }) {
  if (!hasContent(value)) return null;
  return (
    <div className="card-elevated" style={{ padding: "24px" }}>
      <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px", color: "var(--text-primary)" }}>{title}</h2>
      {renderData(value, title)}
    </div>
  );
}

function FullLawyerPageContent() {
  const searchParams = useSearchParams();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [maxDocuments, setMaxDocuments] = useState(4);
  const [generatePackage, setGeneratePackage] = useState(true);
  const [processualOnly, setProcessualOnly] = useState(true);
  const [autoPreflightBeforeRun, setAutoPreflightBeforeRun] = useState(true);
  const [clarificationAnswers, setClarificationAnswers] = useState<Record<string, string>>({});
  const [reviewConfirmations, setReviewConfirmations] = useState<Record<string, boolean>>({});
  const [result, setResult] = useState<FullLawyerResponse | null>(null);
  const [preflightResult, setPreflightResult] = useState<FullLawyerPreflightResponse | null>(null);
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [selectedCaseDetail, setSelectedCaseDetail] = useState<CaseDetail | null>(null);
  const [caseDecisions, setCaseDecisions] = useState<CaseLawSearchItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [preflightLoading, setPreflightLoading] = useState(false);
  const [downloadingKey, setDownloadingKey] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const loadData = useCallback(async () => {
    try {
      const data = await getCases(getToken(), getUserId());
      setCases(data);
      const requestedCaseId = searchParams.get("case_id") || "";
      if (requestedCaseId && data.some((item) => item.id === requestedCaseId)) {
        setSelectedCaseId(requestedCaseId);
      }
    } catch (err) { console.error(err); }
  }, [searchParams]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

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

  const sections = useMemo(() => {
    if (!result) return [];
    return SECTION_PAIRS.map(([title, key]) => ({ title, value: result[key] })).filter((item) => hasContent(item.value));
  }, [result]);

  const onDrop = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragOver(false);
    const file = event.dataTransfer.files[0];
    if (file) setSelectedFile(file);
  }, []);

  const onDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragOver(true);
  }, []);

  const onDragLeave = useCallback(() => setIsDragOver(false), []);

  async function runPreflight(file: File): Promise<FullLawyerPreflightResponse> {
    return autoProcessFullLawyerPreflight({ file, max_documents: maxDocuments, processual_only: processualOnly, clarifications_json: clarificationAnswers, review_confirmations_json: reviewConfirmations, consume_quota: false, case_id: selectedCaseId || undefined }, getToken(), getUserId());
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!selectedFile) return setError("Спочатку оберіть файл справи.");
    setLoading(true); setError(""); setInfo("");
    try {
      let draftMode = true;
      if (autoPreflightBeforeRun) {
        setPreflightLoading(true);
        try {
          const pf = await runPreflight(selectedFile);
          setPreflightResult(pf);
          draftMode = pf.package_generation_hint.recommended_package_mode === "draft" || (!pf.package_generation_hint.can_generate_final_package && pf.package_generation_hint.can_generate_draft_package);
          if (pf.status !== "ok") return void setInfo(`Префлайт зупинив запуск: ${pf.status}.`);
        } finally { setPreflightLoading(false); }
      }
      const data = await autoProcessFullLawyer({ file: selectedFile, max_documents: maxDocuments, processual_only: processualOnly, clarifications_json: clarificationAnswers, review_confirmations_json: reviewConfirmations, generate_package: generatePackage, generate_package_draft_on_hard_stop: draftMode, case_id: selectedCaseId || undefined }, getToken(), getUserId());
      setResult(data);
      setInfo(`Сформовано документів: ${data.generated_documents.length}.`);
    } catch (err) { setError(String(err)); } finally { setLoading(false); }
  }

  async function onPreflight(): Promise<void> {
    if (!selectedFile) return setError("Спочатку оберіть файл справи.");
    setPreflightLoading(true); setError(""); setInfo("");
    try {
      const pf = await runPreflight(selectedFile);
      setPreflightResult(pf);
      setInfo(pf.status === "ok" ? "Префлайт пройдено." : `Префлайт: ${pf.status}`);
    } catch (err) { setError(String(err)); } finally { setPreflightLoading(false); }
  }

  async function onExportPreflight(format: "pdf" | "docx"): Promise<void> {
    if (!selectedFile) return;
    const key = `preflight:${format}`; setDownloadingKey(key); setError("");
    try {
      const blob = await exportFullLawyerPreflightReport({ file: selectedFile, format, max_documents: maxDocuments, processual_only: processualOnly, clarifications_json: clarificationAnswers, review_confirmations_json: reviewConfirmations, consume_quota: false }, getToken(), getUserId());
      const url = URL.createObjectURL(blob); const a = document.createElement("a");
      a.href = url; a.download = `preflight-report.${format}`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    } catch (err) { setError(String(err)); } finally { setDownloadingKey(null); }
  }

  async function onDownloadDocument(documentId: string, format: "pdf" | "docx"): Promise<void> {
    const key = `${documentId}:${format}`; setDownloadingKey(key); setError("");
    try {
      const blob = await exportDocument(documentId, format, false, getToken(), getUserId());
      const url = URL.createObjectURL(blob); const a = document.createElement("a");
      a.href = url; a.download = `${documentId}.${format}`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    } catch (err) { setError(String(err)); } finally { setDownloadingKey(null); }
  }

  return (
    <div>
      <div className="section-header"><div><h1 className="section-title">Повний юрист</h1><p className="section-subtitle">Завантажте матеріали справи та отримайте стратегію, ризики й пакет документів.</p></div><span className="badge badge-gold">PRO+</span></div>
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
      <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
        <div className="card-elevated" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px", color: "var(--text-primary)" }}>Файл справи</h2>
          <label htmlFor="fileInput" className="form-label">Файл (txt/pdf/docx)</label>
          <div className={`upload-zone ${isDragOver ? "dragover" : ""}`} onDrop={onDrop} onDragOver={onDragOver} onDragLeave={onDragLeave} onClick={() => document.getElementById("fileInput")?.click()} style={{ cursor: "pointer", minHeight: "180px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "10px", borderRadius: "18px", border: `1px dashed ${isDragOver ? "var(--gold-500)" : "rgba(255,255,255,0.14)"}`, background: isDragOver ? "rgba(212,168,67,0.08)" : "rgba(255,255,255,0.02)" }}>
            <div style={{ fontSize: "30px" }}>{selectedFile ? "Файл" : "Завантаження"}</div>
            <div style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-primary)" }}>{selectedFile ? selectedFile.name : "Перетягніть файл сюди або натисніть для вибору"}</div>
            <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>{selectedFile ? `${(selectedFile.size / 1024).toFixed(1)} KB • ${selectedFile.type || "невідомий формат"}` : "Підтримуються: .txt .pdf .docx .doc .rtf .md .html"}</div>
          </div>
          <input id="fileInput" aria-label="Файл (txt/pdf/docx)" type="file" accept=".txt,.pdf,.docx,.doc,.rtf,.md,.html,.htm" style={{ display: "none" }} onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} />
        </div>
        <div className="card-elevated" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px", color: "var(--text-primary)" }}>Налаштування запуску</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "14px" }}>
            <div className="form-group"><label className="form-label" htmlFor="maxDocuments">Макс. документів</label><select id="maxDocuments" className="form-select" value={maxDocuments} onChange={(event) => setMaxDocuments(Number(event.target.value))}>{[1,2,3,4,5].map((n) => <option key={n} value={n}>{n}</option>)}</select></div>
            <div className="form-group"><label className="form-label" htmlFor="generatePackage">Формувати пакет</label><select id="generatePackage" className="form-select" value={String(generatePackage)} onChange={(event) => setGeneratePackage(event.target.value === "true")}><option value="true">Так</option><option value="false">Ні</option></select></div>
            <div className="form-group"><label className="form-label" htmlFor="processualOnly">Лише процесуальні</label><select id="processualOnly" className="form-select" value={String(processualOnly)} onChange={(event) => setProcessualOnly(event.target.value === "true")}><option value="true">Так (рекомендовано)</option><option value="false">Ні</option></select></div>
            <div className="form-group"><label className="form-label" htmlFor="autoPreflight">Автопрефлайт перед повним запуском</label><select id="autoPreflight" aria-label="Автопрефлайт перед повним запуском" className="form-select" value={String(autoPreflightBeforeRun)} onChange={(event) => setAutoPreflightBeforeRun(event.target.value === "true")}><option value="true">Так (рекомендовано)</option><option value="false">Ні</option></select></div>
            <div className="form-group"><label className="form-label">Пов'язати зі справою</label><select className="form-select" value={selectedCaseId} onChange={e => setSelectedCaseId(e.target.value)}><option value="">Без прив'язки</option>{cases.map(c => <option key={c.id} value={c.id}>{c.title} ({c.case_number || "No #"})</option>)}</select></div>
          </div>
        </div>
        {error && <div className="alert alert-error">⚠ {error}</div>}
        {info && <div className="alert alert-info">{info}</div>}
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          <button type="button" className="btn btn-secondary" onClick={() => void onPreflight()} disabled={!selectedFile || preflightLoading || loading}>{preflightLoading ? "Перевірка..." : "Запустити префлайт"}</button>
          {selectedFile && autoPreflightBeforeRun && <button type="button" className="btn btn-secondary" disabled>Запустити з preflight-виправленнями</button>}
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => void onExportPreflight("pdf")} disabled={!selectedFile || !!downloadingKey}>Звіт PDF</button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => void onExportPreflight("docx")} disabled={!selectedFile || !!downloadingKey}>Звіт DOCX</button>
          <button type="submit" className="btn btn-primary" disabled={!selectedFile || loading || preflightLoading}>{loading ? "Обробка..." : "Запустити повний режим"}</button>
        </div>
      </form>
      {preflightResult && <Section title="Preflight" value={{ status: preflightResult.status, package_generation_hint: preflightResult.package_generation_hint, next_actions: preflightResult.next_actions, preflight_submission_gate: preflightResult.final_submission_gate }} />}
      {result && (
        <div className="animate-fade-in" style={{ marginTop: "32px", display: "flex", flexDirection: "column", gap: "24px" }}>
          <div className="card-elevated" style={{ padding: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap", marginBottom: "16px" }}><h2 style={{ fontSize: "18px", fontWeight: 800, color: "#fff" }}>Підсумок справи</h2><span className="badge badge-gold">Confidence score: {Math.round(result.confidence_score * 100)}%</span></div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px" }}>
              <div className="stat-card"><div className="stat-label">Тип спору</div><div className="stat-value" style={{ fontSize: "20px" }}>{result.summary.dispute_type}</div></div>
              <div className="stat-card"><div className="stat-label">Процедура</div><div className="stat-value" style={{ fontSize: "20px" }}>{result.summary.procedure}</div></div>
              <div className="stat-card"><div className="stat-label">Терміновість</div><div className="stat-value" style={{ fontSize: "20px" }}>{result.summary.urgency}</div></div>
              <div className="stat-card"><div className="stat-label">Орієнтовний судовий збір</div><div className="stat-value" style={{ fontSize: "20px" }}>{result.summary.estimated_court_fee_uah ? `${result.summary.estimated_court_fee_uah.toLocaleString()} грн` : "—"}</div></div>
            </div>
          </div>
          <Section title="AI analysis highlights" value={{ analysis_highlights: result.analysis_highlights, next_actions: result.next_actions, procedural_conclusions: result.procedural_conclusions, legal_basis: result.legal_basis, strategy_steps: result.strategy_steps }} />
          <Section title="Ready for filing" value={{ ready_for_filing: result.ready_for_filing, readiness_breakdown: result.readiness_breakdown }} />
          <div className="card-elevated" style={{ padding: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap", marginBottom: "16px" }}><h2 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)" }}>Generated documents</h2>{badge(result.status)}</div>
            <div style={{ display: "grid", gap: "12px" }}>
              {result.generated_documents.map((document) => (
                <div key={document.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", padding: "12px 14px", borderRadius: "12px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
                  <div><div style={{ color: "#fff", fontWeight: 700 }}>{document.title || document.doc_type}</div><div style={{ color: "var(--text-muted)", fontSize: "12px" }}>{document.doc_type}</div></div>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => void onDownloadDocument(document.id, "docx")} disabled={!!downloadingKey}>{downloadingKey === `${document.id}:docx` ? "..." : "DOCX"}</button>
                    <button type="button" className="btn btn-primary btn-sm" onClick={() => void onDownloadDocument(document.id, "pdf")} disabled={!!downloadingKey}>{downloadingKey === `${document.id}:pdf` ? "..." : "PDF"}</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <Section title="Filing package status" value={{ filing_package: result.filing_package, processual_package_gate: result.processual_package_gate, advocate_signoff_packet: result.advocate_signoff_packet }} />
          <div className="card-elevated" style={{ padding: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap", marginBottom: "16px" }}><h2 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)" }}>Final submission gate</h2>{badge(result.final_submission_gate.status)}</div>
            {result.final_submission_gate.hard_stop && <div className="alert alert-warning" style={{ marginBottom: "12px" }}>Жорсткий стоп: подання заблоковане</div>}
            {(result.final_submission_gate.critical_deadlines ?? []).length > 0 && <div style={{ marginBottom: "12px" }}><div style={{ color: "var(--text-primary)", fontWeight: 700, marginBottom: "8px" }}>Критичні строки:</div>{renderData(result.final_submission_gate.critical_deadlines ?? [], "critical-deadlines")}</div>}
            {renderData({ blockers: result.final_submission_gate.blockers, next_step: result.final_submission_gate.next_step, note: result.final_submission_gate.note }, "final-gate")}
          </div>
          {sections.map((section) => <Section key={section.title} title={section.title} value={section.value} />)}
        </div>
      )}
    </div>
  );
}

export default function FullLawyerPage() {
  return (
    <Suspense fallback={<div className="card-elevated" style={{ padding: 24 }}>Завантаження повного режиму...</div>}>
      <FullLawyerPageContent />
    </Suspense>
  );
}
