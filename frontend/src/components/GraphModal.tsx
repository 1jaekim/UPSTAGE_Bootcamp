import type { ReactNode } from 'react';

export function GraphModal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/40 p-4 backdrop-blur-sm" role="dialog" aria-modal="true">
      <div className="grid h-[min(760px,88vh)] w-[min(1180px,96vw)] grid-rows-[60px_minmax(0,1fr)] overflow-hidden rounded-[18px] border border-slate-200 bg-white shadow-2xl">
        <header className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-5">
          <h2 className="text-base font-extrabold text-slate-900">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 bg-white text-xl leading-none text-slate-500 transition hover:border-slate-300 hover:text-slate-800"
            aria-label="관계도 닫기"
          >
            ×
          </button>
        </header>
        {children}
      </div>
    </div>
  );
}
