import { useState, useRef, useCallback, useEffect } from 'react';
import { useAvatarStore } from '@/lib/stores/avatarStore';

const SAMPLE_RATE = 16000;
const CHUNK_INTERVAL_MS = 1000;
const EMOTION_CONFIDENCE_THRESHOLD = 0.35;

type PerceptionMessage = {
  type?: string;
  text?: string;
  confidence?: number;
  emotion?: string;
  emotion_confidence?: number;
  arousal?: number;
  valence?: number;
  is_final?: boolean;
};

function normalizeEmotion(raw: string): string {
  const mapping: Record<string, string> = {
    happy: 'joy',
    sad: 'sadness',
    angry: 'anger',
    fearful: 'fear',
    surprised: 'surprise',
    disgusted: 'disgust',
  };
  return mapping[raw.toLowerCase()] || raw.toLowerCase();
}

function mapEmotionToExpression(emotion: string): string {
  switch (emotion) {
    case 'joy':
      return 'smile';
    case 'sadness':
    case 'fear':
      return 'sad';
    case 'anger':
      return 'angry';
    case 'surprise':
      return 'surprise';
    case 'disgust':
      return 'thinking';
    default:
      return 'neutral';
  }
}

export function useVoice() {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [emotion, setEmotion] = useState<string>('neutral');
  const [emotionConfidence, setEmotionConfidence] = useState(0);
  const [arousal, setArousal] = useState(0.5);
  const [valence, setValence] = useState(0.5);
  const [transcriptConfidence, setTranscriptConfidence] = useState(0);
  const [emotionCapturedAt, setEmotionCapturedAt] = useState<number | null>(null);
  const [volume, setVolume] = useState(0);
  const [permissionGranted, setPermissionGranted] = useState<boolean | null>(null);

  const streamRef = useRef<MediaStream | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const volumeTimerRef = useRef<number | null>(null);
  const finalTranscriptRef = useRef('');

  const setAvatarEmotion = useAvatarStore(state => state.setEmotion);
  const setAvatarExpression = useAvatarStore(state => state.setExpression);

  // Volume meter
  const startVolumeMeter = useCallback(() => {
    if (!analyserRef.current) return;
    const data = new Uint8Array(analyserRef.current.frequencyBinCount);
    const tick = () => {
      analyserRef.current?.getByteFrequencyData(data);
      const avg = data.reduce((a, b) => a + b, 0) / data.length;
      setVolume(Math.min(1, avg / 128));
      volumeTimerRef.current = requestAnimationFrame(tick);
    };
    volumeTimerRef.current = requestAnimationFrame(tick);
  }, []);

  const stopVolumeMeter = useCallback(() => {
    if (volumeTimerRef.current) {
      cancelAnimationFrame(volumeTimerRef.current);
      volumeTimerRef.current = null;
    }
    setVolume(0);
  }, []);

  const applyEmotionSnapshot = useCallback((msg: PerceptionMessage) => {
    if (!msg.emotion) {
      return;
    }

    const normalizedEmotion = normalizeEmotion(msg.emotion);
    const confidence = Math.max(0, Math.min(1, msg.emotion_confidence ?? 0));
    const nextArousal = Math.max(0, Math.min(1, msg.arousal ?? 0.5));
    const nextValence = Math.max(0, Math.min(1, msg.valence ?? 0.5));
    const stableEmotion = confidence >= EMOTION_CONFIDENCE_THRESHOLD ? normalizedEmotion : 'neutral';

    setEmotion(stableEmotion);
    setEmotionConfidence(confidence);
    setArousal(nextArousal);
    setValence(nextValence);
    setEmotionCapturedAt(Date.now());

    if (stableEmotion !== 'neutral') {
      setAvatarEmotion(stableEmotion);
      setAvatarExpression(mapEmotionToExpression(stableEmotion), Math.max(0.35, confidence));
    }
  }, [setAvatarEmotion, setAvatarExpression]);

  const applyTranscriptSnapshot = useCallback((msg: PerceptionMessage) => {
    const incomingText = (msg.text || '').trim();
    if (!incomingText) {
      return;
    }

    if (typeof msg.confidence === 'number') {
      setTranscriptConfidence(msg.confidence);
    }

    if (msg.is_final) {
      finalTranscriptRef.current = [finalTranscriptRef.current, incomingText].filter(Boolean).join(' ').trim();
      setTranscript(finalTranscriptRef.current);
      return;
    }

    setTranscript([finalTranscriptRef.current, incomingText].filter(Boolean).join(' ').trim());
  }, []);

  const startListening = useCallback(async () => {
    try {
      finalTranscriptRef.current = '';
      setTranscript('');
      setTranscriptConfidence(0);
      setEmotion('neutral');
      setEmotionConfidence(0);
      setArousal(0.5);
      setValence(0.5);
      setEmotionCapturedAt(null);

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: SAMPLE_RATE,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      setPermissionGranted(true);
      streamRef.current = stream;

      // Audio context + analyser
      const ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
      audioCtxRef.current = ctx;
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyserRef.current = analyser;
      source.connect(analyser);
      startVolumeMeter();

      // WebSocket streaming to perception service
      const wsUrl = (process.env.NEXT_PUBLIC_PERCEPTION_WS_URL || 'ws://localhost:8001')
        + `/ws/stream/${Date.now()}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[VoiceHook] WS connected to perception');
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as PerceptionMessage;

          if (msg.type === 'transcript') {
            applyTranscriptSnapshot(msg);
            applyEmotionSnapshot(msg);
          } else if (msg.type === 'emotion') {
            applyEmotionSnapshot(msg);
          }
        } catch (e) {
          console.warn('[VoiceHook] Invalid WS payload:', e);
        }
      };

      ws.onerror = (e) => console.error('[VoiceHook] WS error:', e);
      ws.onclose = () => console.log('[VoiceHook] WS closed');

      // ScriptProcessor to capture raw PCM chunks
      const processor = ctx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;
      source.connect(processor);
      processor.connect(ctx.destination);

      let buffer: Float32Array[] = [];
      let lastSent = Date.now();

      processor.onaudioprocess = (e) => {
        const data = e.inputBuffer.getChannelData(0);
        buffer.push(new Float32Array(data));

        const now = Date.now();
        if (now - lastSent >= CHUNK_INTERVAL_MS && ws.readyState === WebSocket.OPEN) {
          // Concatenate + convert to 16-bit PCM
          const totalLength = buffer.reduce((s, b) => s + b.length, 0);
          const merged = new Float32Array(totalLength);
          let offset = 0;
          for (const b of buffer) {
            merged.set(b, offset);
            offset += b.length;
          }
          buffer = [];
          lastSent = now;

          const pcm = float32ToInt16(merged);
          ws.send(pcm.buffer);
        }
      };

      setIsListening(true);
    } catch (err: any) {
      if (err.name === 'NotAllowedError') {
        setPermissionGranted(false);
      }
      console.error('[VoiceHook] startListening error:', err);
    }
  }, [applyEmotionSnapshot, applyTranscriptSnapshot, startVolumeMeter]);

  const stopListening = useCallback(() => {
    // Stop stream tracks
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;

    // Disconnect audio graph
    processorRef.current?.disconnect();
    processorRef.current = null;

    audioCtxRef.current?.close();
    audioCtxRef.current = null;
    analyserRef.current = null;

    // Close WS
    wsRef.current?.close();
    wsRef.current = null;

    stopVolumeMeter();
    setIsListening(false);
  }, [stopVolumeMeter]);

  const toggleListening = useCallback(() => {
    if (isListening) stopListening();
    else startListening();
  }, [isListening, startListening, stopListening]);

  const clearTranscript = useCallback(() => {
    finalTranscriptRef.current = '';
    setTranscript('');
    setTranscriptConfidence(0);
  }, []);

  useEffect(() => {
    return () => {
      stopListening();
    };
  }, [stopListening]);

  return {
    isListening,
    transcript,
    transcriptConfidence,
    emotion,
    emotionConfidence,
    arousal,
    valence,
    emotionCapturedAt,
    volume,
    permissionGranted,
    toggleListening,
    clearTranscript,
  };
}

function float32ToInt16(input: Float32Array): Int16Array {
  const output = new Int16Array(input.length);
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]));
    output[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return output;
}
