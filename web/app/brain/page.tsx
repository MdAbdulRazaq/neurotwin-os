'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Brain, HardDrive, TrendingUp, Edit2, Save, Trash2, Plus, X } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ScatterChart, Scatter } from 'recharts';
import { useRouter } from 'next/navigation';
import { memoryApi } from '@/lib/api';

// Types
interface Memory {
  id: string;
  content: string;
  memory_type: string;
  importance_score: number;
  created_at: string;
  metadata: Record<string, any>;
}

interface TwinProfile {
  personality_traits: string[];
  communication_style: string;
  interested_topics: string[];
  emotional_patterns: {
    dominant_emotion: string;
    emotion_distribution: Record<string, number>;
  };
  facts: Array<{key: string; value: string; source: string}>;
}

export default function BrainPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'memories' | 'profile' | 'topics'>('memories');
  const [memories, setMemories] = useState<Memory[]>([]);
  const [profile, setProfile] = useState<TwinProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [editingProfile, setEditingProfile] = useState(false);
  const [editedTraits, setEditedTraits] = useState<string[]>([]);
  const [newTrait, setNewTrait] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // Auth guard
  useEffect(() => {
    const token = localStorage.getItem('nt_access_token');
    if (!token) {
      router.replace('/auth/login');
    }
  }, [router]);

  // Load data
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const [memoriesData, profileData] = await Promise.all([
          memoryApi.list(),
          fetchProfile(),
        ]);
        setMemories(memoriesData);
        setProfile(profileData);
      } catch (error) {
        console.error('Failed to load brain data:', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const fetchProfile = async (): Promise<TwinProfile> => {
    // This would call an API endpoint to get twin profile from Neo4j
    // For now, return mock data derived from memories
    const traits = [...new Set(memories.map(m => m.memory_type).filter(Boolean))];
    return {
      personality_traits: traits.slice(0, 5),
      communication_style: 'supportive and warm',
      interested_topics: extractTopics(memories),
      emotional_patterns: {
        dominant_emotion: 'neutral',
        emotion_distribution: {},
      },
      facts: memories.slice(0, 10).map(m => ({
        key: m.memory_type || 'general',
        value: m.content.substring(0, 100),
        source: 'conversation',
      })),
    };
  };

  const extractTopics = (mems: Memory[]): string[] => {
    // Simple topic extraction from memory content
    const words = mems.flatMap(m => m.content.toLowerCase().split(/\s+/));
    const stopWords = new Set(['the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'this', 'that', 'these', 'those']);
    const filtered = words.filter(w => w.length > 3 && !stopWords.has(w));
    const counts: Record<string, number> = {};
    filtered.forEach(w => counts[w] = (counts[w] || 0) + 1);
    return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 15).map(([word]) => word);
  };

  const handleDeleteMemory = async (memoryId: string) => {
    if (!confirm('Delete this memory?')) return;
    try {
      await memoryApi.delete([memoryId]);
      setMemories(memories.filter(m => m.id !== memoryId));
    } catch (error) {
      console.error('Failed to delete memory:', error);
    }
  };

  const handleAddTrait = () => {
    if (newTrait.trim() && !editedTraits.includes(newTrait.trim())) {
      setEditedTraits([...editedTraits, newTrait.trim()]);
      setNewTrait('');
    }
  };

  const handleRemoveTrait = (trait: string) => {
    setEditedTraits(editedTraits.filter(t => t !== trait));
  };

  const handleSaveProfile = async () => {
    // Save profile changes
    if (profile) {
      const updated = { ...profile, personality_traits: editedTraits };
      setProfile(updated);
      setEditingProfile(false);
      // TODO: API call to save to Neo4j
    }
  };

  const filteredMemories = memories.filter(m =>
    m.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.memory_type?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const memoryTypeColors: Record<string, string> = {
    personal: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
    preference: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    history: 'bg-green-500/20 text-green-300 border-green-500/30',
    fact: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  return (
    <div className="brain-page">
      <div className="page-header">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-4"
        >
          <div className="p-3 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30">
            <Brain className="w-8 h-8 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white">Your Digital Twin</h1>
            <p className="text-slate-400">Memory & personality profile</p>
          </div>
        </motion.div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-8 border-b border-slate-700/50">
        {(['memories', 'profile', 'topics'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-6 py-3 capitalize transition-all ${
              activeTab === tab
                ? 'text-white border-b-2 border-indigo-500 bg-indigo-500/10'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'memories' && (
        <motion.div
          key="memories"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="space-y-6"
        >
          {/* Search */}
          <div className="relative">
            <input
              type="text"
              placeholder="Search memories..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full bg-slate-800/50 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Memory list */}
          <div className="space-y-3">
            {filteredMemories.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
                <HardDrive className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No memories stored yet. Start chatting to build your twin profile!</p>
              </div>
            ) : (
              filteredMemories.map((memory, idx) => (
                <motion.div
                  key={memory.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 hover:border-indigo-500/30 transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <p className="text-slate-200 mb-2">{memory.content}</p>
                      <div className="flex items-center gap-3 text-sm text-slate-400">
                        <span className={`px-2 py-0.5 rounded text-xs border ${memoryTypeColors[memory.memory_type] || 'bg-slate-700'}`}>
                          {memory.memory_type || 'general'}
                        </span>
                        <span>{new Date(memory.created_at).toLocaleDateString()}</span>
                        <span>importance: {(memory.importance_score * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteMemory(memory.id)}
                      className="p-2 text-slate-400 hover:text-red-400 transition-colors"
                      title="Delete memory"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </motion.div>
              ))
            )}
          </div>
        </motion.div>
      )}

      {activeTab === 'profile' && (
        <motion.div
          key="profile"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="space-y-8"
        >
          <div className="grid md:grid-cols-2 gap-8">
            {/* Personality Traits */}
            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-indigo-400" />
                  Personality Traits
                </h3>
                {!editingProfile ? (
                  <button
                    onClick={() => setEditingProfile(true)}
                    className="text-sm text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                  >
                    <Edit2 className="w-4 h-4" /> Edit
                  </button>
                ) : (
                  <div className="flex gap-2">
                    <button onClick={handleSaveProfile} className="text-sm text-green-400 flex items-center gap-1">
                      <Save className="w-4 h-4" /> Save
                    </button>
                    <button onClick={() => { setEditingProfile(false); setEditedTraits(profile?.personality_traits || []); }} className="text-sm text-slate-400">
                      Cancel
                    </button>
                  </div>
                )}
              </div>

              {editingProfile ? (
                <div className="space-y-3">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Add trait..."
                      value={newTrait}
                      onChange={e => setNewTrait(e.target.value)}
                      onKeyPress={e => e.key === 'Enter' && handleAddTrait()}
                      className="flex-1 bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
                    />
                    <button onClick={handleAddTrait} className="px-3 py-2 bg-indigo-600 rounded-lg text-white">
                      <Plus className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {editedTraits.map(trait => (
                      <span
                        key={trait}
                        className="px-3 py-1 bg-indigo-500/20 text-indigo-300 rounded-full text-sm flex items-center gap-1"
                      >
                        {trait}
                        <button onClick={() => handleRemoveTrait(trait)} className="hover:text-red-300">
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {profile?.personality_traits.map(trait => (
                    <span key={trait} className="px-3 py-1 bg-indigo-500/20 text-indigo-300 rounded-full text-sm">
                      {trait}
                    </span>
                  )) || <span className="text-slate-400">No traits defined yet</span>}
                </div>
              )}
            </div>

            {/* Communication Style */}
            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                <Brain className="w-5 h-5 text-purple-400" />
                Communication Style
              </h3>
              <p className="text-slate-300 leading-relaxed">
                {profile?.communication_style || 'Your communication style will be learned from your conversations over time.'}
              </p>
              <div className="mt-4 pt-4 border-t border-slate-700">
                <h4 className="text-sm font-medium text-slate-400 mb-2">Interested Topics</h4>
                <div className="flex flex-wrap gap-2">
                  {profile?.interested_topics.slice(0, 8).map(topic => (
                    <span key={topic} className="px-2 py-1 bg-slate-700/50 text-slate-300 rounded text-xs">
                      {topic}
                    </span>
                  )) || <span className="text-sm text-slate-500">Topics will appear here as you chat</span>}
                </div>
              </div>
            </div>
          </div>

          {/* Emotion Patterns Chart */}
          {profile?.emotional_patterns.emotion_distribution && (
            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Emotional Patterns</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis type="category" dataKey="emotion" stroke="#94a3b8" />
                    <YAxis type="number" stroke="#94a3b8" name="Frequency" />
                    <Tooltip
                      contentStyle={{ background: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                      labelStyle={{ color: '#e2e8f0' }}
                    />
                    <Scatter
                      data={Object.entries(profile.emotional_patterns.emotion_distribution).map(([emotion, value]) => ({
                        emotion,
                        value,
                        size: value * 100,
                      }))}
                      fill="#8b5cf6"
                    />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </motion.div>
      )}

      {activeTab === 'topics' && (
        <motion.div
          key="topics"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="space-y-6"
        >
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Topic Cloud</h3>
            <div className="flex flex-wrap gap-3">
              {profile?.interested_topics.map((topic, idx) => {
                const size = Math.max(12, Math.min(24, 12 + (15 - idx) * 1.5));
                return (
                  <span
                    key={topic}
                    className="px-4 py-2 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 rounded-full text-white"
                    style={{ fontSize: `${size}px` }}
                  >
                    {topic}
                  </span>
                );
              })}
            </div>
          </div>

          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Memory by Type</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {['personal', 'preference', 'history', 'fact'].map(type => {
                const count = memories.filter(m => m.memory_type === type).length;
                return (
                  <div key={type} className="bg-slate-900/50 rounded-lg p-4 text-center">
                    <div className="text-3xl font-bold text-indigo-400">{count}</div>
                    <div className="text-sm text-slate-400 capitalize">{type}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}
