// ── 리마인드 패널 (F3): 경계선까지의 요약 라인 ─────────────────
import { BOOK_ID } from '../lib/constants';
import { useReminders } from '../api/hooks';
import { useSpoStore } from '../store';
import { SlideOverPanel } from './SlideOverPanel';

export function ReminderPanel() {
  const spoilerBoundary = useSpoStore((s) => s.spoilerBoundary);
  const { data, isLoading, isError } = useReminders(BOOK_ID, spoilerBoundary);

  const isEmpty = !!data && data.lines.length === 0;

  return (
    <SlideOverPanel title="리마인드" subtitle={`경계선 offset ${spoilerBoundary}까지의 줄거리`}>
      <div className="mb-4 rounded-xl border border-indigo-100 bg-indigo-50/60 px-3 py-2 text-xs leading-5 text-indigo-700">
        읽은 지점까지의 핵심만 다시 짚어드려요. 스포일러는 포함하지 않습니다.
      </div>

      {isLoading && (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-14 animate-pulse rounded-xl bg-slate-100" />
          ))}
        </div>
      )}

      {isError && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-600">
          리마인드를 불러오지 못했어요.
        </div>
      )}

      {isEmpty && (
        <div className="grid place-items-center rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-12 text-center">
          <div className="mb-2 text-3xl" aria-hidden>📖</div>
          <p className="text-sm font-medium text-slate-600">아직 정리할 내용이 없어요.</p>
          <p className="mt-1 text-xs text-slate-400">조금 더 읽으면 줄거리를 요약해 드립니다.</p>
        </div>
      )}

      {data && !isEmpty && (
        <ol className="space-y-2">
          {data.lines.map((line, i) => (
            <li
              key={i}
              className="flex gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm"
            >
              <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-accent/10 text-xs font-bold text-accent">
                {i + 1}
              </span>
              <p className="text-sm leading-6 text-slate-700">{line.text}</p>
            </li>
          ))}
        </ol>
      )}
    </SlideOverPanel>
  );
}
