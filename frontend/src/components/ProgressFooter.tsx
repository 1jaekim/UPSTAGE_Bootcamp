import { useEffect } from 'react';
import { useProgress } from '../api/hooks';
import { useSpoStore } from '../store';

export function ProgressFooter() {
  const selectedBookId = useSpoStore((s) => s.selectedBookId);
  const currentPage = useSpoStore((s) => s.currentPage);
  const totalPages = useSpoStore((s) => s.totalPages);
  const setProgress = useSpoStore((s) => s.setProgress);
  const requestPage = useSpoStore((s) => s.requestPage);
  const { data: progress } = useProgress(selectedBookId);

  useEffect(() => {
    if (progress) {
      setProgress(
        progress.reading_offset,
        progress.spoiler_boundary,
        progress.current_page,
        progress.total_pages,
        progress.spoiler_boundary_page,
        progress.current_cfi,
      );
    }
  }, [progress, setProgress]);

  return (
    <footer className="z-30 grid gap-2 border-t border-slate-200 bg-white px-4 py-3 md:px-7">
      <input
        type="range"
        min={1}
        max={Math.max(totalPages, 1)}
        step={1}
        value={Math.max(currentPage, 1)}
        onChange={(event) => requestPage(Number(event.target.value))}
        disabled={totalPages <= 0}
        className="h-1.5 w-full cursor-pointer accent-accent"
        aria-label="읽기 위치 이동"
      />
      <div className="flex items-center justify-between gap-3 text-xs font-semibold text-slate-500">
        <span>{currentPage > 0 && totalPages > 0 ? `${currentPage} / ${totalPages}` : '페이지 계산 중'}</span>
        <span className="hidden rounded-full border border-blue-100 bg-blue-50 px-3 py-1 text-accent sm:inline">
          {currentPage > 0
            ? `현재 ${currentPage}페이지까지 공개된 정보`
            : '페이지 계산 중'}
        </span>
        <span className="rounded-md bg-indigo-50 px-2 py-1 font-mono text-[11px] font-bold text-accent">
          {currentPage > 0 ? `현재 ${currentPage}페이지` : '현재 위치'}
        </span>
        <span>{totalPages > 0 ? `${currentPage} / 전체 ${totalPages}페이지` : '페이지 계산 중'}</span>
      </div>
    </footer>
  );
}
