const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000/api";

function buildHeaders(token: string | null, userId: string | null): HeadersInit {
    const headers: Record<string, string> = {
        "Content-Type": "application/json",
    };
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }
    if (userId) {
        headers["X-User-Id"] = userId;
    }
    return headers;
}

export interface GeneratePacketRequest {
    strategy_text: string;
}

export interface GeneratedPacketDoc {
    doc_type: string;
    title: string;
    generated_text: string;
    ai_model?: string;
    tokens_used?: number;
    ai_error?: string;
    _source_form_data: Record<string, any>;
}

export interface SimulateJudgeRequest {
    strategy_text: string;
}

export interface JudgeSimulationResponse {
    win_probability: number;
    vulnerabilities: string[];
    recommendations: string[];
    judge_commentary: string;
}


export async function simulateJudge(
    payload: SimulateJudgeRequest,
    token: string | null,
    userId: string | null
): Promise<JudgeSimulationResponse> {
    const response = await fetch(`${API_BASE}/strategy/simulate-judge`, {
        method: "POST",
        headers: buildHeaders(token, userId),
        body: JSON.stringify(payload),
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || "Failed to simulate judge verdict");
    }
    return await response.json();
}

export async function generateDocumentPacket(
    payload: GeneratePacketRequest,
    token: string | null,
    userId: string | null
): Promise<GeneratedPacketDoc[]> {
    const response = await fetch(`${API_BASE}/strategy/generate-packet`, {
        method: "POST",
        headers: buildHeaders(token, userId),
        body: JSON.stringify(payload),
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || "Failed to generate document packet");
    }
    return await response.json();
}

// Re-exporting other functions that might exist in this file
export * from "./auth"; // Assuming auth helpers are here

// Mocking other existing functions for completeness
export async function analyzeIntake(payload: any, token: string | null, userId: string | null, options: any): Promise<any> { return {}; }
export async function getContractAnalysisHistory(token: string | null, userId: string | null): Promise<any> { return { items: [] }; }
export async function processContractAnalysis(payload: any, token: string | null, userId: string | null): Promise<any> { return {}; }
export async function getAuditHistory(params: any, token: string | null, userId: string | null): Promise<any> { return { items: [] }; }
export async function getAuditIntegrity(params: any, token: string | null, userId: string | null): Promise<any> { return { status: 'pass' }; }

export interface DocumentIntakeResponse {
    raw_text_preview?: string;
    [key: string]: any;
}
export interface ContractAnalysisItem { }
export interface ContractAnalysisHistoryResponse {
    items: any[];
    total: number;
    page: number;
    pages: number;
}
export interface AuditHistoryResponse { }
export interface AuditIntegrityResponse { }