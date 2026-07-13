import { useEffect, useRef, useState } from 'react';
import ePub, { type Book, type Rendition } from 'epubjs';
import { bookFileUrl } from '../api/client';
import { useProgress, usePutProgress } from '../api/hooks';
import { useSpoStore } from '../store';
import { ReaderToolbar } from './ReaderToolbar';

type LocationsWithTotal = {
  locationFromCfi: (cfi: string) => number;
  cfiFromLocation: (location: number) => string;
  total: number;
};

function charsForViewport(width: number, height: number): number {
  // epub.js locations는 문자 단위이므로 현재 viewport가 담을 수 있는 문자 수를 기준으로
  // 다시 생성한다. 화면/폰트 reflow 시 같은 CFI의 표시 page가 새로 계산된다.
  const columns = Math.max(24, Math.floor(width / 10));
  const rows = Math.max(12, Math.floor(height / 29));
  return Math.max(300, Math.min(2400, columns * rows));
}

// 페이지 번호/슬라이더 위치는 서버 응답을 기다릴 필요 없이 클라이언트에서 바로 계산되므로
// (epub.js locations가 이미 로컬에 있음) 즉시 반영한다. 서버 확정 상태(reading_offset,
// spoiler_boundary 등)만 이 지연 이후 한 번 저장한다 — 슬라이더를 빠르게 끌 때마다
// 매번 요청을 쏘지 않기 위한 최소한의 디바운스.
const PROGRESS_FLUSH_DELAY_MS = 150;

