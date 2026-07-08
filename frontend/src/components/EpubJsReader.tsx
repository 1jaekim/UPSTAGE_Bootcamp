// ── epub.js 기반 실제 리더 ──────────────────────────────────────
// 화면(뷰포트) 크기에 맞춰 실제로 페이지를 나눠서 보여주고, epub.js가 주는 진짜 CFI를
// 그대로 백엔드에 보낸다. 10페이지마다 한 번씩만 progress를 갱신해 분석 트리거를 늦춘다.
import { useEffect, useRef, useState } from 'react';
import ePub, { type Book, type Rendition } from 'epubjs';
import { bookFileUrl } from '../api/client';
import { usePutProgress } from '../api/hooks';
import { useSpoStore } from '../store';

const PAGES_PER_UPDATE = 10;

export function EpubJsReader() {
  const bookId = useSpoStore((s) => s.selectedBookId);
  const setProgress = useSpoStore((s) => s.setProgress);
  const putProgress = usePutProgress(bookId);

  const containerRef = useRef<HTMLDivElement>(null);
  const bookRef = useRef<Book | null>(null);
  const renditionRef = useRef<Rendition | null>(null);
  const pageCountRef = useRef(0);

  const [loadError, setLoadError] = useState<string | null>(null);
  const [locationLabel, setLocationLabel] = useState<string>('');

  useEffect(() => {
    if (!containerRef.current) return;
    setLoadError(null);
    pageCountRef.current = 0;

    // URL이 '.epub'로 안 끝나서(우리 API는 /file 경로) openAs를 명시해야
    // epub.js가 이걸 "이미 풀린 폴더"가 아니라 "받아서 풀어야 할 압축 파일"로 인식한다.
    const book = ePub(bookFileUrl(bookId), { openAs: 'epub' });
    bookRef.current = book;
    const rendition = book.renderTo(containerRef.current, {
      width: '100%',
      height: '100%',
      flow: 'paginated',
    });
    renditionRef.current = rendition;

    rendition.display().catch((e: unknown) => {
      setLoadError(e instanceof Error ? e.message : 'EPUB을 불러오지 못했습니다.');
    });

    rendition.on('relocated', (location: { start: { cfi: string; displayed: { page: number; total: number } } }) => {
      setLocationLabel(`${location.start.displayed.page} / ${location.start.displayed.total}`);
      pageCountRef.current += 1;

      // 10페이지마다 한 번씩만 서버에 반영 (분석 갱신 트리거 억제)
      if (pageCountRef.current % PAGES_PER_UPDATE === 0) {
        putProgress.mutate(
          { cfi: location.start.cfi },
          { onSuccess: (p) => setProgress(p.reading_offset, p.spoiler_boundary) },
        );
      }
    });

    return () => {
      rendition.destroy();
      book.destroy();
      renditionRef.current = null;
      bookRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookId]);

  return (
    <section className="flex min-h-0 flex-col rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header className="flex items-center justify-between gap-2 border-b border-slate-100 px-5 py-3">
        <div className="flex items-center gap-2">
          <span className="text-lg" aria-hidden>📖</span>
          <h2 className="text-sm font-bold text-slate-800">EPUB 리더 (epub.js)</h2>
        </div>
        <span className="text-xs text-slate-400">{locationLabel}</span>
      </header>

      <div className="relative min-h-0 flex-1">
        {loadError ? (
          <p className="p-5 text-sm text-red-500">{loadError}</p>
        ) : (
          <div ref={containerRef} className="h-full w-full" />
        )}
      </div>

      <div className="flex items-center justify-between border-t border-slate-100 px-5 py-3">
        <button
          type="button"
          onClick={() => renditionRef.current?.prev()}
          className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 shadow-sm transition hover:border-slate-300"
        >
          ← 이전 페이지
        </button>
        <button
          type="button"
          onClick={() => renditionRef.current?.next()}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:brightness-110"
        >
          다음 페이지 →
        </button>
      </div>
    </section>
  );
}
