type ReaderToolbarProps = {
  currentPage: number;
  totalPages: number;
  locationsReady: boolean;
};

export function ReaderToolbar({ currentPage, totalPages, locationsReady }: ReaderToolbarProps) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <div>
        <h1 className="text-base font-extrabold text-slate-900">Reader</h1>
        <p className="text-xs font-semibold text-slate-400">EPUB Reader · offset 기반 데이터 로딩</p>
      </div>
      <div className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-500 shadow-sm">
        {!locationsReady ? '페이지 계산 중' : totalPages > 0 ? `${currentPage} / ${totalPages}` : '준비 중'}
      </div>
    </div>
  );
}
