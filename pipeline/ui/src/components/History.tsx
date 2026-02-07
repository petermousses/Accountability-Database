import { useEffect, useCallback } from 'react';
import { useHistory } from '../hooks/useApi';
import type { HistoryEntry } from '../types';

interface HistoryProps {
  onSelectRun: (runId: string) => void;
}

const STATUS_COLORS: Record<string, string> = {
  complete: 'badge-complete',
  running: 'badge-running',
  error: 'badge-error',
  pending: 'badge-pending',
  waiting_for_ollama: 'badge-waiting',
};

function HistoryRow({
  entry,
  onSelect,
}: {
  entry: HistoryEntry;
  onSelect: (runId: string) => void;
}) {
  const statusClass = STATUS_COLORS[entry.status] || 'badge-pending';

  return (
    <tr className="history-row" onClick={() => onSelect(entry.run_id)}>
      <td>
        <code className="run-id-link">{entry.run_id}</code>
      </td>
      <td>{entry.filename}</td>
      <td>
        <span className={`badge ${statusClass}`}>{entry.status}</span>
      </td>
      <td>{entry.current_stage}</td>
      <td className="number-cell">{entry.entity_count ?? '--'}</td>
      <td className="number-cell">{entry.relationship_count ?? '--'}</td>
      <td className="date-cell">{new Date(entry.created_at).toLocaleString()}</td>
      <td className="date-cell">{new Date(entry.updated_at).toLocaleString()}</td>
    </tr>
  );
}

export default function History({ onSelectRun }: HistoryProps) {
  const { data: history, loading, error, fetchHistory } = useHistory();

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleRefresh = useCallback(() => {
    fetchHistory();
  }, [fetchHistory]);

  return (
    <div className="component-card">
      <div className="history-header">
        <div>
          <h2>Pipeline History</h2>
          <p className="component-description">
            View all previous pipeline runs. Click a row to view its status or results.
          </p>
        </div>
        <button className="btn btn-secondary" onClick={handleRefresh} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div className="message message-error">
          <strong>Error:</strong> {error}
        </div>
      )}

      {history && history.length > 0 && (
        <div className="table-wrapper">
          <table className="data-table history-table">
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Filename</th>
                <th>Status</th>
                <th>Stage</th>
                <th>Entities</th>
                <th>Relations</th>
                <th>Created</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {history.map((entry) => (
                <HistoryRow
                  key={entry.run_id}
                  entry={entry}
                  onSelect={onSelectRun}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {history && history.length === 0 && (
        <div className="empty-state">
          No pipeline runs found. Upload a document to get started.
        </div>
      )}

      {loading && !history && (
        <div className="loading-indicator">Loading history...</div>
      )}
    </div>
  );
}
