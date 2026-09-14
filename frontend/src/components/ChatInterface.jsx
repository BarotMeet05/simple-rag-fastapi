import { useState, useRef, useEffect } from 'react';
import { sendChatMessage } from '../services/api';

const SUGGESTIONS = [
  "What technologies are mentioned in the documents?",
  "Give me a summary of the key points",
  "What are the rules around deployments?",
  "Tell me about the expense policy",
];

export default function ChatInterface() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  async function handleSend(questionOverride) {
    const question = questionOverride || input.trim();
    if (!question || isLoading) return;

    setMessages(prev => [...prev, { role: 'user', content: question }]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await sendChatMessage(question);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.answer,
        sources: res.sources || [],
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: err.message,
        sources: [],
        isError: true,
      }]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="main-content">
      <div className="chat-header">
        <h1>Chat</h1>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && !isLoading ? (
          <div className="chat-welcome">
            <div className="welcome-icon">D</div>
            <h2 className="welcome-title">Ask anything about your documents</h2>
            <p className="welcome-sub">
              Upload a PDF or text file in the sidebar, then ask questions here.
              Answers come only from your documents — nothing made up.
            </p>
            <div className="suggestion-chips">
              {SUGGESTIONS.map((s, i) => (
                <button key={i} className="suggestion-chip" onClick={() => handleSend(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <div key={i} className={`message ${msg.role}`}>
                <div className="message-label">
                  {msg.role === 'user' ? 'You' : 'DocuMind'}
                </div>
                <div className={`message-bubble ${msg.isError ? 'error' : ''}`}>
                  {msg.content}
                </div>
                {msg.sources && msg.sources.length > 0 && (
                  <div className="sources-container">
                    <span className="sources-title">Sources</span>
                    {msg.sources.map((src, si) => (
                      <span key={si} className="source-chip">
                        {src.document_name}, page {src.page_number}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="message assistant">
                <div className="message-label">DocuMind</div>
                <div className="message-bubble">
                  <div className="loading-dots">
                    <span /><span /><span />
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <div className="chat-input-wrapper">
          <textarea
            ref={inputRef}
            className="chat-input"
            placeholder="Type your question here..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={isLoading}
          />
          <button
            className="send-button"
            onClick={() => handleSend()}
            disabled={!input.trim() || isLoading}
          >
            ↑
          </button>
        </div>
      </div>
    </div>
  );
}
