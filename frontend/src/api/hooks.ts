// ── TanStack Query 훅 (SPEC §2 서버상태) ──────────────────────
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './client';

export function useBooks() {
  return useQuery({
    queryKey: ['books'],
    queryFn: () => api.getBooks(),
  });
}

export function useUploadBook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => api.uploadBook(file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['books'] });
    },
  });
}

export function useBook(bookId: string) {
  return useQuery({
    queryKey: ['book', bookId],
    queryFn: () => api.getBook(bookId),
  });
}

export function useChapter(bookId: string, index: number) {
  return useQuery({
    queryKey: ['chapter', bookId, index],
    queryFn: () => api.getChapter(bookId, index),
    enabled: index > 0,
  });
}

/** useGraph(bookId, boundary, spoilerSafe) — 키 ['graph',bookId,boundary,spoilerSafe]
 *  spoilerSafe=false → reveal_all=true. boundary 변경 시 자동 refetch. */
export function useGraph(bookId: string, boundary: number, spoilerSafe: boolean) {
  return useQuery({
    queryKey: ['graph', bookId, boundary, spoilerSafe],
    queryFn: () => api.getGraph(bookId, boundary, !spoilerSafe),
  });
}

export function useReminders(bookId: string, boundary: number, entityId?: string) {
  return useQuery({
    queryKey: ['reminders', bookId, boundary, entityId ?? null],
    queryFn: () => api.getReminders(bookId, boundary, entityId),
  });
}

export function useProgress(bookId: string) {
  return useQuery({
    queryKey: ['progress', bookId],
    queryFn: () => api.getProgress(bookId),
  });
}

export function usePutProgress(bookId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: number | { offset?: number; cfi?: string; force?: boolean }) =>
      typeof args === 'number'
        ? api.putProgress(bookId, { offset: args })
        : api.putProgress(bookId, args),
    onSuccess: (data) => {
      qc.setQueryData(['progress', bookId], data);
    },
  });
}
