export interface Workspace {
  id: string;
  title: string;
  status: "active" | "submitted";
  submitted_at: string | null;
  openai_vector_store_id: string | null;
  chat_count: number;
  file_count: number;
  created_at: string;
  updated_at: string;
}

export interface Chat {
  id: string;
  workspace_id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  chat_id: string;
  role: "user" | "assistant" | "system";
  content_text: string;
  sequence_number: number;
  openai_response_id: string | null;
  metadata_jsonb: Record<string, unknown> | null;
  created_at: string;
}

export interface ChatWithMessages {
  id: string;
  workspace_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
}

export interface UploadedFile {
  id: string;
  workspace_id: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  file_role: string;
  is_available_for_ai_context: boolean;
  openai_file_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Submission {
  id: string;
  workspace_id: string;
  primary_file_id: string;
  submitted_at: string;
  status: "submitted" | "analyzing" | "completed" | "failed";
  files: { file_id: string; role: string }[];
}

export interface FactorBreakdown {
  name: string;
  weight: number;
  score: number;
  explanation: string;
}

export interface EvidenceItem {
  ai_excerpt: string;
  assignment_excerpt: string;
  similarity: number;
  semantic_score: number;
  lexical_score: number;
  relation_type: string | null;
}

export interface AnalysisReport {
  summary: string;
  reliance_score: number;
  reliance_label: "Low" | "Moderate" | "High";
  usage_type: string[];
  evidence: EvidenceItem[];
  observations: string[];
  confidence: "Low" | "Medium" | "High";
  prompt_intent_summary: string | null;
  transformation_findings: string[];
  factor_breakdown: FactorBreakdown[];
  increasing_factors: string[];
  decreasing_factors: string[];
  caveats: string[];
}

export interface ReportResponse {
  status: string;
  report: AnalysisReport | null;
  markdown: string | null;
}
