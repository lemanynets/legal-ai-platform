"use client";

import { FormEvent, useState } from "react";

import {
  autoProcessFullLawyer,
  autoProcessFullLawyerPreflight,
  type FullLawyerPreflightResponse,
  type FullLawyerResponse,
} from "@/lib/api";
import { getToken, getUserId } from "@/lib/auth";
import { normalizeGenerationRun, type UnifiedGenerationRun } from "@/lib/workflow-normalizers";

export default function GeneratePackagePage() {
  const [file, setFile] = useState<File | null>(null);
  const [maxDocuments, setMaxDocuments] = useState(4);
  const [processualOnly, setProcessualOnly] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [preflight, setPreflight] = useState<FullLawyerPreflightResponse | null>(null);
  const [result, setResult] = useState<FullLawyerResponse | null>(null);
  const [run, setRun] = useState<UnifiedGenerationRun | null>(null);

  async function runPreflight(event?: FormEvent) {
    event?.preventDefault();
    if (!file) {
      setError("Select file first.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const response = await autoProcessFullLawyerPreflight(
        {
          file,
          max_documents: maxDocuments,
          processual_only: processualOnly,
          consume_quota: false,
        },
        getToken(),
        getUserId()
      );
      setPreflight(response);
      setResult(null);
      setRun(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function runGeneration() {
    if (!file) {
      setError("Select file first.");
      return;
    }
    if (!preflight) {
      setError("Run preflight first. Package generation is blocked without it.");
      return;
    }
    const hint = preflight.package_generation_hint;
    if (!hint.can_generate_final_package && !hint.can_generate_draft_package) {
      setError("Preflight gate is blocked. Fix blockers before package generation.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const response = await autoProcessFullLawyer(
        {
          file,
          max_documents: maxDocuments,
          processual_only: processualOnly,
          generate_package: true,
          generate_package_draft_on_hard_stop: true,
        },
        getToken(),
        getUserId()
      );
      setResult(response);
      setRun(normalizeGenerationRun(response));
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
          <h1 className="section-title">Generate: Package</h1>
          <p className="section-subtitle">
            Mandatory preflight mode for package generation. Final generation runs only after gate checks.
          </p>
        </div>
      </div>

      {error && (
        <div className="preflight-block">
          <span style={{ color: "var(--danger)" }}>{error}</span>
        </div>
      )}

      <form className="card-elevated" style={{ padding: "20px", display: "grid", gap: "12px" }} onSubmit={runPreflight}>
        <label className="form-label" htmlFor="package-file">Case document</label>
        <input
          id="package-file"
          className="form-input"
          type="file"
          accept=".txt,.pdf,.doc,.docx,.rtf,.md,.html,.htm,.jpg,.jpeg,.png,.webp"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <div className="grid-2" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
          <div>
            <label className="form-label">Max documents</label>
            <input
              className="form-input"
              type="number"
              min={1}
              max={8}
              value={maxDocuments}
              onChange={(event) => setMaxDocuments(Number(event.target.value || 4))}
            />
          </div>
          <div style={{ display: "flex", alignItems: "end" }}>
            <label style={{ display: "flex", gap: "8px", alignItems: "center" }}>
              <input
                type="checkbox"
                checked={processualOnly}
                onChange={(event) => setProcessualOnly(event.target.checked)}
              />
              Processual-only mode
            </label>
          </div>
        </div>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <button type="submit" className="btn btn-secondary" disabled={loading}>
            {loading ? "Running..." : "Run Preflight"}
          </button>
          <button type="button" className="btn btn-primary" disabled={loading || !preflight} onClick={() => void runGeneration()}>
            {loading ? "Running..." : "Generate Package"}
          </button>
        </div>
      </form>

      {preflight && (
        <div className="card-elevated" style={{ padding: "20px" }}>
          <h2 style={{ marginBottom: "8px" }}>Preflight Gate</h2>
          <p style={{ color: "var(--text-secondary)" }}>
            Status: {preflight.final_submission_gate.status}
            <br />
            Final package allowed: {preflight.package_generation_hint.can_generate_final_package ? "yes" : "no"}
            <br />
            Draft package allowed: {preflight.package_generation_hint.can_generate_draft_package ? "yes" : "no"}
          </p>
          {preflight.package_generation_hint.blockers.length > 0 && (
            <ul style={{ marginTop: "8px", paddingLeft: "20px" }}>
              {preflight.package_generation_hint.blockers.map((item, index) => (
                <li key={`${item}-${index}`} style={{ color: "var(--warning)" }}>{item}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {run && (
        <div className="card-elevated" style={{ padding: "20px" }}>
          <h2 style={{ marginBottom: "8px" }}>Unified Generation Run</h2>
          <p style={{ color: "var(--text-secondary)" }}>
            Kind: {run.kind}
            <br />
            Generated count: {run.generatedCount}
            <br />
            Warnings: {run.warnings.length}
          </p>
        </div>
      )}

      {result && (
        <div className="card-elevated" style={{ padding: "20px" }}>
          <h2 style={{ marginBottom: "8px" }}>Package Result</h2>
          <p style={{ color: "var(--text-secondary)" }}>
            Generated documents: {result.generated_documents.length}
            <br />
            Ready for filing: {result.ready_for_filing ? "yes" : "no"}
          </p>
        </div>
      )}
    </div>
  );
}
