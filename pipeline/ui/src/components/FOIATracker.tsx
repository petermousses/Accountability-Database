import { useState, useCallback } from 'react';
import { useFOIA } from '../hooks/useApi';

export default function FOIATracker() {
  const { data: generated, loading, error, generate } = useFOIA();
  const [agency, setAgency] = useState('');
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [dateStart, setDateStart] = useState('');
  const [dateEnd, setDateEnd] = useState('');
  const [entitiesInput, setEntitiesInput] = useState('');
  const [copied, setCopied] = useState(false);

  const handleGenerate = useCallback(async () => {
    if (!agency.trim() || !subject.trim()) return;

    const entities = entitiesInput
      .split(',')
      .map((e) => e.trim())
      .filter(Boolean);

    await generate({
      agency: agency.trim(),
      subject: subject.trim(),
      description: description.trim(),
      date_range_start: dateStart || undefined,
      date_range_end: dateEnd || undefined,
      entities,
    });
  }, [agency, subject, description, dateStart, dateEnd, entitiesInput, generate]);

  const handleCopy = useCallback(async () => {
    if (!generated?.request_text) return;
    try {
      await navigator.clipboard.writeText(generated.request_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = generated.request_text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [generated]);

  const handleReset = () => {
    setAgency('');
    setSubject('');
    setDescription('');
    setDateStart('');
    setDateEnd('');
    setEntitiesInput('');
  };

  return (
    <div className="component-card">
      <h2>FOIA Request Generator</h2>
      <p className="component-description">
        Generate Freedom of Information Act request letters based on pipeline findings.
      </p>

      <div className="foia-form">
        <div className="form-group">
          <label className="form-label" htmlFor="foia-agency">
            Agency <span className="required">*</span>
          </label>
          <input
            id="foia-agency"
            type="text"
            className="input"
            placeholder="e.g., Department of Justice, FBI, SEC..."
            value={agency}
            onChange={(e) => setAgency(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="foia-subject">
            Subject <span className="required">*</span>
          </label>
          <input
            id="foia-subject"
            type="text"
            className="input"
            placeholder="Subject of the FOIA request..."
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="foia-description">
            Description
          </label>
          <textarea
            id="foia-description"
            className="textarea"
            rows={4}
            placeholder="Detailed description of records being requested..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label className="form-label" htmlFor="foia-date-start">
              Date Range Start
            </label>
            <input
              id="foia-date-start"
              type="date"
              className="input"
              value={dateStart}
              onChange={(e) => setDateStart(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="foia-date-end">
              Date Range End
            </label>
            <input
              id="foia-date-end"
              type="date"
              className="input"
              value={dateEnd}
              onChange={(e) => setDateEnd(e.target.value)}
            />
          </div>
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="foia-entities">
            Related Entities
          </label>
          <input
            id="foia-entities"
            type="text"
            className="input"
            placeholder="Comma-separated: John Doe, Acme Corp, ..."
            value={entitiesInput}
            onChange={(e) => setEntitiesInput(e.target.value)}
          />
          <span className="form-hint">
            Names of people, organizations, or other entities related to the request.
          </span>
        </div>

        <div className="form-actions">
          <button
            className="btn btn-primary"
            onClick={handleGenerate}
            disabled={loading || !agency.trim() || !subject.trim()}
          >
            {loading ? 'Generating...' : 'Generate FOIA Request'}
          </button>
          <button className="btn btn-secondary" onClick={handleReset}>
            Clear Form
          </button>
        </div>
      </div>

      {error && (
        <div className="message message-error">
          <strong>Error:</strong> {error}
        </div>
      )}

      {generated && (
        <div className="foia-result">
          <div className="foia-result-header">
            <h3>Generated FOIA Request</h3>
            <div className="foia-result-meta">
              <span>
                <span className="label">Agency:</span> {generated.agency}
              </span>
              <span>
                <span className="label">Subject:</span> {generated.subject}
              </span>
              <span>
                <span className="label">Generated:</span>{' '}
                {new Date(generated.generated_at).toLocaleString()}
              </span>
            </div>
          </div>
          <div className="foia-request-text-wrapper">
            <button className="btn btn-small copy-btn" onClick={handleCopy}>
              {copied ? 'Copied!' : 'Copy to Clipboard'}
            </button>
            <pre className="foia-request-text">{generated.request_text}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
