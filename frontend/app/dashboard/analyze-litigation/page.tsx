"use client";

import { FormEvent, useState } from "react";

import {
  analyzeIntake,
  analyzePrecedentMap,
  autoProcessDecisionAnalysis,
  createStrategyBlueprint,
  runJudgeSimulation,
  type DecisionAnalysisResponse,
  type DocumentIntakeResponse,
  type PrecedentMapResponse,
  type StrategyBlueprintResponse,
  type JudgeSimulationResponse,
} from "@/lib/api";
import { getToken, getUserId } from "@/lib/auth";
import { normalizeLitigationAnalysis, type UnifiedAnalysisResult } from "@/lib/workflow-normalizers";

export default function AnalyzeLitigationPage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [intake, setIntake] = useState<DocumentIntakeResponse | null>(null);
  const [precedentMap, setPrecedentMap] = useState<PrecedentMapResponse | null>(null);
  const [strategy, setStrategy] = useState<StrategyBlueprintResponse | null>(null);
  const [judge, setJudge] = useState<JudgeSimulationResponse | null>(null);
  const [decisionAudit, setDecisionAudit] = useState<DecisionAnalysisResponse | null>(null);
  const [unified, setUnified] = useState<UnifiedAnalysisResult | null>(null);

  async function runPipeline(event: FormEvent) {
    event.preventDefault();
    if (!file) {
      setError("Select file first.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const intakeResult = await analyzeIntake({ file }, getToken(), getUserId(), { mode: "deep" });
      setIntake(intakeResult);

      const map = await analyzePrecedentMap(intakeResult.id, { limit: 15 }, getToken(), getUserId());
      setPrecedentMap(map);

      const blueprint = await createStrategyBlueprint(
        {
          intake_id: intakeResult.id,
          regenerate: true,
          refresh_precedent_map: true,
          precedent_limit: 15,
        },
        getToken(),
        getUserId()
      );
      setStrategy(blueprint);

      const judgeSim = await runJudgeSimulation({ strategy_id: blueprint.id }, getToken(), getUserId());
      setJudge(judgeSim);

      setUnified(
        normalizeLitigationAnalysis({
          intakeType: intakeResult.classified_type,
          precedentMap: map,
          strategy: blueprint,
          decisionAudit: null,
        })
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function runDecisionAudit() {
    if (!file) {
      setError("Select file first.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const report = await autoProcessDecisionAnalysis(
        {
          file,
          include_recent_case_law: true,
          case_law_days: 365,
          case_law_limit: 12,
          only_supreme_case_law: false,
          ai_enhance: true,
        },
        getToken(),
        getUserId()
      );
      setDecisionAudit(report);
      setUnified(
        normalizeLitigationAnalysis({
          intakeType: intake?.classified_type,
          precedentMap,
          strategy,
          decisionAudit: report,
        })
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: "16px" }}>
      <div className="section-header">
        <div>
          <h1 className="section-title">Analyze: Litigation</h1>
          <p className="section-subtitle">
            Single entrypoint for intake, precedent map, strategy blueprint, judge simulation, and decision audit.
          </p>
        </div>
      </div>

      {error && (
        <div className="preflight-block">
          <span style={{ color: "var(--danger)" }}>{error}</span>
        </div>
      )}

      <form className="card-elevated" style={{ padding: "20px", display: "grid", gap: "12px" }} onSubmit={runPipeline}>
        <label className="form-label" htmlFor="litigation-file">Decision or case document</label>
        <input
          id="litigation-file"
          className="form-input"
          type="file"
          accept=".txt,.pdf,.doc,.docx,.rtf,.md,.html,.htm,.jpg,.jpeg,.png,.webp"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? "Running..." : "Run Litigation Pipeline"}
          </button>
          <button type="button" className="btn btn-secondary" disabled={loading || !file} onClick={() => void runDecisionAudit()}>
            {loading ? "Running..." : "Run Decision Audit"}
          </button>
        </div>
      </form>

      {unified && (
        <div className="card-elevated" style={{ padding: "20px" }}>
          <h2 style={{ marginBottom: "8px" }}>Unified Analysis Result</h2>
          <div style={{ color: "var(--text-secondary)" }}>
            Summary: {unified.summary}
            <br />
            References: {unified.referencesCount ?? 0}
            <br />
            Confidence: {typeof unified.confidenceScore === "number" ? unified.confidenceScore.toFixed(2) : "n/a"}
            <br />
            Warnings: {unified.warnings.length}
          </div>
        </div>
      )}

      {intake && (
        <div className="card-elevated" style={{ padding: "20px" }}>
          <h2 style={{ marginBottom: "8px" }}>Intake</h2>
          <p style={{ color: "var(--text-secondary)" }}>
            Type: {intake.classified_type} | Subject: {intake.subject_matter || "n/a"}
          </p>
        </div>
      )}

      {precedentMap && (
        <div className="card-elevated" style={{ padding: "20px" }}>
          <h2 style={{ marginBottom: "8px" }}>Precedent Map</h2>
          <p style={{ color: "var(--text-secondary)" }}>References found: {precedentMap.refs.length}</p>
        </div>
      )}

      {strategy && (
        <div className="card-elevated" style={{ padding: "20px" }}>
          <h2 style={{ marginBottom: "8px" }}>Strategy Blueprint</h2>
          <p style={{ color: "var(--text-secondary)" }}>
            Confidence score: {typeof strategy.confidence_score === "number" ? strategy.confidence_score.toFixed(2) : "n/a"}
          </p>
        </div>
      )}

      {judge && (
        <div className="card-elevated" style={{ padding: "20px" }}>
          <h2 style={{ marginBottom: "8px" }}>Judge Simulation</h2>
          <p style={{ color: "var(--text-secondary)" }}>
            Verdict probability: {(judge.verdict_probability * 100).toFixed(1)}%
          </p>
        </div>
      )}

      {decisionAudit && (
        <div className="card-elevated" style={{ padding: "20px" }}>
          <h2 style={{ marginBottom: "8px" }}>Decision Audit</h2>
          <p style={{ color: "var(--text-secondary)" }}>
            Confidence: {decisionAudit.overall_confidence_score.toFixed(2)} | Issues: {decisionAudit.key_issues.length}
          </p>
        </div>
      )}
    </div>
  );
}
