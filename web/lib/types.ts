export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  emotion?: string;
  avatarCommand?: AvatarCommand;
  ttsUrl?: string;
  createdAt: string;
  latencyMs?: number;
}

export interface AvatarCommand {
  type: 'expression' | 'speak' | 'gesture';
  expression?: string;
  intensity?: number;
  duration_ms?: number;
  blend?: boolean;
}

export interface Session {
  session_id: string;
  user_id: string;
  created_at: string;
  persona: string;
}

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  locale: string;
  preferences: UserPreferences;
  created_at: string;
  avatar_url?: string;
}

export interface UserPreferences {
  language: string;
  persona_tone: string;
  memory_enabled: boolean;
  voice_enabled: boolean;
  emotion_detection: boolean;
  avatar_style: string;
  flirt_level: number;
}

export interface MoodDataPoint {
  timestamp: string;
  emotion: string;
  intensity: number;
  session_id: string | null;
}

export interface AnalyticsSummary {
  user_id: string;
  period_days: number;
  total_sessions: number;
  total_messages: number;
  avg_session_length_minutes: number;
  top_topics: TopicFrequency[];
  mood_timeline: MoodDataPoint[];
  engagement_score: number;
}

export interface TopicFrequency {
  topic: string;
  count: number;
  last_mentioned: string;
}

export interface MemoryEntry {
  id: string;
  type: string;
  summary: string;
  timestamp: string;
  importance: number;
  emotion?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LipSyncFrame {
  viseme_id: number;
  start_ms: number;
  end_ms: number;
  weight: number;
}
