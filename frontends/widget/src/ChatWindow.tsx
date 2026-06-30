/** Chat-Fenster mit Nachrichtenverlauf und Eingabefeld. */

import { useCallback, useEffect, useRef, useState } from 'react';
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
  const [chatMessages, setChatMessages] = useState<
    { role: 'user' | 'assistant'; content: string }[]
  >([{ role: 'assistant', content: config.welcomeMessage }]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const handleIncomingMessage = useCallback(
    (message: { role: 'user' | 'assistant'; content: string }) => {
      setChatMessages((prev) => [
        ...prev,
        { role: message.role, content: message.content },
      ]);
    },
    [],
  );

  const { send, connected, connecting, typing } = useWebSocket({
    url: config.apiUrl,
    studio: config.studio,
    visitorId,
    onMessage: handleIncomingMessage,
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages.length, typing]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || !connected) return;
    setChatMessages((prev) => [...prev, { role: 'user', content: text }]);
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
        {chatMessages.map((msg, i) => (
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