export function EpubJsReader() {
  const bookId = useSpoStore((s) => s.selectedBookId);
  const setProgress = useSpoStore((s) => s.setProgress);
  const setPage = useSpoStore((s) => s.setPage);
  const setLatestCfi = useSpoStore((s) => s.setLatestCfi);
  const currentPage = useSpoStore((s) => s.currentPage);
  const totalPages = useSpoStore((s) => s.totalPages);
  const latestCfi = useSpoStore((s) => s.latestCfi);
  const requestedPage = useSpoStore((s) => s.requestedPage);
  const requestPage = useSpoStore((s) => s.requestPage);
  const putProgress = usePutProgress(bookId);
  const { data: progress, isLoading: progressLoading } = useProgress(bookId);

  const containerRef = useRef<HTMLDivElement>(null);
  const bookRef = useRef<Book | null>(null);
  const renditionRef = useRef<Rendition | null>(null);
  const viewportRef = useRef({ width: 0, height: 0 });
  const syncSequenceRef = useRef(0);
  const flushTimerRef = useRef<number | null>(null);

  const [loadError, setLoadError] = useState<string | null>(null);
  const [locationsReady, setLocationsReady] = useState(false);
  const [paginationRevision, setPaginationRevision] = useState(0);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const observer = new ResizeObserver(([entry]) => {
      const width = Math.round(entry.contentRect.width);
      const height = Math.round(entry.contentRect.height);
      const previous = viewportRef.current;
      viewportRef.current = { width, height };
      if (previous.width > 0 && previous.height > 0 && (previous.width !== width || previous.height !== height)) {
        clearTimeout(timer);
        timer = setTimeout(() => setPaginationRevision((value) => value + 1), 180);
      }
    });
    observer.observe(element);
    return () => {
      clearTimeout(timer);
      observer.disconnect();
    };
  }, []);

  useEffect(() => {
    if (!containerRef.current || progressLoading) return;
    syncSequenceRef.current += 1;
    setLoadError(null);
    setLocationsReady(false);
    setPage(0, 0);

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
      const locations = book.locations as unknown as LocationsWithTotal;
      const locationIndex = locations.locationFromCfi(cfi);
      const totalLocationCount = locations.total;
      if (typeof locationIndex === 'number' && totalLocationCount > 0) {
        const page = locationIndex + 1;
        return { page, totalPages: totalLocationCount + 1 };
      }
      return null;
    };

    const flushProgress = (cfi: string, pagination: { page: number; totalPages: number }) => {
      const sequence = ++syncSequenceRef.current;
      putProgress.mutate(
        {
          currentCfi: cfi,
          currentPage: pagination.page,
          totalPages: pagination.totalPages,
        },
        {
          onSuccess: (next) => {
            if (sequence !== syncSequenceRef.current) return;
            setProgress(
              next.reading_offset,
              next.spoiler_boundary,
              next.current_page,
              next.total_pages,
              next.spoiler_boundary_page,
              next.current_cfi,
            );
            setLocationsReady(true);
          },
        },
      );
    };

    const syncLocation = (cfi: string) => {
      const pagination = reportPage(cfi);
      setLatestCfi(cfi);
      if (!pagination) return;

      // 페이지 번호/슬라이더는 서버 응답을 기다리지 않고 여기서 바로 갱신한다 —
      // epub.js locations가 이미 로컬에 있어서 즉시 계산 가능하다. 서버 확정 상태
      // (reading_offset/spoiler_boundary 등)만 디바운스 후 저장한다.
      setPage(pagination.page, pagination.totalPages);

      if (flushTimerRef.current !== null) window.clearTimeout(flushTimerRef.current);
      flushTimerRef.current = window.setTimeout(() => {
        flushTimerRef.current = null;
        flushProgress(cfi, pagination);
      }, PROGRESS_FLUSH_DELAY_MS);
    };

    book.ready
      .then(() => {
        const { width, height } = viewportRef.current;
        return book.locations.generate(charsForViewport(width || 760, height || 560));
      })
      .then(() => {
        if (cancelled) return undefined;
        return rendition.display(latestCfi ?? progress?.current_cfi ?? progress?.cfi ?? undefined).then(() => {
          const current = rendition.currentLocation() as { start?: { cfi: string } } | undefined;
          if (current?.start?.cfi) {
            syncLocation(current.start.cfi);
          }
        });
      })
      .catch((error: unknown) => {
        if (!cancelled) setLoadError(error instanceof Error ? error.message : 'EPUB을 불러오지 못했습니다.');
      });

    rendition.on('relocated', (location: { start: { cfi: string } }) => {
      syncLocation(location.start.cfi);
    });

    return () => {
      cancelled = true;
      // 디바운스 타이머가 아직 안 끝난 상태로 책을 나가거나 바꾸면 마지막 위치
      // 저장이 유실될 수 있어 여기서 한 번 더 확실히 저장한다.
      if (flushTimerRef.current !== null) {
        window.clearTimeout(flushTimerRef.current);
        flushTimerRef.current = null;
        const current = rendition.currentLocation() as { start?: { cfi: string } } | undefined;
        if (current?.start?.cfi) {
          const pagination = reportPage(current.start.cfi);
          if (pagination) flushProgress(current.start.cfi, pagination);
        }
      }
      rendition.destroy();
      book.destroy();
      renditionRef.current = null;
      bookRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookId, paginationRevision, progressLoading]);

  useEffect(() => {
    if (!locationsReady || requestedPage === null || !renditionRef.current || !bookRef.current) return;
    const locations = bookRef.current.locations as unknown as LocationsWithTotal;
    const target = Math.max(0, Math.min(requestedPage - 1, locations.total));
    const cfi = locations.cfiFromLocation(target);
    requestPage(null);
    if (cfi) void renditionRef.current.display(cfi);
  }, [locationsReady, requestPage, requestedPage]);

  return (
    <div className="mx-auto flex h-full max-w-[980px] flex-col">
      <ReaderToolbar currentPage={currentPage} totalPages={totalPages} locationsReady={locationsReady} />
      <section className="relative min-h-0 flex-1 rounded-[18px] border border-slate-200 bg-white px-5 py-6 shadow-[0_10px_24px_rgba(15,23,42,0.04)] sm:px-10 lg:px-14">
        {loadError ? (
          <div className="grid h-full place-items-center text-center">
            <p className="max-w-md rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-600">
              {loadError}
            </p>
          </div>
        ) : (
          <div ref={containerRef} className="h-full w-full overflow-hidden" />
        )}
      </section>
      <div className="mt-4 flex items-center justify-between">
        <button
          type="button"
          onClick={() => renditionRef.current?.prev()}
          className="grid h-11 w-11 place-items-center rounded-full border border-slate-300 bg-white text-xl font-bold text-accent shadow-[0_8px_18px_rgba(15,23,42,0.08)] transition hover:border-accent hover:bg-indigo-50"
          aria-label="이전 페이지"
        >
          ‹
        </button>
        <div className="text-xs font-bold text-slate-400">EPUB pagination</div>
        <button
          type="button"
          onClick={() => renditionRef.current?.next()}
          className="grid h-11 w-11 place-items-center rounded-full border border-slate-300 bg-white text-xl font-bold text-accent shadow-[0_8px_18px_rgba(15,23,42,0.08)] transition hover:border-accent hover:bg-indigo-50"
          aria-label="다음 페이지"
        >
          ›
        </button>
      </div>
    </div>
  );
}
