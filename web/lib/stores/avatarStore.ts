import { create } from 'zustand';

interface AvatarState {
  expression: string;
  isSpeaking: boolean;
  emotion: string;
  intensity: number;
  animationQueue: Array<{ expression: string; duration: number }>;
  setExpression: (expression: string, intensity?: number) => void;
  setIsSpeaking: (speaking: boolean) => void;
  setEmotion: (emotion: string) => void;
  queueAnimation: (expression: string, duration: number) => void;
  clearQueue: () => void;
}

export const useAvatarStore = create<AvatarState>((set, get) => ({
  expression: 'neutral',
  isSpeaking: false,
  emotion: 'neutral',
  intensity: 0.8,
  animationQueue: [],

  setExpression: (expression, intensity = 0.8) =>
    set({ expression, intensity }),

  setIsSpeaking: (isSpeaking) =>
    set({ isSpeaking }),

  setEmotion: (emotion) =>
    set({ emotion }),

  queueAnimation: (expression, duration) =>
    set(state => ({
      animationQueue: [...state.animationQueue, { expression, duration }],
    })),

  clearQueue: () => set({ animationQueue: [] }),
}));
