// ── 리더 뷰 (F1): 본문 + 페이지네이션 + offset 추적 → PUT progress
import { useEffect, useMemo, useState } from 'react';
import { BOOK_ID } from '../lib/constants';
import { useBook, useChapter, useProgress, usePutProgress } from '../api/hooks';
import { useSpoStore } from '../store';

/** 챕터 내 페이지(문단) 위치를 offset으로 보간 */
function pageOffset(start: number, end: number, pageIdx: number, pageCount: number) {
  const frac = (pageIdx + 1) / pageCount;
  return Math.round(start + (end - start) * frac);
}

export function ReaderView() {
  const { data: book } = useBook(BOOK_ID);
  const { data: progress } = useProgress(BOOK_ID);
  const putProgress = usePutProgress(BOOK_ID);
  const setProgress = useSpoStore((s) => s.setProgress);

  const [chapterIndex, setChapterIndex] = useState(3); // 데모 기본: 챕터3
  const [page, setPage] = useState(0);
  const { data: chapter, isLoading } = useChapter(BOOK_ID, chapterIndex);

  // 최초 progress 로드 → store 동기화
  useEffect(() => {
    if (progress) setProgress(progress.reading_offset, progress.spoiler_boundary);
  }, [progress, setProgress]);

  // 문단 단위 페이지
  const pages = useMemo(
    () => (chapter?.content ?? '').split('\n\n').filter(Boolean),
    [chapter],
  );
  const pageCount = Math.max(pages.length, 1);

  // 현재 페이지 → offset 계산 후 progress 갱신 (읽은 위치 추적)
  useEffect(() => {
    if (!chapter) return;
    const off = pageOffset(chapter.start_offset, chapter.end_offset, page, pageCount);
    putProgress.mutate(off, {
      onSuccess: (p) => setProgress(p.reading_offset, p.spoiler_boundary),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapter, page, pageCount]);

  const goChapter = (idx: number) => {
    setChapterIndex(idx);
    setPage(0);
  };

  return (
    <div className="mx-auto flex h-full w-full max-w-2xl flex-col px-4 py-6 sm:px-0">
      {/* 챕터 선택 */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {book?.chapters.map((c) => (
          <button
            key={c.id}
            type="button"
            onClick={() => goChapter(c.index)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition ${
              c.index === chapterIndex
                ? 'bg-accent text-white'
                : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
            }`}
          >
            {c.index}. {c.title}
          </button>
        ))}
      </div>

      {/* 본문 카드 */}
      <article className="flex-1 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-10">
        {isLoading ? (
          <div className="space-y-3">
            <div className="h-5 w-1/3 animate-pulse rounded bg-slate-100" />
            <div className="h-4 w-full animate-pulse rounded bg-slate-100" />
            <div className="h-4 w-5/6 animate-pulse rounded bg-slate-100" />
          </div>
        ) : chapter ? (
          <>
            <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-accent">
              {chapter.index}부 · {chapter.title}
            </div>
            <h2 className="mb-6 text-2xl font-bold text-slate-800">{chapter.title}</h2>
            <p className="min-h-[8rem] whitespace-pre-line text-[17px] leading-8 text-slate-700">
              {pages[page]}
            </p>
          </>
        ) : (
          <p className="text-slate-400">본문을 불러오지 못했어요.</p>
        )}
      </article>

      {/* 페이지네이션 */}
      <div className="mt-4 flex items-center justify-between">
        <button
          type="button"
          disabled={page === 0}
          onClick={() => setPage((p) => Math.max(0, p - 1))}
          className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 shadow-sm transition enabled:hover:border-slate-300 disabled:opacity-40"
        >
          ← 이전
        </button>
        <span className="text-xs text-slate-400">
          {page + 1} / {pageCount} 쪽
        </span>
        <button
          type="button"
          disabled={page >= pageCount - 1}
          onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white shadow-sm transition enabled:hover:brightness-110 disabled:opacity-40"
        >
          다음 →
        </button>
      </div>
    </div>
  );
}
