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

/** 업로드 직후 분석 진행률을 폴링한다. status가 running일 때만 2초마다 다시 불러오고,
 *  done/failed가 되면 폴링을 멈춘다. enabled=false면 아예 요청하지 않는다. */
export function useAnalysisStatus(bookId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ['analysisStatus', bookId],
    queryFn: () => api.getAnalysisStatus(bookId as string),
    enabled: enabled && !!bookId,
    refetchInterval: (query) => (query.state.data?.status === 'running' ? 2000 : false),
  });
}

export function useDeleteBook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (bookId: string) => api.deleteBook(bookId),
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
