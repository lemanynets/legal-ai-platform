"use client";

import Link from "next/link";
import { FormEvent, Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { getToken, getUserId } from "@/lib/auth";
import {
  autoProcessDecisionAnalysis,
  autoProcessDecisionAnalysisPackage,
  exportDecisionAnalysisHistoryReport,
  exportDecisionAnalysisReport,
  getCase,
  getDecisionAnalysisHistory,
  getCases,
  searchCaseLaw,
  type Case,
  type CaseDetail,
  type CaseLawSearchItem,
  type DecisionAnalysisHistoryResponse,
  type DecisionAnalysisPackageResponse,
  type DecisionAnalysisResponse
} from "@/lib/api";

function DecisionAnalysisPageContent() {
  const searchParams = useSearchParams();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [includeRecentCaseLaw, setIncludeRecentCaseLaw] = useState(true);
  const [caseLawDays, setCaseLawDays] = useState("365");
  const [caseLawLimit, setCaseLawLimit] = useState("12");
  const [caseLawCourtType, setCaseLawCourtType] = useState("");
  const [caseLawSource, setCaseLawSource] = useState("");
  const [onlySupremeCaseLaw, setOnlySupremeCaseLaw] = useState(false);
  const [aiEnhance, setAiEnhance] = useState(true);
  const [packageMaxDocuments, setPackageMaxDocuments] = useState("4");
  const [packageIncludeWarnReadiness, setPackageIncludeWarnReadiness] = useState(true);
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [selectedCaseDetail, setSelectedCaseDetail] = useState<CaseDetail | null>(null);
  const [caseDecisions, setCaseDecisions] = useState<CaseLawSearchItem[]>([]);

  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [downloadingKey, setDownloadingKey] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [result, setResult] = useState<DecisionAnalysisResponse | null>(null);
  const [packageResult, setPackageResult] = useState<DecisionAnalysisPackageResponse | null>(null);
  const [history, setHistory] = useState<DecisionAnalysisHistoryResponse | null>(null);

  useEffect(() => {
    getCases(getToken(), getUserId())
      .then((items) => {
        setCases(items);
        const requestedCaseId = searchParams.get("case_id") || "";
        if (requestedCaseId && items.some((item) => item.id === requestedCaseId)) {
          setSelectedCaseId(requestedCaseId);
        }
      })
      .catch((err) => console.error("Failed to load cases", err));
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

  async function onSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!selectedFile) {
        setError("Оберіть файл для аналізу.");
        return;
    }
    setLoading(true); setError(""); setInfo("");
    try {
      const response = await autoProcessDecisionAnalysis(
        {
          file: selectedFile,
          include_recent_case_law: includeRecentCaseLaw,
          case_law_days: Number(caseLawDays) || 365,
          case_law_limit: Number(caseLawLimit) || 12,
          case_law_court_type: caseLawCourtType || undefined,
          case_law_source: caseLawSource || undefined,
          only_supreme_case_law: onlySupremeCaseLaw,
          ai_enhance: aiEnhance,
          case_id: selectedCaseId || undefined
        },
        getToken(), getUserId()
      );
      setResult(response);
      setInfo("Аналіз рішення завершено.");
    } catch (err) { setResult(null); setError(String(err)); }
    finally { setLoading(false); }
  }

  async function onExport(format: "pdf" | "docx"): Promise<void> {
    if (!selectedFile) return;
    const key = `export:${format}`;
    setDownloadingKey(key); setError(""); setInfo("");
    try {
      const blob = await exportDecisionAnalysisReport(
        {
          file: selectedFile, format,
          include_recent_case_law: includeRecentCaseLaw,
          case_law_days: Number(caseLawDays) || 365,
          case_law_limit: Number(caseLawLimit) || 12,
          case_law_court_type: caseLawCourtType || undefined,
          case_law_source: caseLawSource || undefined,
          only_supreme_case_law: onlySupremeCaseLaw,
          ai_enhance: aiEnhance,
          consume_quota: false,
          case_id: selectedCaseId || undefined
        },
        getToken(), getUserId()
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `decision-analysis-${format}.${format}`;
      document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url);
    } catch (err) { setError(String(err)); }
    finally { setDownloadingKey(null); }
  }

  async function onLoadHistory(): Promise<void> {
    setLoadingHistory(true); setError("");
    try {
      const payload = await getDecisionAnalysisHistory({ page: 1, page_size: 20, event: "all" }, getToken(), getUserId());
      setHistory(payload);
    } catch (err) { setError(String(err)); setHistory(null); }
    finally { setLoadingHistory(false); }
  }

  async function onGeneratePackage(): Promise<void> {
    if (!selectedFile) return;
    setDownloadingKey("package:generate"); setError(""); setInfo("");
    try {
      const response = await autoProcessDecisionAnalysisPackage(
        {
          file: selectedFile,
          max_documents: Number(packageMaxDocuments) || 4,
          include_warn_readiness: packageIncludeWarnReadiness,
          include_recent_case_law: includeRecentCaseLaw,
          case_law_days: Number(caseLawDays) || 365,
          case_law_limit: Number(caseLawLimit) || 12,
          case_law_court_type: caseLawCourtType || undefined,
          case_law_source: caseLawSource || undefined,
          only_supreme_case_law: onlySupremeCaseLaw,
          ai_enhance: aiEnhance,
          consume_analysis_quota: false,
          case_id: selectedCaseId || undefined
        },
        getToken(), getUserId()
      );
      setPackageResult(response);
      setInfo("Пакет документів згенеровано.");
    } catch (err) { setPackageResult(null); setError(String(err)); }
    finally { setDownloadingKey(null); }
  }

  const scoreColor = (score: number) => {
    if (score >= 80) return "var(--success)";
    if (score >= 50) return "var(--warning)";
    return "var(--danger)";
  };

  return (
    <div>
      <div className="section-header">
        <div>
          <h1 className="section-title">Аналіз судового рішення</h1>
          <p className="section-subtitle">Глибокий аудит судового акта з підбором практики та оцінкою перспектив</p>
        </div>
      </div>

      {info && <div className="card-elevated" style={{ padding: "12px 16px", marginBottom: "16px", borderLeft: "3px solid var(--success)", color: "var(--success)" }}>✓ {info}</div>}
      {error && <div className="preflight-block" style={{ marginBottom: 16 }}><span style={{ color: "var(--danger)" }}>⚠ {error}</span></div>}
      {selectedCaseDetail && (
        <div className="card-elevated" style={{ padding: "16px 18px", marginBottom: "16px", border: "1px solid rgba(96,165,250,0.18)", background: "rgba(96,165,250,0.06)" }}>
          <div style={{ fontSize: "12px", color: "#93c5fd", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "6px" }}>Контекст справи</div>
          <div style={{ fontSize: "15px", fontWeight: 700, color: "#fff" }}>{selectedCaseDetail.title}</div>
          <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "6px" }}>
            {selectedCaseDetail.case_number ? `Номер: ${selectedCaseDetail.case_number}` : "Номер справи не заповнений"}
            {caseDecisions.length ? ` • Рішень з бази: ${caseDecisions.length}` : " • Рішень з локальної бази поки не знайдено"}
          </div>
        </div>
      )}

      <div className="grid-2" style={{ gap: 20, marginBottom: 20 }}>
        {/* Config / Form */}
        <div className="card-elevated" style={{ padding: 24 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16, color: "var(--text-primary)" }}>📋 Налаштування аналізу</h2>
          <form onSubmit={onSubmit}>
             <div style={{ marginBottom: 16 }}>
                <label className="form-label">Пов'язати зі справою</label>
                <select className="form-input" value={selectedCaseId} onChange={e => setSelectedCaseId(e.target.value)}>
                   <option value="">Без прив'язки</option>
                   {cases.map(c => <option key={c.id} value={c.id}>{c.title} ({c.case_number || "No #"})</option>)}
                </select>
             </div>

             <div style={{ marginBottom: 16 }}>
                <label className="form-label">Судове рішення (PDF, DOCX, TXT)</label>
                <input type="file" className="form-input" accept=".txt,.pdf,.docx,.doc,.rtf,.md" onChange={(e) => setSelectedFile(e.target.files?.[0] || null)} />
             </div>
             
             <div className="grid-2" style={{ marginBottom: 16 }}>
               <div>
                  <label className="form-label">Глибина практики (днів)</label>
                  <input className="form-input" value={caseLawDays} onChange={(e) => setCaseLawDays(e.target.value)} />
               </div>
               <div>
                  <label className="form-label">Ліміт результатів</label>
                  <input className="form-input" value={caseLawLimit} onChange={(e) => setCaseLawLimit(e.target.value)} />
               </div>
             </div>

             <div className="grid-2" style={{ marginBottom: 16 }}>
               <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                 <input type="checkbox" checked={includeRecentCaseLaw} onChange={(e) => setIncludeRecentCaseLaw(e.target.checked)} id="inclPr" />
                 <label htmlFor="inclPr" style={{ fontSize: 13 }}>Включити практику</label>
               </div>
               <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                 <input type="checkbox" checked={onlySupremeCaseLaw} onChange={(e) => setOnlySupremeCaseLaw(e.target.checked)} id="onlySup" />
                 <label htmlFor="onlySup" style={{ fontSize: 13 }}>Лише ВС</label>
               </div>
             </div>

             <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 20 }}>
               <button type="submit" className="btn btn-primary" disabled={loading}>
                 {loading ? "Аналіз..." : "🔍 Запустити аудит"}
               </button>
               <button type="button" className="btn btn-ghost" onClick={onGeneratePackage} disabled={loading || !selectedFile}>
                 📦 Генерувати пакет
               </button>
               <div style={{ display: "flex", gap: 4 }}>
                 <button type="button" className="btn btn-xs btn-ghost" onClick={() => onExport("pdf")} disabled={!selectedFile}>PDF</button>
                 <button type="button" className="btn btn-xs btn-ghost" onClick={() => onExport("docx")} disabled={!selectedFile}>DOCX</button>
               </div>
             </div>
          </form>
        </div>

        {/* Quick Result Summary */}
        <div style={{ display: "flex", flexDirection: "column", gap: 15 }}>
          {result && (
            <div className="card-elevated" style={{ padding: 24, borderLeft: "3px solid var(--gold-500)" }}>
              <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16 }}>🎯 Вердикт системи</h2>
              <div className="stat-card" style={{ marginBottom: 12 }}>
                <div className="stat-label">Загальний бал довіри</div>
                <div className="stat-value" style={{ color: scoreColor(result.overall_confidence_score) }}>{result.overall_confidence_score}%</div>
              </div>
              <div style={{ fontSize: 13, background: "rgba(255,255,255,0.03)", padding: 12, borderRadius: 8 }}>
                <strong>Quality Gate:</strong> {result.quality_gate.status} <br/>
                <strong>Можна подавати:</strong> {result.quality_gate.can_proceed_to_filing ? "✅ ТАК" : "❌ НІ"}
              </div>
            </div>
          )}
          
          <div className="card-elevated" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>📂 Історія аналізів</h3>
            <button className="btn btn-xs btn-ghost" onClick={onLoadHistory} disabled={loadingHistory}>
              {loadingHistory ? "Завантаження..." : "Переглянути історію"}
            </button>
            {history && (
               <div style={{ marginTop: 15, display: "flex", flexDirection: "column", gap: 8 }}>
                 {history.items.slice(0, 3).map(it => (
                    <div key={it.id} style={{ fontSize: 11, color: "var(--text-muted)", padding: "4px 0", borderBottom: "1px solid var(--divider)" }}>
                      {it.source_file_name} · Score: {it.overall_confidence_score}
                    </div>
                 ))}
               </div>
            )}
          </div>
        </div>
      </div>

      {result && (
        <div className="card-elevated" style={{ padding: 24, marginBottom: 20 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 20, color: "var(--gold-400)" }}>Деталізований звіт</h2>
          
          <div className="grid-2" style={{ gap: 20, marginBottom: 30 }}>
            <div>
              <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>📖 Суть спору</h3>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>{result.dispute_summary}</p>
            </div>
            <div>
              <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>⚖️ Касаційні вразливості</h3>
              <ul style={{ fontSize: 13, color: "var(--danger)", paddingLeft: 16 }}>
                {result.cassation_vulnerabilities.map((v, i) => <li key={i} style={{ marginBottom: 4 }}>{v}</li>)}
              </ul>
            </div>
          </div>

          <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16 }}>📊 Блоки якості (Legal Integrity)</h3>
          <div className="grid-2" style={{ gap: 15 }}>
            {result.quality_blocks.map(block => (
               <div key={block.code} className="card-elevated" style={{ padding: 16, background: "rgba(255,255,255,0.01)" }}>
                 <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                   <span style={{ fontSize: 13, fontWeight: 600 }}>{block.title}</span>
                   <span className={`badge ${block.status === "pass" ? "badge-success" : "badge-warning"}`}>{block.score}%</span>
                 </div>
                 <p style={{ fontSize: 11, color: "var(--text-muted)" }}>{block.summary}</p>
               </div>
            ))}
          </div>
          
          <div style={{ marginTop: 30 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16 }}>🗺️ План захисту / Наступні кроки</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {result.defense_plan.map(step => (
                <div key={step.code} className="card-elevated" style={{ padding: 16, borderLeft: "3px solid var(--blue-500)" }}>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>Стадія: {step.stage}</div>
                  <div style={{ fontSize: 12, color: "var(--text-primary)", marginBottom: 8 }}>Ціль: {step.goal}</div>
                  <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                    {step.target_documents.map((d, i) => <span key={i} className="badge badge-muted" style={{ fontSize: 10 }}>{d}</span>)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {packageResult && (
        <div className="card-elevated" style={{ padding: 24, border: "1px solid var(--gold-500)" }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16 }}>📦 Пакет документів сформовано</h2>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 15 }}>
            Сторона: <strong>{packageResult.side_assessment.side}</strong> | 
            Впевненість: <strong>{packageResult.side_assessment.confidence}%</strong>
          </div>
          <p style={{ fontSize: 12, color: "var(--text-muted)" }}>
            Створено {packageResult.generated_documents.length} документів. Вони доступні у розділі "Документи".
          </p>
        </div>
      )}
    </div>
  );
}

export default function DecisionAnalysisPage() {
  return (
    <Suspense fallback={<div className="card-elevated" style={{ padding: 24 }}>Завантаження аналізу...</div>}>
      <DecisionAnalysisPageContent />
    </Suspense>
  );
}
