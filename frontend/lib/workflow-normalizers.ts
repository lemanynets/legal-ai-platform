import type {
  ContractAnalysisItem,
  DecisionAnalysisResponse,
  FullLawyerResponse,
  GenerateBundleResponse,
  GenerateResponse,
  PrecedentMapResponse,
  StrategyBlueprintResponse,
} from "@/lib/api";

export type UnifiedAnalysisResult = {
  kind: "quick" | "litigation";
  status: "ok" | "error";
  summary: string;
  riskLevel?: string;
  warnings: string[];
  referencesCount?: number;
  confidenceScore?: number;
};

export type UnifiedGenerationRun = {
  kind: "single" | "bundle" | "package";
  status: "ok" | "error";
  title: string;
  generatedCount: number;
  documentIds: string[];
  warnings: string[];
};

export function normalizeQuickAnalysis(item: ContractAnalysisItem): UnifiedAnalysisResult {
  return {
    kind: "quick",
    status: "ok",
    summary: item.contract_type || "Contract analysis completed",
    riskLevel: item.risk_level || undefined,
    warnings: [],
    confidenceScore: undefined,
  };
}

export function normalizeLitigationAnalysis(payload: {
  intakeType?: string;
  precedentMap?: PrecedentMapResponse | null;
  strategy?: StrategyBlueprintResponse | null;
  decisionAudit?: DecisionAnalysisResponse | null;
}): UnifiedAnalysisResult {
  const refs = payload.precedentMap?.refs?.length || 0;
  const confidence = payload.strategy?.confidence_score ?? payload.decisionAudit?.overall_confidence_score;
  const warnings = payload.decisionAudit?.warnings || [];
  return {
    kind: "litigation",
    status: "ok",
    summary: payload.intakeType || "Litigation analysis completed",
    warnings,
    referencesCount: refs,
    confidenceScore: typeof confidence === "number" ? confidence : undefined,
  };
}

export function normalizeGenerationRun(
  payload: GenerateResponse | GenerateBundleResponse | FullLawyerResponse
): UnifiedGenerationRun {
  if ("bundle_id" in payload) {
    return {
      kind: "bundle",
      status: "ok",
      title: "Bundle generation completed",
      generatedCount: payload.items.length,
      documentIds: payload.items.map((item) => item.document_id),
      warnings: [],
    };
  }
  if ("generated_documents" in payload) {
    return {
      kind: "package",
      status: "ok",
      title: "Package generation completed",
      generatedCount: payload.generated_documents.length,
      documentIds: payload.generated_documents.map((item) => item.id),
      warnings: payload.warnings || [],
    };
  }
  return {
    kind: "single",
    status: "ok",
    title: payload.title || "Document generated",
    generatedCount: 1,
    documentIds: [payload.document_id],
    warnings: [],
  };
}
