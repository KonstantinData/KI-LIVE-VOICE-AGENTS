/** Chat-Fenster mit Nachrichtenverlauf und Eingabefeld. */

import { useEffect, useRef, useState } from 'react';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';
import { useWebSocket } from './hooks/useWebSocket';
import type { WidgetConfig } from './lib/config';

interface ChatWindowProps {
  config: WidgetConfig;
  visitorId: string;
}

export function ChatWindow({ config, visitorId }: ChatWindowProps) {
  const [input, setInput] = useState('');
  const [userMessages, setUserMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { messages, send, connected, connecting, typing } = useWebSocket({
    url: config.apiUrl,
    studio: config.studio,
    visitorId,
  });

  // Erste Willkommensnachricht
  const allMessages = [
    { role: 'assistant' as const, content: config.welcomeMessage },
    ...messages,
    ...userMessages,
  ];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [allMessages.length]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || !connected) return;
    setUserMessages((prev) => [...prev, { role: 'user', content: text }]);
    send(text);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      <div className="widget-header">
        <div>
          <div className="widget-header-title">{config.agentName}</div>
          <div className="widget-header-subtitle">
            {connecting ? 'Verbinde...' : connected ? 'Online' : 'Offline'}
          </div>
        </div>
      </div>

      <div className="widget-messages">
        {allMessages.map((msg, i) => (
          <MessageBubble key={i} role={msg.role} content={msg.content} />
        ))}
        {typing && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      <div className="widget-input-area">
        <textarea
          className="widget-input"
          placeholder="Schreiben Sie eine Nachricht..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
        />
        <button
          className="widget-send-button"
          onClick={handleSend}
          disabled={!connected || !input.trim()}
          aria-label="Senden"
        >
          ➤
        </button>
      </div>
    </>
  );
}
