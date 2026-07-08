// ── 안심 모드 토글 (spoilerSafe) ──────────────────────────────
import { useSpoStore } from '../store';

export function SpoilerModeToggle() {
  const spoilerSafe = useSpoStore((s) => s.spoilerSafe);
  const setSpoilerSafe = useSpoStore((s) => s.setSpoilerSafe);

  return (
    <button
      type="button"
      role="switch"
      aria-checked={spoilerSafe}
      onClick={() => setSpoilerSafe(!spoilerSafe)}
      className="group flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium shadow-sm transition hover:border-slate-300"
      title={spoilerSafe ? '안심 모드 ON — 경계선 뒤는 숨김' : '안심 모드 OFF — 전체 공개(reveal_all)'}
    >
      <span
        className={`inline-flex h-4 w-4 items-center justify-center rounded-full transition ${
          spoilerSafe ? 'bg-safe' : 'bg-slate-300'
        }`}
        aria-hidden
      >
        <span className="h-1.5 w-1.5 rounded-full bg-white" />
      </span>
      <span className={spoilerSafe ? 'text-slate-700' : 'text-slate-400'}>
        안심 모드 {spoilerSafe ? 'ON' : 'OFF'}
      </span>
    </button>
  );
}
