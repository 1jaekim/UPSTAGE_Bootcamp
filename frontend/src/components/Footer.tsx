// ── 푸터 (F1): 진행바 + 읽기 위치 ────────────────
import { BOOK_ID } from '../lib/constants';
import { useBook } from '../api/hooks';
import { useSpoStore } from '../store';

export function Footer() {
  const { data: book } = useBook(BOOK_ID);
  const readingOffset = useSpoStore((s) => s.readingOffset);
  const spoilerBoundary = useSpoStore((s) => s.spoilerBoundary);

  const total = book?.total_offset ?? 430;
  const pct = Math.round((readingOffset / total) * 100);
  const boundaryPct = Math.round((spoilerBoundary / total) * 100);

  return (
    <footer className="border-t border-slate-200 bg-white px-4 py-3 sm:px-6">
      {/* 진행바: 읽은 위치 + 분석 완료 지점 마커 */}
      <div className="relative mb-2 h-2 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-accent transition-all"
          style={{ width: `${pct}%` }}
        />
        <div
          className="absolute top-1/2 h-4 w-0.5 -translate-y-1/2 bg-safe"
          style={{ left: `${boundaryPct}%` }}
          title="분석 완료 지점"
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 text-[11px] text-slate-500">
        <span>
          현재 위치 <strong className="text-slate-700">{pct}%</strong>
        </span>
        <span>
          읽은 정도 <strong className="text-slate-700">{pct}%</strong>
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-full bg-safe" />
          분석 완료 <strong className="text-slate-700">{boundaryPct}%</strong>
        </span>
      </div>
    </footer>
  );
}
