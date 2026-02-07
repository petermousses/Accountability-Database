import { useState, useCallback } from 'react';
import type {
  UploadResponse,
  PipelineStatus,
  OllamaResponse,
  PipelineResults,
  FOIARequest,
  FOIAGenerateResponse,
  HistoryEntry,
  HealthResponse,
} from '../types';

interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

function useApiState<T>(): ApiState<T> & {
  setData: (d: T | null) => void;
  setLoading: (l: boolean) => void;
  setError: (e: string | null) => void;
} {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return { data, loading, error, setData, setLoading, setError };
}

async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.text();
    let message: string;
    try {
      const parsed = JSON.parse(body);
      message = parsed.detail || parsed.message || body;
    } catch {
      message = body || `Request failed with status ${response.status}`;
    }
    throw new Error(message);
  }
  return response.json();
}

export function useUpload() {
  const state = useApiState<UploadResponse>();

  const upload = useCallback(async (file: File) => {
    state.setLoading(true);
    state.setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const data = await apiFetch<UploadResponse>('/api/upload', {
        method: 'POST',
        body: formData,
      });
      state.setData(data);
      return data;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Upload failed';
      state.setError(msg);
      return null;
    } finally {
      state.setLoading(false);
    }
  }, []);

  return { ...state, upload };
}

export function useStatus() {
  const state = useApiState<PipelineStatus>();

  const fetchStatus = useCallback(async (runId: string) => {
    state.setLoading(true);
    state.setError(null);
    try {
      const data = await apiFetch<PipelineStatus>(`/api/status/${runId}`);
      state.setData(data);
      return data;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch status';
      state.setError(msg);
      return null;
    } finally {
      state.setLoading(false);
    }
  }, []);

  return { ...state, fetchStatus };
}

export function useOllamaResponse() {
  const state = useApiState<{ status: string }>();

  const submitResponse = useCallback(async (payload: OllamaResponse) => {
    state.setLoading(true);
    state.setError(null);
    try {
      const data = await apiFetch<{ status: string }>('/api/ollama-response', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      state.setData(data);
      return data;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to submit response';
      state.setError(msg);
      return null;
    } finally {
      state.setLoading(false);
    }
  }, []);

  return { ...state, submitResponse };
}

export function useResults() {
  const state = useApiState<PipelineResults>();

  const fetchResults = useCallback(async (runId: string) => {
    state.setLoading(true);
    state.setError(null);
    try {
      const data = await apiFetch<PipelineResults>(`/api/results/${runId}`);
      state.setData(data);
      return data;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch results';
      state.setError(msg);
      return null;
    } finally {
      state.setLoading(false);
    }
  }, []);

  return { ...state, fetchResults };
}

export function useFOIA() {
  const state = useApiState<FOIAGenerateResponse>();

  const generate = useCallback(async (request: FOIARequest) => {
    state.setLoading(true);
    state.setError(null);
    try {
      const data = await apiFetch<FOIAGenerateResponse>('/api/foia/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });
      state.setData(data);
      return data;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to generate FOIA request';
      state.setError(msg);
      return null;
    } finally {
      state.setLoading(false);
    }
  }, []);

  return { ...state, generate };
}

export function useHistory() {
  const state = useApiState<HistoryEntry[]>();

  const fetchHistory = useCallback(async () => {
    state.setLoading(true);
    state.setError(null);
    try {
      const data = await apiFetch<HistoryEntry[]>('/api/history');
      state.setData(data);
      return data;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch history';
      state.setError(msg);
      return null;
    } finally {
      state.setLoading(false);
    }
  }, []);

  return { ...state, fetchHistory };
}

export function useHealth() {
  const state = useApiState<HealthResponse>();

  const checkHealth = useCallback(async () => {
    state.setLoading(true);
    state.setError(null);
    try {
      const data = await apiFetch<HealthResponse>('/api/health');
      state.setData(data);
      return data;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'API unavailable';
      state.setError(msg);
      return null;
    } finally {
      state.setLoading(false);
    }
  }, []);

  return { ...state, checkHealth };
}
