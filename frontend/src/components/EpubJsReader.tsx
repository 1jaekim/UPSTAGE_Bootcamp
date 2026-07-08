// ── epub.js 기반 실제 리더 ──────────────────────────────────────
// 화면(뷰포트) 크기에 맞춰 실제로 페이지를 나눠서 보여주고, epub.js가 주는 진짜 CFI를
// 그대로 백엔드에 보낸다. 페이지 표시는 매번 즉시 갱신하되, 분석 갱신(서버 반영)은
// 10페이지마다 한 번씩만 트리거한다. 새로고침 시엔 마지막으로 읽던 위치부터 이어서 연다.
//
// 페이지 번호는 챕터(spine 섹션)마다 따로 매겨지는 epub.js의 기본 displayed.page가 아니라,
// book.locations(책 전체를 미리 스캔해 만드는 절대 위치 인덱스)를 써서 챕터와 무관하게
// 책 전체 기준으로 계산한다.
import { useEffect, useRef, useState } from 'react';
import ePub, { type Book, type Rendition } from 'epubjs';
import { bookFileUrl } from '../api/client';
import { useProgress, usePutProgress } from '../api/hooks';
import { useSpoStore } from '../store';

const PAGES_PER_UPDATE = 10;
const CHARS_PER_LOCATION = 1000; // book.locations 생성 단위 (작을수록 촘촘하지만 생성이 느려짐)

export function EpubJsReader() {
  const bookId = useSpoStore((s) => s.selectedBookId);
  const setProgress = useSpoStore((s) => s.setProgress);
  const setPage = useSpoStore((s) => s.setPage);
  const currentPage = useSpoStore((s) => s.currentPage);
  const totalPages = useSpoStore((s) => s.totalPages);
  const putProgress = usePutProgress(bookId);
  const { data: progress, isLoading: progressLoading } = useProgress(bookId);

  const containerRef = useRef<HTMLDivElement>(null);
  const bookRef = useRef<Book | null>(null);
  const renditionRef = useRef<Rendition | null>(null);
  const pageCountRef = useRef(0);

  const [loadError, setLoadError] = useState<string | null>(null);
  const [locationsReady, setLocationsReady] = useState(false);

  useEffect(() => {
    // progress 조회가 끝날 때까지 기다렸다가 열어야 마지막 위치로 바로 이어서 열 수 있다.
    if (!containerRef.current || progressLoading) return;
    setLoadError(null);
    setLocationsReady(false);
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

    let cancelled = false;

    const reportPage = (cfi: string) => {
      const loc = book.locations.locationFromCfi(cfi);
      const total = book.locations.total;
      if (typeof loc === 'number' && total > 0) {
        setPage(loc + 1, total + 1); // locationFromCfi는 0-based
      }
    };

    book.ready
      .then(() => book.locations.generate(CHARS_PER_LOCATION))
      .then(() => {
        if (cancelled) return;
        setLocationsReady(true);
        // 마지막으로 읽던 CFI가 있으면 거기서, 없으면 처음부터 연다.
        return rendition.display(progress?.cfi ?? undefined).then(() => {
          const current = rendition.currentLocation() as unknown as { start?: { cfi: string } } | undefined;
          if (current?.start?.cfi) reportPage(current.start.cfi);
        });
      })
      .catch((e: unknown) => {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : 'EPUB을 불러오지 못했습니다.');
      });

    rendition.on('relocated', (location: { start: { cfi: string } }) => {
      reportPage(location.start.cfi);
      pageCountRef.current += 1;

      // 분석 갱신(서버 반영)은 10페이지마다 한 번씩만
      if (pageCountRef.current % PAGES_PER_UPDATE === 0) {
        putProgress.mutate(
          { cfi: location.start.cfi },
          { onSuccess: (p) => setProgress(p.reading_offset, p.spoiler_boundary) },
        );
      }
    });

    return () => {
      cancelled = true;
      rendition.destroy();
      book.destroy();
      renditionRef.current = null;
      bookRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookId, progressLoading]);

  return (
    <section className="flex min-h-0 flex-col rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header className="flex items-center justify-between gap-2 border-b border-slate-100 px-5 py-3">
        <div className="flex items-center gap-2">
          <span className="text-lg" aria-hidden>📖</span>
          <h2 className="text-sm font-bold text-slate-800">EPUB 리더 (epub.js)</h2>
        </div>
        <span className="text-xs text-slate-400">
          {!locationsReady ? '페이지 계산 중...' : totalPages > 0 ? `${currentPage} / ${totalPages}` : ''}
        </span>
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
