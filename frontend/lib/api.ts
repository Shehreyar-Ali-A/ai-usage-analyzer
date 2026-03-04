"use client";

export type AnalyzeEvidenceItem = {
  ai_excerpt: string;
  assignment_excerpt: string;
  similarity: number;
};

export type AnalyzeReport = {
  summary: string;
  reliance_score: number;
  reliance_label: "Low" | "Moderate" | "High";
  usage_type: string[];
  evidence: AnalyzeEvidenceItem[];
  observations: string[];
  confidence: "Low" | "Medium" | "High";
};

export type AnalyzeResponse = {
  report: AnalyzeReport;
  markdown_report: string;
  pdf_base64?: string | null;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8888";

export async function analyzeAssignment(params: {
  assignmentFile: File;
  chatJsonFile: File;
}): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("assignment_file", params.assignmentFile);
  form.append("chat_json_file", params.chatJsonFile);

  const res = await fetch(`${API_BASE_URL}/analyze`, {
    method: "POST",
    body: form
  });

  if (!res.ok) {
    let message = "Failed to analyze files.";
    try {
      const data = await res.json();
      if (data?.detail) {
        message = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // ignore JSON parse errors
    }
    throw new Error(message);
  }

  const data = (await res.json()) as AnalyzeResponse;
  return data;
}

