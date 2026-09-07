// frontend/src/components/ChatInterface.jsx
import { useState, useRef, useEffect } from 'react';
import { sendChatMessage } from '../services/api';

const SUGGESTIONS = [
  "What technologies are mentioned?",
  "Summarize the key points",
  "What are the deployment rules?",
  "What is the expense policy?",
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

    setMessages((prev) => [...prev, { role: 'user', content: question }]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await sendChatMessage(question);
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: response.answer,
        sources: response.sources || [],
      }]);
    } catch (err) {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: `Something went wrong: ${err.message}`,
        sources: [],
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

  const showWelcome = messages.length === 0 && !isLoading;

  return (
    <div className="main-content">
      <div className="chat-header">
        <h1>Ask anything about your documents</h1>
      </div>

      <div className="chat-messages">
        {showWelcome ? (
          <div className="chat-welcome">
            <div className="welcome-icon">⚡</div>
            <h2 className="welcome-title">What do you want to know?</h2>
            <p className="welcome-sub">
              Upload documents in the sidebar, then ask questions here. 
              Answers are generated from your files only — no outside data.
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
                <div className="message-bubble">{msg.content}</div>
                {msg.sources && msg.sources.length > 0 && (
                  <div className="sources-container">
                    <span className="sources-title">Sources:</span>
                    {msg.sources.map((src, si) => (
                      <span key={si} className="source-chip">
                        {src.document_name} p.{src.page_number}
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
                    <span></span><span></span><span></span>
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
            placeholder="Ask a question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
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
