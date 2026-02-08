import { useState, useEffect, useCallback } from 'react';
import { useOllamaResponse } from '../hooks/useApi';
import type { OllamaRequest } from '../types';

interface OllamaRequestViewerProps {
  runId: string;
}

export default function OllamaRequestViewer({ runId }: OllamaRequestViewerProps) {
  const [requests, setRequests] = useState<OllamaRequest[]>([]);
  const [loadingRequests, setLoadingRequests] = useState(false);
  const [responseText, setResponseText] = useState<Record<string, string>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const { loading: submitting, error, submitResponse } = useOllamaResponse();

  const fetchRequests = useCallback(async () => {
    setLoadingRequests(true);
    try {
      const res = await fetch(`/api/status/${runId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.pending_requests) {
          setRequests(data.pending_requests);
        }
      }
    } catch {
      // Silently handle -- dashboard will show errors
    } finally {
      setLoadingRequests(false);
    }
  }, [runId]);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  const copyPrompt = useCallback(async (requestId: string, prompt: string) => {
    try {
      await navigator.clipboard.writeText(prompt);
      setCopiedId(requestId);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      // Fallback for environments without clipboard API
      const textarea = document.createElement('textarea');
      textarea.value = prompt;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopiedId(requestId);
      setTimeout(() => setCopiedId(null), 2000);
    }
  }, []);

  const handleSubmitResponse = useCallback(
    async (requestId: string) => {
      const text = responseText[requestId];
      if (!text?.trim()) return;
      const result = await submitResponse({
        request_id: requestId,
        response: text.trim(),
      });
      if (result) {
        setRequests((prev) => prev.filter((r) => r.request_id !== requestId));
        setResponseText((prev) => {
          const next = { ...prev };
          delete next[requestId];
          return next;
        });
      }
    },
    [responseText, submitResponse]
  );

  if (loadingRequests) {
    return (
      <div className="ollama-viewer">
        <h3>Ollama Requests</h3>
        <div className="loading-indicator">Loading pending requests...</div>
      </div>
    );
  }

  if (requests.length === 0) {
    return (
      <div className="ollama-viewer">
        <h3>Ollama Requests</h3>
        <p className="empty-state">
          No pending Ollama requests. The pipeline is waiting for LLM processing.
        </p>
        <button className="btn btn-secondary" onClick={fetchRequests}>
          Refresh
        </button>
      </div>
    );
  }

  return (
    <div className="ollama-viewer">
      <h3>Pending Ollama Requests ({requests.length})</h3>
      <p className="component-description">
        Copy the prompt below, run it through Ollama, and paste the response back.
      </p>

      {error && (
        <div className="message message-error">
          <strong>Error:</strong> {error}
        </div>
      )}

      {requests.map((req) => (
        <div key={req.request_id} className="ollama-request-card">
          <div className="ollama-request-header">
            <div>
              <span className="label">Request:</span>{' '}
              <code>{req.request_id}</code>
            </div>
            <div>
              <span className="label">Model:</span>{' '}
              <span className="badge badge-info">{req.model}</span>
            </div>
            <div>
              <span className="label">Stage:</span> {req.stage}
            </div>
          </div>

          <div className="prompt-section">
            <div className="prompt-header">
              <span className="label">Prompt:</span>
              <button
                className="btn btn-small"
                onClick={() => copyPrompt(req.request_id, req.prompt)}
              >
                {copiedId === req.request_id ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <pre className="prompt-text">{req.prompt}</pre>
          </div>

          <div className="response-section">
            <label className="label" htmlFor={`response-${req.request_id}`}>
              Paste Ollama Response:
            </label>
            <textarea
              id={`response-${req.request_id}`}
              className="textarea"
              rows={6}
              placeholder="Paste the Ollama model response here..."
              value={responseText[req.request_id] || ''}
              onChange={(e) =>
                setResponseText((prev) => ({
                  ...prev,
                  [req.request_id]: e.target.value,
                }))
              }
            />
            <button
              className="btn btn-primary"
              onClick={() => handleSubmitResponse(req.request_id)}
              disabled={submitting || !responseText[req.request_id]?.trim()}
            >
              {submitting ? 'Submitting...' : 'Submit Response'}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
