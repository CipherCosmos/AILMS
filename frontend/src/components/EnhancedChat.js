import React, { useState, useRef, useEffect } from "react";
import api from "../services/api";

function EnhancedChat({ courseId, sessionId, onMessageSent }) {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    loadChatHistory();
  }, [courseId, sessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadChatHistory = async () => {
    if (!courseId || !sessionId) return;

    try {
      const response = await api.get(`/chats/${courseId}/${sessionId}`);
      const formattedMessages = response.data.map(msg => ({
        ...msg,
        formattedContent: formatMessageContent(msg.message)
      }));
      setMessages(formattedMessages);
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  };

  const formatMessageContent = (content) => {
    if (!content) return { type: 'text', content: '' };

    // Check for code blocks (```language\ncode\n```)
    const codeBlockRegex = /```(\w+)?\n?([\s\S]*?)```/g;
    const codeMatches = [...content.matchAll(codeBlockRegex)];

    if (codeMatches.length > 0) {
      const parts = [];
      let lastIndex = 0;

      codeMatches.forEach((match, index) => {
        // Add text before code block
        if (match.index > lastIndex) {
          const textBefore = content.slice(lastIndex, match.index);
          if (textBefore.trim()) {
            parts.push({
              type: 'text',
              content: formatTextContent(textBefore)
            });
          }
        }

        // Add code block
        parts.push({
          type: 'code',
          language: match[1] || 'text',
          content: match[2].trim(),
          highlighted: highlightCode(match[2].trim(), match[1] || 'text')
        });

        lastIndex = match.index + match[0].length;
      });

      // Add remaining text
      if (lastIndex < content.length) {
        const remainingText = content.slice(lastIndex);
        if (remainingText.trim()) {
          parts.push({
            type: 'text',
            content: formatTextContent(remainingText)
          });
        }
      }

      return parts.length === 1 ? parts[0] : { type: 'mixed', parts };
    }

    // Check for inline code (`code`)
    if (content.includes('`')) {
      return {
        type: 'text',
        content: formatTextContent(content)
      };
    }

    // Regular text with formatting
    return {
      type: 'text',
      content: formatTextContent(content)
    };
  };

  const formatTextContent = (text) => {
    // Handle inline code
    text = text.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

    // Handle bold text
    text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Handle italic text
    text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Handle lists
    text = text.replace(/^\* (.+)$/gm, '<li>$1</li>');
    text = text.replace(/^- (.+)$/gm, '<li>$1</li>');

    // Handle line breaks
    text = text.replace(/\n/g, '<br>');

    return text;
  };

  const highlightCode = (code, language) => {
    // Basic syntax highlighting for common languages
    let highlighted = code;

    // Comments
    if (language === 'javascript' || language === 'js' || language === 'typescript' || language === 'ts') {
      highlighted = highlighted.replace(/(\/\/.*$)/gm, '<span class="comment">$1</span>');
      highlighted = highlighted.replace(/(\/\*[\s\S]*?\*\/)/g, '<span class="comment">$1</span>');
    } else if (language === 'python' || language === 'py') {
      highlighted = highlighted.replace(/(#.*$)/gm, '<span class="comment">$1</span>');
      highlighted = highlighted.replace(/("""[\s\S]*?""")/g, '<span class="comment">$1</span>');
    }

    // Strings
    highlighted = highlighted.replace(/(["'`])(.*?)\1/g, '<span class="string">$1$2$1</span>');

    // Keywords
    const keywords = {
      javascript: ['const', 'let', 'var', 'function', 'return', 'if', 'else', 'for', 'while', 'class', 'import', 'export'],
      python: ['def', 'class', 'if', 'elif', 'else', 'for', 'while', 'import', 'from', 'return', 'try', 'except'],
      text: []
    };

    const langKeywords = keywords[language] || [];
    langKeywords.forEach(keyword => {
      const regex = new RegExp(`\\b${keyword}\\b`, 'g');
      highlighted = highlighted.replace(regex, `<span class="keyword">${keyword}</span>`);
    });

    // Numbers
    highlighted = highlighted.replace(/\b\d+\.?\d*\b/g, '<span class="number">$&</span>');

    return highlighted;
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      message: inputMessage,
      timestamp: new Date().toISOString(),
      formattedContent: formatMessageContent(inputMessage)
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage("");
    setIsLoading(true);
    setIsTyping(true);

    try {
      const response = await api.post('/ai/chat', {
        course_id: courseId,
        session_id: sessionId,
        message: inputMessage
      });

      const assistantMessage = {
        id: response.data.assistant_message_id || (Date.now() + 1).toString(),
        role: 'assistant',
        message: response.data.reply,
        timestamp: new Date().toISOString(),
        formattedContent: formatMessageContent(response.data.reply)
      };

      setMessages(prev => [...prev, assistantMessage]);
      onMessageSent?.(assistantMessage);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        id: (Date.now() + 2).toString(),
        role: 'assistant',
        message: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
        formattedContent: formatMessageContent('Sorry, I encountered an error. Please try again.')
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      // You could add a toast notification here
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  const renderMessageContent = (formattedContent) => {
    if (formattedContent.type === 'mixed') {
      return (
        <div className="mixed-content">
          {formattedContent.parts.map((part, index) => (
            <div key={index}>
              {part.type === 'code' ? (
                <div className="code-block-container">
                  <div className="code-header">
                    <span className="code-language">{part.language}</span>
                    <button
                      className="copy-btn"
                      onClick={() => copyToClipboard(part.content)}
                      title="Copy code"
                    >
                      📋
                    </button>
                  </div>
                  <pre className={`code-block language-${part.language}`}>
                    <code dangerouslySetInnerHTML={{ __html: part.highlighted }} />
                  </pre>
                </div>
              ) : (
                <div
                  className="text-content"
                  dangerouslySetInnerHTML={{ __html: part.content }}
                />
              )}
            </div>
          ))}
        </div>
      );
    }

    if (formattedContent.type === 'code') {
      return (
        <div className="code-block-container">
          <div className="code-header">
            <span className="code-language">{formattedContent.language}</span>
            <button
              className="copy-btn"
              onClick={() => copyToClipboard(formattedContent.content)}
              title="Copy code"
            >
              📋
            </button>
          </div>
          <pre className={`code-block language-${formattedContent.language}`}>
            <code dangerouslySetInnerHTML={{ __html: formattedContent.highlighted }} />
          </pre>
        </div>
      );
    }

    return (
      <div
        className="text-content"
        dangerouslySetInnerHTML={{ __html: formattedContent.content }}
      />
    );
  };

  return (
    <div className="enhanced-chat">
      <div className="chat-header">
        <h3>AI Learning Assistant</h3>
        <p>Ask me anything about this course!</p>
      </div>

      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="empty-chat">
            <div className="empty-icon">🤖</div>
            <h4>Start a conversation</h4>
            <p>Ask me questions about the course content, concepts, or anything you're curious about!</p>
            <div className="suggested-questions">
              <button className="suggested-btn" onClick={() => setInputMessage("What are the key concepts in this lesson?")}>
                What are the key concepts?
              </button>
              <button className="suggested-btn" onClick={() => setInputMessage("Can you give me a practice problem?")}>
                Give me a practice problem
              </button>
              <button className="suggested-btn" onClick={() => setInputMessage("Explain this topic in simple terms")}>
                Explain in simple terms
              </button>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`message ${message.role}`}
            >
              <div className="message-avatar">
                {message.role === 'user' ? '👤' : '🤖'}
              </div>
              <div className="message-content">
                <div className="message-header">
                  <span className="message-role">
                    {message.role === 'user' ? 'You' : 'AI Assistant'}
                  </span>
                  <span className="message-time">
                    {new Date(message.timestamp).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </span>
                </div>
                <div className="message-body">
                  {renderMessageContent(message.formattedContent)}
                </div>
              </div>
            </div>
          ))
        )}

        {isTyping && (
          <div className="message assistant typing">
            <div className="message-avatar">🤖</div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <div className="input-wrapper">
          <textarea
            ref={textareaRef}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me anything about the course..."
            className="chat-input"
            rows={1}
            disabled={isLoading}
          />
          <button
            className="send-btn"
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isLoading}
          >
            {isLoading ? (
              <div className="loading-spinner"></div>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M22 2L11 13M22 2L15 22L11 13M22 2L2 9L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            )}
          </button>
        </div>
        <div className="input-footer">
          <span className="input-hint">
            Press Enter to send, Shift+Enter for new line
          </span>
        </div>
      </div>

      <style jsx>{`
        .enhanced-chat {
          display: flex;
          flex-direction: column;
          height: 100%;
          background: rgba(255, 255, 255, 0.9);
          backdrop-filter: blur(20px);
          border-radius: var(--radius-xl);
          overflow: hidden;
          box-shadow: var(--shadow-lg);
        }

        .chat-header {
          padding: var(--space-4) var(--space-6);
          background: linear-gradient(135deg, var(--primary-50), var(--secondary-50));
          border-bottom: 1px solid var(--gray-200);
        }

        .chat-header h3 {
          margin: 0 0 var(--space-1) 0;
          font-size: 1.125rem;
          font-weight: 700;
          color: var(--gray-900);
        }

        .chat-header p {
          margin: 0;
          font-size: 0.875rem;
          color: var(--gray-600);
        }

        .chat-messages {
          flex: 1;
          overflow-y: auto;
          padding: var(--space-4) var(--space-6);
          display: flex;
          flex-direction: column;
          gap: var(--space-4);
        }

        .empty-chat {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          text-align: center;
          padding: var(--space-8);
        }

        .empty-icon {
          font-size: 3rem;
          margin-bottom: var(--space-4);
          opacity: 0.7;
        }

        .empty-chat h4 {
          margin: 0 0 var(--space-2) 0;
          color: var(--gray-900);
          font-size: 1.125rem;
        }

        .empty-chat p {
          margin: 0 0 var(--space-6) 0;
          color: var(--gray-600);
          max-width: 300px;
        }

        .suggested-questions {
          display: flex;
          flex-wrap: wrap;
          gap: var(--space-2);
          justify-content: center;
        }

        .suggested-btn {
          padding: var(--space-2) var(--space-4);
          background: var(--gray-100);
          border: 1px solid var(--gray-200);
          border-radius: var(--radius-lg);
          color: var(--gray-700);
          cursor: pointer;
          font-size: 0.8125rem;
          transition: all var(--transition-fast);
        }

        .suggested-btn:hover {
          background: var(--primary-50);
          border-color: var(--primary-200);
          color: var(--primary-700);
        }

        .message {
          display: flex;
          gap: var(--space-3);
          max-width: 80%;
        }

        .message.user {
          align-self: flex-end;
          flex-direction: row-reverse;
        }

        .message.assistant {
          align-self: flex-start;
        }

        .message-avatar {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1rem;
          flex-shrink: 0;
        }

        .message.user .message-avatar {
          background: linear-gradient(135deg, var(--primary-500), var(--secondary-500));
          color: white;
        }

        .message.assistant .message-avatar {
          background: var(--gray-200);
          color: var(--gray-700);
        }

        .message-content {
          flex: 1;
          min-width: 0;
        }

        .message-header {
          display: flex;
          align-items: center;
          gap: var(--space-2);
          margin-bottom: var(--space-2);
        }

        .message-role {
          font-weight: 600;
          font-size: 0.8125rem;
          color: var(--gray-900);
        }

        .message-time {
          font-size: 0.75rem;
          color: var(--gray-500);
        }

        .message-body {
          background: white;
          border-radius: var(--radius-lg);
          padding: var(--space-4);
          box-shadow: var(--shadow-sm);
          border: 1px solid var(--gray-100);
        }

        .message.user .message-body {
          background: linear-gradient(135deg, var(--primary-500), var(--secondary-500));
          color: white;
        }

        .text-content {
          line-height: 1.6;
          color: var(--gray-700);
        }

        .message.user .text-content {
          color: white;
        }

        .text-content strong {
          font-weight: 700;
          color: var(--gray-900);
        }

        .message.user .text-content strong {
          color: white;
        }

        .text-content em {
          font-style: italic;
        }

        .text-content .inline-code {
          background: var(--gray-100);
          padding: 0.125rem 0.25rem;
          border-radius: var(--radius-sm);
          font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
          font-size: 0.875em;
          color: var(--gray-800);
        }

        .message.user .inline-code {
          background: rgba(255, 255, 255, 0.2);
          color: white;
        }

        .text-content li {
          margin-left: var(--space-4);
          margin-bottom: var(--space-1);
        }

        .code-block-container {
          margin: var(--space-4) 0;
          border-radius: var(--radius-lg);
          overflow: hidden;
          box-shadow: var(--shadow-sm);
        }

        .code-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: var(--space-2) var(--space-4);
          background: var(--gray-800);
          color: var(--gray-300);
          font-size: 0.75rem;
          font-weight: 600;
        }

        .code-language {
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .copy-btn {
          background: none;
          border: none;
          color: var(--gray-400);
          cursor: pointer;
          padding: var(--space-1);
          border-radius: var(--radius-sm);
          transition: all var(--transition-fast);
        }

        .copy-btn:hover {
          background: var(--gray-700);
          color: white;
        }

        .code-block {
          margin: 0;
          padding: var(--space-4);
          background: var(--gray-900);
          color: var(--gray-100);
          font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
          font-size: 0.875rem;
          line-height: 1.5;
          overflow-x: auto;
        }

        .code-block .comment {
          color: var(--gray-500);
          font-style: italic;
        }

        .code-block .string {
          color: #98c379;
        }

        .code-block .keyword {
          color: #c678dd;
          font-weight: 600;
        }

        .code-block .number {
          color: #d19a66;
        }

        .mixed-content {
          display: flex;
          flex-direction: column;
          gap: var(--space-4);
        }

        .typing-indicator {
          display: flex;
          gap: var(--space-1);
          padding: var(--space-2) 0;
        }

        .typing-indicator span {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: var(--gray-400);
          animation: typing 1.4s infinite;
        }

        .typing-indicator span:nth-child(2) {
          animation-delay: 0.2s;
        }

        .typing-indicator span:nth-child(3) {
          animation-delay: 0.4s;
        }

        @keyframes typing {
          0%, 60%, 100% {
            transform: translateY(0);
            opacity: 0.4;
          }
          30% {
            transform: translateY(-10px);
            opacity: 1;
          }
        }

        .chat-input-container {
          padding: var(--space-4) var(--space-6);
          background: rgba(255, 255, 255, 0.9);
          border-top: 1px solid var(--gray-200);
        }

        .input-wrapper {
          display: flex;
          gap: var(--space-3);
          align-items: flex-end;
          background: white;
          border: 2px solid var(--gray-200);
          border-radius: var(--radius-xl);
          padding: var(--space-3);
          transition: all var(--transition-fast);
        }

        .input-wrapper:focus-within {
          border-color: var(--primary-500);
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .chat-input {
          flex: 1;
          border: none;
          outline: none;
          resize: none;
          font-family: inherit;
          font-size: 0.875rem;
          line-height: 1.5;
          color: var(--gray-900);
          background: transparent;
          min-height: 20px;
          max-height: 100px;
        }

        .chat-input::placeholder {
          color: var(--gray-400);
        }

        .send-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 40px;
          height: 40px;
          background: linear-gradient(135deg, var(--primary-600), var(--secondary-600));
          border: none;
          border-radius: var(--radius-lg);
          color: white;
          cursor: pointer;
          transition: all var(--transition-fast);
          flex-shrink: 0;
        }

        .send-btn:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: var(--shadow-md);
        }

        .send-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
          transform: none;
        }

        .loading-spinner {
          width: 20px;
          height: 20px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-top: 2px solid white;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        .input-footer {
          margin-top: var(--space-2);
          text-align: center;
        }

        .input-hint {
          font-size: 0.75rem;
          color: var(--gray-500);
        }

        /* Responsive Design */
        @media (max-width: 768px) {
          .chat-header {
            padding: var(--space-3) var(--space-4);
          }

          .chat-messages {
            padding: var(--space-3) var(--space-4);
          }

          .chat-input-container {
            padding: var(--space-3) var(--space-4);
          }

          .message {
            max-width: 90%;
          }

          .message.user {
            max-width: 85%;
          }

          .code-block {
            font-size: 0.8125rem;
          }
        }

        @media (max-width: 480px) {
          .enhanced-chat {
            border-radius: 0;
          }

          .chat-header {
            padding: var(--space-2);
          }

          .chat-messages {
            padding: var(--space-2);
          }

          .chat-input-container {
            padding: var(--space-2);
          }

          .message {
            gap: var(--space-2);
          }

          .message-avatar {
            width: 28px;
            height: 28px;
            font-size: 0.875rem;
          }

          .message-body {
            padding: var(--space-3);
          }

          .input-wrapper {
            padding: var(--space-2);
          }

          .send-btn {
            width: 36px;
            height: 36px;
          }
        }
      `}</style>
    </div>
  );
}

export default EnhancedChat;