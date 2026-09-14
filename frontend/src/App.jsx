import DocumentUploader from './components/DocumentUploader';
import ChatInterface from './components/ChatInterface';

export default function App() {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo">
            <div className="logo-icon">D</div>
            <div>
              <div className="logo-text">DocuMind</div>
              <div className="logo-sub">Search your documents with AI</div>
            </div>
          </div>
        </div>
        <DocumentUploader />
      </aside>
      <ChatInterface />
    </div>
  );
}
