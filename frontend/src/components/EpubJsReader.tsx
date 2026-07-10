import { useEffect, useRef, useState } from 'react';
import ePub, { type Book, type Rendition } from 'epubjs';
import { bookFileUrl } from '../api/client';
import { useProgress, usePutProgress } from '../api/hooks';
import { useSpoStore } from '../store';
import { ReaderToolbar } from './ReaderToolbar';

const PAGES_PER_UPDATE = 10;
const CHARS_PER_LOCATION = 1000;

type LocationsWithTotal = {
  locationFromCfi: (cfi: string) => number;
  total: number;
};

export function EpubJsReader() {
  const bookId = useSpoStore((s) => s.selectedBookId);
  const setProgress = useSpoStore((s) => s.setProgress);
  const setPage = useSpoStore((s) => s.setPage);
  const setLatestCfi = useSpoStore((s) => s.setLatestCfi);
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
    if (!containerRef.current || progressLoading) return;
    setLoadError(null);
    setLocationsReady(false);
    pageCountRef.current = 0;

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
        setPage(locationIndex + 1, totalLocationCount + 1);
      }
    };

    book.ready
      .then(() => book.locations.generate(CHARS_PER_LOCATION))
      .then(() => {
        if (cancelled) return undefined;
        setLocationsReady(true);
        return rendition.display(progress?.cfi ?? undefined).then(() => {
          const current = rendition.currentLocation() as { start?: { cfi: string } } | undefined;
          if (current?.start?.cfi) {
            reportPage(current.start.cfi);
            setLatestCfi(current.start.cfi);
          }
        });
      })
      .catch((error: unknown) => {
        if (!cancelled) setLoadError(error instanceof Error ? error.message : 'EPUB을 불러오지 못했습니다.');
      });

    rendition.on('relocated', (location: { start: { cfi: string } }) => {
      reportPage(location.start.cfi);
      setLatestCfi(location.start.cfi);
      pageCountRef.current += 1;

      if (pageCountRef.current % PAGES_PER_UPDATE === 0) {
        putProgress.mutate(
          { cfi: location.start.cfi },
          {
            onSuccess: (progressByGlobalIndex) =>
              setProgress(
                progressByGlobalIndex.reading_offset,
                progressByGlobalIndex.spoiler_boundary,
              ),
          },
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
