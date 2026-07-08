// ── UI 상태 (Zustand, SPEC §2) ────────────────────────────────
import { create } from 'zustand';

export type PanelKind = 'closed' | 'relationship' | 'reminder' | 'settings';

interface SpoState {
  spoilerSafe: boolean; // 기본 true (안심 모드 ON)
  panel: PanelKind; // 기본 closed
  readingOffset: number;
  spoilerBoundary: number;
  maskNames: boolean; // 설정: 이름 마스킹
  theme: 'light' | 'dark';
  analyzed: boolean; // 🧠 SpoKeeper Panel: '현재 위치까지 분석' 실행 여부

  setSpoilerSafe: (v: boolean) => void;
  setPanel: (p: PanelKind) => void;
  togglePanel: (p: Exclude<PanelKind, 'closed'>) => void;
  setProgress: (readingOffset: number, spoilerBoundary: number) => void;
  setMaskNames: (v: boolean) => void;
  setTheme: (t: 'light' | 'dark') => void;
  setAnalyzed: (v: boolean) => void;
}

export const useSpoStore = create<SpoState>((set) => ({
  spoilerSafe: true,
  panel: 'closed',
  readingOffset: 0,
  spoilerBoundary: 0,
  maskNames: false,
  theme: 'light',
  analyzed: false,

  setSpoilerSafe: (v) => set({ spoilerSafe: v }),
  setPanel: (panel) => set({ panel }),
  togglePanel: (p) => set((s) => ({ panel: s.panel === p ? 'closed' : p })),
  setProgress: (readingOffset, spoilerBoundary) =>
    set({ readingOffset, spoilerBoundary }),
  setMaskNames: (maskNames) => set({ maskNames }),
  setTheme: (theme) => set({ theme }),
  setAnalyzed: (analyzed) => set({ analyzed }),
}));
