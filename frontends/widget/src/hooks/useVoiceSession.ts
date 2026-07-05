/**
 * useVoiceSession Hook — WebRTC live voice session for KEA.
 *
 * What:    Manages microphone, WebRTC, Realtime data-channel events, and fallback state.
 * Does:    Starts only after consent, brokers SDP through the backend, forwards tool calls.
 * Why:     Voice mode must keep browser secrets out and all business tools server-side.
 * Who:     VoiceControls.tsx.
 * Depends: React, browser WebRTC APIs.
 */

import { useCallback, useRef, useState } from 'react';
import type { WidgetConfig } from '../lib/config';

type VoiceState =
  | 'idle'
  | 'connecting'
  | 'listening'
  | 'thinking'
  | 'speaking'
  | 'interrupted'
  | 'muted'
  | 'fallback_text'
  | 'ended'
  | 'error';

interface UseVoiceSessionOptions {
  config: WidgetConfig;
  visitorId: string;
  consentVersion: string;
}

interface VoiceSessionResponse {
  conversation_id: string;
  voice_session_id: string;
  sdp_answer: string;
}

export function useVoiceSession({
  config,
  visitorId,
  consentVersion,
}: UseVoiceSessionOptions) {
  const [state, setState] = useState<VoiceState>('idle');
  const [muted, setMuted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const peerRef = useRef<RTCPeerConnection | null>(null);
  const channelRef = useRef<RTCDataChannel | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const conversationIdRef = useRef<string | null>(null);

  const postJson = useCallback(
    async <T,>(path: string, body: unknown): Promise<T> => {
      const response = await fetch(`${config.apiHttpUrl}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return response.json() as Promise<T>;
    },
    [config.apiHttpUrl],
  );

  const persistTranscript = useCallback(
    async (role: 'user' | 'assistant', text: string, providerEventId?: string) => {
      if (!conversationIdRef.current || !text.trim()) return;
      await postJson('/voice/transcripts', {
        studio: config.studio,
        visitor_id: visitorId,
        conversation_id: conversationIdRef.current,
        role,
        text,
        provider_event_id: providerEventId ?? null,
        consent_granted: true,
      });
    },
    [config.studio, postJson, visitorId],
  );

  const handleToolCalls = useCallback(
    async (event: any) => {
      const output = event?.response?.output;
      if (!Array.isArray(output) || !conversationIdRef.current) return;
      for (const item of output) {
        if (item?.type !== 'function_call') continue;
        const toolResponse = await postJson<{
          realtime_events: unknown[];
        }>('/voice/tool-calls', {
          studio: config.studio,
          visitor_id: visitorId,
          conversation_id: conversationIdRef.current,
          tool_call_id: item.call_id,
          tool_name: item.name,
          arguments: item.arguments ? JSON.parse(item.arguments) : {},
          consent_granted: true,
        });
        for (const realtimeEvent of toolResponse.realtime_events) {
          channelRef.current?.send(JSON.stringify(realtimeEvent));
        }
      }
    },
    [config.studio, postJson, visitorId],
  );

  const handleRealtimeEvent = useCallback(
    (event: any) => {
      if (event.type === 'input_audio_buffer.speech_started') {
        setState((previous) => (previous === 'speaking' ? 'interrupted' : 'listening'));
      } else if (event.type === 'input_audio_buffer.speech_stopped') {
        setState('thinking');
      } else if (event.type === 'response.output_audio.delta') {
        setState('speaking');
      } else if (event.type === 'response.done') {
        setState('listening');
        void handleToolCalls(event).catch(() => setState('fallback_text'));
      } else if (event.type === 'conversation.item.input_audio_transcription.completed') {
        void persistTranscript('user', event.transcript ?? '', event.event_id);
      } else if (event.type === 'response.output_audio_transcript.done') {
        void persistTranscript('assistant', event.transcript ?? '', event.event_id);
      } else if (event.type === 'error') {
        setError('Die Sprachverbindung hat einen Fehler gemeldet.');
        setState('fallback_text');
      }
    },
    [handleToolCalls, persistTranscript],
  );

  const cleanup = useCallback(() => {
    channelRef.current?.close();
    peerRef.current?.close();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    channelRef.current = null;
    peerRef.current = null;
    streamRef.current = null;
  }, []);

  const start = useCallback(async () => {
    try {
      setError(null);
      setState('connecting');
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      streamRef.current = stream;
      const peer = new RTCPeerConnection();
      peerRef.current = peer;
      const remoteAudio = new Audio();
      remoteAudio.autoplay = true;
      peer.ontrack = (event) => {
        remoteAudio.srcObject = event.streams[0];
      };
      stream.getAudioTracks().forEach((track) => peer.addTrack(track, stream));

      const channel = peer.createDataChannel('oai-events');
      channelRef.current = channel;
      channel.onopen = () => setState('listening');
      channel.onmessage = (message) => {
        try {
          handleRealtimeEvent(JSON.parse(message.data as string));
        } catch {
          setState('fallback_text');
        }
      };
      peer.onconnectionstatechange = () => {
        if (peer.connectionState === 'failed' || peer.connectionState === 'disconnected') {
          setState('fallback_text');
        }
      };

      const offer = await peer.createOffer();
      await peer.setLocalDescription(offer);
      const session = await postJson<VoiceSessionResponse>('/voice/sessions/webrtc', {
        studio: config.studio,
        visitor_id: visitorId,
        client_sdp: offer.sdp,
        consent_granted: true,
        consent_version: consentVersion,
      });
      conversationIdRef.current = session.conversation_id;
      await peer.setRemoteDescription({ type: 'answer', sdp: session.sdp_answer });
    } catch {
      cleanup();
      setError('Sprache ist gerade nicht verfügbar. Der Textchat bleibt aktiv.');
      setState('fallback_text');
    }
  }, [cleanup, config.studio, consentVersion, handleRealtimeEvent, postJson, visitorId]);

  const stop = useCallback(async () => {
    const conversationId = conversationIdRef.current;
    cleanup();
    setState('ended');
    if (conversationId) {
      await postJson('/voice/sessions/end', {
        studio: config.studio,
        visitor_id: visitorId,
        conversation_id: conversationId,
        close_reason: 'user_ended',
        consent_granted: true,
      }).catch(() => undefined);
    }
  }, [cleanup, config.studio, postJson, visitorId]);

  const toggleMute = useCallback(() => {
    const nextMuted = !muted;
    streamRef.current?.getAudioTracks().forEach((track) => {
      track.enabled = !nextMuted;
    });
    setMuted(nextMuted);
    setState(nextMuted ? 'muted' : 'listening');
  }, [muted]);

  return { state, muted, error, start, stop, toggleMute };
}
