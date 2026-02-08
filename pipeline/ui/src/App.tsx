import { useState, useEffect, useCallback } from 'react';
import FileUpload from './components/FileUpload';
import Dashboard from './components/Dashboard';
import ResultsViewer from './components/ResultsViewer';
import FOIATracker from './components/FOIATracker';
import History from './components/History';
import { useHealth } from './hooks/useApi';
import type { TabName } from './types';

const TABS: { id: TabName; label: string }[] = [
  { id: 'upload', label: 'Upload' },
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'foia', label: 'FOIA' },
  { id: 'results', label: 'Results' },
  { id: 'history', label: 'History' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState<TabName>('upload');
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const { data: health, checkHealth } = useHealth();

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  const handleUploadComplete = useCallback((runId: string) => {
    setCurrentRunId(runId);
    setActiveTab('dashboard');
  }, []);

  const handleSelectRun = useCallback((runId: string) => {
    setCurrentRunId(runId);
    setActiveTab('dashboard');
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="header-title">
            <h1>Accountability Pipeline</h1>
            <span className="header-subtitle">FOIA Document Processing</span>
          </div>
          <div className="header-status">
            <span
              className={`status-dot ${health?.status === 'ok' ? 'status-ok' : 'status-offline'}`}
            />
            <span className="status-text">
              {health?.status === 'ok' ? 'API Connected' : 'API Offline'}
            </span>
            {health?.version && (
              <span className="version-text">v{health.version}</span>
            )}
          </div>
        </div>
        <nav className="tab-nav">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`tab-nav-btn ${activeTab === tab.id ? 'tab-nav-btn-active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="app-main">
        {currentRunId && (
          <div className="active-run-banner">
            <span className="label">Active Run:</span>{' '}
            <code>{currentRunId}</code>
            <button
              className="btn btn-small"
              onClick={() => setCurrentRunId(null)}
            >
              Clear
            </button>
          </div>
        )}

        <div className="tab-content">
          {activeTab === 'upload' && (
            <FileUpload onUploadComplete={handleUploadComplete} />
          )}
          {activeTab === 'dashboard' && <Dashboard runId={currentRunId} />}
          {activeTab === 'foia' && <FOIATracker />}
          {activeTab === 'results' && <ResultsViewer runId={currentRunId} />}
          {activeTab === 'history' && <History onSelectRun={handleSelectRun} />}
        </div>
      </main>

      <footer className="app-footer">
        <span>Accountability Database Pipeline</span>
      </footer>
    </div>
  );
}
