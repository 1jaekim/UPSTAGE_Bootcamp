// ── UI 상태 (Zustand, SPEC §2) ────────────────────────────────
import { create } from 'zustand';
import { BOOK_ID } from './lib/constants';

export type PanelKind = 'closed' | 'relationship' | 'reminder' | 'settings';

interface SpoState {
  selectedBookId: string; // 기본값은 constants.BOOK_ID, 책 목록에서 고르면 바뀜
  spoilerSafe: boolean; // 기본 true (안심 모드 ON)
  panel: PanelKind; // 기본 closed
  readingOffset: number;
  spoilerBoundary: number;
  maskNames: boolean; // 설정: 이름 마스킹
  theme: 'light' | 'dark';
  analyzed: boolean; // 🧠 SpoKeeper Panel: '현재 위치까지 분석' 실행 여부

  setSelectedBookId: (id: string) => void;
  setSpoilerSafe: (v: boolean) => void;
  setPanel: (p: PanelKind) => void;
  togglePanel: (p: Exclude<PanelKind, 'closed'>) => void;
  setProgress: (readingOffset: number, spoilerBoundary: number) => void;
  setMaskNames: (v: boolean) => void;
  setTheme: (t: 'light' | 'dark') => void;
  setAnalyzed: (v: boolean) => void;
}

export const useSpoStore = create<SpoState>((set) => ({
  selectedBookId: BOOK_ID,
  spoilerSafe: true,
  panel: 'closed',
  readingOffset: 0,
  spoilerBoundary: 0,
  maskNames: false,
  theme: 'light',
  analyzed: false,

  // 책이 바뀌면 이전 책의 읽기 위치/분석 상태를 그대로 들고 있으면 안 되므로 초기화한다.
  setSelectedBookId: (selectedBookId) =>
    set({ selectedBookId, readingOffset: 0, spoilerBoundary: 0, analyzed: false }),
  setSpoilerSafe: (v) => set({ spoilerSafe: v }),
  setPanel: (panel) => set({ panel }),
  togglePanel: (p) => set((s) => ({ panel: s.panel === p ? 'closed' : p })),
  setProgress: (readingOffset, spoilerBoundary) =>
    set({ readingOffset, spoilerBoundary }),
  setMaskNames: (maskNames) => set({ maskNames }),
  setTheme: (theme) => set({ theme }),
  setAnalyzed: (analyzed) => set({ analyzed }),
}));
