'use client';

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { Canvas, useFrame, useThree, extend } from '@react-three/fiber';
import { Environment, Float, OrbitControls, useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import { useSpring, animated, config } from '@react-spring/three';
import { useAvatarStore } from '@/lib/stores/avatarStore';

// ============================================================================
// TYPES
// ============================================================================

interface VisualState {
  color_palette: {
    primary: string;
    secondary: string;
    highlight: string;
    shadow: string;
  };
  eye_features: {
    brightness: number;
    size_multiplier: number;
    sharpness: number;
    pupil_dilation: number;
    highlight_intensity: number;
  };
  mouth_features: {
    curvature: number;
    openness: number;
    width: number;
    tension: number;
  };
  skin_tone: {
    base_hue: string;
    saturation: number;
    warmth: number;
  };
  special_effects: string[];
  metadata: Record<string, number>;
}

interface AvatarStateData {
  state: string;
  emotion: string;
  emotion_intensity: number;
  is_speaking: boolean;
  is_listening: boolean;
  blendshapes: Record<string, number>;
  state_duration: number;
  timestamp: string;
}

interface BehaviorMessage {
  state: string;
  emotion: string;
  intensity: number;
  blendshapes: Record<string, number>;
}

// ============================================================================
// VISUAL IDENTITY HOOK
// ============================================================================

function useVisualIdentity(emotion: string, intensity: number) {
  const [visualState, setVisualState] = useState<VisualState | null>(null);
  const cacheRef = useRef<Map<string, VisualState>>(new Map());

  useEffect(() => {
    const cacheKey = `${emotion}_${Math.round(intensity * 10) / 10}`;
    if (cacheRef.current.has(cacheKey)) {
      setVisualState(cacheRef.current.get(cacheKey)!);
      return;
    }

    // Fetch from Visual Identity service
    const fetchVisualIdentity = async () => {
      try {
        const response = await fetch('/api/proxy/visual-identity/v1/style/emotion', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            emotion,
            intensity,
            confidence: 0.8
          })
        });
        if (response.ok) {
          const data = await response.json();
          const vs = data.visual_state;
          cacheRef.current.set(cacheKey, vs);
          setVisualState(vs);
        }
      } catch (error) {
        console.warn('Visual Identity fetch failed:', error);
        // Fallback to local mapping
        setVisualState(getFallbackVisualState(emotion, intensity));
      }
    };

    fetchVisualIdentity();
  }, [emotion, intensity]);

  return visualState;
}

function getFallbackVisualState(emotion: string, intensity: number): VisualState {
  const emotionColors: Record<string, { primary: string; secondary: string; highlight: string; shadow: string }> = {
    joy: { primary: '#FFE4B5', secondary: '#FFB347', highlight: '#FFD700', shadow: '#DEB887' },
    sadness: { primary: '#B0C4DE', secondary: '#778899', highlight: '#E6E6FA', shadow: '#6B8E23' },
    anger: { primary: '#DC143C', secondary: '#8B0000', highlight: '#FF4500', shadow: '#2F4F4F' },
    surprise: { primary: '#98FB98', secondary: '#87CEEB', highlight: '#FFFFFF', shadow: '#4682B4' },
    fear: { primary: '#D3D3D3', secondary: '#A9A9A9', highlight: '#F5F5DC', shadow: '#556B2F' },
    disgust: { primary: '#8FBC8F', secondary: '#6B8E23', highlight: '#9ACD32', shadow: '#556B2F' },
    neutral: { primary: '#DEB887', secondary: '#CD853F', highlight: '#FFE4C4', shadow: '#8B7355' },
  };

  const colors = emotionColors[emotion] || emotionColors.neutral;

  return {
    color_palette: colors,
    eye_features: {
      brightness: 1.0,
      size_multiplier: 1.0,
      sharpness: 1.0,
      pupil_dilation: 1.0,
      highlight_intensity: 1.0,
    },
    mouth_features: {
      curvature: 0,
      openness: 0,
      width: 1.0,
      tension: 0,
    },
    skin_tone: {
      base_hue: '#E8BEAC',
      saturation: 1.0,
      warmth: 1.0,
    },
    special_effects: [],
    metadata: { roughness: 0.3, metalness: 0.0 },
  };
}

