'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Mic, MicOff, Settings, Brain, Sparkles, Volume2, VolumeX } from 'lucide-react';
import { AvatarCanvas } from '@/components/avatar/AvatarCanvas';
import { MessageBubble } from '@/components/chat/MessageBubble';
import { VoiceControl } from '@/components/voice/VoiceControl';
import { EmotionIndicator } from '@/components/chat/EmotionIndicator';
import { useConversation } from '@/lib/hooks/useConversation';
import { useVoice } from '@/lib/hooks/useVoice';
import { useAvatarStore } from '@/lib/stores/avatarStore';
import { cn } from '@/lib/utils';

export default function ChatPage() {
  const router = useRouter();
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [voiceMode, setVoiceMode] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const typingTimerRef = useRef<NodeJS.Timeout>();

  const {
    messages,
    sendMessage,
    isStreaming,
    currentEmotion,
    setCurrentEmotion,
    setCurrentPerception,
    sessionId,
    sessionError,
  } = useConversation();
  const {
    isListening,
    transcript,
    emotion,
    emotionConfidence,
    arousal,
    valence,
    emotionCapturedAt,
    toggleListening,
    clearTranscript,
  } = useVoice();
  const { expression, isSpeaking } = useAvatarStore();

  // ── Auth guard — redirect to login if no token ───────────────────────────
  useEffect(() => {
    const token = localStorage.getItem('nt_access_token');
    if (!token) {
      router.replace('/auth/login');
    }
  }, [router]);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Fill input from voice transcript
  useEffect(() => {
    if (transcript) setInput(transcript);
  }, [transcript]);

  // Sync voice-detected emotion to conversation context
  useEffect(() => {
    setCurrentEmotion(emotion);
    setCurrentPerception({
      emotionSource: 'voice',
      emotionConfidence,
      arousal,
      valence,
      capturedAt: emotionCapturedAt,
    });
  }, [emotion, emotionConfidence, arousal, valence, emotionCapturedAt, setCurrentEmotion, setCurrentPerception]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || isStreaming) return;
    setInput('');
    clearTranscript();
    await sendMessage(text);
    inputRef.current?.focus();
  }, [input, isStreaming, sendMessage, clearTranscript]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleTyping = (value: string) => {
    setInput(value);
    setIsTyping(true);
    clearTimeout(typingTimerRef.current);
    typingTimerRef.current = setTimeout(() => setIsTyping(false), 1000);
  };

  return (
    <div className="chat-root">
      {/* ── Background atmosphere ── */}
      <div className="atmosphere" />

      {/* ── Left: Avatar Panel ── */}
      <aside className="avatar-panel">
        <div className="avatar-header">
          <div className="brand-mark">
            <Sparkles size={14} />
            <span>NEUROTWIN</span>
          </div>
          <EmotionIndicator emotion={currentEmotion} />
        </div>

        <div className="avatar-viewport">
          <AvatarCanvas
            sessionId={sessionId}
            expression={expression}
            isSpeaking={isSpeaking}
            emotion={currentEmotion}
          />
          <div className="avatar-glow" />
        </div>

        <div className="avatar-footer">
          <div className="status-row">
            <span className={cn('status-dot', isSpeaking && 'speaking')} />
            <span className="status-label">
              {isSpeaking ? 'Speaking\u2026' : isStreaming ? 'Thinking\u2026' : 'Listening'}
            </span>
          </div>
          <div className="avatar-controls">
            <button
              className={cn('icon-btn', !soundEnabled && 'muted')}
              onClick={() => setSoundEnabled(v => !v)}
              title="Toggle sound"
            >
              {soundEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
            </button>
            <button className="icon-btn" title="Memory"><Brain size={16} /></button>
            <button className="icon-btn" title="Settings"><Settings size={16} /></button>
          </div>
        </div>
      </aside>

      {/* ── Right: Chat Panel ── */}
      <main className="chat-panel">

        {/* Session error banner */}
        {sessionError && (
          <div className="session-error-banner">
            ⚠️ {sessionError}
          </div>
        )}

        {/* Message list */}
        <div className="messages-container">
          <AnimatePresence initial={false}>
            {messages.length === 0 && (
              <motion.div
                className="empty-state"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
              >
                <div className="empty-icon"><Sparkles size={32} /></div>
                <h2>Hello, I&apos;m your NEUROTWIN</h2>
                <p>I remember everything, sense how you feel, and grow with you every day. What&apos;s on your mind?</p>
                <div className="starter-chips">
                  {STARTER_PROMPTS.map((p) => (
                    <button key={p} className="chip" onClick={() => { setInput(p); inputRef.current?.focus(); }}>
                      {p}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            {messages.map((msg, i) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                isLatest={i === messages.length - 1}
              />
            ))}

            {isStreaming && (
              <motion.div
                className="typing-indicator"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <span /><span /><span />
              </motion.div>
            )}
          </AnimatePresence>
          <div ref={messagesEndRef} />
        </div>

        {/* Voice mode overlay */}
        <AnimatePresence>
          {voiceMode && (
            <motion.div
              className="voice-overlay"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
            >
              <VoiceControl
                isListening={isListening}
                transcript={transcript}
                onToggle={toggleListening}
                onSend={handleSend}
                onClose={() => setVoiceMode(false)}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Input bar */}
        <div className="input-bar">
          <div className={cn('input-wrapper', isTyping && 'active')}>
            <textarea
              ref={inputRef}
              className="chat-input"
              value={input}
              onChange={(e) => handleTyping(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Say something\u2026"
              rows={1}
              disabled={isStreaming}
            />

            <div className="input-actions">
              <button
                className={cn('voice-btn', isListening && 'recording')}
                onClick={() => { toggleListening(); if (!voiceMode) setVoiceMode(true); }}
                title={isListening ? 'Stop listening' : 'Voice input'}
              >
                {isListening ? <MicOff size={18} /> : <Mic size={18} />}
              </button>
              <button
                className={cn('send-btn', !input.trim() && 'disabled')}
                onClick={handleSend}
                disabled={!input.trim() || isStreaming}
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </div>
      </main>

      <style jsx>{`
        .chat-root {
          display: flex;
          height: 100vh;
          width: 100vw;
          overflow: hidden;
          background: #080c14;
          font-family: 'Sora', 'DM Sans', sans-serif;
          position: relative;
        }
        .atmosphere {
          position: absolute;
          inset: 0;
          background:
            radial-gradient(ellipse 60% 50% at 20% 50%, rgba(99,102,241,0.08) 0%, transparent 70%),
            radial-gradient(ellipse 40% 60% at 80% 30%, rgba(139,92,246,0.06) 0%, transparent 70%),
            radial-gradient(ellipse 30% 40% at 50% 80%, rgba(20,184,166,0.04) 0%, transparent 60%);
          pointer-events: none;
          z-index: 0;
        }
        .session-error-banner {
          background: rgba(239,68,68,0.12);
          border-bottom: 1px solid rgba(239,68,68,0.25);
          padding: 10px 40px;
          font-size: 13px;
          color: rgba(248,113,113,0.9);
          text-align: center;
          z-index: 2;
          position: relative;
        }
        .avatar-panel {
          width: 340px;
          min-width: 300px;
          flex-shrink: 0;
          display: flex;
          flex-direction: column;
          border-right: 1px solid rgba(255,255,255,0.06);
          background: rgba(10,13,22,0.7);
          backdrop-filter: blur(20px);
          position: relative;
          z-index: 1;
        }
        .avatar-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 20px 20px 0;
        }
        .brand-mark {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          color: rgba(139,92,246,0.9);
        }
        .avatar-viewport {
          flex: 1;
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
          overflow: hidden;
        }
        .avatar-glow {
          position: absolute;
          bottom: -40px;
          left: 50%;
          transform: translateX(-50%);
          width: 200px;
          height: 200px;
          background: radial-gradient(ellipse, rgba(99,102,241,0.2) 0%, transparent 70%);
          pointer-events: none;
        }
        .avatar-footer {
          padding: 16px 20px 24px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          border-top: 1px solid rgba(255,255,255,0.04);
        }
        .status-row { display: flex; align-items: center; gap: 8px; }
        .status-dot {
          width: 8px; height: 8px; border-radius: 50%;
          background: rgba(20,184,166,0.7); transition: all 0.3s;
        }
        .status-dot.speaking {
          background: #a78bfa;
          box-shadow: 0 0 8px rgba(167,139,250,0.6);
          animation: pulse 1s infinite;
        }
        @keyframes pulse {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.3); opacity: 0.7; }
        }
        .status-label { font-size: 12px; color: rgba(255,255,255,0.4); font-weight: 500; }
        .avatar-controls { display: flex; gap: 4px; }
        .icon-btn {
          width: 32px; height: 32px; border-radius: 8px; border: none;
          background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.4);
          cursor: pointer; display: flex; align-items: center; justify-content: center;
          transition: all 0.2s;
        }
        .icon-btn:hover { background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.8); }
        .icon-btn.muted { color: rgba(239,68,68,0.7); }
        .chat-panel {
          flex: 1; display: flex; flex-direction: column;
          position: relative; z-index: 1; overflow: hidden;
        }
        .messages-container {
          flex: 1; overflow-y: auto; padding: 32px 40px 16px;
          display: flex; flex-direction: column; gap: 4px;
          scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.08) transparent;
        }
        .empty-state {
          flex: 1; display: flex; flex-direction: column; align-items: center;
          justify-content: center; text-align: center; padding: 60px 40px; gap: 16px;
        }
        .empty-icon {
          width: 64px; height: 64px; border-radius: 20px;
          background: linear-gradient(135deg, rgba(99,102,241,0.3), rgba(139,92,246,0.2));
          border: 1px solid rgba(139,92,246,0.3);
          display: flex; align-items: center; justify-content: center;
          color: rgba(139,92,246,0.9); margin-bottom: 8px;
        }
        .empty-state h2 { font-size: 22px; font-weight: 700; color: rgba(255,255,255,0.9); letter-spacing: -0.02em; }
        .empty-state p { font-size: 14px; color: rgba(255,255,255,0.4); max-width: 380px; line-height: 1.7; }
        .starter-chips { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 8px; }
        .chip {
          background: rgba(99,102,241,0.1); border: 1px solid rgba(99,102,241,0.25);
          border-radius: 100px; padding: 8px 16px; font-size: 13px;
          color: rgba(99,102,241,0.9); cursor: pointer; transition: all 0.2s; font-family: inherit;
        }
        .chip:hover { background: rgba(99,102,241,0.2); border-color: rgba(99,102,241,0.5); transform: translateY(-1px); }
        .typing-indicator {
          display: flex; gap: 5px; padding: 12px 16px; align-items: center;
          align-self: flex-start; background: rgba(255,255,255,0.04);
          border-radius: 16px 16px 16px 4px; margin: 4px 0;
        }
        .typing-indicator span {
          width: 7px; height: 7px; border-radius: 50%;
          background: rgba(139,92,246,0.6); animation: bounce 1.2s infinite;
        }
        .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
        .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.6; }
          30% { transform: translateY(-6px); opacity: 1; }
        }
        .voice-overlay {
          position: absolute; inset: 0; z-index: 20;
          background: rgba(8,12,20,0.92); backdrop-filter: blur(12px);
          display: flex; align-items: center; justify-content: center;
        }
        .input-bar { padding: 20px 40px 28px; border-top: 1px solid rgba(255,255,255,0.04); }
        .input-wrapper {
          display: flex; align-items: flex-end; gap: 12px;
          background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
          border-radius: 16px; padding: 12px 12px 12px 20px; transition: all 0.2s;
        }
        .input-wrapper.active {
          border-color: rgba(99,102,241,0.4); background: rgba(99,102,241,0.05);
          box-shadow: 0 0 0 3px rgba(99,102,241,0.08);
        }
        .chat-input {
          flex: 1; background: transparent; border: none; outline: none;
          color: rgba(255,255,255,0.9); font-size: 15px; font-family: inherit;
          line-height: 1.5; resize: none; max-height: 120px; overflow-y: auto;
        }
        .chat-input::placeholder { color: rgba(255,255,255,0.2); }
        .input-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }
        .voice-btn {
          width: 38px; height: 38px; border-radius: 10px;
          border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.05);
          color: rgba(255,255,255,0.5); cursor: pointer; display: flex;
          align-items: center; justify-content: center; transition: all 0.2s; font-family: inherit;
        }
        .voice-btn:hover { background: rgba(255,255,255,0.1); color: white; }
        .voice-btn.recording {
          background: rgba(239,68,68,0.2); border-color: rgba(239,68,68,0.5);
          color: rgb(239,68,68); animation: recording-pulse 1.5s infinite;
        }
        @keyframes recording-pulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.3); }
          50% { box-shadow: 0 0 0 8px rgba(239,68,68,0); }
        }
        .send-btn {
          width: 38px; height: 38px; border-radius: 10px; border: none;
          background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white;
          cursor: pointer; display: flex; align-items: center; justify-content: center;
          transition: all 0.2s; font-family: inherit;
        }
        .send-btn:hover:not(.disabled) { transform: scale(1.05); box-shadow: 0 4px 20px rgba(99,102,241,0.4); }
        .send-btn.disabled { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.2); cursor: not-allowed; }
      `}</style>
    </div>
  );
}

const STARTER_PROMPTS = [
  "How are you feeling today?",
  "Tell me something interesting",
  "Help me think through a decision",
  "What do you remember about me?",
];
