import { useEffect } from 'react';
import { useBook, useProgress, usePutProgress } from '../api/hooks';
import { useSpoStore } from '../store';

export function ProgressFooter() {
  const selectedBookId = useSpoStore((s) => s.selectedBookId);
  const readingOffset = useSpoStore((s) => s.readingOffset);
  const spoilerBoundary = useSpoStore((s) => s.spoilerBoundary);
  const currentPage = useSpoStore((s) => s.currentPage);
  const totalPages = useSpoStore((s) => s.totalPages);
  const setProgress = useSpoStore((s) => s.setProgress);
  const { data: book } = useBook(selectedBookId);
  const { data: progress } = useProgress(selectedBookId);
  const putProgress = usePutProgress(selectedBookId);
  const total = Math.max(book?.total_offset ?? 1, 1);
  const percent = Math.min(100, Math.round((readingOffset / total) * 100));

  useEffect(() => {
    if (progress) setProgress(progress.reading_offset, progress.spoiler_boundary);
  }, [progress, setProgress]);

  const onSlide = (value: number) => {
    setProgress(value, Math.max(useSpoStore.getState().spoilerBoundary, value));
    putProgress.mutate(value, {
      onSuccess: (next) => setProgress(next.reading_offset, next.spoiler_boundary),
    });
  };

  return (
    <footer className="z-30 grid gap-2 border-t border-slate-200 bg-white px-4 py-3 md:px-7">
      <input
        type="range"
        min={0}
        max={total}
        step={5}
        value={readingOffset}
        onChange={(event) => onSlide(Number(event.target.value))}
        className="h-1.5 w-full cursor-pointer accent-accent"
        aria-label="읽기 offset 이동"
      />
      <div className="flex items-center justify-between gap-3 text-xs font-semibold text-slate-500">
        <span>현재 위치 {percent}%</span>
        <span className="hidden rounded-full border border-blue-100 bg-blue-50 px-3 py-1 text-accent sm:inline">
          {spoilerBoundary} offset까지 공개
        </span>
        <span className="rounded-md bg-indigo-50 px-2 py-1 font-mono text-[11px] font-bold text-accent">
          offset {String(readingOffset).padStart(3, '0')}
        </span>
        <span>{totalPages > 0 ? `${currentPage} / ${totalPages}` : '페이지 계산 중'}</span>
      </div>
    </footer>
  );
}
