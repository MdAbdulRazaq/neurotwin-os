'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to dashboard or login
    router.push('/dashboard');
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-900 to-slate-800">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-white mb-4">NEUROTWIN OS</h1>
        <p className="text-xl text-slate-300 mb-8">AI Companion Platform</p>
        <div className="animate-pulse text-slate-400">Loading...</div>
      </div>
    </div>
  );
}
