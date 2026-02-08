import { useState, useCallback } from 'react';
import { useResults } from '../hooks/useApi';
import type { Entity, Relationship, AnalysisReport } from '../types';

interface ResultsViewerProps {
  runId: string | null;
}

function EntityTable({ entities }: { entities: Entity[] }) {
  const [filter, setFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');

  const types = Array.from(new Set(entities.map((e) => e.type))).sort();
  const filtered = entities.filter((e) => {
    const matchesText =
      !filter ||
      e.name.toLowerCase().includes(filter.toLowerCase()) ||
      (e.description || '').toLowerCase().includes(filter.toLowerCase());
    const matchesType = typeFilter === 'all' || e.type === typeFilter;
    return matchesText && matchesType;
  });

  return (
    <div className="results-section">
      <h3>Entities ({entities.length})</h3>
      <div className="filter-row">
        <input
          type="text"
          className="input"
          placeholder="Filter entities..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <select
          className="input select"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
        >
          <option value="all">All Types</option>
          {types.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>
      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Description</th>
              <th>Attributes</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((entity) => (
              <tr key={entity.id}>
                <td className="entity-name">{entity.name}</td>
                <td>
                  <span className="badge badge-type">{entity.type}</span>
                </td>
                <td>{entity.description || '--'}</td>
                <td className="attributes-cell">
                  {Object.entries(entity.attributes).length > 0 ? (
                    <dl className="attributes-list">
                      {Object.entries(entity.attributes).map(([k, v]) => (
                        <div key={k}>
                          <dt>{k}:</dt>
                          <dd>{v}</dd>
                        </div>
                      ))}
                    </dl>
                  ) : (
                    '--'
                  )}
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={4} className="empty-cell">No entities match the filter.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RelationshipTable({ relationships }: { relationships: Relationship[] }) {
  return (
    <div className="results-section">
      <h3>Relationships ({relationships.length})</h3>
      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Source</th>
              <th>Relationship</th>
              <th>Target</th>
              <th>Description</th>
              <th>Evidence</th>
            </tr>
          </thead>
          <tbody>
            {relationships.map((rel, i) => (
              <tr key={i}>
                <td className="entity-name">{rel.source}</td>
                <td>
                  <span className="badge badge-relationship">{rel.type}</span>
                </td>
                <td className="entity-name">{rel.target}</td>
                <td>{rel.description || '--'}</td>
                <td className="evidence-cell">{rel.evidence || '--'}</td>
              </tr>
            ))}
            {relationships.length === 0 && (
              <tr>
                <td colSpan={5} className="empty-cell">No relationships found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AnalysisSection({ analysis }: { analysis: AnalysisReport }) {
  return (
    <div className="results-section">
      <h3>Analysis Report</h3>

      <div className="analysis-block">
        <h4>Summary</h4>
        <p>{analysis.summary}</p>
      </div>

      <div className="analysis-block">
        <h4>Key Findings</h4>
        <ul className="findings-list">
          {analysis.key_findings.map((f, i) => (
            <li key={i}>{f}</li>
          ))}
        </ul>
      </div>

      <div className="analysis-block">
        <h4>Risk Indicators</h4>
        <ul className="risk-list">
          {analysis.risk_indicators.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      </div>

      <div className="analysis-block">
        <h4>Recommended Actions</h4>
        <ul className="actions-list">
          {analysis.recommended_actions.map((a, i) => (
            <li key={i}>{a}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function ResultsViewer({ runId }: ResultsViewerProps) {
  const { data: results, loading, error, fetchResults } = useResults();
  const [inputRunId, setInputRunId] = useState(runId || '');
  const [activeTab, setActiveTab] = useState<'entities' | 'relationships' | 'analysis'>('entities');

  const handleLoad = useCallback(() => {
    const id = inputRunId.trim();
    if (id) fetchResults(id);
  }, [inputRunId, fetchResults]);

  return (
    <div className="component-card">
      <h2>Results Viewer</h2>
      <p className="component-description">
        View extracted entities, relationships, and analysis from completed pipeline runs.
      </p>

      <div className="input-row">
        <input
          type="text"
          className="input"
          placeholder="Enter run ID..."
          value={inputRunId}
          onChange={(e) => setInputRunId(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleLoad()}
        />
        <button className="btn btn-primary" onClick={handleLoad} disabled={loading}>
          {loading ? 'Loading...' : 'Load Results'}
        </button>
      </div>

      {error && (
        <div className="message message-error">
          <strong>Error:</strong> {error}
        </div>
      )}

      {results && (
        <div className="results-content">
          <div className="results-meta">
            <span>
              <span className="label">Run:</span> <code>{results.run_id}</code>
            </span>
            <span>
              <span className="label">File:</span> {results.filename}
            </span>
            <span>
              <span className="label">Completed:</span>{' '}
              {new Date(results.completed_at).toLocaleString()}
            </span>
          </div>

          <div className="results-tabs">
            <button
              className={`tab-btn ${activeTab === 'entities' ? 'tab-btn-active' : ''}`}
              onClick={() => setActiveTab('entities')}
            >
              Entities ({results.entities.length})
            </button>
            <button
              className={`tab-btn ${activeTab === 'relationships' ? 'tab-btn-active' : ''}`}
              onClick={() => setActiveTab('relationships')}
            >
              Relationships ({results.relationships.length})
            </button>
            <button
              className={`tab-btn ${activeTab === 'analysis' ? 'tab-btn-active' : ''}`}
              onClick={() => setActiveTab('analysis')}
            >
              Analysis
            </button>
          </div>

          {activeTab === 'entities' && <EntityTable entities={results.entities} />}
          {activeTab === 'relationships' && (
            <RelationshipTable relationships={results.relationships} />
          )}
          {activeTab === 'analysis' && <AnalysisSection analysis={results.analysis} />}
        </div>
      )}

      {!results && !loading && !error && (
        <div className="empty-state">
          Enter a run ID to view pipeline results.
        </div>
      )}
    </div>
  );
}
