'use client';

import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Mic, MicOff, Send, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface VoiceControlProps {
  isListening: boolean;
  transcript: string;
  onToggle: () => void;
  onSend: () => void;
  onClose: () => void;
}

export function VoiceControl({ isListening, transcript, onToggle, onSend, onClose }: VoiceControlProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>();

  // Animated waveform
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;
    let t = 0;

    const draw = () => {
      const { width, height } = canvas;
      ctx.clearRect(0, 0, width, height);

      const bars = 48;
      const barW = width / bars;
      const center = height / 2;

      for (let i = 0; i < bars; i++) {
        const phase = (i / bars) * Math.PI * 4 + t;
        const amplitude = isListening
          ? (Math.sin(phase) * 0.5 + 0.5) * (Math.sin(t * 2 + i * 0.3) * 0.3 + 0.7)
          : 0.08;
        const h = amplitude * center * 0.8;
        const alpha = isListening ? 0.7 + amplitude * 0.3 : 0.2;
        ctx.fillStyle = `rgba(139,92,246,${alpha})`;
        ctx.beginPath();
        ctx.roundRect(i * barW + 1, center - h, barW - 2, h * 2, 2);
        ctx.fill();
      }
      t += 0.06;
      animRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => { if (animRef.current) cancelAnimationFrame(animRef.current); };
  }, [isListening]);

  return (
    <motion.div
      className="voice-panel"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
    >
      <button className="close-btn" onClick={onClose}><X size={18} /></button>

      <div className="voice-title">
        {isListening ? 'Listening…' : 'Tap to speak'}
      </div>

      <canvas ref={canvasRef} width={360} height={80} className="waveform" />

      {transcript && (
        <motion.div
          className="transcript-box"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {transcript}
        </motion.div>
      )}

      <div className="voice-btns">
        <motion.button
          className={cn('mic-btn', isListening && 'active')}
          onClick={onToggle}
          whileTap={{ scale: 0.92 }}
          animate={isListening ? { boxShadow: ['0 0 0 0 rgba(139,92,246,0.4)', '0 0 0 20px rgba(139,92,246,0)', '0 0 0 0 rgba(139,92,246,0)'] } : {}}
          transition={{ duration: 1.5, repeat: Infinity }}
        >
          {isListening ? <MicOff size={28} /> : <Mic size={28} />}
        </motion.button>

        {transcript && (
          <motion.button
            className="send-voice-btn"
            onClick={onSend}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            whileTap={{ scale: 0.92 }}
          >
            <Send size={20} />
          </motion.button>
        )}
      </div>

      <style jsx>{`
        .voice-panel {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 24px;
          padding: 48px 40px;
          position: relative;
          width: 440px;
          max-width: 90vw;
        }

        .close-btn {
          position: absolute;
          top: 16px;
          right: 16px;
          background: rgba(255,255,255,0.08);
          border: none;
          border-radius: 8px;
          width: 36px;
          height: 36px;
          color: rgba(255,255,255,0.5);
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s;
        }

        .close-btn:hover { background: rgba(255,255,255,0.15); color: white; }

        .voice-title {
          font-size: 20px;
          font-weight: 700;
          color: rgba(255,255,255,0.85);
          letter-spacing: -0.02em;
        }

        .waveform {
          width: 360px;
          height: 80px;
          max-width: 100%;
        }

        .transcript-box {
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 14px;
          padding: 14px 18px;
          font-size: 15px;
          color: rgba(255,255,255,0.8);
          line-height: 1.6;
          width: 100%;
          text-align: center;
          min-height: 52px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .voice-btns {
          display: flex;
          gap: 16px;
          align-items: center;
        }

        .mic-btn {
          width: 72px;
          height: 72px;
          border-radius: 50%;
          border: none;
          background: rgba(139,92,246,0.15);
          border: 2px solid rgba(139,92,246,0.4);
          color: rgba(139,92,246,0.9);
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s;
        }

        .mic-btn.active {
          background: rgba(139,92,246,0.3);
          border-color: rgba(139,92,246,0.8);
          color: rgba(167,139,250,1);
        }

        .send-voice-btn {
          width: 52px;
          height: 52px;
          border-radius: 50%;
          border: none;
          background: linear-gradient(135deg, #6366f1, #8b5cf6);
          color: white;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s;
        }

        .send-voice-btn:hover { transform: scale(1.05); box-shadow: 0 6px 24px rgba(99,102,241,0.4); }
      `}</style>
    </motion.div>
  );
}
