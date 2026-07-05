/**
 * useWebSocket Hook — WebSocket connection with auto-reconnect.
 *
 * What:    Manages a WebSocket connection to the chat backend.
 * Does:    Connects only when `enabled` is true; auto-reconnects on disconnect.
 * Why:     `enabled` gate ensures WebSocket does NOT connect before DSGVO consent
 *          is given (Art. 6/7 DSGVO). ChatWindow passes enabled=true after consent.
 * Who:     ChatWindow.tsx
 * Depends: React
 */

import { useCallback, useEffect, useRef, useState } from 'react';

export interface Choice {
  id: string;
  label: string;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  choices?: Choice[];
}

interface UseWebSocketOptions {
  url: string;
  studio: string;
  visitorId: string;
  /** Only connect when true — must be false until DSGVO consent is given. */
  enabled?: boolean;
  onMessage?: (message: Message) => void;
  onSession?: (conversationId: string) => void;
}

interface UseWebSocketReturn {
  messages: Message[];
  send: (text: string) => void;
  sendAction: (actionId: string, label: string) => void;
  connected: boolean;
  connecting: boolean;
  typing: boolean;
}

export function useWebSocket({
  url,
  studio,
  visitorId,
  enabled = true,
  onMessage,
  onSession,
}: UseWebSocketOptions): UseWebSocketReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [typing, setTyping] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (!enabled) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setConnecting(true);
    const params = new URLSearchParams({
      studio,
      visitor: visitorId,
      consent: '1',
    });
    const wsUrl = `${url}/ws/chat?${params.toString()}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setConnecting(false);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string);
        if (data.type === 'message') {
          const msg: Message = {
            role: data.role,
            content: data.content,
            timestamp: data.timestamp ?? new Date().toISOString(),
            choices: Array.isArray(data.choices) ? data.choices : undefined,
          };
          setTyping(false);
          setMessages((prev) => [...prev, msg]);
          onMessage?.(msg);
        } else if (data.type === 'typing') {
          setTyping(true);
        } else if (data.type === 'session' && typeof data.conversation_id === 'string') {
          onSession?.(data.conversation_id);
        } else if (data.type === 'error') {
          const msg: Message = {
            role: 'assistant',
            content: data.message ?? 'KEA ist gerade technisch nicht erreichbar.',
            timestamp: data.timestamp ?? new Date().toISOString(),
          };
          setTyping(false);
          setMessages((prev) => [...prev, msg]);
          onMessage?.(msg);
        }
      } catch {
        // Nicht-JSON Nachricht ignorieren
      }
    };

    ws.onclose = () => {
      setConnected(false);
      setConnecting(false);
      setTyping(false);
      if (enabled) {
        // Reconnect nach 3 Sekunden
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [url, studio, visitorId, enabled, onMessage, onSession]);

  useEffect(() => {
    if (enabled) {
      connect();
    }
    return () => {
      reconnectTimeoutRef.current && clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [connect, enabled]);

  const send = useCallback((text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ message: text }));
    }
  }, []);

  const sendAction = useCallback((actionId: string, label: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action_id: actionId, label }));
    }
  }, []);

  return { messages, send, sendAction, connected, connecting, typing };
}
