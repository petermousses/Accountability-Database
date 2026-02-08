import { useState, useRef, useCallback } from 'react';
import type React from 'react';
import { useUpload } from '../hooks/useApi';

interface FileUploadProps {
  onUploadComplete: (runId: string) => void;
}

export default function FileUpload({ onUploadComplete }: FileUploadProps) {
  const { data, loading, error, upload } = useUpload();
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
    }
  }, []);

  const handleUpload = useCallback(async () => {
    if (!selectedFile) return;
    const result = await upload(selectedFile);
    if (result) {
      onUploadComplete(result.run_id);
    }
  }, [selectedFile, upload, onUploadComplete]);

  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="component-card">
      <h2>Upload Document</h2>
      <p className="component-description">
        Upload FOIA documents (PDF, DOCX, TXT, CSV) for processing through the
        accountability pipeline.
      </p>

      <div
        className={`drop-zone ${dragActive ? 'drop-zone-active' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt,.csv,.xlsx,.json"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        <div className="drop-zone-content">
          <div className="drop-zone-icon">+</div>
          <p className="drop-zone-text">
            {dragActive
              ? 'Drop file here'
              : 'Drag and drop a file here, or click to browse'}
          </p>
          <p className="drop-zone-hint">
            Supported formats: PDF, DOCX, TXT, CSV, XLSX, JSON
          </p>
        </div>
      </div>

      {selectedFile && (
        <div className="selected-file">
          <div className="file-info">
            <span className="file-name">{selectedFile.name}</span>
            <span className="file-size">{formatSize(selectedFile.size)}</span>
          </div>
          <button
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={loading}
          >
            {loading ? 'Uploading...' : 'Upload and Process'}
          </button>
        </div>
      )}

      {error && (
        <div className="message message-error">
          <strong>Error:</strong> {error}
        </div>
      )}

      {data && (
        <div className="message message-success">
          <strong>Upload successful!</strong>
          <div className="upload-result">
            <div><span className="label">Run ID:</span> <code>{data.run_id}</code></div>
            <div><span className="label">File:</span> {data.filename}</div>
            <div><span className="label">Status:</span> {data.status}</div>
            {data.message && <div><span className="label">Message:</span> {data.message}</div>}
          </div>
        </div>
      )}
    </div>
  );
}
