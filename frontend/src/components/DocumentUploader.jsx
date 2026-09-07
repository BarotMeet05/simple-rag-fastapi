// frontend/src/components/DocumentUploader.jsx
import { useState, useRef, useEffect } from 'react';
import { uploadDocument, fetchDocuments } from '../services/api';

export default function DocumentUploader() {
  const [documents, setDocuments] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [toast, setToast] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => { loadDocuments(); }, []);

  async function loadDocuments() {
    try {
      const data = await fetchDocuments();
      setDocuments(data.documents || []);
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  }

  function showToast(message, type = 'success') {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  }

  async function handleFile(file) {
    if (!file) return;
    if (!file.name.endsWith('.pdf') && !file.name.endsWith('.txt')) {
      showToast('Only PDF and TXT files are supported.', 'error');
      return;
    }

    showToast(`Uploading ${file.name}...`, 'info');
    try {
      await uploadDocument(file);
      showToast(`${file.name} uploaded and indexed.`, 'success');
      await loadDocuments();
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  return (
    <>
      <div className="upload-section">
        <div
          className={`upload-zone ${isDragging ? 'dragging' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={(e) => { e.preventDefault(); setIsDragging(false); }}
          onDrop={(e) => { e.preventDefault(); setIsDragging(false); handleFile(e.dataTransfer.files[0]); }}
          onClick={() => fileInputRef.current?.click()}
        >
          <div className="upload-icon">+</div>
          <div className="upload-text"><strong>Upload a file</strong> or drag here</div>
          <div className="upload-hint">PDF, TXT — up to 50 MB</div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt"
            style={{ display: 'none' }}
            onChange={(e) => { handleFile(e.target.files[0]); e.target.value = ''; }}
          />
        </div>
      </div>

      <div className="document-list">
        <div className="document-list-title">Documents ({documents.length})</div>
        {documents.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📄</div>
            <div className="empty-state-text">No documents uploaded</div>
          </div>
        ) : (
          documents.map((doc) => (
            <div key={doc.document_id} className="document-item">
              <div className={`doc-icon ${doc.file_type}`}>
                {doc.file_type === 'pdf' ? '📄' : '📝'}
              </div>
              <div className="doc-info">
                <div className="doc-name" title={doc.filename}>{doc.filename}</div>
                <div className="doc-meta">
                  <span>{formatSize(doc.file_size_bytes)}</span>
                  {doc.chunk_count > 0 && <span>· {doc.chunk_count} chunks</span>}
                </div>
              </div>
              <div className={`doc-status ${doc.processing_status}`}>
                {doc.processing_status}
              </div>
            </div>
          ))
        )}
      </div>

      {toast && (
        <div className={`toast ${toast.type}`}>
          <div className="toast-content">
            <span className="toast-icon">
              {toast.type === 'success' ? '✓' : toast.type === 'error' ? '✕' : '…'}
            </span>
            <span className="toast-text">{toast.message}</span>
          </div>
        </div>
      )}
    </>
  );
}
