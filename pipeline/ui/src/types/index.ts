export interface UploadResponse {
  run_id: string;
  filename: string;
  status: string;
  message: string;
}

export type PipelineStage =
  | 'upload'
  | 'text_extraction'
  | 'chunking'
  | 'entity_extraction'
  | 'relationship_mapping'
  | 'analysis'
  | 'complete'
  | 'error';

export interface StageStatus {
  stage: PipelineStage;
  status: 'pending' | 'running' | 'complete' | 'error' | 'waiting_for_ollama';
  message: string;
  progress?: number;
  started_at?: string;
  completed_at?: string;
}

export interface PipelineStatus {
  run_id: string;
  filename: string;
  current_stage: PipelineStage;
  stages: StageStatus[];
  created_at: string;
  updated_at: string;
  error?: string;
}

export interface OllamaRequest {
  request_id: string;
  run_id: string;
  prompt: string;
  model: string;
  stage: string;
  created_at: string;
}

export interface OllamaResponse {
  request_id: string;
  response: string;
}

export interface Entity {
  id: string;
  name: string;
  type: string;
  description?: string;
  attributes: Record<string, string>;
}

export interface Relationship {
  source: string;
  target: string;
  type: string;
  description?: string;
  evidence?: string;
}

export interface AnalysisReport {
  summary: string;
  key_findings: string[];
  risk_indicators: string[];
  recommended_actions: string[];
}

export interface PipelineResults {
  run_id: string;
  filename: string;
  entities: Entity[];
  relationships: Relationship[];
  analysis: AnalysisReport;
  completed_at: string;
}

export interface FOIARequest {
  agency: string;
  subject: string;
  description: string;
  date_range_start?: string;
  date_range_end?: string;
  entities: string[];
}

export interface FOIAGenerateResponse {
  request_text: string;
  agency: string;
  subject: string;
  generated_at: string;
}

export interface HistoryEntry {
  run_id: string;
  filename: string;
  status: string;
  current_stage: PipelineStage;
  created_at: string;
  updated_at: string;
  entity_count?: number;
  relationship_count?: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  uptime?: number;
}

export type TabName = 'upload' | 'dashboard' | 'foia' | 'results' | 'history';
