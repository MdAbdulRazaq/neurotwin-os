import { useState, useCallback, useRef } from 'react';
import { useAvatarStore } from '@/lib/stores/avatarStore';
import { apiClient } from '@/lib/api';
import type { Message } from '@/lib/types';

// Guaranteed fallback — never undefined in browser
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const VOICE_CONTEXT_TTL_MS = 15000;

type PerceptionContext = {
  emotionSource?: 'voice' | 'text' | 'manual';
  emotionConfidence?: number;
  arousal?: number;
  valence?: number;
  capturedAt?: number | null;
};

function getAccessToken(): string {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem('nt_access_token') || '';
}

function redirectToLogin(): void {
  if (typeof window !== 'undefined') {
    window.location.href = '/auth/login';
  }
}

export function useConversation() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentEmotion, setCurrentEmotion] = useState('neutral');
  const [currentPerception, setCurrentPerception] = useState<PerceptionContext>({
    emotionSource: 'text',
    capturedAt: null,
  });
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const { setExpression, setIsSpeaking } = useAvatarStore();

  // ── Create or reuse session ──────────────────────────────────────────────
  const ensureSession = useCallback(async (): Promise<string> => {
    if (sessionId) return sessionId;

    try {
      const resp = await apiClient.post('/v1/conversation/session', {});
      const id: string = resp.data.session_id;
      setSessionId(id);
      setSessionError(null);
      return id;
    } catch (err: any) {
      // 401 = token expired or missing → send to login
      if (err.response?.status === 401 || err.response?.status === 403) {
        redirectToLogin();
        throw new Error('Unauthenticated');
      }
      const msg = err.response?.data?.detail || 'Failed to start session';
      setSessionError(msg);
      throw new Error(msg);
    }
  }, [sessionId]);

  // ── Send message with SSE streaming ─────────────────────────────────────
  const sendMessage = useCallback(async (content: string) => {
    let sid: string;

    try {
      sid = await ensureSession();
    } catch {
      return;
    }

    // Add user message immediately to UI
    const userMsg: Message = {
      id: `user_${Date.now()}`,
      role: 'user',
      content,
      emotion: currentEmotion,
      createdAt: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setIsStreaming(true);
    setExpression('thinking');
    setIsSpeaking(false);

    // Placeholder assistant message (fills token-by-token)
    const assistantMsgId = `ast_${Date.now()}`;
    let assistantText = '';

    const assistantMsg: Message = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      createdAt: new Date().toISOString(),
    };
    setMessages(prev => [...prev, assistantMsg]);

    abortControllerRef.current = new AbortController();
    const hasFreshVoiceContext =
      currentPerception.emotionSource === 'voice' &&
      !!currentPerception.capturedAt &&
      Date.now() - currentPerception.capturedAt < VOICE_CONTEXT_TTL_MS &&
      (currentPerception.emotionConfidence ?? 0) >= 0.35 &&
      currentEmotion !== 'neutral';

    const requestEmotion = hasFreshVoiceContext ? currentEmotion : undefined;
    const requestPerception = hasFreshVoiceContext
      ? currentPerception
      : { emotionSource: 'text' as const, emotionConfidence: undefined, arousal: undefined, valence: undefined };

    try {
      const response = await fetch(
        `${API_URL}/v1/conversation/${sid}/stream`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getAccessToken()}`,
          },
          body: JSON.stringify({
            content,
            session_id: sid,
            emotion_hint: requestEmotion,
            emotion_source: requestPerception.emotionSource,
            emotion_confidence: requestPerception.emotionConfidence,
            arousal: requestPerception.arousal,
            valence: requestPerception.valence,
          }),
          signal: abortControllerRef.current.signal,
        }
      );

      // Handle auth failure on the stream endpoint
      if (response.status === 401 || response.status === 403) {
        redirectToLogin();
        return;
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();

      // ── SSE reader loop ──────────────────────────────────────────────────
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const rawText = decoder.decode(value, { stream: true });
        const lines = rawText.split('\n').filter(l => l.startsWith('data:'));

        for (const line of lines) {
          const raw = line.slice(5).trim();
          if (!raw) continue;

          try {
            const chunk = JSON.parse(raw);

            if (chunk.type === 'token') {
              assistantText += chunk.data;
              setMessages(prev =>
                prev.map(m =>
                  m.id === assistantMsgId ? { ...m, content: assistantText } : m
                )
              );
            } else if (chunk.type === 'avatar') {
              if (chunk.data === 'thinking') setExpression('thinking');
            } else if (chunk.type === 'done') {
              const avatarCmd = chunk.metadata?.avatar_command;
              if (avatarCmd?.expression) setExpression(avatarCmd.expression);
              setMessages(prev =>
                prev.map(m =>
                  m.id === assistantMsgId
                    ? { ...m, emotion: requestEmotion, avatarCommand: avatarCmd }
                    : m
                )
              );
            } else if (chunk.type === 'error') {
              console.error('[NEUROTWIN] Stream error from API:', chunk.data);
              setMessages(prev =>
                prev.map(m =>
                  m.id === assistantMsgId
                    ? { ...m, content: 'Something went wrong. Please try again.' }
                    : m
                )
              );
            }
          } catch {
            // Partial chunk — safe to ignore
          }
        }
      }

    } catch (err: any) {
      if (err.name === 'AbortError') return;

      console.error('[NEUROTWIN] sendMessage error:', err);
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantMsgId
            ? {
                ...m,
                content:
                  assistantText ||
                  'I had trouble responding. Please check your connection and try again.',
              }
            : m
        )
      );
    } finally {
      setIsStreaming(false);
      setIsSpeaking(false);
    }
  }, [ensureSession, currentEmotion, currentPerception, setExpression, setIsSpeaking]);

  // ── Controls ─────────────────────────────────────────────────────────────
  const stopStreaming = useCallback(() => {
    abortControllerRef.current?.abort();
    setIsStreaming(false);
    setIsSpeaking(false);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setSessionError(null);
  }, []);

  return {
    messages,
    sendMessage,
    stopStreaming,
    clearMessages,
    isStreaming,
    currentEmotion,
    setCurrentEmotion,
    currentPerception,
    setCurrentPerception,
    sessionId,
    sessionError,
  };
}
