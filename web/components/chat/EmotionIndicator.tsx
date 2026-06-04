'use client';

import { motion, AnimatePresence } from 'framer-motion';

const EMOTION_CONFIG: Record<string, { emoji: string; label: string; color: string }> = {
  joy:      { emoji: '✨', label: 'Joyful',    color: '#a78bfa' },
  sadness:  { emoji: '💧', label: 'Sad',       color: '#60a5fa' },
  anger:    { emoji: '🔥', label: 'Tense',     color: '#f87171' },
  neutral:  { emoji: '○',  label: 'Neutral',   color: '#6b7280' },
  surprise: { emoji: '⚡', label: 'Surprised', color: '#fbbf24' },
  fear:     { emoji: '🌊', label: 'Anxious',   color: '#34d399' },
  disgust:  { emoji: '△',  label: 'Aversive',  color: '#fb923c' },
};

export function EmotionIndicator({ emotion }: { emotion: string }) {
  const config = EMOTION_CONFIG[emotion] || EMOTION_CONFIG.neutral;

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={emotion}
        className="emotion-indicator"
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.8 }}
        transition={{ duration: 0.25 }}
        style={{ borderColor: `${config.color}40`, background: `${config.color}15` }}
      >
        <span className="emotion-emoji">{config.emoji}</span>
        <span className="emotion-label" style={{ color: config.color }}>{config.label}</span>

        <style jsx>{`
          .emotion-indicator {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 100px;
            border: 1px solid;
            backdrop-filter: blur(8px);
          }

          .emotion-emoji { font-size: 12px; }

          .emotion-label {
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
          }
        `}</style>
      </motion.div>
    </AnimatePresence>
  );
}
