import { useState, useEffect, useCallback } from 'react';
import { useStatus } from '../hooks/useApi';
import type { StageStatus } from '../types';
import OllamaRequestViewer from './OllamaRequestViewer';

interface DashboardProps {
  runId: string | null;
}

const STAGE_LABELS: Record<string, string> = {
  upload: 'File Upload',
  text_extraction: 'Text Extraction',
  chunking: 'Document Chunking',
  entity_extraction: 'Entity Extraction',
  relationship_mapping: 'Relationship Mapping',
  analysis: 'Analysis',
  complete: 'Complete',
  error: 'Error',
};

const STATUS_SYMBOLS: Record<string, string> = {
  pending: '○',
  running: '◎',
  complete: '●',
  error: '✕',
  waiting_for_ollama: '◇',
};

function StageRow({ stage }: { stage: StageStatus }) {
  const statusClass = `stage-status-${stage.status}`;

  return (
    <div className={`stage-row ${statusClass}`}>
      <span className="stage-symbol">{STATUS_SYMBOLS[stage.status] || '○'}</span>
      <span className="stage-name">{STAGE_LABELS[stage.stage] || stage.stage}</span>
      <span className="stage-badge">{stage.status.replace(/_/g, ' ')}</span>
      {stage.progress !== undefined && stage.progress > 0 && (
        <div className="stage-progress-bar">
          <div
            className="stage-progress-fill"
            style={{ width: `${Math.min(stage.progress, 100)}%` }}
          />
          <span className="stage-progress-text">{stage.progress}%</span>
        </div>
      )}
      {stage.message && <span className="stage-message">{stage.message}</span>}
    </div>
  );
}

export default function Dashboard({ runId }: DashboardProps) {
  const { data: status, loading, error, fetchStatus } = useStatus();
  const [inputRunId, setInputRunId] = useState(runId || '');
  const [activeRunId, setActiveRunId] = useState(runId || '');
  const [polling, setPolling] = useState(false);

  const loadStatus = useCallback(() => {
    if (activeRunId) {
      fetchStatus(activeRunId);
    }
  }, [activeRunId, fetchStatus]);

  useEffect(() => {
    if (runId) {
      setInputRunId(runId);
      setActiveRunId(runId);
    }
  }, [runId]);

  useEffect(() => {
    if (!activeRunId) return;
    loadStatus();
  }, [activeRunId, loadStatus]);

  useEffect(() => {
    if (!polling || !activeRunId) return;
    const interval = setInterval(loadStatus, 3000);
    return () => clearInterval(interval);
  }, [polling, activeRunId, loadStatus]);

  useEffect(() => {
    if (status) {
      const isTerminal =
        status.current_stage === 'complete' || status.current_stage === 'error';
      if (isTerminal) {
        setPolling(false);
      } else if (!polling) {
        setPolling(true);
      }
    }
  }, [status, polling]);

  const handleTrack = () => {
    if (inputRunId.trim()) {
      setActiveRunId(inputRunId.trim());
    }
  };

  const hasWaitingStage = status?.stages.some(
    (s) => s.status === 'waiting_for_ollama'
  );

  return (
    <div className="component-card">
      <h2>Pipeline Dashboard</h2>
      <p className="component-description">
        Monitor the progress of a pipeline run through each processing stage.
      </p>

      <div className="input-row">
        <input
          type="text"
          className="input"
          placeholder="Enter run ID..."
          value={inputRunId}
          onChange={(e) => setInputRunId(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleTrack()}
        />
        <button className="btn btn-primary" onClick={handleTrack} disabled={loading}>
          {loading ? 'Loading...' : 'Track'}
        </button>
        {activeRunId && (
          <button
            className={`btn ${polling ? 'btn-danger' : 'btn-secondary'}`}
            onClick={() => setPolling(!polling)}
          >
            {polling ? 'Stop Polling' : 'Auto-Refresh'}
          </button>
        )}
      </div>

      {error && (
        <div className="message message-error">
          <strong>Error:</strong> {error}
        </div>
      )}

      {status && (
        <div className="dashboard-content">
          <div className="status-header">
            <div className="status-meta">
              <div>
                <span className="label">Run ID:</span> <code>{status.run_id}</code>
              </div>
              <div>
                <span className="label">File:</span> {status.filename}
              </div>
              <div>
                <span className="label">Current Stage:</span>{' '}
                <span className={`badge badge-${status.current_stage}`}>
                  {STAGE_LABELS[status.current_stage] || status.current_stage}
                </span>
              </div>
              <div>
                <span className="label">Started:</span>{' '}
                {new Date(status.created_at).toLocaleString()}
              </div>
              <div>
                <span className="label">Updated:</span>{' '}
                {new Date(status.updated_at).toLocaleString()}
              </div>
            </div>
          </div>

          {status.error && (
            <div className="message message-error">
              <strong>Pipeline Error:</strong> {status.error}
            </div>
          )}

          <div className="stages-list">
            <h3>Stage Progress</h3>
            {status.stages.map((stage) => (
              <StageRow key={stage.stage} stage={stage} />
            ))}
          </div>

          {hasWaitingStage && (
            <OllamaRequestViewer runId={status.run_id} />
          )}
        </div>
      )}

      {!status && !loading && !error && (
        <div className="empty-state">
          Enter a run ID to view pipeline status, or upload a document to begin.
        </div>
      )}
    </div>
  );
}
