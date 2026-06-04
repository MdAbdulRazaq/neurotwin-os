'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Settings, User, Bell, Lock, Eye, EyeOff, Save, RotateCcw, Trash2, Key, Mic, Volume2 } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface SettingsState {
  // Privacy
  memory_enabled: boolean;
  analytics_enabled: boolean;
  voice_enabled: boolean;

  // Voice settings
  stt_provider: 'deepgram' | 'whisper';
  tts_voice_id: string;
  tts_provider: 'elevenlabs' | 'local';

  // Display
  theme: 'dark' | 'light' | 'auto';
  avatar_style: 'anime' | 'realistic' | 'abstract';

  // API Keys (masked)
  anthropic_key: string;
  openai_key: string;
  pinecone_key: string;
  deepgram_key: string;
  elevenlabs_key: string;
}

export default function SettingsPage() {
  const router = useRouter();
  const [activeSection, setActiveSection] = useState<'privacy' | 'voice' | 'api' | 'account'>('privacy');
  const [settings, setSettings] = useState<SettingsState>({
    memory_enabled: true,
    analytics_enabled: true,
    voice_enabled: false,
    stt_provider: 'deepgram',
    tts_voice_id: 'EXAVITQu4vr4xnSDxMaL',
    tts_provider: 'elevenlabs',
    theme: 'dark',
    avatar_style: 'anime',
    anthropic_key: '',
    openai_key: '',
    pinecone_key: '',
    deepgram_key: '',
    elevenlabs_key: '',
  });
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{type: 'success' | 'error'; text: string} | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('nt_access_token');
    if (!token) {
      router.replace('/auth/login');
    }
    // Load saved settings from localStorage
    const saved = localStorage.getItem('neurotwin_settings');
    if (saved) {
      try {
        setSettings({ ...settings, ...JSON.parse(saved) });
      } catch (e) {
        console.error('Failed to parse settings:', e);
      }
    }
  }, [router]);

  const handleSave = async () => {
    setSaving(true);
    try {
      // Save to localStorage for now, would be API call
      localStorage.setItem('neurotwin_settings', JSON.stringify(settings));
      setMessage({ type: 'success', text: 'Settings saved successfully!' });
      setTimeout(() => setMessage(null), 3000);
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to save settings' });
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    if (confirm('Reset all settings to defaults?')) {
      const defaults: SettingsState = {
        memory_enabled: true,
        analytics_enabled: true,
        voice_enabled: false,
        stt_provider: 'deepgram',
        tts_voice_id: 'EXAVITQu4vr4xnSDxMaL',
        tts_provider: 'elevenlabs',
        theme: 'dark',
        avatar_style: 'anime',
        anthropic_key: '',
        openai_key: '',
        pinecone_key: '',
        deepgram_key: '',
        elevenlabs_key: '',
      };
      setSettings(defaults);
      localStorage.setItem('neurotwin_settings', JSON.stringify(defaults));
      setMessage({ type: 'success', text: 'Settings reset to defaults' });
      setTimeout(() => setMessage(null), 3000);
    }
  };

  const handleDeleteAccount = async () => {
    if (!confirm('Are you sure? This will permanently delete your account and all data. This action cannot be undone.')) {
      return;
    }
    try {
      const token = localStorage.getItem('nt_access_token');
      const response = await fetch('/api/proxy/auth/account', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        localStorage.clear();
        router.replace('/auth/login');
      } else {
        setMessage({ type: 'error', text: 'Failed to delete account' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Error deleting account' });
    }
  };

  const updateSetting = <K extends keyof SettingsState>(key: K, value: SettingsState[K]) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const toggleKeyVisibility = (key: string) => {
    setShowKeys(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const MaskedKey = ({ value, name }: { value: string; name: string }) => {
    const visible = showKeys[name];
    if (!value) return <span className="text-slate-500 text-sm">Not set</span>;
    return (
      <div className="flex items-center gap-2">
        <code className="flex-1 bg-slate-900 px-3 py-2 rounded text-sm font-mono text-slate-300">
          {visible ? value : '•'.repeat(Math.min(value.length, 20)) + (value.length > 20 ? '...' : '')}
        </code>
        <button
          type="button"
          onClick={() => toggleKeyVisibility(name)}
          className="p-2 text-slate-400 hover:text-white"
        >
          {visible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
    );
  };

  const sections = [
    { id: 'privacy', label: 'Privacy & Data', icon: Lock },
    { id: 'voice', label: 'Voice Settings', icon: Mic },
    { id: 'api', label: 'API Keys', icon: Key },
    { id: 'account', label: 'Account', icon: User },
  ] as const;

  return (
    <div className="settings-page">
      <div className="page-header">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-4"
        >
          <div className="p-3 rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 border border-emerald-500/30">
            <Settings className="w-8 h-8 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white">Settings</h1>
            <p className="text-slate-400">Manage your preferences and data</p>
          </div>
        </motion.div>
      </div>

      {/* Message Toast */}
      {message && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`p-4 rounded-lg mb-6 ${
            message.type === 'success' ? 'bg-green-500/20 border border-green-500/30 text-green-300' :
            'bg-red-500/20 border border-red-500/30 text-red-300'
          }`}
        >
          {message.text}
        </motion.div>
      )}

      <div className="grid md:grid-cols-4 gap-6">
        {/* Sidebar */}
        <div className="md:col-span-1 space-y-2">
          {sections.map(section => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                activeSection === section.id
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
              }`}
            >
              <section.icon className="w-5 h-5" />
              <span>{section.label}</span>
            </button>
          ))}
        </div>

        {/* Main Content */}
        <div className="md:col-span-3">
          {activeSection === 'privacy' && (
            <motion.div
              key="privacy"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-6"
            >
              <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Lock className="w-5 h-5 text-indigo-400" />
                  Data Privacy
                </h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-white font-medium">Memory Storage</div>
                      <div className="text-sm text-slate-400">Store conversation memories for future recall</div>
                    </div>
                    <button
                      onClick={() => updateSetting('memory_enabled', !settings.memory_enabled)}
                      className={`relative w-12 h-6 rounded-full transition-colors ${
                        settings.memory_enabled ? 'bg-indigo-600' : 'bg-slate-600'
                      }`}
                    >
                      <span
                        className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                          settings.memory_enabled ? 'translate-x-6' : 'translate-x-0'
                        }`}
                      />
                    </button>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-white font-medium">Analytics Collection</div>
                      <div className="text-sm text-slate-400">Help improve neurotwin by sharing usage patterns</div>
                    </div>
                    <button
                      onClick={() => updateSetting('analytics_enabled', !settings.analytics_enabled)}
                      className={`relative w-12 h-6 rounded-full transition-colors ${
                        settings.analytics_enabled ? 'bg-indigo-600' : 'bg-slate-600'
                      }`}
                    >
                      <span
                        className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                          settings.analytics_enabled ? 'translate-x-6' : 'translate-x-0'
                        }`}
                      />
                    </button>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-white font-medium">Voice Processing</div>
                      <div className="text-sm text-slate-400">Enable voice input and TTS output</div>
                    </div>
                    <button
                      onClick={() => updateSetting('voice_enabled', !settings.voice_enabled)}
                      className={`relative w-12 h-6 rounded-full transition-colors ${
                        settings.voice_enabled ? 'bg-indigo-600' : 'bg-slate-600'
                      }`}
                    >
                      <span
                        className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                          settings.voice_enabled ? 'translate-x-6' : 'translate-x-0'
                        }`}
                      />
                    </button>
                  </div>
                </div>
              </div>

              <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Eye className="w-5 h-5 text-emerald-400" />
                  Data Management
                </h3>
                <div className="space-y-4">
                  <button
                    onClick={async () => {
                      if (confirm('Export all your memories and data?')) {
                        try {
                          const token = localStorage.getItem('nt_access_token');
                          const response = await fetch('/api/proxy/memory/export', {
                            headers: { Authorization: `Bearer ${token}` },
                          });
                          if (response.ok) {
                            const blob = await response.blob();
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = `neurotwin-data-${new Date().toISOString().split('T')[0]}.json`;
                            a.click();
                          }
                        } catch (error) {
                          console.error('Export failed:', error);
                        }
                      }
                    }}
                    className="w-full p-4 bg-slate-900/50 border border-slate-700 rounded-lg text-left hover:border-indigo-500/30 transition-colors"
                  >
                    <div className="font-medium text-white">Export Data</div>
                    <div className="text-sm text-slate-400">Download all your memories and settings as JSON</div>
                  </button>

                  <button
                    onClick={handleDeleteAccount}
                    className="w-full p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-left hover:bg-red-500/20 transition-colors"
                  >
                    <div className="font-medium text-red-400 flex items-center gap-2">
                      <Trash2 className="w-4 h-4" />
                      Delete Account
                    </div>
                    <div className="text-sm text-red-300/70">Permanently remove all data from NEUROTWIN</div>
                  </button>
                </div>
              </div>
            </motion.div>
          )}

          {activeSection === 'voice' && (
            <motion.div
              key="voice"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-6"
            >
              <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Volume2 className="w-5 h-5 text-blue-400" />
                  Speech-to-Text
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">STT Provider</label>
                    <select
                      value={settings.stt_provider}
                      onChange={e => updateSetting('stt_provider', e.target.value as 'deepgram' | 'whisper')}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="deepgram">Deepgram Nova-2 (Recommended)</option>
                      <option value="whisper">OpenAI Whisper</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Volume2 className="w-5 h-5 text-purple-400" />
                  Text-to-Speech
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">TTS Provider</label>
                    <select
                      value={settings.tts_provider}
                      onChange={e => updateSetting('tts_provider', e.target.value as 'elevenlabs' | 'local')}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="elevenlabs">ElevenLabs (Premium)</option>
                      <option value="local">Local (Browser built-in)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">Voice ID</label>
                    <input
                      type="text"
                      value={settings.tts_voice_id}
                      onChange={e => updateSetting('tts_voice_id', e.target.value)}
                      placeholder="ElevenLabs voice ID"
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                    <p className="text-xs text-slate-500 mt-1">Default: EXAVITQu4vr4xnSDxMaL (Rachel)</p>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {activeSection === 'api' && (
            <motion.div
              key="api"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-6"
            >
              <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Key className="w-5 h-5 text-yellow-400" />
                  API Keys
                </h3>
                <p className="text-sm text-slate-400 mb-4">
                  These keys are stored locally and used for AI services. They are never sent to our servers except directly to the service providers.
                </p>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">Anthropic API Key (Claude)</label>
                    <MaskedKey value={settings.anthropic_key} name="anthropic_key" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">OpenAI API Key</label>
                    <MaskedKey value={settings.openai_key} name="openai_key" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">Pinecone API Key</label>
                    <MaskedKey value={settings.pinecone_key} name="pinecone_key" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">Deepgram API Key</label>
                    <MaskedKey value={settings.deepgram_key} name="deepgram_key" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">ElevenLabs API Key</label>
                    <MaskedKey value={settings.elevenlabs_key} name="elevenlabs_key" />
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {activeSection === 'account' && (
            <motion.div
              key="account"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-6"
            >
              <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <User className="w-5 h-5 text-green-400" />
                  Profile
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">Display Name</label>
                    <input
                      type="text"
                      placeholder="Your name"
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">Bio</label>
                    <textarea
                      rows={3}
                      placeholder="Tell your neurotwin about yourself..."
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                </div>
              </div>

              <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <RotateCcw className="w-5 h-5 text-orange-400" />
                  Reset Options
                </h3>
                <div className="space-y-3">
                  <button className="w-full p-4 bg-slate-900/50 border border-slate-700 rounded-lg text-left hover:border-orange-500/30 transition-colors">
                    <div className="font-medium text-white">Clear All Memories</div>
                    <div className="text-sm text-slate-400">Remove all stored memories from your digital twin</div>
                  </button>
                  <button className="w-full p-4 bg-slate-900/50 border border-slate-700 rounded-lg text-left hover:border-orange-500/30 transition-colors">
                    <div className="font-medium text-white">Reset Personality</div>
                    <div className="text-sm text-slate-400">Clear learned personality traits and start fresh</div>
                  </button>
                </div>
              </div>

              {/* Danger Zone */}
              <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-red-400 mb-4">Danger Zone</h3>
                <button
                  onClick={handleDeleteAccount}
                  className="w-full p-4 bg-red-500/20 rounded-lg text-left hover:bg-red-500/30 transition-colors"
                >
                  <div className="font-medium text-red-300 flex items-center gap-2">
                    <Trash2 className="w-4 h-4" />
                    Delete Account
                  </div>
                  <div className="text-sm text-red-300/70">Permanently delete your account and all associated data</div>
                </button>
              </div>
            </motion.div>
          )}
        </div>
      </div>

      {/* Save Button */}
      <div className="fixed bottom-8 right-8">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-full shadow-lg shadow-indigo-500/30 transition-all disabled:opacity-50"
        >
          {saving ? (
            <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-white"></div>
          ) : (
            <Save className="w-5 h-5" />
          )}
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
}
