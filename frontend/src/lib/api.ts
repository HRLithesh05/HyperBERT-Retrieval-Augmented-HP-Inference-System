/**
 * HyperBERT API Client
 * Connects the React frontend to the Flask backend at localhost:5000
 */

const BASE = "/api";

export type SourceType = "extracted_from_paper" | "inferred_from_corpus" | "bert_default";

export interface HPEntry {
  value: number | string | null;
  source: SourceType;
  confidence: number;
  confidence_pct: number;
  papers: number | null;
  confidence_decomposition: { similarity: number; agreement: number; support: number };
  inference_trace: string[];
  distribution: { v: string; count: number }[];
}

export interface AnalysisResult {
  session_id: string;
  generated_at: string;
  pipeline_seconds: number;
  paper: {
    title: string;
    task: string | null;
    model: string | null;
    dataset: string | null;
    reproducibility_score: number;
    explicit_hp_count: number;
    total_hp_count: number;
  };
  completeness: {
    rscore: number;
    present_params: string[];
    missing_params: string[];
    completeness_pct: number;
    needs_inference: boolean;
  };
  strategy_cascade: Record<string, { status: string; papers: number; label: string }>;
  strategy_used: string;
  config: Record<string, HPEntry>;
  evidence_papers: any[];
  constraints: Array<{
    param: string;
    rule: string;
    old_value: any;
    new_value: any;
    explanation: string;
    citation: string;
  }>;
  contradictions: any[];
  contradiction_summary: string;
  validation: {
    verdict: string;
    errors: any[];
    corrections: any[];
    warnings: any[];
  };
  audit_log: Array<{ module: string; timestamp: string; message: string }>;
  llm_comparison?: any;
  agent_decisions?: Array<{
    param: string;
    action: string;
    original_value: any;
    original_confidence: number;
    result_value: any;
    result_confidence: number;
    reasoning: string[];
  }>;
  agent_summary?: {
    total_params_reviewed: number;
    accepted: number;
    llm_consulted: number;
    confidence_boosted: number;
    llm_overridden: number;
    has_llm_access: boolean;
  };
}

/** Upload a PDF and run the full M1-M7 pipeline */
export async function analyzePDF(file: File, guestId?: string): Promise<AnalysisResult> {
  const form = new FormData();
  form.append("file", file);

  const headers: Record<string, string> = {};
  if (guestId) headers["X-Guest-Id"] = guestId;

  const res = await fetch(`${BASE}/analyze`, {
    method: "POST",
    body: form,
    headers,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Unknown server error" }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }

  return res.json();
}

/** Upload PDF with SSE streaming — real-time module progress */
export async function analyzePDFStream(
  file: File,
  onProgress: (module: string, step: number, message: string) => void,
  guestId?: string,
): Promise<AnalysisResult> {
  const form = new FormData();
  form.append("file", file);

  const headers: Record<string, string> = {};
  if (guestId) headers["X-Guest-Id"] = guestId;

  const res = await fetch(`${BASE}/analyze-stream`, {
    method: "POST",
    body: form,
    headers,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Unknown server error" }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }

  return new Promise((resolve, reject) => {
    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let resolved = false;

    function processLines(lines: string[]) {
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (line.startsWith("event: result")) {
          // Next line should be the data
          if (i + 1 < lines.length && lines[i + 1].startsWith("data: ")) {
            try {
              resolved = true;
              resolve(JSON.parse(lines[i + 1].slice(6)));
              return;
            } catch {}
          }
        }
        if (line.startsWith("event: error")) {
          if (i + 1 < lines.length && lines[i + 1].startsWith("data: ")) {
            try {
              const errData = JSON.parse(lines[i + 1].slice(6));
              resolved = true;
              reject(new Error(errData.error || "Pipeline failed"));
              return;
            } catch {}
          }
        }
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.module && data.step) {
              onProgress(data.module, data.step, data.message);
            }
          } catch {}
        }
      }
    }

    function pump(): Promise<void> {
      return reader.read().then(({ done, value }) => {
        if (done) {
          if (buffer.trim()) {
            processLines(buffer.split("\n"));
          }
          return;
        }
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        processLines(lines);
        if (!resolved) return pump();
      });
    }

    pump().catch(reject);
  });
}

/** Fetch a previously stored session by ID */
export async function getSession(sessionId: string): Promise<AnalysisResult> {
  const res = await fetch(`${BASE}/session/${sessionId}`);
  if (!res.ok) throw new Error("Session not found");
  return res.json();
}

/** Get corpus papers with optional filters */
export async function getCorpusPapers(params: {
  task?: string;
  model?: string;
  q?: string;
  page?: number;
  per_page?: number;
} = {}): Promise<{ total: number; papers: any[] }> {
  const qs = new URLSearchParams();
  if (params.task) qs.set("task", params.task);
  if (params.model) qs.set("model", params.model);
  if (params.q) qs.set("q", params.q);
  if (params.page !== undefined) qs.set("page", String(params.page));
  if (params.per_page !== undefined) qs.set("per_page", String(params.per_page));

  const res = await fetch(`${BASE}/corpus/papers?${qs}`);
  if (!res.ok) throw new Error("Failed to fetch corpus papers");
  return res.json();
}

/** Get corpus statistics */
export async function getCorpusStats(): Promise<any> {
  const res = await fetch(`${BASE}/corpus/stats`);
  if (!res.ok) throw new Error("Failed to fetch corpus stats");
  return res.json();
}

/** Fetch LLM comparison data for a session */
export async function getComparison(sessionId: string): Promise<any> {
  const res = await fetch(`${BASE}/compare/${sessionId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Comparison failed" }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

/** Check Ollama health status */
export async function getOllamaStatus(): Promise<{
  running: boolean;
  models: string[];
  has_qwen: boolean;
  error: string | null;
}> {
  const res = await fetch(`${BASE}/ollama/status`);
  if (!res.ok) {
    return { running: false, models: [], has_qwen: false, error: `HTTP ${res.status}` };
  }
  return res.json();
}

/** Run live Ollama comparison for a session */
export async function runLiveComparison(sessionId: string): Promise<any> {
  const res = await fetch(`${BASE}/compare-live/${sessionId}`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Live comparison failed" }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

/** Session history entry */
export interface SessionSummary {
  session_id: string;
  paper_title: string;
  paper_task: string | null;
  paper_model: string | null;
  completeness_pct: number;
  created_at: string;
}

/** Fetch list of past analysis sessions */
export async function getSessions(guestId?: string): Promise<{
  total: number;
  sessions: SessionSummary[];
}> {
  const qs = new URLSearchParams();
  if (guestId) qs.set("guest_id", guestId);
  const res = await fetch(`${BASE}/sessions?${qs}`);
  if (!res.ok) {
    return { total: 0, sessions: [] };
  }
  return res.json();
}

/** Download URL helpers */
export const downloadUrl = {
  notebook: (id: string) => `${BASE}/download/${id}/notebook`,
  script: (id: string) => `${BASE}/download/${id}/script`,
  yaml: (id: string) => `${BASE}/download/${id}/yaml`,
  config: (id: string) => `${BASE}/download/${id}/config`,
};
