// ── API 클라이언트: mock ↔ 실서버 스위치 (SPEC §2 API 레이어) ──
// VITE_USE_MOCK=true 면 MOCKS.md 픽스처 반환, false 면 실서버(/api) fetch.

import type { Book, BookSummary, Chapter, GraphJson, Progress, Reminders, UploadResult } from './types';
import {
  BOOK_MIST,
  CHAPTERS_BY_INDEX,
  mockProgress,
  pickGraph,
  pickReminders,
} from './mock';

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false';
const BASE = import.meta.env.VITE_API_BASE ?? '';

export function bookFileUrl(bookId: string): string {
  return `${BASE}/api/books/${bookId}/file`;
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${path}`);
  return res.json() as Promise<T>;
}

// mock progress는 모듈 메모리에 유지 (boundary 단조 증가)
const mockProgressState: Progress = { ...mockProgress };

export const api = {
  async getBooks(): Promise<BookSummary[]> {
    if (USE_MOCK) {
      await sleep(100);
      return [
        {
          id: BOOK_MIST.id,
          title: BOOK_MIST.title,
          author: BOOK_MIST.author,
          total_offset: BOOK_MIST.total_offset,
        },
      ];
    }
    return http<BookSummary[]>('/api/books');
  },

  async uploadBook(file: File): Promise<UploadResult> {
    if (USE_MOCK) {
      await sleep(300);
      return { book_id: BOOK_MIST.id, reused: true, paragraph_count: 0 };
    }
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${BASE}/api/books/upload`, { method: 'POST', body: form });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText} — /api/books/upload`);
    return res.json() as Promise<UploadResult>;
  },

  async getBook(bookId: string): Promise<Book> {
    if (USE_MOCK) {
      await sleep(150);
      return structuredClone(BOOK_MIST);
    }
    return http<Book>(`/api/books/${bookId}`);
  },

  async getChapter(bookId: string, index: number): Promise<Chapter> {
    if (USE_MOCK) {
      await sleep(150);
      const ch = CHAPTERS_BY_INDEX[index];
      if (!ch) throw new Error(`chapter ${index} 없음`);
      return structuredClone(ch);
    }
    return http<Chapter>(`/api/books/${bookId}/chapters/${index}`);
  },

  async getGraph(bookId: string, offset: number, revealAll: boolean): Promise<GraphJson> {
    if (USE_MOCK) {
      await sleep(200);
      // 안심 모드 OFF(reveal_all)여도 데모에서는 380 응답과 동일 (MOCKS.md)
      return structuredClone(pickGraph(offset));
    }
    const q = new URLSearchParams({ offset: String(offset) });
    if (revealAll) q.set('reveal_all', 'true');
    return http<GraphJson>(`/api/books/${bookId}/graph?${q}`);
  },

  async getReminders(bookId: string, offset: number, entityId?: string): Promise<Reminders> {
    if (USE_MOCK) {
      await sleep(200);
      const r = structuredClone(pickReminders(offset));
      if (entityId) r.lines = r.lines.filter((l) => l.entity_ids.includes(entityId));
      return r;
    }
    const q = new URLSearchParams({ offset: String(offset) });
    if (entityId) q.set('entity_id', entityId);
    return http<Reminders>(`/api/books/${bookId}/reminders?${q}`);
  },

  async getProgress(bookId: string): Promise<Progress> {
    if (USE_MOCK) {
      await sleep(100);
      return { ...mockProgressState };
    }
    return http<Progress>(`/api/books/${bookId}/progress`);
  },

  async putProgress(
    bookId: string,
    args: { offset?: number; cfi?: string; force?: boolean },
  ): Promise<Progress> {
    const { offset = 0, cfi, force = false } = args;
    if (USE_MOCK) {
      await sleep(100);
      mockProgressState.reading_offset = offset;
      // boundary = max(기존, 신규) 단조 증가 (SPEC 불변식 5) — force=true면 재독 모드로 강제 리셋
      mockProgressState.spoiler_boundary = force
        ? offset
        : Math.max(mockProgressState.spoiler_boundary, offset);
      return { ...mockProgressState };
    }
    return http<Progress>(`/api/books/${bookId}/progress`, {
      method: 'PUT',
      body: JSON.stringify({ reading_offset: offset, cfi, force }),
    });
  },
};

export const IS_MOCK = USE_MOCK;
