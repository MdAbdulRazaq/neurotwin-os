'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { Sparkles, Eye, EyeOff, ArrowRight, Loader2 } from 'lucide-react';
import { authApi } from '@/lib/api';
import { cn } from '@/lib/utils';

export default function LoginPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      if (mode === 'login') {
        await authApi.login(email, password);
      } else {
        await authApi.register(name, email, password);
      }
      router.push('/chat');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-root">
      <div className="auth-bg">
        <div className="orb orb-1" />
        <div className="orb orb-2" />
        <div className="orb orb-3" />
        <div className="grid-overlay" />
      </div>

      <motion.div
        className="auth-card"
        initial={{ opacity: 0, y: 32, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      >
        {/* Logo */}
        <div className="auth-logo">
          <div className="logo-icon">
            <Sparkles size={22} />
          </div>
          <span className="logo-text">NEUROTWIN</span>
        </div>

        <h1 className="auth-title">
          {mode === 'login' ? 'Welcome back' : 'Create your twin'}
        </h1>
        <p className="auth-sub">
          {mode === 'login'
            ? 'Your digital companion is waiting'
            : 'Begin your journey with an AI that truly knows you'}
        </p>

        <form onSubmit={handleSubmit} className="auth-form">
          {mode === 'register' && (
            <div className="field">
              <label>Name</label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="Your name"
                required
                autoComplete="name"
              />
            </div>
          )}

          <div className="field">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoComplete="email"
            />
          </div>

          <div className="field">
            <label>Password</label>
            <div className="pw-wrapper">
              <input
                type={showPw ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                minLength={8}
              />
              <button type="button" className="pw-toggle" onClick={() => setShowPw(v => !v)}>
                {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {error && (
            <motion.div
              className="error-msg"
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
            >
              {error}
            </motion.div>
          )}

          <button type="submit" className="submit-btn" disabled={loading}>
            {loading
              ? <Loader2 size={18} className="spinning" />
              : <>{mode === 'login' ? 'Sign in' : 'Get started'} <ArrowRight size={16} /></>
            }
          </button>
        </form>

        <div className="auth-switch">
          {mode === 'login' ? (
            <>Don&apos;t have an account? <button onClick={() => setMode('register')}>Create one</button></>
          ) : (
            <>Already have an account? <button onClick={() => setMode('login')}>Sign in</button></>
          )}
        </div>
      </motion.div>

      <style jsx>{`
        .auth-root {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #060910;
          font-family: 'Sora', 'DM Sans', sans-serif;
          position: relative;
          overflow: hidden;
        }

        .auth-bg { position: fixed; inset: 0; pointer-events: none; z-index: 0; }

        .orb {
          position: absolute;
          border-radius: 50%;
          filter: blur(80px);
          opacity: 0.35;
        }
        .orb-1 { width: 500px; height: 500px; background: radial-gradient(circle, #6366f1, transparent); top: -100px; left: -100px; }
        .orb-2 { width: 400px; height: 400px; background: radial-gradient(circle, #8b5cf6, transparent); bottom: -80px; right: -80px; }
        .orb-3 { width: 300px; height: 300px; background: radial-gradient(circle, #14b8a6, transparent); top: 50%; left: 50%; transform: translate(-50%,-50%); opacity: 0.12; }

        .grid-overlay {
          position: absolute;
          inset: 0;
          background-image:
            linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
          background-size: 48px 48px;
        }

        .auth-card {
          width: 420px;
          background: rgba(12, 16, 28, 0.85);
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 24px;
          padding: 40px;
          backdrop-filter: blur(24px);
          box-shadow: 0 32px 80px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.04);
          position: relative;
          z-index: 1;
        }

        .auth-logo {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 28px;
        }

        .logo-icon {
          width: 40px;
          height: 40px;
          border-radius: 12px;
          background: linear-gradient(135deg, #6366f1, #8b5cf6);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
        }

        .logo-text {
          font-size: 15px;
          font-weight: 800;
          letter-spacing: 0.1em;
          color: rgba(255,255,255,0.9);
        }

        .auth-title {
          font-size: 26px;
          font-weight: 800;
          color: white;
          letter-spacing: -0.03em;
          margin: 0 0 8px;
        }

        .auth-sub {
          font-size: 14px;
          color: rgba(255,255,255,0.35);
          margin: 0 0 28px;
          line-height: 1.6;
        }

        .auth-form { display: flex; flex-direction: column; gap: 16px; }

        .field { display: flex; flex-direction: column; gap: 7px; }

        .field label {
          font-size: 12px;
          font-weight: 700;
          color: rgba(255,255,255,0.45);
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }

        .field input {
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 12px;
          padding: 12px 16px;
          color: rgba(255,255,255,0.9);
          font-size: 15px;
          font-family: inherit;
          outline: none;
          transition: all 0.2s;
          width: 100%;
          box-sizing: border-box;
        }

        .field input:focus {
          border-color: rgba(99,102,241,0.5);
          background: rgba(99,102,241,0.07);
          box-shadow: 0 0 0 3px rgba(99,102,241,0.12);
        }

        .field input::placeholder { color: rgba(255,255,255,0.2); }

        .pw-wrapper { position: relative; }
        .pw-wrapper input { padding-right: 44px; }
        .pw-toggle {
          position: absolute;
          right: 14px;
          top: 50%;
          transform: translateY(-50%);
          background: none;
          border: none;
          color: rgba(255,255,255,0.3);
          cursor: pointer;
          padding: 0;
          display: flex;
          align-items: center;
        }
        .pw-toggle:hover { color: rgba(255,255,255,0.7); }

        .error-msg {
          background: rgba(239,68,68,0.12);
          border: 1px solid rgba(239,68,68,0.25);
          border-radius: 10px;
          padding: 10px 14px;
          font-size: 13px;
          color: rgba(248,113,113,0.9);
        }

        .submit-btn {
          background: linear-gradient(135deg, #6366f1, #8b5cf6);
          border: none;
          border-radius: 12px;
          padding: 14px;
          color: white;
          font-size: 15px;
          font-weight: 700;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          margin-top: 4px;
          transition: all 0.2s;
          font-family: inherit;
        }

        .submit-btn:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 8px 30px rgba(99,102,241,0.4);
        }

        .submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }

        .spinning { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }

        .auth-switch {
          text-align: center;
          margin-top: 20px;
          font-size: 13px;
          color: rgba(255,255,255,0.3);
        }

        .auth-switch button {
          background: none;
          border: none;
          color: rgba(99,102,241,0.9);
          cursor: pointer;
          font-weight: 700;
          font-family: inherit;
          font-size: inherit;
          padding: 0;
          margin-left: 4px;
        }

        .auth-switch button:hover { text-decoration: underline; }
      `}</style>
    </div>
  );
}