// ============================================================================
// WEB SOCKET HOOK FOR BEHAVIOR STATE
// ============================================================================

function useBehaviorState(sessionId: string) {
  const [state, setState] = useState<AvatarStateData | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    // Connect to main API WebSocket for realtime updates
    const wsUrl = `ws://localhost:8000/ws/realtime/${sessionId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('Behavior WS connected');
      // Subscribe to avatar state updates
      ws.send(JSON.stringify({
        event: 'subscribe',
        channel: 'neurotwin:avatar_state'
      }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === 'avatar_state' || data.state) {
          setState(data as AvatarStateData);
        }
        if (data.event === 'avatar_command') {
          // Handle direct avatar commands from orchestrator
          useAvatarStore.getState().setExpression(data.command?.expression || 'neutral');
        }
      } catch (e) {
        console.warn('Invalid WS message:', e);
      }
    };

    ws.onerror = (error) => {
      console.error('Behavior WS error:', error);
    };

    ws.onclose = () => {
      console.log('Behavior WS closed, reconnecting in 2s...');
      setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.CLOSED) {
          wsRef.current = null;
        }
      }, 2000);
    };

    return () => {
      ws.close();
    };
  }, [sessionId]);

  return state;
}

// ============================================================================
// LIP-SYNC VISEME CONTROLLER
// ============================================================================

const VISEME_MAP: Record<string, Record<string, number>> = {
  rest: { jawOpen: 0.0, mouthSmile_L: 0.1, mouthSmile_R: 0.1 },
  aa: { jawOpen: 0.7, mouthSmile_L: 0.1, mouthSmile_R: 0.1, mouthPucker: 0.3 },
  ee: { jawOpen: 0.4, mouthSmile_L: 0.6, mouthSmile_R: 0.6 },
  ih: { jawOpen: 0.3, mouthSmile_L: 0.2, mouthSmile_R: 0.2 },
  oh: { jawOpen: 0.5, mouthSmile_L: 0.3, mouthSmile_R: 0.3, mouthPucker: 0.2 },
  uu: { jawOpen: 0.4, mouthSmile_L: 0.0, mouthSmile_R: 0.0, mouthPucker: 0.5 },
  th: { jawOpen: 0.2, mouthFrown_L: 0.4, mouthFrown_R: 0.4 },
  ff: { jawOpen: 0.0, mouthSmile_L: 0.3, mouthSmile_R: 0.3, lipSuck: 0.2 },
  pp: { jawOpen: 0.0, mouthSmile_L: 0.2, mouthSmile_R: 0.2 },
  ss: { jawOpen: 0.1, mouthFrown_L: 0.3, mouthFrown_R: 0.3 },
};

class LipSyncController {
  private currentViseme: string = 'rest';
  private targetViseme: string = 'rest';
  private transition: number = 0;
  private amplitude: number = 0;
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private dataArray: Uint8Array | null = null;
  private lipCues: Array<{time_s: number, viseme: string, blendshapes: Record<string, number>}> = [];
  private lipCueStart: number | null = null;

  setAmplitude(amp: number) {
    this.amplitude = Math.max(0, Math.min(1, amp));
  }

  setViseme(viseme: string) {
    if (viseme !== this.targetViseme) {
      this.currentViseme = this.targetViseme;
      this.targetViseme = viseme;
      this.transition = 0;
    }
  }

  getBlendshapes(): Record<string, number> {
    const current = VISEME_MAP[this.currentViseme] || VISEME_MAP.rest;
    const target = VISEME_MAP[this.targetViseme] || VISEME_MAP.rest;

    // Interpolate between visemes
    const t = this.transition;
    const blendshapes: Record<string, number> = {};

    // Get all keys from both
    const allKeys = new Set([...Object.keys(current), ...Object.keys(target)]);
    for (const key of allKeys) {
      const from = current[key] || 0;
      const to = target[key] || 0;
      blendshapes[key] = from + (to - from) * t;
    }

    // Add amplitude modulation to jawOpen
    if (blendshapes.jawOpen !== undefined) {
      blendshapes.jawOpen *= (0.5 + 0.5 * this.amplitude);
    }

    // Advance transition
    this.transition = Math.min(1, this.transition + 0.15);

    return blendshapes;
  }

  setLipsyncCues(cues: any[], startTime: number) {
    this.lipCues = cues;
    this.lipCueStart = startTime;
  }

  clearLipsyncCues() {
    this.lipCues = [];
    this.lipCueStart = null;
  }

  updateFromLipsync(now: number) {
    if (!this.lipCueStart || this.lipCues.length === 0) return;
    const elapsed = (now - this.lipCueStart) / 1000;
    let currentCue = null;
    for (let i = this.lipCues.length - 1; i >= 0; i--) {
      if (this.lipCues[i].time_s <= elapsed) {
        currentCue = this.lipCues[i];
        break;
      }
    }
    if (currentCue && currentCue.viseme !== this.targetViseme) {
      this.currentViseme = this.targetViseme;
      this.targetViseme = currentCue.viseme;
      this.transition = 0;
    }
  }

  initAudioAnalysis(audioElement: HTMLAudioElement) {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      const source = this.audioContext.createMediaElementSource(audioElement);
      source.connect(this.analyser);
      this.analyser.connect(this.audioContext.destination);
      this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    }
  }

  updateFromAudio(): number {
    if (this.analyser && this.dataArray) {
      this.analyser.getByteFrequencyData(this.dataArray as Uint8Array<ArrayBuffer>);
      const sum = this.dataArray.reduce((a, b) => a + b, 0);
      const avg = sum / this.dataArray.length / 255;
      this.setAmplitude(avg);
      return avg;
    }
    return this.amplitude;
  }
}

// ============================================================================
// AVATAR MODEL COMPONENT
// ============================================================================

interface AvatarModelProps {
  behaviorState: AvatarStateData | null;
  visualState: VisualState | null;
  expression: string;
  isSpeaking: boolean;
  emotion: string;
  lipSyncController: LipSyncController;
}

function AvatarModel({
  behaviorState,
  visualState,
  expression,
  isSpeaking,
  emotion,
  lipSyncController
}: AvatarModelProps) {
  const groupRef = useRef<THREE.Group>(null);
  const headRef = useRef<THREE.Mesh>(null);
  const leftEyeRef = useRef<THREE.Mesh>(null);
  const rightEyeRef = useRef<THREE.Mesh>(null);
  const mouthGroupRef = useRef<THREE.Group>(null);
  const jawRef = useRef<THREE.Mesh>(null);

  const avatarStore = useAvatarStore();
  const [blendshapes, setBlendshapes] = useState<Record<string, number>>({
    eyeBlinkL: 0, eyeBlinkR: 0,
    mouthSmile_L: 0.1, mouthSmile_R: 0.1,
    mouthFrown_L: 0, mouthFrown_R: 0,
    browDown_L: 0, browDown_R: 0,
    jawOpen: 0,
  });

  // Animation state
  const idleState = useRef({
    breathPhase: 0,
    eyeDriftX: 0,
    eyeDriftY: 0,
    headTilt: 0,
    blinkTimer: 0,
    blinkDuration: 0.15,
    isBlinking: false,
  });

  // Calculate expression blendshapes
  const expressionBlendshapes = useMemo(() => {
    const expr = (expression || 'neutral').toLowerCase();
    const base: Record<string, number> = {
      eyeBlinkL: 0, eyeBlinkR: 0,
      mouthSmile_L: 0, mouthSmile_R: 0,
      mouthFrown_L: 0, mouthFrown_R: 0,
      browDown_L: 0, browDown_R: 0,
      browInnerUp: 0,
      jawOpen: 0,
    };

    switch (expr) {
      case 'smile':
      case 'excited':
        base.mouthSmile_L = 0.8;
        base.mouthSmile_R = 0.8;
        base.cheekSquint_L = 0.3;
        base.cheekSquint_R = 0.3;
        base.browInnerUp = 0.2;
        break;
      case 'sad':
        base.browInnerUp = 0.7;
        base.browDown_L = 0.4;
        base.browDown_R = 0.4;
        base.mouthFrown_L = 0.6;
        base.mouthFrown_R = 0.6;
        base.eyeBlinkL = 0.3;
        base.eyeBlinkR = 0.3;
        break;
      case 'angry':
      case 'anger':
        base.browDown_L = 0.8;
        base.browDown_R = 0.8;
        base.browInnerUp = 0.1;
        base.mouthFrown_L = 0.4;
        base.mouthFrown_R = 0.4;
        base.cheekSquint_L = 0.3;
        base.cheekSquint_R = 0.3;
        break;
      case 'surprise':
        base.browInnerUp = 1.0;
        base.browOuterUp_L = 0.8;
        base.browOuterUp_R = 0.8;
        base.eyeWide_L = 0.9;
        base.eyeWide_R = 0.9;
        base.jawOpen = 0.4;
        break;
      case 'thinking':
        base.browDown_L = 0.3;
        base.browDown_R = 0.1;
        base.eyeLookUp_L = 0.4;
        base.eyeLookUp_R = 0.2;
        base.mouthPress_L = 0.3;
        base.mouthPress_R = 0.3;
        break;
    }

    return base;
  }, [expression]);

  // Apply emotion color
  const emotionColorMap = useMemo(() => ({
    joy: { primary: '#a78bfa', secondary: '#fbbf24', emissive: '#a78bfa' },
    sadness: { primary: '#60a5fa', secondary: '#93c5fd', emissive: '#60a5fa' },
    anger: { primary: '#f87171', secondary: '#fbbf24', emissive: '#dc2626' },
    surprise: { primary: '#fbbf24', secondary: '#fef08a', emissive: '#fbbf24' },
    fear: { primary: '#9ca3af', secondary: '#d1d5db', emissive: '#6b7280' },
    disgust: { primary: '#34d399', secondary: '#a7f3d0', emissive: '#10b981' },
    neutral: { primary: '#c4b5fd', secondary: '#ddd6fe', emissive: '#8b5cf6' },
  }), []);

  const colors = emotionColorMap[emotion as keyof typeof emotionColorMap] || emotionColorMap.neutral;

  // Apply Visual Identity colors if available
  const applyVisualIdentity = () => {
    if (!visualState) return { ...colors };

    const { color_palette } = visualState;
    return {
      primary: color_palette.primary,
      secondary: color_palette.secondary,
      emissive: color_palette.highlight,
    };
  };

  const appliedColors = useMemo(() => applyVisualIdentity(), [visualState]);

  // Animation frame
  useFrame((state, delta) => {
    if (!headRef.current) return;

    // Update lip-sync viseme if cues are active
    lipSyncController.updateFromLipsync(performance.now());

    const t = state.clock.getElapsedTime();

    // =========== IDLE ANIMATIONS ===========
    const stateName = behaviorState?.state || 'idle';
    const isIdle = stateName === 'idle' || stateName === 'thinking';

    if (isIdle) {
      // Breathing - subtle chest expansion
      idleState.current.breathPhase += delta * 1.5;
      const breathScale = 1 + 0.01 * Math.sin(idleState.current.breathPhase);

      // Eye drift - Brownian-like motion
      idleState.current.eyeDriftX += (Math.random() - 0.5) * delta * 0.3;
      idleState.current.eyeDriftY += (Math.random() - 0.5) * delta * 0.3;
      idleState.current.eyeDriftX = Math.max(-0.02, Math.min(0.02, idleState.current.eyeDriftX));
      idleState.current.eyeDriftY = Math.max(-0.02, Math.min(0.02, idleState.current.eyeDriftY));

      // Head micro-movements
      idleState.current.headTilt = Math.sin(t * 0.5) * 0.03;

      // Apply to head group
      headRef.current.scale.y = breathScale;
      headRef.current.rotation.z = idleState.current.headTilt;
    } else {
      // Return from idle gradually
      idleState.current.breathPhase *= 0.95;
      idleState.current.eyeDriftX *= 0.9;
      idleState.current.eyeDriftY *= 0.9;
      idleState.current.headTilt *= 0.9;
    }

    // =========== BLINK CYCLE ===========
    if (!isSpeaking && isIdle) {
      idleState.current.blinkTimer += delta;
      if (idleState.current.blinkTimer >= 2.5 + Math.random() * 1.5) {
        idleState.current.isBlinking = true;
        idleState.current.blinkTimer = 0;
      }

      if (idleState.current.isBlinking) {
        idleState.current.blinkDuration += delta;
        if (idleState.current.blinkDuration >= 0.15) {
          idleState.current.isBlinking = false;
          idleState.current.blinkDuration = 0;
        }
      }
    }

    // =========== BLENDSHAPE INTERPOLATION ===========
    const targetBlendshapes: Record<string, number> = { ...expressionBlendshapes };

    // Add behavior state blendshapes
    if (behaviorState?.blendshapes) {
      Object.assign(targetBlendshapes, behaviorState.blendshapes);
    }

    // Add lip-sync if speaking
    if (isSpeaking) {
      const lipBlendshapes = lipSyncController.getBlendshapes();
      Object.assign(targetBlendshapes, lipBlendshapes);
    }

    // Add emotion-specific intensity modulation
    if (behaviorState) {
      const intensityMult = behaviorState.emotion_intensity || 1;
      for (const key in targetBlendshapes) {
        targetBlendshapes[key] *= intensityMult;
      }
    }

    // Add blink
    if (idleState.current.isBlinking) {
      const progress = idleState.current.blinkDuration / 0.15;
      const blinkVal = progress < 0.5 ? progress * 2 : 2 - progress * 2;
      targetBlendshapes.eyeBlinkL = blinkVal;
      targetBlendshapes.eyeBlinkR = blinkVal;
    }

    // Smooth interpolation
    const lerpFactor = 0.15;
    for (const key in targetBlendshapes) {
      const current = blendshapes[key] || 0;
      const target = targetBlendshapes[key] || 0;
      setBlendshapes(prev => ({
        ...prev,
        [key]: current + (target - current) * lerpFactor,
      }));
    }

    // Position update from eye drift
    if (leftEyeRef.current && rightEyeRef.current) {
      leftEyeRef.current.position.x = -0.24 + idleState.current.eyeDriftX;
      leftEyeRef.current.position.y = 0.1 + idleState.current.eyeDriftY;
      rightEyeRef.current.position.x = 0.24 + idleState.current.eyeDriftX;
      rightEyeRef.current.position.y = 0.1 + idleState.current.eyeDriftY;
    }
  });

  // Render procedural head with materials controlled by blendshapes
  const renderBlendshapeMaterial = (
    baseColor: string,
    roughness: number = 0.7,
    metalness: number = 0.0,
    emissive?: string
  ) => (
    <meshStandardMaterial
      color={baseColor}
      roughness={roughness}
      metalness={metalness}
      emissive={emissive || 'black'}
      emissiveIntensity={emissive ? 0.1 : 0}
    />
  );

  // Extract mouth openness from blendshapes (jawOpen affects mouth height)
  const mouthOpenness = (blendshapes.jawOpen || 0) * 0.15;
  const mouthSmile = (blendshapes.mouthSmile_L || 0) * 0.1 - (blendshapes.mouthFrown_L || 0) * 0.08;
  const mouthWidth = (blendshapes.mouthSmile_L || 0) * 0.05;

  return (
    <Float speed={1} rotationIntensity={0.1} floatIntensity={0.15}>
      <group ref={groupRef}>
        {/* Head */}
        <mesh ref={headRef}>
          <sphereGeometry args={[0.75, 64, 64]} />
          {renderBlendshapeMaterial(appliedColors.primary, 0.7, 0.0, appliedColors.emissive)}
        </mesh>

        {/* Neck */}
        <mesh position={[0, -0.85, 0]}>
          <cylinderGeometry args={[0.22, 0.28, 0.35, 32]} />
          <meshStandardMaterial color="#e0c9b5" roughness={0.8} />
        </mesh>

        {/* Left Eye Socket */}
        <mesh position={[-0.24, 0.1, 0.68]}>
          <sphereGeometry args={[0.1, 32, 32]} />
          <meshStandardMaterial color="white" roughness={0.1} />
        </mesh>
        {/* Left Iris */}
        <mesh position={[-0.24, 0.1, 0.77]}>
          <sphereGeometry args={[0.065, 32, 32]} />
          <meshStandardMaterial
            color={(visualState?.eye_features?.brightness ?? 1) > 1.2 ? '#fff8dc' : '#1a0a2e'}
            roughness={0.05}
          />
        </mesh>
        {/* Left Pupil */}
        <mesh position={[-0.24, 0.1, 0.79]}>
          <sphereGeometry args={[0.028, 32, 32]} />
          <meshStandardMaterial color="black" />
        </mesh>
        {/* Eye highlight */}
        <mesh position={[-0.21, 0.13, 0.8]}>
          <sphereGeometry args={[0.01, 16, 16]} />
          <meshStandardMaterial color="white" emissive="white" emissiveIntensity={1} />
        </mesh>

        {/* Right Eye Socket */}
        <mesh position={[0.24, 0.1, 0.68]}>
          <sphereGeometry args={[0.1, 32, 32]} />
          <meshStandardMaterial color="white" roughness={0.1} />
        </mesh>
        <mesh position={[0.24, 0.1, 0.77]}>
          <sphereGeometry args={[0.065, 32, 32]} />
          <meshStandardMaterial
            color={(visualState?.eye_features?.brightness ?? 1) > 1.2 ? '#fff8dc' : '#1a0a2e'}
            roughness={0.05}
          />
        </mesh>
        <mesh position={[0.24, 0.1, 0.79]}>
          <sphereGeometry args={[0.028, 32, 32]} />
          <meshStandardMaterial color="black" />
        </mesh>
        <mesh position={[0.21, 0.13, 0.8]}>
          <sphereGeometry args={[0.01, 16, 16]} />
          <meshStandardMaterial color="white" emissive="white" emissiveIntensity={1} />
        </mesh>

        {/* Mouth area */}
        <group ref={mouthGroupRef} position={[0, -0.22, 0.7]}>
          {/* Lower lip/jaw for opening */}
          <mesh ref={jawRef} position={[0, -0.12, 0]}>
            <capsuleGeometry args={[0.05, 0.28, 8, 16]} />
            <meshStandardMaterial
              color={appliedColors.secondary}
              roughness={0.6}
            />
          </mesh>
          {/* Upper lip */}
          <mesh position={[0, 0.02, 0.05]}>
            <capsuleGeometry args={[0.045, 0.25, 8, 16]} />
            <meshStandardMaterial
              color={appliedColors.secondary}
              roughness={0.6}
            />
          </mesh>
        </group>

        {/* Nose */}
        <mesh position={[0, -0.04, 0.74]} rotation={[0.3, 0, 0]}>
          <sphereGeometry args={[0.055, 16, 16]} />
          <meshStandardMaterial color="#d4b8a5" roughness={0.8} />
        </mesh>

        {/* Hair */}
        <mesh position={[0, 0.55, 0]}>
          <sphereGeometry args={[0.77, 48, 32, 0, Math.PI * 2, 0, Math.PI * 0.55]} />
          <meshStandardMaterial color="#2d1810" roughness={0.95} />
        </mesh>
      </group>
    </Float>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function AvatarCanvas({
  sessionId,
  expression,
  isSpeaking,
  emotion,
}: {
  sessionId: string | null;
  expression: string;
  isSpeaking: boolean;
  emotion: string;
}) {
  const setExpression = useAvatarStore((state) => state.setExpression);
  const [lipSyncController] = useState(() => new LipSyncController());

  // Connect to behavior state via WebSocket
  const behaviorState = useBehaviorState(sessionId || '');

  // Fetch Visual Identity based on emotion
  const visualState = useVisualIdentity(emotion, behaviorState?.emotion_intensity || 0.5);

  // Sync expression from local store
  useEffect(() => {
    if (expression) {
      setExpression(expression);
    }
  }, [expression, setExpression]);

  // Handle audio for lip-sync
  useEffect(() => {
    if (isSpeaking) {
      lipSyncController.setAmplitude(0.7);
    } else {
      lipSyncController.setAmplitude(0);
    }
  }, [isSpeaking, lipSyncController]);

  // Update expression based on behavior state
  useEffect(() => {
    if (!behaviorState?.emotion) {
      return;
    }

    // Keep the canvas on expressions it can actually render.
    const emotionToExpression: Record<string, string> = {
      joy: 'smile',
      sadness: 'sad',
      anger: 'angry',
      fear: 'sad',
      surprise: 'surprise',
      disgust: 'thinking',
      neutral: 'neutral',
    };
    const expr = emotionToExpression[behaviorState.emotion] || 'neutral';
    setExpression(expr);
  }, [behaviorState, setExpression]);

  return (
    <div className="avatar-canvas-container" style={{ width: '100%', height: '100%' }}>
      <Canvas
        camera={{ position: [0, 0, 2.8], fov: 42 }}
        dpr={[1, 2]}
        gl={{
          antialias: true,
          alpha: true,
          powerPreference: 'high-performance',
        }}
        style={{ background: 'transparent' }}
      >
        {/* Lighting based on emotion */}
        <ambientLight intensity={0.6} />
        <directionalLight
          position={[5, 8, 5]}
          intensity={1.2}
          castShadow
          shadow-mapSize-width={1024}
          shadow-mapSize-height={1024}
        />
        <pointLight
          position={[-3, 2, 2]}
          intensity={0.8}
          color={visualState?.color_palette?.highlight || '#a78bfa'}
        />
        <pointLight
          position={[3, -2, 4]}
          intensity={0.4}
          color="#8b5cf6"
        />

        {/* Avatar Model */}
        <AvatarModel
          behaviorState={behaviorState}
          visualState={visualState}
          expression={expression}
          isSpeaking={isSpeaking}
          emotion={emotion}
          lipSyncController={lipSyncController}
        />

        {/* Environment for reflections */}
        <Environment preset="studio" background={false} />

        {/* Camera controls (optional for user interaction) */}
        <OrbitControls
          enableZoom={false}
          enablePan={false}
          minPolarAngle={Math.PI / 2.5}
          maxPolarAngle={Math.PI / 1.5}
          rotateSpeed={0.5}
        />
      </Canvas>

      {/* Emotion indicator overlay */}
      <div className="emotion-overlay">
        <span className={`emotion-badge emotion-${emotion}`}>
          {emotion}
        </span>
      </div>
    </div>
  );
}

export default AvatarCanvas;
