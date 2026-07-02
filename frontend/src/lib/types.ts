export interface DocumentSummary {
  id: string;
  title: string;
  chunk_count: number;
  char_count: number;
  created_at: string;
}

export interface DocumentList {
  documents: DocumentSummary[];
  total_chunks: number;
}

export interface Health {
  status: string;
  llm_configured: boolean;
  model: string;
  document_count: number;
}

export interface Citation {
  marker: number;
  document_id: string;
  document_title: string;
  snippet: string;
  score: number;
}
