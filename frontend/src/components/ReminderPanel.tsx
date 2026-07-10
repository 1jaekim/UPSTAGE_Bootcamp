import { useReminders } from '../api/hooks';
import { useSpoStore } from '../store';

export function ReminderPanel() {
  const bookId = useSpoStore((s) => s.selectedBookId);
  const spoilerBoundary = useSpoStore((s) => s.spoilerBoundary);
  const { data, isLoading, isError } = useReminders(bookId, spoilerBoundary);

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-xs font-semibold leading-5 text-blue-700">
        현재 offset까지의 사건만 요약합니다. 이후 내용은 spoiler boundary 밖에 남겨둡니다.
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((index) => (
            <div key={index} className="h-16 animate-pulse rounded-xl bg-slate-100" />
          ))}
        </div>
      ) : null}

      {isError ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm font-semibold text-rose-600">
          요약을 불러오지 못했습니다.
        </div>
      ) : null}

      {data && data.lines.length === 0 ? (
        <div className="grid min-h-[280px] place-items-center rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 text-center text-sm font-semibold text-slate-400">
          아직 정리할 사건이 없습니다.
        </div>
      ) : null}

      {data && data.lines.length > 0 ? (
        <ol className="grid gap-3">
          {data.lines.map((line, index) => (
            <li key={`${line.text}-${index}`} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mb-2 text-xs font-bold text-accent">Reminder {index + 1}</div>
              <p className="text-sm leading-6 text-slate-700">{line.text}</p>
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}
