'use client';

import { motion } from 'framer-motion';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import type { Message } from '@/lib/types';

const EMOTION_COLORS: Record<string, string> = {
  joy:      'rgba(167, 139, 250, 0.15)',
  sadness:  'rgba(96, 165, 250, 0.12)',
  anger:    'rgba(248, 113, 113, 0.12)',
  neutral:  'transparent',
  surprise: 'rgba(251, 191, 36, 0.12)',
  fear:     'rgba(52, 211, 153, 0.08)',
};

const EMOTION_BORDER: Record<string, string> = {
  joy:      'rgba(167, 139, 250, 0.3)',
  sadness:  'rgba(96, 165, 250, 0.25)',
  anger:    'rgba(248, 113, 113, 0.25)',
  neutral:  'rgba(255,255,255,0.06)',
  surprise: 'rgba(251, 191, 36, 0.25)',
  fear:     'rgba(52, 211, 153, 0.2)',
};

interface MessageBubbleProps {
  message: Message;
  isLatest: boolean;
}

export function MessageBubble({ message, isLatest }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const emotion = message.emotion || 'neutral';
  const bgColor = isUser ? 'transparent' : EMOTION_COLORS[emotion];
  const borderColor = isUser ? 'rgba(99,102,241,0.25)' : EMOTION_BORDER[emotion];

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
      className={cn('msg-row', isUser ? 'user' : 'assistant')}
    >
      {!isUser && (
        <div className="avatar-dot">
          <span>N</span>
        </div>
      )}

      <div
        className={cn('bubble', isUser ? 'bubble-user' : 'bubble-assistant')}
        style={{
          background: isUser
            ? 'linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.15))'
            : bgColor,
          borderColor,
        }}
      >
        <div className="bubble-content">
          {message.content}
        </div>

        <div className="bubble-meta">
          {emotion !== 'neutral' && !isUser && (
            <span className="emotion-tag">
              {EMOTION_EMOJI[emotion]} {emotion}
            </span>
          )}
          <span className="timestamp">
            {formatDistanceToNow(new Date(message.createdAt), { addSuffix: true })}
          </span>
        </div>
      </div>

      {isUser && (
        <div className="user-dot">
          <span>You</span>
        </div>
      )}

      <style jsx>{`
        .msg-row {
          display: flex;
          gap: 12px;
          align-items: flex-end;
          max-width: 78%;
          padding: 3px 0;
        }

        .msg-row.user {
          align-self: flex-end;
          flex-direction: row-reverse;
        }

        .msg-row.assistant {
          align-self: flex-start;
        }

        .avatar-dot {
          width: 32px;
          height: 32px;
          border-radius: 10px;
          background: linear-gradient(135deg, #6366f1, #8b5cf6);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          font-weight: 700;
          color: white;
          flex-shrink: 0;
          margin-bottom: 4px;
        }

        .user-dot {
          width: 32px;
          height: 32px;
          border-radius: 10px;
          background: rgba(255,255,255,0.08);
          border: 1px solid rgba(255,255,255,0.1);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 9px;
          font-weight: 600;
          color: rgba(255,255,255,0.4);
          flex-shrink: 0;
          margin-bottom: 4px;
          letter-spacing: 0.05em;
        }

        .bubble {
          padding: 12px 16px;
          border-radius: 16px;
          border: 1px solid;
          backdrop-filter: blur(8px);
          max-width: 100%;
          transition: all 0.2s;
        }

        .bubble-user {
          border-radius: 16px 16px 4px 16px;
        }

        .bubble-assistant {
          border-radius: 16px 16px 16px 4px;
        }

        .bubble-content {
          font-size: 15px;
          color: rgba(255,255,255,0.88);
          line-height: 1.65;
          white-space: pre-wrap;
          word-break: break-word;
          font-family: 'Sora', 'DM Sans', sans-serif;
        }

        .bubble-meta {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 6px;
          flex-wrap: wrap;
        }

        .emotion-tag {
          font-size: 10px;
          font-weight: 600;
          color: rgba(255,255,255,0.35);
          text-transform: capitalize;
          letter-spacing: 0.05em;
          background: rgba(255,255,255,0.05);
          border-radius: 100px;
          padding: 2px 8px;
        }

        .timestamp {
          font-size: 11px;
          color: rgba(255,255,255,0.2);
          margin-left: auto;
        }
      `}</style>
    </motion.div>
  );
}

const EMOTION_EMOJI: Record<string, string> = {
  joy: '😊',
  sadness: '😢',
  anger: '😤',
  surprise: '😲',
  fear: '😰',
  neutral: '',
};
